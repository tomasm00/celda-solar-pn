"""
Eficiencia cuántica: de cada cien fotones de un color, cuántos producen corriente.

Es el punto de encuentro entre la óptica y la electricidad. Combina dónde nacen
los pares (Pestaña 1) con qué fracción de ellos llega viva a la juntura
(probabilidad de colección) y entrega la respuesta de la celda color por color.

El enunciado escribe la eficiencia cuántica externa como

    EQE(λ) = [1 − R(λ)] · ∫₀^W f_c(x) · α(λ) · e^(−α(λ)x) dx

Aquí se calcula reusando el perfil de generación que ya resolvió el módulo de
óptica, porque ese perfil es exactamente α·Nph·(1−R)·e^(−αx). Dividiendo la
integral de f_c·G por el flujo incidente se recupera la misma expresión, con una
ventaja importante: la óptica de la Pestaña 1 y la electricidad de la Pestaña 3
quedan atadas al mismo cálculo por construcción, que es justo lo que exige la
verificación V3.
"""

from dataclasses import dataclass

import numpy as np

import constants as C
from physics.collection import Transporte, probabilidad_coleccion
from physics.material import longitud_difusion


def eficiencia_cuantica(campo, fc):
    """
    EQE e IQE en función de la longitud de onda.

    EQE es respecto de todos los fotones que llegan a la celda; IQE descuenta los
    que se reflejaron y nunca entraron, así que mide solo la calidad interna del
    dispositivo (U3, lámina 25).
    """
    integrando = campo.G * np.asarray(fc)[:, None]
    eqe = np.trapezoid(integrando, campo.x_cm, axis=0) / campo.Nph
    iqe = np.divide(eqe, 1.0 - campo.R, out=np.zeros_like(eqe),
                    where=(1.0 - campo.R) > 1e-9)
    return eqe, iqe


def eqe_a_una_longitud(campo, fc, indice_lambda):
    """EQE para un solo color. Barato: evita integrar todo el espectro."""
    integrando = campo.G[:, indice_lambda] * np.asarray(fc)
    return float(np.trapezoid(integrando, campo.x_cm) / campo.Nph[indice_lambda])


def corriente_de_cortocircuito(campo, eqe):
    """
    Densidad de corriente que entrega la celda, en A/cm2.

    J = q·∫ Nph(λ)·EQE(λ) dλ  (U3, lámina 26). Cada fotón que la eficiencia
    cuántica cuenta como aprovechado aporta una carga elemental al circuito.

    Ésta es la vía óptica de la verificación V3: en el Hito 5 se comparará contra
    la corriente leída de la curva J-V.
    """
    return float(C.Q * np.trapezoid(campo.Nph * eqe, campo.lambda_nm))


def absorbida_en_silicio(campo, W_cm):
    """
    Fraccion de los fotones incidentes que el silicio realmente absorbe.

        A = (1 - R)(1 - e^{-alpha W})

    Es lo que queda tras descontar lo reflejado en el frente y lo transmitido
    hasta el fondo, en un solo paso.
    """
    return (1.0 - campo.R) * (1.0 - np.exp(-campo.alpha * W_cm))


def iqe_referida_a_absorcion(campo, eqe, W_cm):
    """
    Eficiencia cuantica por foton **absorbido**, no por foton que entro.

    El enunciado y la Unidad 3 definen IQE = EQE/(1-R), que descuenta solo la
    reflexion frontal. Esa definicion mezcla dos perdidas distintas cuando la
    luz atraviesa la celda: en el infrarrojo, la mayor parte de lo que le falta
    para llegar a 1 no es recombinacion sino **absorcion incompleta**.

    Esta segunda curva divide por lo realmente absorbido, asi que aisla la
    calidad de coleccion. Se muestra junto a la del enunciado, no en su lugar
    (ver D-24).
    """
    a = absorbida_en_silicio(campo, W_cm)
    return np.divide(eqe, a, out=np.zeros_like(eqe), where=a > 1e-6)


def cota_superior(campo):
    """
    Cota física que la eficiencia cuántica no puede superar: 1 − R.

    Ningún fotón reflejado puede generar un par. Es la verificación V5.
    """
    return 1.0 - campo.R


# ---------------------------------------------------------------------------
# Grilla de sectores
# ---------------------------------------------------------------------------

@dataclass
class Sectores:
    """
    Malla de sectores de la celda, cada uno con su propia calidad local.

    Una oblea real no es homogénea: el tiempo de vida y la pasivación superficial
    varían de un punto a otro por el proceso de fabricación. Aquí esa variación
    se genera con una distribución log-normal en torno al valor nominal, que es
    la forma habitual de describir dispersiones multiplicativas.
    """

    n: int
    tau_n_s: np.ndarray      # (n, n) tiempo de vida local en la base
    s_f: np.ndarray          # (n, n) recombinación superficial frontal local
    dispersion: float

    @property
    def area_por_sector(self) -> float:
        return 1.0 / (self.n * self.n)


def generar_sectores(n, tau_n_s, s_f, dispersion=0.20, semilla=20260907):
    """
    Genera la malla de sectores.

    `dispersion` es la desviación logarítmica: 0 deja la celda perfectamente
    homogénea, 0,20 produce variaciones típicas de un factor 1,2 arriba y abajo.
    La semilla es fija para que el mapa sea reproducible entre ejecuciones y
    entre pestañas.
    """
    rng = np.random.default_rng(semilla)
    if dispersion <= 0:
        return Sectores(n=n, tau_n_s=np.full((n, n), tau_n_s),
                        s_f=np.full((n, n), s_f), dispersion=0.0)

    tau = tau_n_s * np.exp(rng.normal(0.0, dispersion, (n, n)))
    # La recombinación superficial empeora donde la pasivación es peor: se genera
    # de forma independiente del tiempo de vida, que es un defecto de volumen.
    sf = s_f * np.exp(rng.normal(0.0, dispersion, (n, n)))
    return Sectores(n=n, tau_n_s=tau, s_f=sf, dispersion=dispersion)


def transporte_de_sector(tr: Transporte, tau_n_s, s_f):
    """
    Copia los parámetros de transporte cambiando solo lo que varía por sector.

    La difusividad no cambia: depende de la movilidad y la temperatura, que son
    globales. Lo que varía localmente es el tiempo de vida —y con él la longitud
    de difusión— y la pasivación de la superficie frontal.
    """
    return Transporte(
        D_p=tr.D_p, L_p=tr.L_p, S_f=float(s_f),
        D_n=tr.D_n, L_n=float(longitud_difusion(tr.D_n, tau_n_s)), S_r=tr.S_r,
    )


def coleccion_de_celda(campo, union, W_cm, tr, sectores):
    """
    Probabilidad de colección de LA celda, que es una sola, no sesenta y cuatro.

    La celda no es un conjunto de celdas independientes: es un único dispositivo
    cuya respuesta varía de un punto a otro. Bajo iluminación uniforme, todos los
    sectores reciben el mismo flujo por unidad de área, y la eficiencia cuántica
    es **lineal** en la probabilidad de colección:

        EQE(λ) = (1/Nph) · ∫ G(x,λ) · f_c(x) dx

    Por lo tanto el promedio por área de las eficiencias locales es idéntico a la
    eficiencia calculada con la probabilidad de colección promedio. No es una
    aproximación: es una identidad exacta, y la verificación C-T7 la comprueba.

    De ahí que la forma correcta de obtener la respuesta de la celda sea promediar
    la colección sobre los sectores y calcular una sola curva con ella, en lugar de
    calcular una curva por sector y tratarlas como dispositivos separados.

    Devuelve la colección promedio de la celda y la pila de las locales, que es lo
    que necesitan los mapas.
    """
    n = sectores.n
    locales = np.empty((n * n, len(campo.x_cm)))
    k = 0
    for i in range(n):
        for j in range(n):
            tr_local = transporte_de_sector(tr, sectores.tau_n_s[i, j],
                                            sectores.s_f[i, j])
            locales[k] = probabilidad_coleccion(campo.x_cm, union, W_cm, tr_local)
            k += 1
    # Todos los sectores tienen la misma área, así que el promedio por área es la
    # media aritmética. Si algún día dejan de tenerla, aquí va el peso.
    return locales.mean(axis=0), locales.reshape(n, n, -1)


def mapa_iqe_desde_locales(campo, fc_locales, indice_lambda):
    """
    Mapa de eficiencia interna local a un color, desde colecciones ya resueltas.

    Reutiliza la pila que devolvió `coleccion_de_celda` en vez de volver a resolver
    los sectores. Además de ser mucho más barato, garantiza que el mapa y la curva
    de la celda salgan exactamente de los mismos sectores: si se recalculan por
    separado, nada obliga a que coincidan.
    """
    g = campo.G[:, indice_lambda]
    eqe_local = np.trapezoid(g * np.asarray(fc_locales), campo.x_cm, axis=-1)
    eqe_local = eqe_local / campo.Nph[indice_lambda]
    denominador = max(1.0 - float(campo.R[indice_lambda]), 1e-9)
    return eqe_local / denominador


def mapa_iqe_local(campo, union, W_cm, tr, sectores, indice_lambda):
    """
    Eficiencia cuántica interna local, sector por sector, a un color dado.

    Solo se evalúa la longitud de onda pedida: recorrer todo el espectro en los
    64 sectores costaría cincuenta millones de operaciones y no aporta nada al
    mapa de calor.
    """
    n = sectores.n
    mapa = np.empty((n, n))
    denominador = max(1.0 - float(campo.R[indice_lambda]), 1e-9)

    for i in range(n):
        for j in range(n):
            tr_local = transporte_de_sector(tr, sectores.tau_n_s[i, j],
                                            sectores.s_f[i, j])
            fc = probabilidad_coleccion(campo.x_cm, union, W_cm, tr_local)
            mapa[i, j] = eqe_a_una_longitud(campo, fc, indice_lambda) / denominador

    return mapa


def curvas_por_tiempo_de_vida(campo, union, W_cm, tr, taus_s):
    """
    Familia de curvas de eficiencia cuántica interna para distintos tiempos de
    vida en el volumen.

    Reproduce la figura de la lámina 30 de la Unidad 3: al subir el tiempo de
    vida mejora la respuesta en el rojo, mientras que el azul no se mueve, porque
    el azul se absorbe en el emisor y nunca llega a enterarse de lo que pasa en
    el volumen de la base.
    """
    curvas = {}
    for tau in taus_s:
        tr_local = transporte_de_sector(tr, tau, tr.S_f)
        fc = probabilidad_coleccion(campo.x_cm, union, W_cm, tr_local)
        _, iqe = eficiencia_cuantica(campo, fc)
        curvas[tau] = iqe
    return curvas
