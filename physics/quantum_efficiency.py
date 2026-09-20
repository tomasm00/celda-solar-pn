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
from physics.collection import (Destinos, Transporte, colecciones_por_sector,
                                probabilidad_coleccion, probabilidades_de_destino)
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


def absorbida_en_silicio(campo):
    """
    Fraccion de los fotones incidentes que el silicio realmente absorbe.

    Es la integral del perfil de generación dividida por el flujo que llega, así
    que cuenta todo lo que el perfil cuenta: sin reflector vale (1 − R)(1 − e^{−αW}),
    y con reflector suma la luz que vuelve del aluminio en todos sus rebotes. Usar
    la fórmula de una sola pasada con el reflector activo dejaba afuera esa luz y la
    eficiencia por fotón absorbido superaba el 100 % en el infrarrojo (D-43).
    """
    return np.trapezoid(campo.G, campo.x_cm, axis=0) / campo.Nph


def iqe_referida_a_absorcion(campo, eqe):
    """
    Eficiencia cuantica por foton **absorbido**, no por foton que entro.

    El enunciado y la Unidad 3 definen IQE = EQE/(1-R), que descuenta solo la
    reflexion frontal. Esa definicion mezcla dos perdidas distintas cuando la
    luz atraviesa la celda: en el infrarrojo, la mayor parte de lo que le falta
    para llegar a 1 no es recombinacion sino **absorcion incompleta**.

    Esta segunda curva divide por lo realmente absorbido en el silicio —con el
    reflector, contando la luz que vuelve—, asi que aisla la calidad de coleccion
    y nunca supera 1. Se muestra junto a la del enunciado, no en su lugar (ver D-24
    y D-43).
    """
    a = absorbida_en_silicio(campo)
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

# Largo de correlación de la variación de fabricación, en sectores. Con la grilla de
# 8 × 8 sobre una oblea de 15,6 cm, 1,2 sectores son unos 2,3 cm: las zonas buenas y
# malas abarcan varios sectores vecinos, como en un mapa de vida media real, en lugar
# de alternar al azar de un sector al siguiente. Parámetro de diseño (D-41).
LARGO_CORRELACION_SECTORES = 1.2


@dataclass
class Sectores:
    """
    Malla de sectores de la celda, cada uno con su propia calidad local.

    Una oblea real no es homogénea: el tiempo de vida y la pasivación superficial
    varían de un punto a otro por el proceso de fabricación, y varían de forma
    suave, porque sus causas —la historia térmica del lingote, la uniformidad del
    horno de difusión— actúan sobre regiones extensas. El enunciado exige que cada
    sector tenga su propio τ local y su propia S_frontal local.
    """

    n: int
    tau_n_s: np.ndarray      # (n, n) tiempo de vida local en la base
    s_f: np.ndarray          # (n, n) recombinación superficial frontal local
    dispersion: float

    @property
    def area_por_sector(self) -> float:
        return 1.0 / (self.n * self.n)


def campo_correlacionado(n, largo, rng):
    """
    Campo aleatorio suave sobre la grilla, con media cero y desviación uno.

    Se sortea un valor independiente por sector y se suaviza promediando cada
    sector con sus vecinos, con un peso que cae como una campana de ancho `largo`.
    El resultado conserva el azar pero lo agrupa: sectores cercanos se parecen.
    Se normaliza para que la variación sea exactamente la que pide el control.
    """
    ruido = rng.normal(size=(n, n))
    k = int(np.ceil(3.0 * largo))
    ejes = np.arange(-k, k + 1)
    nucleo = np.exp(-(ejes[:, None] ** 2 + ejes[None, :] ** 2) / (2.0 * largo ** 2))
    relleno = np.pad(ruido, k, mode="reflect")
    suave = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            suave[i, j] = np.sum(relleno[i:i + 2 * k + 1, j:j + 2 * k + 1] * nucleo)
    suave = suave - suave.mean()
    desviacion = suave.std()
    return suave / desviacion if desviacion > 0 else suave


def generar_sectores(n, tau_n_s, s_f, dispersion=0.25, semilla=20260907):
    """
    Genera la malla de sectores.

    `dispersion` es la desviación del logaritmo de cada magnitud entre sectores: 0
    deja la celda perfectamente homogénea; 0,25 produce sectores entre unas 0,6 y
    1,6 veces el valor nominal. La variación es multiplicativa porque las vidas
    medias y las velocidades de recombinación varían en factores, no en sumas.

    El valor nominal del control es la media geométrica de los sectores: la
    semilla sigue describiendo la celda, y los sectores se reparten a su alrededor.
    El tiempo de vida y la pasivación frontal se sortean de forma independiente,
    porque uno es un defecto del volumen y la otra de la superficie. La semilla del
    sorteo es fija, así que el mapa es el mismo en todas las pestañas y ejecuciones.
    """
    if dispersion <= 0:
        return Sectores(n=n, tau_n_s=np.full((n, n), tau_n_s),
                        s_f=np.full((n, n), s_f), dispersion=0.0)
    rng = np.random.default_rng(semilla)
    campo_tau = campo_correlacionado(n, LARGO_CORRELACION_SECTORES, rng)
    campo_sf = campo_correlacionado(n, LARGO_CORRELACION_SECTORES, rng)
    tau = tau_n_s * np.exp(dispersion * campo_tau)
    sf = s_f * np.exp(dispersion * campo_sf)
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
    locales = colecciones_por_sector(campo.x_cm, union, W_cm, tr,
                                     sectores.tau_n_s, sectores.s_f)
    # Todos los sectores tienen la misma área, así que el promedio por área es la
    # media aritmética. Si algún día dejan de tenerla, aquí va el peso.
    return locales.mean(axis=0), locales.reshape(n, n, -1)


def destinos_de_celda(campo, union, W_cm, tr, sectores) -> Destinos:
    """
    Las tres probabilidades de destino de LA celda, promediadas por área.

    Es la misma idea que `coleccion_de_celda`, extendida a los otros dos destinos:
    cada probabilidad es lineal en la cantidad de pares, así que el promedio por
    área de los sectores es exactamente la probabilidad de la celda completa. Con
    dispersión cero todos los sectores son idénticos y se recupera el caso
    homogéneo sin ninguna diferencia.

    La Pestaña 1 usa esto en lugar del perfil nominal, para describir la misma
    celda que las Pestañas 2, 3 y 4 (ver D-28).
    """
    n = sectores.n
    fc = np.zeros(len(campo.x_cm))
    p_sup = np.zeros_like(fc)
    p_vol = np.zeros_like(fc)
    for i in range(n):
        for j in range(n):
            tr_local = transporte_de_sector(tr, sectores.tau_n_s[i, j], sectores.s_f[i, j])
            d = probabilidades_de_destino(campo.x_cm, union, W_cm, tr_local)
            fc += d.fc
            p_sup += d.p_superficie
            p_vol += d.p_volumen
    k = n * n
    return Destinos(fc=fc / k, p_superficie=p_sup / k, p_volumen=p_vol / k)


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
