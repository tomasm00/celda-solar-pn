"""
Óptica de la celda: ley de Beer-Lambert y generación de pares electrón-hueco.

Cadena que resuelve este módulo (U2, láminas 32 a 39):

    espectro solar  ->  flujo de fotones que entra al silicio (descontando la
    reflexión en la superficie)  ->  ese flujo se agota exponencialmente con la
    profundidad  ->  la tasa a la que se agota es la tasa de generación de pares.

Convención de profundidad: x = 0 en la superficie frontal iluminada, x creciente
hacia el interior. La juntura está en x_j = d_n. Todo en cm internamente.
"""

from dataclasses import dataclass

import numpy as np

import constants as C
from data.loaders import constantes_opticas_silicio, espectro_am15g

# Puntos de la grilla no uniforme y factor de estiramiento de cada region.
# Ver decision D-03: a 300 nm el silicio absorbe en los primeros 5,6 nm mientras
# la celda mide ~100 um. Una grilla uniforme no resuelve esa region y rompe el
# balance de fotones sin dar ninguna señal de error.
N_PUNTOS_EMISOR = 400
N_PUNTOS_BASE = 400
ESTIRAMIENTO_EMISOR = 8.0
ESTIRAMIENTO_BASE = 6.0


def _tramo_exponencial(x0, x1, n, k):
    """
    Tramo con nodos concentrados cerca de x0 y progresivamente mas separados.

    u recorre [0,1] uniformemente y x = x0 + (x1-x0)*(e^{k u} - 1)/(e^k - 1),
    de modo que el primer paso es ~k/(e^k - 1) veces menor que el uniforme.
    """
    u = np.linspace(0.0, 1.0, n)
    return x0 + (x1 - x0) * np.expm1(k * u) / np.expm1(k)


def grilla_profundidad(d_n_cm, W_p_cm, nodos_extra=()):
    """
    Grilla de profundidad no uniforme sobre toda la celda, en cm.

    Se refina cerca de la superficie frontal (donde muere el azul) y cerca de la
    juntura (donde muere el verde y el rojo temprano). El nodo de la juntura
    aparece exactamente una vez, lo que permite separar limpiamente emisor y base.

    `nodos_extra` fuerza nodos en profundidades concretas. Se usa para los bordes
    de la zona de depleción: ahí la probabilidad de colección tiene un quiebre
    (cambia de rama), y sin un nodo exactamente en el borde la discretización se
    lo salta y el valor unitario que debe tener en el borde no aparece.
    """
    emisor = _tramo_exponencial(0.0, d_n_cm, N_PUNTOS_EMISOR, ESTIRAMIENTO_EMISOR)
    base = _tramo_exponencial(d_n_cm, d_n_cm + W_p_cm, N_PUNTOS_BASE, ESTIRAMIENTO_BASE)
    x = np.concatenate([emisor[:-1], base])

    extras = np.asarray([n for n in nodos_extra if 0.0 < n < d_n_cm + W_p_cm])
    if extras.size:
        x = np.unique(np.concatenate([x, extras]))
    return x


@dataclass
class CampoOptico:
    """Resultado del cálculo óptico sobre la grilla de profundidad y de color."""

    x_cm: np.ndarray            # (nx,)      profundidad
    lambda_nm: np.ndarray       # (nl,)      longitud de onda
    alpha: np.ndarray           # (nl,)      coeficiente de absorción, 1/cm
    R: np.ndarray               # (nl,)      reflectancia frontal
    Nph: np.ndarray             # (nl,)      flujo incidente, 1/(cm2 s nm)
    G: np.ndarray               # (nx, nl)   generación, 1/(cm3 s nm)
    d_n_cm: float
    W_cm: float
    reflector: bool
    reflectancia_fija: float | None = None

    @property
    def R_trasera(self) -> float:
        """Reflectancia del contacto trasero vista desde el silicio."""
        return C.R_CONTACTO_AL if self.reflector else 0.0

    @property
    def indice_juntura(self) -> int:
        return int(np.argmin(np.abs(self.x_cm - self.d_n_cm)))

    def generacion_total(self) -> np.ndarray:
        """Integra la generación sobre todo el espectro. Devuelve G_tot(x) en 1/(cm3 s)."""
        return np.trapezoid(self.G, self.lambda_nm, axis=1)

    def perfil_a(self, lambda_nm: float) -> np.ndarray:
        """Perfil de generación G(x) para el color más cercano al pedido."""
        i = int(np.argmin(np.abs(self.lambda_nm - lambda_nm)))
        return self.G[:, i]


def _factor_de_rebotes(alpha, W_cm, R_frontal, R_trasera):
    """
    Cuánto se multiplica la luz dentro de la celda por los rebotes sucesivos.

    Con reflector, la luz que vuelve del aluminio llega a la cara frontal, y ahí
    una fracción R vuelve a reflejarse hacia adentro —la misma interfaz, vista
    desde el otro lado, refleja lo mismo a incidencia normal—. Ese haz hace otro
    viaje de ida y vuelta, y así sucesivamente. Cada ciclo completo multiplica la
    intensidad por R_frontal · R_trasera · e^{-2 alpha W}, así que la suma de todos
    los ciclos es una serie geométrica cuya suma exacta es el inverso de uno menos
    ese producto.

    Sin reflector el producto es cero y el factor vale exactamente uno.
    """
    ciclo = R_frontal * R_trasera * np.exp(-2.0 * alpha * W_cm)
    return 1.0 / (1.0 - ciclo)


def _atenuacion(x_cm, alpha, W_cm, R_frontal, R_trasera):
    """
    Factor de atenuación del flujo dentro del silicio, adimensional.

    Sin reflector: un solo paso, e^{-alpha x}.

    Con reflector: en cada punto se suman el haz que baja y el que sube tras
    rebotar en el aluminio, R_Al · e^{-alpha (2W - x)}, y los dos se multiplican
    por el factor de rebotes sucesivos. Decisión D-06 (reflector apagado por
    defecto) y D-32 (serie completa de rebotes en lugar de solo dos pasos).
    """
    ida = np.exp(-np.outer(x_cm, alpha))
    if R_trasera <= 0.0:
        return ida
    vuelta = R_trasera * np.exp(-np.outer(2.0 * W_cm - x_cm, alpha))
    return (ida + vuelta) * _factor_de_rebotes(alpha, W_cm, R_frontal, R_trasera)


def campo_optico(d_n_cm, W_p_cm, reflector=False, irradiancia_soles=1.0,
                 nodos_extra=(), reflectancia_fija=None):
    """
    Resuelve la óptica completa de la celda.

    El flujo que logra entrar es Nph*(1-R). Se agota exponencialmente con la
    profundidad, y la tasa de generación de pares es la derivada de ese
    agotamiento respecto de x: G = alpha * Nph * (1-R) * e^{-alpha x}
    (U2, lámina 36).

    `reflectancia_fija` reemplaza la reflectancia medida del silicio desnudo por
    un valor constante, que es el segundo modo de reflexión frontal que exige el
    enunciado para la Pestaña 1. Con None se usa la medida de Green (2008).

    `nodos_extra` se propaga a la grilla. Óptica y colección tienen que compartir
    exactamente la misma grilla, porque la eficiencia cuántica integra el producto
    de ambas.
    """
    optica = constantes_opticas_silicio()
    espectro = espectro_am15g()

    lam = optica["lambda_nm"]
    alpha = optica["alpha"]
    if reflectancia_fija is None:
        reflectancia = optica["R"]
    else:
        reflectancia = np.full_like(lam, float(reflectancia_fija), dtype=float)
    nph = np.interp(lam, espectro["lambda_nm"], espectro["Nph"]) * irradiancia_soles

    x = grilla_profundidad(d_n_cm, W_p_cm, nodos_extra)
    W = d_n_cm + W_p_cm
    R_trasera = C.R_CONTACTO_AL if reflector else 0.0

    flujo_que_entra = nph * (1.0 - reflectancia)          # (nl,)
    G = alpha * flujo_que_entra * _atenuacion(x, alpha, W, reflectancia, R_trasera)

    return CampoOptico(
        x_cm=x, lambda_nm=lam, alpha=alpha, R=reflectancia, Nph=nph,
        G=G, d_n_cm=d_n_cm, W_cm=W, reflector=reflector,
        reflectancia_fija=reflectancia_fija,
    )


def balance_fotones(campo: CampoOptico):
    """
    Reparto de los fotones incidentes, color por color. Verificación V1.

    Destinos posibles:
      reflejada      : rebota en la superficie frontal, nunca entra
      absorbida      : integral numérica de la generación sobre el espesor
      aluminio       : llega al contacto trasero y el metal la absorbe
      escapa_frente  : con reflector, vuelve del aluminio y sale por el frente
      transmitida    : aluminio + escapa_frente, lo que deja la celda sin generar

    La fracción absorbida se obtiene integrando G sobre la grilla, no con la
    fórmula cerrada. Así V1 mide de verdad si la discretización resuelve la
    absorción, que es su función como test (decisión D-03). Las otras dos salen
    de sumar la serie de rebotes (D-32); sin reflector se reducen a que todo lo
    que llega al fondo lo absorbe el aluminio.
    """
    absorbida = np.trapezoid(campo.G, campo.x_cm, axis=0) / campo.Nph
    entra = 1.0 - campo.R
    llega = np.exp(-campo.alpha * campo.W_cm)
    rebotes = _factor_de_rebotes(campo.alpha, campo.W_cm, campo.R, campo.R_trasera)

    aluminio = entra * llega * (1.0 - campo.R_trasera) * rebotes
    escapa_frente = entra * campo.R_trasera * llega ** 2 * (1.0 - campo.R) * rebotes
    transmitida = aluminio + escapa_frente
    return {
        "lambda_nm": campo.lambda_nm,
        "reflejada": campo.R,
        "absorbida": absorbida,
        "aluminio": aluminio,
        "escapa_frente": escapa_frente,
        "transmitida": transmitida,
        "suma": campo.R + absorbida + transmitida,
    }


def fracciones_por_region(campo: CampoOptico):
    """
    Reparto de los pares generados entre emisor y base, integrado sobre el espectro.

    Devuelve fracciones respecto del total de fotones incidentes, de modo que
    junto con la reflejada y la transmitida cierran el balance completo.
    """
    j = campo.indice_juntura
    g_por_color = np.trapezoid(campo.G, campo.x_cm, axis=0)
    g_emisor = np.trapezoid(campo.G[: j + 1], campo.x_cm[: j + 1], axis=0)
    g_base = g_por_color - g_emisor

    incidentes = np.trapezoid(campo.Nph, campo.lambda_nm)
    integra = lambda y: np.trapezoid(y, campo.lambda_nm)

    balance = balance_fotones(campo)
    return {
        "pares_emisor": integra(g_emisor) / incidentes,
        "pares_base": integra(g_base) / incidentes,
        "reflejados": integra(campo.R * campo.Nph) / incidentes,
        "transmitidos": integra(balance["transmitida"] * campo.Nph) / incidentes,
        "pares_totales_cm2_s": integra(g_por_color),
    }


def profundidad_absorcion_cm(alpha):
    """Profundidad característica 1/alpha: donde el flujo cae a 1/e de su valor."""
    return 1.0 / np.asarray(alpha, dtype=float)


def profundidad_para_fraccion(alpha, fraccion=0.90):
    """
    Profundidad a la que se ha absorbido una fracción dada de los fotones que
    entraron. Se despeja de 1 - e^{-alpha x} = fraccion.
    """
    return -np.log(1.0 - fraccion) / np.asarray(alpha, dtype=float)
