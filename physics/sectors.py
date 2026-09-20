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

from dataclasses import dataclass

import numpy as np

import constants as C
from physics.collection import colecciones_por_sector
from physics.diode import corrientes_saturacion
from units import voltaje_termico

ITERACIONES_NEWTON = 60
EXPANSIONES_MAXIMAS = 60
EXPONENTE_MAXIMO = 600.0
TOLERANCIA_VOLTAJE = 1e-13
TOLERANCIA_CORRIENTE = 1e-12      # A/cm2: una parte en 10^10 de la corriente de la celda


@dataclass
class CeldaPorSectores:
    """La celda resuelta sobre la malla fina, celda por celda."""

    n: int
    j_l: np.ndarray              # (n, n) fotocorriente local, A/cm2
    j_0: np.ndarray              # (n, n) corriente de saturacion local, A/cm2
    r_s: np.ndarray              # (n, n) resistencia serie local, ohm*cm2
    tau_n_s: np.ndarray          # (n, n) tiempo de vida local ya degradado
    fallas: object = None        # MapaDeFallas con la grieta, la mancha y lo aislado

    @property
    def area_por_sector(self):
        return 1.0 / (self.n * self.n)

    @property
    def aislados(self):
        if self.fallas is None:
            return np.zeros((self.n, self.n), dtype=bool)
        return self.fallas.aislados


def generacion_integrada(campo):
    """Generación total en función de la profundidad, integrada sobre el espectro."""
    return np.trapezoid(campo.G, campo.lambda_nm, axis=1)


def _pesos_de_trapecio(x):
    """Pesos con que se integra sobre la profundidad, para hacerlo como producto."""
    h = np.zeros_like(x)
    d = 0.5 * np.diff(x)
    h[:-1] += d
    h[1:] += d
    return h


def fotocorriente_de_perfil(x_cm, g_tot, fc):
    """J_L = q · ∫ G_tot(x) · f_c(x) dx, la forma que prescribe el enunciado."""
    return C.Q * float(np.trapezoid(g_tot * fc, x_cm))


def armar_celda(campo, union, W_cm, tr, sectores, fallas, fraccion_sombra, na, nd, t_k):
    """
    Resuelve fotocorriente, corriente de saturación y resistencia serie por celda.

    La contaminación baja el tiempo de vida local, y eso tiene **dos** efectos, no
    uno: acorta la longitud de difusión —y con ella la colección— pero además
    aumenta la recombinación en oscuridad, porque la corriente de saturación de la
    base va como el inverso de la longitud de difusión. Calcular solo el primero
    subestima el daño y falsea el reparto entre corriente y factor de forma
    (ver D-19).

    La resistencia serie no se impone: la trae el mapa de fallas, que la calculó
    desde el camino de cada celda hasta la barra colectora.
    """
    forma = sectores.tau_n_s.shape
    tau_local = sectores.tau_n_s * fallas.factor_tau
    fc = colecciones_por_sector(campo.x_cm, union, W_cm, tr, tau_local, sectores.s_f)

    g_tot = generacion_integrada(campo)
    pesos = _pesos_de_trapecio(np.asarray(campo.x_cm, dtype=float))
    j_l = C.Q * (fc @ (g_tot * pesos))
    j_l = j_l.reshape(forma) * (1.0 - fraccion_sombra)

    L_n = np.sqrt(tr.D_n * tau_local)
    j_0 = corrientes_saturacion(na, nd, tr, t_k, union, W_cm, L_n, sectores.s_f)

    return CeldaPorSectores(n=forma[0], j_l=j_l, j_0=np.asarray(j_0).reshape(forma),
                            r_s=fallas.r_serie, tau_n_s=tau_local, fallas=fallas)


def _voltaje_de_juntura(v, j_l, j_0, r_s, r_p, vt_n, semilla=None):
    """
    Voltaje que ve la juntura de cada sector, resuelto para todos a la vez.

    El residuo crece siempre con el voltaje de juntura —su derivada es la suma de
    tres términos positivos—, así que la raíz es única y se puede encerrar de
    entrada entre dos valores calculados: por abajo, un voltaje apenas menor que el
    de terminal, donde el sector tendría que estar consumiendo más de lo que genera;
    por arriba, su propio circuito abierto local, donde el diodo ya se come toda su
    fotocorriente. Acotarlo así, y no con la caída sobre la resistencia serie,
    mantiene el intervalo por debajo de un volt incluso cuando un sector quedó
    aislado y su resistencia vale un millón de ohm.

    Dentro se usa Newton con red de seguridad: si el paso se sale del intervalo que
    se va cerrando, se reemplaza por una bisección. La exponencial hace que Newton
    avance despacio cuando se arranca lejos, así que el punto de partida importa:
    con el de la solución anterior del barrido, bastan tres o cuatro pasos.
    """
    jl = np.maximum(j_l, 0.0)
    circuito_abierto_local = vt_n * np.log1p(jl / np.maximum(j_0, 1e-30))
    bajo = np.minimum(v, 0.0) - 1e-3
    alto = np.maximum(v, circuito_abierto_local) + 5.0 * vt_n
    bajo, alto = np.broadcast_arrays(bajo, alto)
    bajo, alto = bajo.astype(float).copy(), alto.astype(float).copy()

    if semilla is None:
        semilla = np.minimum(v + r_s * jl, circuito_abierto_local)
    v_j = np.clip(np.broadcast_to(semilla, bajo.shape).astype(float), bajo, alto)

    for _ in range(ITERACIONES_NEWTON):
        expo = np.clip(v_j / vt_n, -EXPONENTE_MAXIMO, EXPONENTE_MAXIMO)
        exponencial = np.exp(expo)
        residuo = (v_j - v) / r_s + j_0 * (exponencial - 1.0) + v_j / r_p - j_l
        bajo = np.where(residuo < 0.0, v_j, bajo)
        alto = np.where(residuo < 0.0, alto, v_j)
        if np.max(np.abs(residuo)) < TOLERANCIA_CORRIENTE:
            break

        derivada = 1.0 / r_s + j_0 * exponencial / vt_n + 1.0 / r_p
        paso = v_j - residuo / derivada
        fuera = (paso <= bajo) | (paso >= alto) | ~np.isfinite(paso)
        v_j = np.where(fuera, 0.5 * (bajo + alto), paso)
        if np.max(alto - bajo) < TOLERANCIA_VOLTAJE:
            break
    return v_j


def corrientes_por_sector(v, celda: CeldaPorSectores, r_p, n_idealidad, t_k):
    """
    Corriente que entrega cada sector, en A/cm2 de su propia área.

    `v` puede ser un voltaje o un arreglo de voltajes; en ese caso devuelve una
    matriz con un voltaje por fila y un sector por columna. El voltaje de la
    juntura puede quedar por debajo del de terminal: eso ocurre cuando un sector
    dañado consume corriente en vez de entregarla, porque el resto del conjunto lo
    polariza por encima de su propio circuito abierto.
    """
    vt_n = n_idealidad * voltaje_termico(t_k)
    escalar = np.ndim(v) == 0
    voltajes = np.atleast_1d(np.asarray(v, dtype=float))[:, None]

    j_l = celda.j_l.ravel()[None, :]
    j_0 = celda.j_0.ravel()[None, :]
    r_s = celda.r_s.ravel()[None, :]

    sin_resistencia = r_s <= 0
    r_seguro = np.where(sin_resistencia, 1e-12, r_s)

    # Los voltajes se recorren en orden, y cada uno arranca donde terminó el
    # anterior: la solución se mueve poco de un punto al siguiente, así que Newton
    # converge en tres o cuatro pasos en vez de los cuarenta que necesita cuando
    # parte del medio del intervalo.
    j = np.empty((voltajes.shape[0], j_l.shape[1]))
    v_j = None
    for k in range(voltajes.shape[0]):
        v_j = _voltaje_de_juntura(voltajes[k:k + 1], j_l, j_0, r_seguro, r_p, vt_n,
                                  semilla=v_j)
        j[k] = ((v_j - voltajes[k:k + 1]) / r_seguro)[0]

    if np.any(sin_resistencia):
        expo = np.clip(voltajes / vt_n, -EXPONENTE_MAXIMO, EXPONENTE_MAXIMO)
        directa = j_l - j_0 * (np.exp(expo) - 1.0) - voltajes / r_p
        j = np.where(sin_resistencia, directa, j)

    return j[0] if escalar else j


def voltajes_de_juntura(v, celda: CeldaPorSectores, r_p, n_idealidad, t_k):
    """
    Voltaje interno de cada sector a un voltaje de terminal dado, en volts.

    Es lo que decide la electroluminiscencia: un sector emite luz en proporción a
    la exponencial de su voltaje de juntura, así que los sectores que no reciben
    voltaje aparecen negros.
    """
    vt_n = n_idealidad * voltaje_termico(t_k)
    r_s = np.maximum(celda.r_s.ravel()[None, :], 1e-12)
    v_j = _voltaje_de_juntura(float(v), celda.j_l.ravel()[None, :],
                              celda.j_0.ravel()[None, :], r_s, r_p, vt_n)
    return v_j.reshape(celda.j_l.shape)


def corriente_total(v, celda: CeldaPorSectores, r_p, n_idealidad, t_k):
    """Corriente del conjunto a un voltaje de terminal: promedio por área."""
    return float(np.mean(corrientes_por_sector(v, celda, r_p, n_idealidad, t_k)))


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

    # Se parte de la estimación analítica del sector medio, que deja la raíz muy
    # cerca: con eso la búsqueda necesita unas pocas evaluaciones en vez de decenas.
    vt = voltaje_termico(t_k) * n_idealidad
    alto = float(np.clip(vt * np.log(max(celda.j_l.mean() / max(celda.j_0.mean(), 1e-30), 1.0) + 1.0) * 1.15, 0.05, 5.0))
    for _ in range(EXPANSIONES_MAXIMAS):
        if f(alto) < 0.0:
            return float(brentq(f, 0.0, alto, xtol=1e-9, maxiter=100))
        alto *= 1.4
    return float(alto)


def curva_global(celda: CeldaPorSectores, r_p, n_idealidad, t_k, n_puntos=220):
    """
    Curva corriente-voltaje del conjunto: la suma por área de todos los sectores,
    todos al mismo voltaje de terminal.

    El barrido se extiende hasta algo más allá del circuito abierto real, que se
    localiza primero, en lugar de hasta un voltaje fijado a mano. Los 220 voltajes
    se resuelven de una sola vez.
    """
    v_oc = voltaje_circuito_abierto(celda, r_p, n_idealidad, t_k)
    v = np.linspace(0.0, max(v_oc, 1e-6) * 1.02, n_puntos)
    j = corrientes_por_sector(v, celda, r_p, n_idealidad, t_k).mean(axis=1)
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
