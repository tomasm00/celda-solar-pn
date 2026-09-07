"""
La celda como diodo iluminado: la curva corriente-voltaje.

En oscuridad, la juntura p-n es un diodo: al aplicar voltaje la barrera baja y
la corriente crece exponencialmente (ecuación de Shockley, U3 lámina 13). Bajo
iluminación se suma una corriente constante en sentido contrario, la de los
pares fotogenerados que la juntura separa y los contactos colectan.

El dispositivo real añade dos resistencias parásitas:

  Serie. Cuesta sacar la corriente del dispositivo: parte del voltaje aplicado
  se consume en el camino y la juntura ve menos de lo que marcan los terminales.
  Por eso en la exponencial aparece V - Rs*J y no V a secas.

  Paralelo. Hay caminos de fuga por donde la corriente se escapa sin pasar por
  la carga útil.

La ecuación resultante tiene la corriente en ambos lados y no se puede despejar.
Hay que resolverla numéricamente voltaje por voltaje. El enunciado advierte
explícitamente que graficar la forma explícita ignorando el término Rs*J produce
una curva que se ve correcta y cuyo factor de forma está sistemáticamente
equivocado.

Convención de signos, la del enunciado: la corriente del diodo es positiva en
directa y la fotogenerada entra restando, de modo que en cortocircuito la
corriente sale negativa. Al graficar se invierte el eje, como es costumbre.
"""

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

import constants as C
from physics.material import concentracion_intrinseca
from units import voltaje_termico

# Argumento maximo admitido en la exponencial. np.exp desborda cerca de 709; se
# recorta antes para que la busqueda de raiz pueda explorar sin producir infinitos.
EXPONENTE_MAXIMO = 600.0


def corriente_saturacion(na, nd, tr, t_k):
    """
    Densidad de corriente de saturación inversa, en A/cm2.

    J0 = q·ni²·(Dn/(NA·Ln) + Dp/(ND·Lp))   (U3, lámina 13)

    Es la fuga del diodo en oscuridad: mide qué tan bien construida está la
    juntura. Cada término dice cuántos minoritarios logran cruzar desde un lado;
    sube con la concentración intrínseca y baja con el dopaje.

    Con nuestros parámetros el término de la base domina al del emisor en razón
    1200 a 1, que es lo que acota el error de usar estadística de Boltzmann en un
    emisor degenerado (ver D-05).
    """
    ni = float(concentracion_intrinseca(t_k))
    termino_base = tr.D_n / (na * tr.L_n)
    termino_emisor = tr.D_p / (nd * tr.L_p)
    return C.Q * ni ** 2 * (termino_base + termino_emisor), termino_base, termino_emisor


def _residuo(j, v, j0, jl, rs, rp, vt_n):
    """Lo que debe anularse: la ecuación del diodo escrita como f(J) = 0."""
    v_juntura = v - rs * j
    exponente = np.clip(v_juntura / vt_n, -EXPONENTE_MAXIMO, EXPONENTE_MAXIMO)
    return j - (j0 * (np.exp(exponente) - 1.0) + v_juntura / rp - jl)


def resolver_corriente(v, j0, jl, rs, rp, n_idealidad, t_k):
    """
    Resuelve la corriente para un voltaje dado, buscando la raíz.

    El residuo es estrictamente creciente en J —su derivada vale 1 más dos
    términos positivos—, así que la raíz es única y basta con encerrarla entre
    dos valores de signo opuesto.
    """
    vt_n = n_idealidad * voltaje_termico(t_k)

    j_bajo = -abs(jl) - 1e-6
    j_alto = max(abs(jl), 1e-3)
    intentos = 0
    while _residuo(j_alto, v, j0, jl, rs, rp, vt_n) < 0 and intentos < 80:
        j_alto *= 2.0
        intentos += 1
    while _residuo(j_bajo, v, j0, jl, rs, rp, vt_n) > 0 and intentos < 160:
        j_bajo *= 2.0
        intentos += 1

    return brentq(_residuo, j_bajo, j_alto, args=(v, j0, jl, rs, rp, vt_n),
                  xtol=1e-14, rtol=1e-12, maxiter=200)


@dataclass
class CurvaIV:
    v: np.ndarray            # V
    j: np.ndarray            # A/cm2, positiva en el sentido de la celda que entrega
    p: np.ndarray            # W/cm2
    j_sc: float
    v_oc: float
    ff: float
    p_max: float
    v_mpp: float
    j_mpp: float
    eficiencia: float
    j0: float
    j_l: float


def factor_de_forma_ideal(v_oc, t_k):
    """
    Factor de forma ideal segun la expresion empirica del Anexo B (U4):

        FF0 = [v0 - ln(v0 + 0,72)] / (v0 + 1),  con v0 = Voc/(kB*T/q)

    Es el factor de forma que tendria la celda sin resistencias parasitas y con
    factor de idealidad unitario. Es la referencia de la verificacion V4.
    """
    v0 = v_oc / voltaje_termico(t_k)
    return (v0 - np.log(v0 + 0.72)) / (v0 + 1.0)


def curva_iv(j0, jl, rs, rp, n_idealidad, t_k, irradiancia_w_cm2=None,
             n_puntos=420):
    """
    Resuelve la curva completa y extrae los parámetros de la celda.

    El barrido se hace de 0 hasta algo más allá del voltaje de circuito abierto,
    que se localiza primero para no desperdiciar puntos donde no hay nada que ver.
    """
    p_entrada = irradiancia_w_cm2 or C.IRRADIANCE_1SUN

    # Voltaje de circuito abierto: donde la corriente neta se anula. Se acota con
    # la estimacion analitica sin resistencias y se afina buscando la raiz.
    vt = voltaje_termico(t_k)
    v_oc_estimado = n_idealidad * vt * np.log(max(jl / j0, 1e-30) + 1.0)
    v_oc = brentq(
        lambda v: resolver_corriente(v, j0, jl, rs, rp, n_idealidad, t_k),
        0.0, max(v_oc_estimado * 1.6, 0.05), xtol=1e-12, maxiter=200)

    v = np.linspace(0.0, v_oc * 1.02, n_puntos)
    j_diodo = np.array([resolver_corriente(vv, j0, jl, rs, rp, n_idealidad, t_k)
                        for vv in v])

    # Se invierte el signo para trabajar en el primer cuadrante, como la lamina 20
    # de la Unidad 3: corriente que la celda entrega, positiva.
    j = -j_diodo
    p = v * j

    i_mpp = int(np.argmax(p))
    v_mpp, j_mpp, p_max = _refinar_maximo(v, j, i_mpp, j0, jl, rs, rp,
                                          n_idealidad, t_k)

    j_sc = float(j[0])
    ff = float(p_max / (v_oc * j_sc)) if v_oc * j_sc > 0 else 0.0

    return CurvaIV(
        v=v, j=j, p=p, j_sc=j_sc, v_oc=float(v_oc), ff=ff, p_max=float(p_max),
        v_mpp=float(v_mpp), j_mpp=float(j_mpp),
        eficiencia=float(p_max / p_entrada), j0=float(j0), j_l=float(jl),
    )


def _refinar_maximo(v, j, i_mpp, j0, jl, rs, rp, n_idealidad, t_k):
    """
    Afina el punto de máxima potencia entre los dos vecinos del máximo grueso.

    Sin este refinamiento, la potencia máxima queda subestimada por la resolución
    de la grilla de voltaje, y el factor de forma sale bajo por una razón
    puramente numérica. La verificación V4 exige coincidir con la expresión
    empírica dentro de un 1 %, así que la precisión importa.
    """
    lo = v[max(i_mpp - 1, 0)]
    hi = v[min(i_mpp + 1, len(v) - 1)]
    if hi <= lo:
        return v[i_mpp], j[i_mpp], v[i_mpp] * j[i_mpp]

    finos = np.linspace(lo, hi, 60)
    j_finos = np.array([-resolver_corriente(vv, j0, jl, rs, rp, n_idealidad, t_k)
                        for vv in finos])
    p_finos = finos * j_finos
    k = int(np.argmax(p_finos))
    return finos[k], j_finos[k], p_finos[k]
