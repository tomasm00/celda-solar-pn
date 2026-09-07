"""
La celda por sectores: defectos localizados y su propagación a la curva global.

Los 64 sectores no son 64 celdas independientes. Están conectados en paralelo,
compartiendo el mismo emisor por arriba y el mismo contacto de aluminio por
abajo, así que todos operan al **mismo voltaje de terminal**. Para cada voltaje
del barrido, cada sector entrega la corriente que le corresponde con su propia
fotocorriente local y su propia resistencia serie local, y la curva global es la
suma ponderada por área (decisión D-10).

De ahí emerge sola la asimetría que el enunciado pide explicar:

  Un defecto de colección —una región de bajo tiempo de vida— reduce la
  fotocorriente de esos sectores, así que la corriente de cortocircuito global
  cae aproximadamente en proporción al área dañada.

  Un defecto de resistencia serie —un dedo interrumpido— no reduce cuántos pares
  se generan ni se colectan. Cerca de cortocircuito el voltaje sobre esa
  resistencia es pequeño y el sector entrega casi toda su corriente. Pero al
  acercarse al punto de máxima potencia el sector se ahoga, y lo que se
  deteriora es el factor de forma.

Simplificación de cálculo, exacta y no aproximada: la probabilidad de colección
no depende del color, así que la fotocorriente de un sector puede escribirse
integrando primero la generación sobre todo el espectro y ponderando después por
la colección. Es literalmente la forma que el enunciado prescribe para J_L, y
reduce el trabajo de cincuenta millones de operaciones a cincuenta mil.
"""

from dataclasses import dataclass, field

import numpy as np

import constants as C
from physics.collection import probabilidad_coleccion
from physics.front_grid import malla
from physics.quantum_efficiency import transporte_de_sector
from units import voltaje_termico

ITERACIONES_BISECCION = 60


@dataclass(frozen=True)
class Defectos:
    """Defectos localizados que el usuario introduce sobre la malla de sectores."""

    # Region de bajo tiempo de vida (contaminacion metalica)
    contaminacion_activa: bool = False
    fila_0: int = 2
    fila_1: int = 4
    columna_0: int = 2
    columna_1: int = 4
    factor_tau: float = 0.02       # el tiempo de vida local se multiplica por esto

    # Dedo de plata interrumpido
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
    r_s: np.ndarray              # (n, n) resistencia serie local, ohm*cm2
    tau_n_s: np.ndarray          # (n, n) tiempo de vida local
    con_contaminacion: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))
    con_dedo_roto: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), bool))

    @property
    def area_por_sector(self):
        return 1.0 / (self.n * self.n)


def generacion_integrada(campo):
    """
    Generación total en función de la profundidad, ya integrada sobre el espectro.

    Es la G_tot(x) que el enunciado nombra explícitamente. Unidad: pares/(cm3·s).
    """
    return np.trapezoid(campo.G, campo.lambda_nm, axis=1)


def fotocorriente_de_perfil(x_cm, g_tot, fc):
    """
    Fotocorriente a partir de la generación total ponderada por la colección.

    J_L = q · ∫ G_tot(x) · f_c(x) dx   (forma que prescribe el enunciado)
    """
    return C.Q * float(np.trapezoid(g_tot * fc, x_cm))


def armar_celda(campo, union, W_cm, tr, sectores, defectos: Defectos,
                n_dedos, ancho_dedo_cm, rs_base):
    """
    Resuelve la fotocorriente y la resistencia serie de cada sector.

    El defecto de contaminación entra bajando el tiempo de vida local, lo que
    acorta la longitud de difusión y hunde la colección de ese sector. El dedo
    interrumpido entra por la otra vía: los sectores que dependían de él tienen
    que mandar su corriente al dedo siguiente, así que ven la separación entre
    dedos duplicada.
    """
    n = sectores.n
    g_tot = generacion_integrada(campo)

    contaminados = defectos.mascara_contaminacion(n)
    tau_local = np.where(contaminados, sectores.tau_n_s * defectos.factor_tau,
                         sectores.tau_n_s)

    j_l = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            tr_local = transporte_de_sector(tr, tau_local[i, j], sectores.s_f[i, j])
            fc = probabilidad_coleccion(campo.x_cm, union, W_cm, tr_local)
            j_l[i, j] = fotocorriente_de_perfil(campo.x_cm, g_tot, fc)

    # Resistencia serie. Al interrumpirse los dedos que sirven a una columna de
    # sectores, la corriente de esa franja tiene que alcanzar el siguiente dedo
    # intacto, varias separaciones mas alla. Como la resistencia del emisor crece
    # con el cuadrado de esa distancia, el efecto es severo.
    malla_sana = malla(n_dedos, ancho_dedo_cm)
    dedos_por_columna = max(n_dedos / n, 1.0)
    malla_rota = malla(n_dedos, ancho_dedo_cm,
                       factor_separacion=dedos_por_columna + 1.0)
    rotos = defectos.mascara_dedo_roto(n)
    r_s = np.where(rotos, rs_base + malla_rota.r_serie, rs_base + malla_sana.r_serie)

    # El sombreado no cambia: el metal roto sigue ahi tapando la luz, solo dejo de
    # conducir. Se aplica por igual a todos los sectores.
    j_l = j_l * (1.0 - malla_sana.fraccion_sombra)

    return CeldaPorSectores(n=n, j_l=j_l, r_s=r_s, tau_n_s=tau_local,
                            con_contaminacion=contaminados, con_dedo_roto=rotos)


def _corriente_vectorizada(v, j_l, r_s, j0, r_p, n_idealidad, t_k):
    """
    Corriente que entrega cada sector a un voltaje de terminal dado.

    Se resuelve sobre el voltaje que ve la juntura, no sobre la corriente. Ese
    cambio de variable deja el problema en un intervalo acotado —la juntura ve
    entre el voltaje de terminal y ese voltaje más la caída máxima posible— y
    permite biseccionar de forma vectorizada sobre los 64 sectores a la vez, sin
    riesgo de divergencia.
    """
    vt_n = n_idealidad * voltaje_termico(t_k)

    sin_resistencia = r_s <= 0
    resultado = np.empty_like(j_l)

    if np.any(sin_resistencia):
        expo = np.clip(v / vt_n, -600, 600)
        resultado[sin_resistencia] = (
            j_l[sin_resistencia] - j0 * (np.exp(expo) - 1.0) - v / r_p)

    con = ~sin_resistencia
    if np.any(con):
        jl_c, rs_c = j_l[con], r_s[con]
        bajo = np.full(jl_c.shape, v)
        alto = v + rs_c * np.maximum(jl_c, 1e-9) * 1.5 + 1e-6

        for _ in range(ITERACIONES_BISECCION):
            medio = 0.5 * (bajo + alto)
            expo = np.clip(medio / vt_n, -600, 600)
            g = (medio - v) / rs_c + j0 * (np.exp(expo) - 1.0) + medio / r_p - jl_c
            negativo = g < 0
            bajo = np.where(negativo, medio, bajo)
            alto = np.where(negativo, alto, medio)

        v_juntura = 0.5 * (bajo + alto)
        resultado[con] = (v_juntura - v) / rs_c

    return resultado


def curva_global(celda: CeldaPorSectores, j0, r_p, n_idealidad, t_k,
                 v_max, n_puntos=220):
    """
    Curva corriente-voltaje del conjunto: la suma ponderada por área de los 64
    sectores, todos al mismo voltaje de terminal.
    """
    v = np.linspace(0.0, v_max, n_puntos)
    j_total = np.empty(n_puntos)
    for k, vv in enumerate(v):
        j_sectores = _corriente_vectorizada(vv, celda.j_l, celda.r_s, j0, r_p,
                                            n_idealidad, t_k)
        j_total[k] = float(np.mean(j_sectores))
    return v, j_total


def parametros_de_curva(v, j, irradiancia_w_cm2):
    """Extrae los cuatro parámetros de una curva ya resuelta."""
    j_sc = float(j[0])
    positivos = j > 0
    if np.any(~positivos):
        k = int(np.argmax(~positivos))
        v_oc = float(np.interp(0.0, [j[k], j[k - 1]], [v[k], v[k - 1]]))
    else:
        v_oc = float(v[-1])

    p = v * j
    i = int(np.argmax(p))
    p_max = float(p[i])
    ff = p_max / (v_oc * j_sc) if v_oc * j_sc > 0 else 0.0
    return {
        "j_sc": j_sc, "v_oc": v_oc, "ff": ff, "p_max": p_max,
        "v_mpp": float(v[i]), "j_mpp": float(j[i]),
        "eficiencia": p_max / irradiancia_w_cm2,
    }
