"""
Color real de cada longitud de onda.

Se usa como lenguaje visual consistente en toda la aplicación: un fotón de 450 nm
se dibuja azul en la animación, y la curva de 450 nm es del mismo azul en los
gráficos. Fuera del visible no hay color percibido, así que el ultravioleta se
representa violeta oscuro y el infrarrojo rojo profundo, atenuados, para que se
lea que el ojo ya no los ve.

Aproximación de Bruton para el visible (380-780 nm).
"""

import numpy as np

VISIBLE_MIN_NM = 380.0
VISIBLE_MAX_NM = 780.0


def _rgb_visible(lam):
    if lam < 440:
        r, g, b = -(lam - 440) / 60.0, 0.0, 1.0
    elif lam < 490:
        r, g, b = 0.0, (lam - 440) / 50.0, 1.0
    elif lam < 510:
        r, g, b = 0.0, 1.0, -(lam - 510) / 20.0
    elif lam < 580:
        r, g, b = (lam - 510) / 70.0, 1.0, 0.0
    elif lam < 645:
        r, g, b = 1.0, -(lam - 645) / 65.0, 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    return r, g, b


def _atenuacion_borde(lam):
    """El ojo pierde sensibilidad en los extremos del visible."""
    if lam < 420:
        return 0.30 + 0.70 * (lam - 380) / 40.0
    if lam > 700:
        return 0.30 + 0.70 * (780 - lam) / 80.0
    return 1.0


def rgb_de_longitud_onda(lam_nm, gamma=0.8):
    """Devuelve (r, g, b) en 0-255 para una longitud de onda en nm."""
    lam = float(lam_nm)

    if lam < VISIBLE_MIN_NM:
        # Ultravioleta: violeta muy oscuro, cada vez mas apagado
        f = max(0.15, 0.45 * lam / VISIBLE_MIN_NM)
        r, g, b, atenuacion = 0.45, 0.0, 1.0, f
    elif lam > VISIBLE_MAX_NM:
        # Infrarrojo: rojo profundo, apagandose
        f = max(0.12, 0.45 * (1.0 - (lam - VISIBLE_MAX_NM) / 500.0))
        r, g, b, atenuacion = 1.0, 0.05, 0.0, f
    else:
        r, g, b = _rgb_visible(lam)
        atenuacion = _atenuacion_borde(lam)

    canales = [int(round(255 * (c * atenuacion) ** gamma)) for c in (r, g, b)]
    return tuple(min(255, max(0, c)) for c in canales)


def hex_de_longitud_onda(lam_nm):
    return "#{:02X}{:02X}{:02X}".format(*rgb_de_longitud_onda(lam_nm))


def rgba_de_longitud_onda(lam_nm, alfa=1.0):
    r, g, b = rgb_de_longitud_onda(lam_nm)
    return f"rgba({r},{g},{b},{alfa})"


def escala_espectral(lambdas_nm, n=48):
    """Escala de color de Plotly que recorre el espectro real."""
    lo, hi = float(np.min(lambdas_nm)), float(np.max(lambdas_nm))
    return [
        [i / (n - 1), hex_de_longitud_onda(lo + (hi - lo) * i / (n - 1))]
        for i in range(n)
    ]
