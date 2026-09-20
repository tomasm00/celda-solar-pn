"""
La malla frontal de plata: el compromiso entre tapar luz y conducir.

El enunciado pide que se vea. La figura lleva las dos pérdidas a una sola unidad
—puntos de eficiencia— y las apila contra el número de dedos, de modo que el
óptimo es simplemente el mínimo de la pila (D-44).
"""

import numpy as np
import plotly.graph_objects as go

import constants as C
from visualization.optics_plots import ACENTO, TINTA, _base, _coma, _titulo

COLOR_SOMBRA = "#8894A8"
COLOR_EMISOR_R = "#5AA8D6"
COLOR_DEDOS_R = "#C98A1B"
COLOR_TOTAL = "#E4664A"


def _caida_dedo(y_cm, j_a_cm2, separacion_cm, ancho_dedo_cm):
    """
    Voltaje que pierde la corriente recorriendo el propio dedo, en volts.

    El dedo recoge corriente a lo largo de su camino, así que la que transporta
    crece hacia la barra colectora: a una distancia y del extremo libre lleva
    J·S·y por cada centímetro de ancho recogido. Integrando la resistencia del
    metal, V(y) = ρ·J·S·y² / (2·ancho·espesor). Su promedio pesado da la
    resistencia de los dedos que usa el modelo de la malla.
    """
    return (C.RHO_PLATA_SERIGRAFIA * j_a_cm2 * separacion_cm * y_cm ** 2
            / (2.0 * ancho_dedo_cm * C.ESPESOR_DEDO))


def perdidas_de_la_malla(referencia, puntos, n_actual):
    """
    Las tres pérdidas de la malla, en la misma unidad: puntos de eficiencia.

    Apiladas, su altura es todo lo que la malla le quita a la celda. El mínimo de
    esa altura es el óptimo, y se ve sin comparar ejes distintos.
    """
    n = [p.n_dedos for p in puntos]
    capas = [
        ("Tapa la luz", [p.perdida_sombra for p in puntos], COLOR_SOMBRA),
        ("Resistencia del emisor", [p.perdida_emisor for p in puntos], COLOR_EMISOR_R),
        ("Resistencia de los dedos", [p.perdida_dedos for p in puntos], COLOR_DEDOS_R),
    ]
    total = np.array([p.perdida_total for p in puntos])
    mejor = int(np.argmin(total))

    fig = go.Figure()
    for nombre, valores, color in capas:
        fig.add_trace(go.Scatter(
            x=n, y=valores, mode="lines", name=nombre, stackgroup="perdidas",
            line=dict(width=0.6, color=color), fillcolor=color,
            hovertemplate="%{x} dedos<br>" + nombre.lower() + ": %{y:.3f} puntos<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=n, y=total, mode="lines", name="Pérdida total",
        line=dict(color=COLOR_TOTAL, width=2.4),
        hovertemplate="%{x} dedos<br>pierde %{y:.3f} puntos<extra></extra>"))

    fig.add_vline(x=n[mejor], line=dict(color=ACENTO, width=1.6, dash="dash"))
    fig.add_annotation(x=n[mejor], y=1.0, yref="paper", xanchor="left", yanchor="bottom",
                       xshift=5, showarrow=False, font=dict(color=ACENTO, size=11),
                       text=f"óptimo · {n[mejor]} dedos · pierde {_coma(total[mejor], 3)}")
    fig.add_vline(x=n_actual, line=dict(color=TINTA, width=1.4, dash="dot"))
    fig.add_annotation(x=n_actual, y=0.02, yref="paper", xanchor="right", yanchor="bottom",
                       xshift=-5, showarrow=False, font=dict(color=TINTA, size=11),
                       text=f"la malla actual · {n_actual}")

    fig.update_xaxes(title="Número de dedos de plata")
    fig.update_yaxes(title="Eficiencia perdida  [puntos]", rangemode="tozero")
    fig.update_layout(
        title=_titulo("Lo que cuesta la malla, repartido por causa",
                      f"sin malla, la celda daría {_coma(100 * referencia, 3)} % · pocos dedos "
                      f"pierden por resistencia, muchos por sombra"),
        legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=10.5)))
    return _base(fig, alto=430, margen_superior=76)
