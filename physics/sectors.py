"""
La celda por sectores: defectos localizados y su propagación a la curva global.

Los 64 sectores no son 64 celdas independientes. Están conectados en paralelo,
compartiendo el mismo emisor por arriba y el mismo contacto de aluminio por
abajo, así que todos operan al **mismo voltaje de terminal**. Para cada voltaje
del barrido, cada sector entrega —o consume— la corriente que le corresponde con
su propia fotocorriente, su propia corriente de saturación y su propia
resistencia serie, y la curva global es la suma ponderada por área (D-10).

Un sector con poca fotocorriente tiene un voltaje de circuito abierto local más
bajo que el del conjunto. Por encima de ese voltaje **consume** corriente: su
diodo conduce en directa alimentado por los sectores sanos. Eso no requiere
ruptura inversa ni acoplamiento lateral; es la consecuencia directa de estar en
paralelo. El solver tiene que permitirlo (ver D-18).

Simplificación de cálculo, exacta y no aproximada: la probabilidad de colección
no depende del color, así que la fotocorriente de un sector puede escribirse
integrando primero la generación sobre todo el espectro y ponderando después por
la colección. Es la forma que el enunciado prescribe para J_L.
"""

from dataclasses import dataclass, field

import numpy as np

import constants as C
from physics.collection import probabilidad_coleccion
from physics.diode import corriente_saturacion
from physics.front_grid import malla
from physics.quantum_efficiency import transporte_de_sector
from units import voltaje_termico

ITERACIONES_BISECCION = 80
EXPANSIONES_MAXIMAS = 60


@dataclass(frozen=True)
class Defectos:
    """Defectos localizados que el usuario introduce sobre la malla de sectores."""

    contaminacion_activa: bool = False
    fila_0: int = 2
    fila_1: int = 4
    columna_0: int = 2
    columna_1: int = 4
    factor_tau: float = 0.02

    dedo_roto_activo: bool = False
    columna_dedo: int = 6

    def mascara_contaminacion(self, n):
        m = np.zeros((n, n), dtype=bool)
        if self.contaminacion_activa:
            f0, f1 = sorted((self.fila_0, self.fila_1))
            c0, c1 = sorted((self.columna_0, self.columna_1))
            m[f0:f1 + 1, c0:c1 + 1] = True
        return m

    def mascara_dedo_roto(self, n):
        m = np.zeros((n, n), dtype=bool)
        if self.dedo_roto_activo:
            m[:, self.columna_dedo] = True
        return m


@dataclass
class CeldaPorSectores:
    n: int
    j_l: np.ndarray              # (n, n) fotocorriente local, A/cm2
    j_0: np.ndarray              # (n, n) corriente de saturacion local, A/cm2
    r_s: np.ndarray              # (n, n) resistencia serie local, ohm*cm2
    tau_n_s: np.ndarray          # (n, n) tiempo de vida local
    con_contaminacion: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))
    con_dedo_roto: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))

    @property
    def area_por_sector(self):
        return 1.0 / (self.n * self.n)


def generacion_integrada(campo):
    """Generación total en función de la profundidad, integrada sobre el espectro."""
    return np.trapezoid(campo.G, campo.lambda_nm, axis=1)


def fotocorriente_de_perfil(x_cm, g_tot, fc):
    """J_L = q · ∫ G_tot(x) · f_c(x) dx, la forma que prescribe el enunciado."""
    return C.Q * float(np.trapezoid(g_tot * fc, x_cm))


def armar_celda(campo, union, W_cm, tr, sectores, defectos: Defectos,
                n_dedos, ancho_dedo_cm, rs_base, na, nd, t_k):
    """
    Resuelve fotocorriente, corriente de saturación y resistencia serie por sector.

    La contaminación baja el tiempo de vida local, y eso tiene **dos** efectos, no
    uno: acorta la longitud de difusión —y con ella la colección— pero además
    aumenta la recombinación en oscuridad, porque la corriente de saturación de la
    base va como el inverso de la longitud de difusión. Calcular solo el primero
    subestima el daño y falsea el reparto entre corriente y factor de forma
    (ver D-19).
    """
    n = sectores.n
    g_tot = generacion_integrada(campo)

    contaminados = defectos.mascara_contaminacion(n)
    tau_local = np.where(contaminados, sectores.tau_n_s * defectos.factor_tau,
                         sectores.tau_n_s)

    j_l = np.empty((n, n))
    j_0 = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            tr_local = transporte_de_sector(tr, tau_local[i, j], sectores.s_f[i, j])
            fc = probabilidad_coleccion(campo.x_cm, union, W_cm, tr_local)
            j_l[i, j] = fotocorriente_de_perfil(campo.x_cm, g_tot, fc)
            j_0[i, j], _, _ = corriente_saturacion(na, nd, tr_local, t_k,
                                                   union=union, W_cm=W_cm)

    malla_sana = malla(n_dedos, ancho_dedo_cm)
    dedos_por_columna = max(n_dedos / n, 1.0)
    malla_rota = malla(n_dedos, ancho_dedo_cm,
                       factor_separacion=dedos_por_columna + 1.0)
    rotos = defectos.mascara_dedo_roto(n)
    r_s = np.where(rotos, rs_base + malla_rota.r_serie, rs_base + malla_sana.r_serie)

    j_l = j_l * (1.0 - malla_sana.fraccion_sombra)

    return CeldaPorSectores(n=n, j_l=j_l, j_0=j_0, r_s=r_s, tau_n_s=tau_local,
                            con_contaminacion=contaminados, con_dedo_roto=rotos)


def _residuo_juntura(v_j, v, j_l, j_0, r_s, r_p, vt_n):
    """
    Residuo de la ecuación del diodo escrita sobre el voltaje de la juntura.

    Con J = (V_j − V)/R_s, la ecuación queda estrictamente creciente en V_j, lo
    que garantiza raíz única y permite biseccionar de forma vectorizada.
    """
    expo = np.clip(v_j / vt_n, -600.0, 600.0)
    return (v_j - v) / r_s + j_0 * (np.exp(expo) - 1.0) + v_j / r_p - j_l


def _corriente_vectorizada(v, j_l, j_0, r_s, r_p, n_idealidad, t_k):
    """
    Corriente que entrega cada sector a un voltaje de terminal dado.

    El voltaje que ve la juntura **puede quedar por debajo del de terminal**:
    ocurre cuando el sector consume corriente en vez de entregarla, que es lo que
    pasa cuando el voltaje del conjunto supera su circuito abierto local. Por eso
    el intervalo de búsqueda se expande hacia ambos lados hasta encerrar la raíz
    con cambio de signo, en lugar de arrancar en el voltaje de terminal.
    """
    vt_n = n_idealidad * voltaje_termico(t_k)

    sin_resistencia = r_s <= 0
    resultado = np.empty_like(np.asarray(j_l, dtype=float))

    if np.any(sin_resistencia):
        expo = np.clip(v / vt_n, -600.0, 600.0)
        resultado[sin_resistencia] = (
            j_l[sin_resistencia] - j_0[sin_resistencia] * (np.exp(expo) - 1.0) - v / r_p)

    con = ~sin_resistencia
    if not np.any(con):
        return resultado

    jl_c, j0_c, rs_c = j_l[con], j_0[con], r_s[con]
    g = lambda vj: _residuo_juntura(vj, v, jl_c, j0_c, rs_c, r_p, vt_n)

    alto = np.full(jl_c.shape, v + 1e-9)
    paso = np.maximum(rs_c * np.maximum(jl_c, 1e-9), 1e-3)
    for _ in range(EXPANSIONES_MAXIMAS):
        faltan = g(alto) < 0
        if not np.any(faltan):
            break
        alto = np.where(faltan, alto + paso, alto)
        paso = paso * 2.0

    bajo = np.full(jl_c.shape, v - 1e-9)
    paso = np.maximum(rs_c * np.maximum(jl_c, 1e-9), 1e-3)
    for _ in range(EXPANSIONES_MAXIMAS):
        faltan = g(bajo) > 0
        if not np.any(faltan):
            break
        bajo = np.where(faltan, bajo - paso, bajo)
        paso = paso * 2.0

    for _ in range(ITERACIONES_BISECCION):
        medio = 0.5 * (bajo + alto)
        negativo = g(medio) < 0
        bajo = np.where(negativo, medio, bajo)
        alto = np.where(negativo, alto, medio)

    v_juntura = 0.5 * (bajo + alto)
    resultado[con] = (v_juntura - v) / rs_c
    return resultado


def corriente_total(v, celda: CeldaPorSectores, r_p, n_idealidad, t_k):
    """Corriente del conjunto a un voltaje de terminal: promedio ponderado por área."""
    return float(np.mean(_corriente_vectorizada(
        v, celda.j_l, celda.j_0, celda.r_s, r_p, n_idealidad, t_k)))


def voltaje_circuito_abierto(celda: CeldaPorSectores, r_p, n_idealidad, t_k):
    """
    Voltaje al que la corriente neta del conjunto se anula.

    Se busca la raíz de verdad, expandiendo el intervalo hasta encerrarla. Fijar
    un voltaje máximo de antemano y devolver el último punto del barrido produce
    un circuito abierto y un factor de forma inventados cuando la celda opera
    fuera de ese rango, por ejemplo en frío (ver D-18).
    """
    from scipy.optimize import brentq

    f = lambda v: corriente_total(v, celda, r_p, n_idealidad, t_k)
    if f(0.0) <= 0.0:
        return 0.0

    alto = 0.7
    for _ in range(EXPANSIONES_MAXIMAS):
        if f(alto) < 0.0:
            return float(brentq(f, 0.0, alto, xtol=1e-10, maxiter=200))
        alto *= 1.5
    return float(alto)


def curva_global(celda: CeldaPorSectores, r_p, n_idealidad, t_k, n_puntos=220):
    """
    Curva corriente-voltaje del conjunto: la suma ponderada por área de los 64
    sectores, todos al mismo voltaje de terminal.

    El barrido se extiende hasta algo más allá del circuito abierto real, que se
    localiza primero, en lugar de hasta un voltaje fijado a mano.
    """
    v_oc = voltaje_circuito_abierto(celda, r_p, n_idealidad, t_k)
    v = np.linspace(0.0, max(v_oc, 1e-6) * 1.02, n_puntos)
    j = np.array([corriente_total(vv, celda, r_p, n_idealidad, t_k) for vv in v])
    return v, j, v_oc


def parametros_de_curva(v, j, irradiancia_w_cm2, v_oc=None):
    """Extrae los cuatro parámetros. El circuito abierto se recibe ya resuelto."""
    j_sc = float(j[0])
    if v_oc is None:
        cruza = np.where(j <= 0)[0]
        v_oc = (float(np.interp(0.0, [j[cruza[0]], j[cruza[0] - 1]],
                                [v[cruza[0]], v[cruza[0] - 1]]))
                if cruza.size and cruza[0] > 0 else float(v[-1]))

    p = v * j
    i = int(np.argmax(p))
    p_max = float(p[i])
    ff = p_max / (v_oc * j_sc) if v_oc * j_sc > 0 else 0.0
    return {
        "j_sc": j_sc, "v_oc": float(v_oc), "ff": ff, "p_max": p_max,
        "v_mpp": float(v[i]), "j_mpp": float(j[i]),
        "eficiencia": p_max / irradiancia_w_cm2,
    }
