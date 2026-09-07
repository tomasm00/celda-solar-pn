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
    de la zona de deplexión: ahí la probabilidad de colección tiene un quiebre
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


def _atenuacion(x_cm, alpha, W_cm, reflector):
    """
    Factor de atenuación del flujo dentro del silicio, adimensional.

    Un solo paso: e^{-alpha x}.

    Con reflector trasero activo se suma el haz de retorno: la luz que llegó al
    fondo con e^{-alpha W}, se reflejó con R_Al, y volvió a recorrer W - x, lo que
    da R_Al * e^{-alpha (2W - x)}. Decisión D-06: apagado por defecto, para que la
    eficiencia cuántica sea la fórmula de un solo paso del enunciado.
    """
    ida = np.exp(-np.outer(x_cm, alpha))
    if not reflector:
        return ida
    vuelta = C.R_CONTACTO_AL * np.exp(-np.outer(2.0 * W_cm - x_cm, alpha))
    return ida + vuelta


def campo_optico(d_n_cm, W_p_cm, reflector=False, irradiancia_soles=1.0,
                 nodos_extra=()):
    """
    Resuelve la óptica completa de la celda.

    El flujo que logra entrar es Nph*(1-R). Se agota exponencialmente con la
    profundidad, y la tasa de generación de pares es la derivada de ese
    agotamiento respecto de x: G = alpha * Nph * (1-R) * e^{-alpha x}
    (U2, lámina 36).

    `nodos_extra` se propaga a la grilla. Óptica y colección tienen que compartir
    exactamente la misma grilla, porque la eficiencia cuántica del Hito 4 integra
    el producto de ambas.
    """
    optica = constantes_opticas_silicio()
    espectro = espectro_am15g()

    lam = optica["lambda_nm"]
    alpha = optica["alpha"]
    reflectancia = optica["R"]
    nph = np.interp(lam, espectro["lambda_nm"], espectro["Nph"]) * irradiancia_soles

    x = grilla_profundidad(d_n_cm, W_p_cm, nodos_extra)
    W = d_n_cm + W_p_cm

    flujo_que_entra = nph * (1.0 - reflectancia)          # (nl,)
    G = alpha * flujo_que_entra * _atenuacion(x, alpha, W, reflector)

    return CampoOptico(
        x_cm=x, lambda_nm=lam, alpha=alpha, R=reflectancia, Nph=nph,
        G=G, d_n_cm=d_n_cm, W_cm=W, reflector=reflector,
    )


def balance_fotones(campo: CampoOptico):
    """
    Reparto de los fotones incidentes, color por color. Verificación V1.

    Tres destinos posibles en el modelo de un solo paso:
      reflejada   : rebota en la superficie frontal, nunca entra
      absorbida   : integral numérica de la generación sobre el espesor
      transmitida : llega al contacto trasero sin haber sido absorbida

    La fracción absorbida se obtiene integrando G sobre la grilla, no con la
    fórmula cerrada. Así V1 mide de verdad si la discretización resuelve la
    absorción, que es su función como test (decisión D-03).
    """
    absorbida = np.trapezoid(campo.G, campo.x_cm, axis=0) / campo.Nph
    transmitida = (1.0 - campo.R) * np.exp(-campo.alpha * campo.W_cm)
    if campo.reflector:
        # Con reflector, lo que "escapa" es lo que el aluminio no devuelve, mas
        # lo que sale por el frente tras el segundo paso.
        llega_al_fondo = (1.0 - campo.R) * np.exp(-campo.alpha * campo.W_cm)
        transmitida = llega_al_fondo * (1.0 - C.R_CONTACTO_AL)
        vuelve_al_frente = (llega_al_fondo * C.R_CONTACTO_AL
                            * np.exp(-campo.alpha * campo.W_cm))
        transmitida = transmitida + vuelve_al_frente
    return {
        "lambda_nm": campo.lambda_nm,
        "reflejada": campo.R,
        "absorbida": absorbida,
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
