"""
La cascada de la energía: de los 100 mW/cm² del sol a lo que la celda entrega.

Una sola unidad y un solo eje. Cada barra es un escalón que baja, con el color de
su familia: lo que impone el silicio, lo que se pierde como luz, lo que se
recombina y lo que se pierde en electricidad (D-47).
"""

import numpy as np
import plotly.graph_objects as go

from visualization.optics_plots import REJILLA, TINTA, _base, _coma, _titulo

COLORES = {
    "sol": "#F2D399",
    "fundamental": "#5A6B84",
    "optica": "#E5A33F",
    "recombinacion": "#E4664A",
    "electrica": "#9B8BE0",
    "entrega": "#5FC49B",
}
NOMBRE_FAMILIA = {
    "fundamental": "Lo que impone el silicio",
    "optica": "Luz que no llega a crear un par",
    "recombinacion": "Pares que no llegan a la juntura",
    "electrica": "Pérdidas eléctricas",
}


def cascada_de_potencia(balance):
    """
    El balance como escalera descendente.

    La primera barra es toda la potencia que trae el espectro y la última, la que
    sale por los terminales; entre medio, cada pérdida con su altura. Como todas
    comparten el eje, se comparan de un vistazo.
    """
    etiquetas = ["Llega del sol"] + [e.nombre for e in balance.etapas]
    bases, alturas, colores, textos, detalles = [0.0], [balance.incidente], [COLORES["sol"]], \
        [_coma(balance.incidente, 1)], ["espectro AM1.5G completo"]

    corriendo = balance.incidente
    for etapa in balance.etapas:
        if etapa.familia == "entrega":
            bases.append(0.0)
            alturas.append(etapa.potencia)
        else:
            corriendo -= etapa.potencia
            bases.append(corriendo)
            alturas.append(etapa.potencia)
        colores.append(COLORES[etapa.familia])
        textos.append(("" if etapa.familia == "entrega" else "−") + _coma(etapa.potencia, 2))
        detalles.append(etapa.detalle)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=etiquetas, y=alturas, base=bases, marker=dict(color=colores, line=dict(width=0)),
        text=textos, textposition="outside", cliponaxis=False,
        textfont=dict(color=TINTA, size=11), customdata=detalles,
        hovertemplate="<b>%{x}</b><br>%{y:.2f} mW/cm²<br>%{customdata}<extra></extra>",
        showlegend=False))

    # Los escalones, unidos con una línea fina
    for i in range(len(etiquetas) - 2):
        y = bases[i] + alturas[i] if i == 0 else bases[i]
        fig.add_shape(type="line", x0=i, x1=i + 1, y0=y, y1=y, xref="x", yref="y",
                      line=dict(color=REJILLA, width=1))
    fig.add_shape(type="line", x0=len(etiquetas) - 2, x1=len(etiquetas) - 1,
                  y0=bases[-2], y1=bases[-2], line=dict(color=REJILLA, width=1))

    fig.add_hline(y=balance.disponible, line=dict(color=COLORES["fundamental"], width=1.2,
                                                  dash="dash"))
    fig.add_annotation(x=1.0, y=balance.disponible, xref="paper", yref="y", xanchor="right",
                       yanchor="bottom", showarrow=False, font=dict(color=COLORES["fundamental"], size=11),
                       text=f"lo que el silicio puede aprovechar · {_coma(balance.disponible, 1)} mW/cm²")

    for familia, nombre in NOMBRE_FAMILIA.items():
        fig.add_trace(go.Bar(x=[None], y=[None], name=nombre,
                             marker=dict(color=COLORES[familia]), showlegend=True))

    fig.update_xaxes(tickangle=-35, tickfont=dict(size=10.5))
    fig.update_yaxes(title="Potencia  [mW/cm²]", rangemode="tozero")
    fig.update_layout(
        barmode="overlay", bargap=0.35,
        title=_titulo("A dónde va la energía del sol",
                      f"de {_coma(balance.incidente, 1)} mW/cm² que llegan, la celda entrega "
                      f"{_coma(balance.entregada, 2)}"),
        legend=dict(orientation="h", y=-0.42, x=0, font=dict(size=10.5)))
    return _base(fig, alto=520, margen_superior=76)
