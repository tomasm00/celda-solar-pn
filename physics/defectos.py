"""
Fallas localizadas con forma de falla real, y el camino eléctrico que dejan.

Ninguna falla de laboratorio tiene forma de rectángulo. Lo que se ve en una oblea
son grietas que se propagan desde un borde o desde un punto de impacto, manchas de
contaminación de forma orgánica, y —lo más importante— regiones que se apagan no
porque alguien las haya marcado, sino porque se quedaron sin camino hacia la barra
colectora.

Este módulo genera las dos fallas y, sobre todo, **calcula** el camino eléctrico de
cada celda hasta la barra más cercana: por el metal donde el dedo sigue entero,
cruzando el emisor donde no. De ese cálculo salen la resistencia serie local y, sin
dibujarlas, las zonas aisladas (D-48).

La malla es fina —48 × 48 celdas de 3,25 mm de lado— porque con la de 8 × 8 que
exige el enunciado no se puede dibujar una grieta. Cada celda sigue siendo un
problema unidimensional: su lado es diez veces la longitud de difusión de la base,
así que los portadores no alcanzan a cruzar de una celda a la vecina.
"""

import heapq
from dataclasses import dataclass

import numpy as np

import constants as C

FACTOR_TAU_MINIMO = 1e-3         # lo peor que deja la contaminación, a severidad máxima
AREA_MAXIMA_MANCHA = 0.30        # fracción de la celda que cubre la mancha a severidad 1
RESISTENCIA_AISLADO = 1e6        # ohm*cm2: un sector sin camino no entrega ni consume
LARGO_MAXIMO_GRIETA = 2.6        # en lados de la celda, a severidad 1
SEVERIDAD_DE_IMPACTO = 0.5       # desde aquí la grieta nace de un impacto, no de un borde
RAMIFICACION = 0.06              # probabilidad de ramificarse por paso, a severidad 1


@dataclass(frozen=True)
class Defectos:
    """Lo que el usuario introduce: dos fallas, su severidad y el sorteo."""

    grieta_activa: bool = True
    severidad_grieta: float = 0.5
    contaminacion_activa: bool = True
    severidad_contaminacion: float = 0.5
    semilla: int = 7

    @property
    def hay_defectos(self) -> bool:
        return ((self.grieta_activa and self.severidad_grieta > 0) or
                (self.contaminacion_activa and self.severidad_contaminacion > 0))


@dataclass
class MapaDeFallas:
    """Lo que las fallas dejan sobre la malla fina."""

    n: int
    grieta: np.ndarray               # (n, n) celdas partidas por la grieta
    factor_tau: np.ndarray           # (n, n) multiplicador local del tiempo de vida
    r_serie: np.ndarray              # (n, n) resistencia serie local, ohm*cm2
    aislados: np.ndarray             # (n, n) celdas sin camino a la barra colectora
    distancia_cm: np.ndarray         # (n, n) cuánto hay que cruzar por el emisor
    dedos_cortados: int
    dedos_totales: int

    @property
    def area_aislada(self) -> float:
        return float(self.aislados.mean())

    @property
    def area_contaminada(self) -> float:
        return float((self.factor_tau < 0.9).mean())


def promedio_por_bloques(matriz, n_reporte):
    """Promedia la malla fina en la grilla de 8 × 8 con que se reporta."""
    m = np.asarray(matriz, dtype=float)
    k = m.shape[0] // n_reporte
    return m.reshape(n_reporte, k, n_reporte, k).mean(axis=(1, 3))


def campo_fino(campo_grueso, n_fino, largo_fino, rng):
    """
    Lleva el campo de fabricación de 8 × 8 a la malla fina sin cambiarlo.

    El campo fino es el de 8 × 8 más un detalle de promedio cero dentro de cada
    sector, generado con el mismo largo de correlación en centímetros. Así el
    promedio por bloques del campo fino es **exactamente** el campo de 8 × 8 que usa
    la Pestaña 2: las dos pestañas describen la misma celda y ninguna cifra de
    referencia se mueve. Como el largo de correlación, 2,3 cm, es mucho mayor que un
    sector fino, el detalle dentro de cada sector es naturalmente pequeño.
    """
    from physics.quantum_efficiency import campo_correlacionado

    n_grueso = campo_grueso.shape[0]
    k = n_fino // n_grueso
    detalle = campo_correlacionado(n_fino, largo_fino, rng)
    detalle = detalle - np.kron(promedio_por_bloques(detalle, n_grueso), np.ones((k, k)))
    return np.kron(campo_grueso, np.ones((k, k))) + detalle


def generar_sectores_finos(n_fino, tau_n_s, s_f, dispersion, n_reporte=8,
                           semilla=20260907):
    """
    La misma celda de la Pestaña 2, resuelta sobre la malla fina.

    Se sortean primero los dos campos de 8 × 8 —con la misma semilla y en el mismo
    orden que `generar_sectores`, así que salen idénticos— y después el detalle
    interior. El promedio por bloques del campo fino es exactamente el de 8 × 8.
    """
    from physics.quantum_efficiency import (LARGO_CORRELACION_SECTORES, Sectores,
                                            campo_correlacionado)

    if dispersion <= 0:
        return Sectores(n=n_fino, tau_n_s=np.full((n_fino, n_fino), tau_n_s),
                        s_f=np.full((n_fino, n_fino), s_f), dispersion=0.0)

    rng = np.random.default_rng(semilla)
    grueso_tau = campo_correlacionado(n_reporte, LARGO_CORRELACION_SECTORES, rng)
    grueso_sf = campo_correlacionado(n_reporte, LARGO_CORRELACION_SECTORES, rng)
    largo_fino = LARGO_CORRELACION_SECTORES * n_fino / n_reporte
    fino_tau = campo_fino(grueso_tau, n_fino, largo_fino, rng)
    fino_sf = campo_fino(grueso_sf, n_fino, largo_fino, rng)
    return Sectores(n=n_fino, tau_n_s=tau_n_s * np.exp(dispersion * fino_tau),
                    s_f=s_f * np.exp(dispersion * fino_sf), dispersion=dispersion)


def generar_grieta(n, severidad, rng):
    """
    Una grieta que se propaga, no un rectángulo.

    Arranca en un punto del borde y avanza con dirección persistente: en cada paso
    gira un poco al azar. Con cierta probabilidad se ramifica, y la rama avanza con
    un ángulo distinto y la mitad del recorrido que le queda a la principal. La
    severidad controla cuánto avanza y cuánto se ramifica; el trazado concreto sale
    de ahí.
    """
    grieta = np.zeros((n, n), dtype=bool)
    if severidad <= 0:
        return grieta

    largo = int(LARGO_MAXIMO_GRIETA * n * severidad)
    if severidad >= SEVERIDAD_DE_IMPACTO:
        # Impacto: la grieta nace en un punto y sale en varias direcciones, que es
        # lo que deja un golpe. Cuando dos brazos alcanzan bordes distintos, la
        # cuña que queda encerrada se desconecta sola.
        inicio = (rng.uniform(0.2, 0.8) * (n - 1), rng.uniform(0.2, 0.8) * (n - 1))
        primer_angulo = rng.uniform(0.0, 2 * np.pi)
        ramas = [(inicio, primer_angulo + k * 2 * np.pi / 3 + rng.normal(0.0, 0.25), largo)
                 for k in range(3)]
    else:
        borde = rng.integers(0, 4)
        t = rng.uniform(0.15, 0.85) * (n - 1)
        inicio, angulo = {
            0: ((0.0, t), 0.0),
            1: ((n - 1.0, t), np.pi),
            2: ((t, 0.0), 0.5 * np.pi),
            3: ((t, n - 1.0), -0.5 * np.pi),
        }[int(borde)]
        ramas = [(inicio, angulo + rng.normal(0.0, 0.5), largo)]
    while ramas:
        (fila, columna), angulo, pasos = ramas.pop()
        for paso in range(pasos):
            f, c = int(round(fila)), int(round(columna))
            if not (0 <= f < n and 0 <= c < n):
                break
            grieta[f, c] = True
            angulo += rng.normal(0.0, 0.28)
            fila += np.sin(angulo)
            columna += np.cos(angulo)
            if pasos - paso > 6 and rng.random() < RAMIFICACION * severidad:
                giro = rng.choice([-1.0, 1.0]) * rng.uniform(0.6, 1.0)
                ramas.append(((fila, columna), angulo + giro, (pasos - paso) // 2))
    return grieta


def generar_mancha(n, severidad, rng, largo):
    """
    Una mancha de contaminación de forma orgánica.

    Se sortea un campo aleatorio suave y se recorta por encima de un umbral: lo que
    queda tiene bordes irregulares, como una mancha real. La severidad mueve dos
    cosas a la vez, cuánta área cubre y cuánto se degrada el tiempo de vida dentro,
    que es como se comporta una contaminación metálica: primero aparece un núcleo
    muy malo y después se extiende.
    """
    factor = np.ones((n, n))
    if severidad <= 0:
        return factor

    from physics.quantum_efficiency import campo_correlacionado

    campo = campo_correlacionado(n, largo, rng)
    area = AREA_MAXIMA_MANCHA * severidad
    umbral = float(np.quantile(campo, 1.0 - area))
    if campo.max() <= umbral:
        return factor

    hondura = np.clip((campo - umbral) / (campo.max() - umbral), 0.0, 1.0)
    exponente = severidad * np.log10(1.0 / FACTOR_TAU_MINIMO)
    return np.where(campo > umbral, 10.0 ** (-exponente * hondura), 1.0)


def _distancia_a_las_fuentes(fuentes, bloqueadas, paso_cm):
    """
    Distancia por el emisor hasta la fuente más cercana, esquivando la grieta.

    Es un frente que avanza desde todas las celdas con dedo útil a la vez, por los
    ocho vecinos, con el costo geométrico de cada paso. Las celdas partidas por la
    grieta no conducen: el silicio está roto, no solo el metal.
    """
    n = fuentes.shape[0]
    distancia = np.full((n, n), np.inf)
    origen = np.full((n, n), -1, dtype=int)
    cola = []
    for f, c in zip(*np.nonzero(fuentes & ~bloqueadas)):
        distancia[f, c] = 0.0
        origen[f, c] = f * n + c
        cola.append((0.0, int(f), int(c)))
    heapq.heapify(cola)

    vecinos = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
               (-1, -1, np.sqrt(2)), (-1, 1, np.sqrt(2)),
               (1, -1, np.sqrt(2)), (1, 1, np.sqrt(2))]
    while cola:
        d, f, c = heapq.heappop(cola)
        if d > distancia[f, c]:
            continue
        for df, dc, costo in vecinos:
            g, h = f + df, c + dc
            if 0 <= g < n and 0 <= h < n and not bloqueadas[g, h]:
                nueva = d + costo * paso_cm
                if nueva < distancia[g, h] - 1e-12:
                    distancia[g, h] = nueva
                    origen[g, h] = origen[f, c]
                    heapq.heappush(cola, (nueva, g, h))
    return distancia, origen


def caminos_electricos(grieta, n_dedos, ancho_dedo_cm, rs_externa,
                       rho_cuadro=C.RHO_CUADRO_EMISOR):
    """
    Resistencia serie de cada celda, calculada desde su camino a la barra.

    El camino tiene dos tramos. Primero el emisor, que la corriente cruza de lado
    hasta el dedo útil más cercano; su resistencia va con el cuadrado de la
    distancia, porque la corriente se va acumulando por el camino. Después el propio
    dedo, hasta la barra colectora, con la misma dependencia cuadrática y por la
    misma razón.

    Las dos expresiones son las mismas cuya media da la resistencia de la malla sana
    que usan las Pestañas 3 y 4, así que sin grieta este cálculo reproduce ese valor:
    ésa es su calibración.

    Un dedo cortado por la grieta deja de conducir desde el corte hacia el lado sin
    barra. Una celda cuyo dedo quedó aislado tiene que cruzar por el emisor hasta
    otro dedo; si no hay ninguno alcanzable, la celda queda **aislada** y no entrega
    nada. Eso no se dibuja: sale del cálculo.
    """
    n = grieta.shape[0]
    lado = C.LADO_CELDA
    paso = lado / n
    separacion = lado / max(int(n_dedos), 1)

    # Dónde cae cada dedo y cada barra colectora sobre la malla fina
    columnas_dedo = np.unique(np.clip(
        ((np.arange(n_dedos) + 0.5) * separacion / paso).astype(int), 0, n - 1))
    filas_barra = np.unique(np.clip(
        ((np.arange(C.N_BARRAS_COLECTORAS) + 0.5) * lado / C.N_BARRAS_COLECTORAS
         / paso).astype(int), 0, n - 1))

    # Tramo por el dedo: hasta qué barra llega cada trozo de dedo sin cruzar la grieta
    resistencia_dedo = np.full((n, n), np.inf)
    constante_dedo = (C.RHO_PLATA_SERIGRAFIA * separacion
                      / (ancho_dedo_cm * C.ESPESOR_DEDO))
    for columna in columnas_dedo:
        cortado = grieta[:, columna]
        for fila in range(n):
            if cortado[fila]:
                continue
            mejor = np.inf
            for barra in filas_barra:
                lo, hi = (fila, barra) if fila <= barra else (barra, fila)
                if np.any(cortado[lo:hi + 1]):
                    continue
                mejor = min(mejor, abs(barra - fila) * paso)
            if np.isfinite(mejor):
                resistencia_dedo[fila, columna] = constante_dedo * mejor ** 2

    utiles = np.isfinite(resistencia_dedo)
    distancia, origen = _distancia_a_las_fuentes(utiles, grieta, paso)

    # Tramo por el emisor: el cruce hasta el dedo útil, más el reparto dentro de la
    # celda, que es el término de la malla sana.
    dentro = rho_cuadro * separacion ** 2 / 12.0
    r_emisor = rho_cuadro * np.where(np.isfinite(distancia), distancia, 0.0) ** 2 + dentro

    plano = resistencia_dedo.ravel()
    indice = np.where(origen.ravel() >= 0, origen.ravel(), 0)
    r_dedo = np.where(origen.ravel() >= 0, plano[indice], np.inf).reshape(n, n)

    aislados = ~np.isfinite(distancia) | ~np.isfinite(r_dedo) | grieta
    r_serie = np.where(aislados, RESISTENCIA_AISLADO,
                       rs_externa + r_emisor + np.where(np.isfinite(r_dedo), r_dedo, 0.0))
    cortados = int(sum(bool(np.any(grieta[:, c])) for c in columnas_dedo))
    return MapaDeFallas(
        n=n, grieta=grieta, factor_tau=np.ones((n, n)), r_serie=r_serie,
        aislados=aislados, distancia_cm=np.where(np.isfinite(distancia), distancia, np.nan),
        dedos_cortados=cortados, dedos_totales=len(columnas_dedo))


def sin_fallas(n, r_serie):
    """
    Una celda intacta con una resistencia serie uniforme.

    La usan las verificaciones que comparan el motor de sectores en paralelo con el
    de un solo diodo: las dos vías tienen que partir de la misma resistencia para
    que la comparación mida el motor y no la malla.
    """
    ceros = np.zeros((n, n), dtype=bool)
    return MapaDeFallas(
        n=n, grieta=ceros, factor_tau=np.ones((n, n)),
        r_serie=np.full((n, n), float(r_serie)), aislados=ceros,
        distancia_cm=np.zeros((n, n)), dedos_cortados=0, dedos_totales=0)


def mapa_de_fallas(defectos: Defectos, n, n_dedos, ancho_dedo_cm, rs_externa, largo_mancha):
    """Genera las dos fallas y resuelve el camino eléctrico que dejan."""
    rng = np.random.default_rng(defectos.semilla)
    grieta = (generar_grieta(n, defectos.severidad_grieta, rng)
              if defectos.grieta_activa else np.zeros((n, n), dtype=bool))
    mapa = caminos_electricos(grieta, n_dedos, ancho_dedo_cm, rs_externa)
    if defectos.contaminacion_activa:
        mapa.factor_tau = generar_mancha(n, defectos.severidad_contaminacion, rng,
                                         largo_mancha)
    return mapa
