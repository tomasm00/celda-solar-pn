"""
Probabilidad de colección: qué fracción de los pares nacidos a cada profundidad
llega viva hasta la juntura.

Un par electrón-hueco solo sirve si alcanza la zona de deplexión, donde el campo
eléctrico lo separa y lo manda a los contactos. Mientras difunde al azar compite
contra dos destinos: recombinarse en el volumen, o ser capturado por una
superficie. Estas expresiones, que el enunciado entrega ya resueltas, son la
solución de la ecuación de difusión con esas dos condiciones de borde.

Se leen así: en cada región, el cociente S·L/D compara qué tan ávida es la
superficie contra qué tan bien difunde el material. Cuando ese número es grande
la superficie gana y la colección se desploma; cuando es pequeño el material
gana y casi todo se colecta.

Convención de portador minoritario, la del enunciado:
    emisor tipo n -> huecos -> D_p, L_p, compiten contra S_f (cara frontal)
    base tipo p   -> electrones -> D_n, L_n, compiten contra S_r (cara trasera)
"""

from dataclasses import dataclass

import numpy as np

from physics.material import difusividad, longitud_difusion


@dataclass
class Transporte:
    """Parámetros de transporte del portador minoritario en cada región."""

    D_p: float      # cm2/s   huecos en el emisor
    L_p: float      # cm      longitud de difusión en el emisor
    S_f: float      # cm/s    recombinación en la cara frontal
    D_n: float      # cm2/s   electrones en la base
    L_n: float      # cm      longitud de difusión en la base
    S_r: float      # cm/s    recombinación en la cara trasera

    @property
    def peso_superficie_frontal(self) -> float:
        """S_f·L_p/D_p — cuánto pesa la superficie frontal frente a la difusión."""
        return self.S_f * self.L_p / self.D_p

    @property
    def peso_superficie_trasera(self) -> float:
        return self.S_r * self.L_n / self.D_n


def transporte(mu_p, tau_p_s, mu_n, tau_n_s, s_f, s_r, t_k):
    """Arma los parámetros de transporte desde movilidades, tiempos de vida y T."""
    d_p = float(difusividad(mu_p, t_k))
    d_n = float(difusividad(mu_n, t_k))
    return Transporte(
        D_p=d_p, L_p=float(longitud_difusion(d_p, tau_p_s)), S_f=float(s_f),
        D_n=d_n, L_n=float(longitud_difusion(d_n, tau_n_s)), S_r=float(s_r),
    )


def _razon_hiperbolica(a, b, k):
    """
    Calcula [cosh(a) + k·sinh(a)] / [cosh(b) + k·sinh(b)] con 0 <= a <= b.

    Escrito de forma directa, esto desborda: con una base gruesa y un tiempo de
    vida corto, b puede llegar a 16, donde el coseno hiperbólico ya vale diez
    millones, y con valores mayores se va a infinito. Aquí se saca el factor
    e^b de numerador y denominador, con lo que todos los exponentes quedan
    negativos y el cálculo es estable en todo el rango de los deslizadores.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    numerador = (1.0 + k) * np.exp(a - b) + (1.0 - k) * np.exp(-a - b)
    denominador = (1.0 + k) + (1.0 - k) * np.exp(-2.0 * b)
    return numerador / denominador


def probabilidad_coleccion(x_cm, union, W_cm, tr: Transporte, recortar=True):
    """
    Probabilidad de colección en cada punto de la grilla de profundidad.

    Adimensional, acotada entre 0 y 1. Vale exactamente 1 en ambos bordes de la
    zona de deplexión y decae hacia las dos superficies.
    """
    x = np.asarray(x_cm, dtype=float)
    fc = np.ones_like(x)

    en_emisor = x <= union.x_n
    en_base = x >= union.x_p

    if np.any(en_emisor) and union.x_n > 0:
        fc[en_emisor] = _razon_hiperbolica(
            x[en_emisor] / tr.L_p, union.x_n / tr.L_p, tr.peso_superficie_frontal)

    ancho_base = W_cm - union.x_p
    if np.any(en_base) and ancho_base > 0:
        u = x[en_base] - union.x_p
        fc[en_base] = _razon_hiperbolica(
            (ancho_base - u) / tr.L_n, ancho_base / tr.L_n,
            tr.peso_superficie_trasera)

    # El recorte es una red de seguridad, no parte del modelo: las expresiones
    # deben entregar ya un valor en [0,1]. Poder pedir el valor SIN recortar es lo
    # que permite que la verificacion C-T1 compruebe algo de verdad; comprobar el
    # resultado ya recortado no puede fallar nunca (ver D-26).
    return np.clip(fc, 0.0, 1.0) if recortar else fc


def reparto_generacion(G, fc):
    """
    Separa la generación en la parte que se colecta y la que se recombina.

    G tiene forma (profundidad, color) y fc solo (profundidad), así que la
    probabilidad se aplica a cada color por igual: la colección depende de dónde
    nació el par, no del color del fotón que lo creó.
    """
    fc_col = np.asarray(fc)[:, None]
    return G * fc_col, G * (1.0 - fc_col)


def fraccion_colectada(x_cm, G, lambda_nm, fc):
    """Fracción del total de pares generados que termina siendo colectada."""
    colectada, _ = reparto_generacion(G, fc)
    total = np.trapezoid(np.trapezoid(G, lambda_nm, axis=1), x_cm)
    util = np.trapezoid(np.trapezoid(colectada, lambda_nm, axis=1), x_cm)
    return float(util / total) if total > 0 else 0.0
