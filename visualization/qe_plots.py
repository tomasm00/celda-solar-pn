"""Gráficos de eficiencia cuántica y del mapa por sectores."""

import numpy as np
import plotly.graph_objects as go

from visualization.optics_plots import ACENTO, BASE, EMISOR, REJILLA, SUAVE, TINTA, _base, _titulo

COLOR_EQE = "#E5A33F"
COLOR_IQE = "#5FC49B"
COLOR_COTA = "#8894A8"
ESCALA_IQE = [
    [0.00, "#1B1F2A"], [0.20, "#2E3F63"], [0.40, "#2E6F8E"],
    [0.60, "#3FAE8B"], [0.80, "#C9C05A"], [1.00, "#F2D399"],
]


def curvas_eficiencia(lambda_nm, eqe, iqe, cota, lambda_marcada=None):
    """
    Las dos eficiencias cuánticas contra el color, con su cota física.

    La externa cuenta respecto de todos los fotones que llegan; la interna
    descuenta los reflejados, así que mide solo la calidad interna del
    dispositivo. La distancia entre la curva externa y la cota es exactamente lo
    que se pierde por reflexión.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=lambda_nm, y=100 * cota, mode="lines", name="Cota física 1 − R",
        line=dict(color=COLOR_COTA, width=1.6, dash="dot"),
        hovertemplate="λ = %{x:.0f} nm<br>tope %{y:.1f} %<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=lambda_nm, y=100 * iqe, mode="lines", name="Interna (IQE)",
        line=dict(color=COLOR_IQE, width=2.4),
        hovertemplate="λ = %{x:.0f} nm<br>IQE %{y:.1f} %<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=lambda_nm, y=100 * eqe, mode="lines", name="Externa (EQE)",
        line=dict(color=COLOR_EQE, width=2.6),
        hovertemplate="λ = %{x:.0f} nm<br>EQE %{y:.1f} %<extra></extra>",
    ))
    if lambda_marcada is not None:
        fig.add_vline(x=lambda_marcada, line=dict(color=TINTA, width=1.4, dash="dot"))

    fig.update_xaxes(title="Longitud de onda λ  [nm]")
    fig.update_yaxes(title="Eficiencia cuántica  [%]", range=[0, 102])
    fig.update_layout(
        title=_titulo("De cada cien fotones de cada color, cuántos dan corriente",
                      "la externa nunca puede superar la cota: es la verificación V5"),
        legend=dict(orientation="h", y=-0.26, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=400, margen_superior=58)


def curvas_por_tiempo_de_vida(lambda_nm, curvas, d_n_um):
    """
    Reproducción de la lámina 30 de la Unidad 3.

    Al subir el tiempo de vida del volumen mejora la respuesta en el rojo,
    mientras que la del azul no se mueve en absoluto: el azul se absorbe dentro
    del emisor y nunca se entera de lo que ocurre en el volumen de la base.
    """
    fig = go.Figure()
    taus = sorted(curvas)
    for k, tau in enumerate(taus):
        tono = 0.35 + 0.65 * k / max(len(taus) - 1, 1)
        fig.add_trace(go.Scatter(
            x=lambda_nm, y=100 * curvas[tau], mode="lines",
            name=f"τₙ = {tau * 1e6:.0f} µs",
            line=dict(color=f"rgba(95,196,155,{tono:.2f})", width=2.2),
            hovertemplate="λ = %{x:.0f} nm<br>IQE %{y:.1f} %<extra></extra>",
        ))

    fig.add_vrect(x0=300, x1=550, fillcolor=EMISOR, opacity=0.10, line_width=0,
                  layer="below")
    fig.add_annotation(x=425, y=0.94, yref="paper",
                       text="el azul no se mueve:<br>vive y muere en el emisor",
                       showarrow=False, font=dict(color=EMISOR, size=10.5))
    fig.add_annotation(x=980, y=0.55, yref="paper",
                       text="aquí sí manda<br>el volumen", showarrow=False,
                       font=dict(color=COLOR_IQE, size=10.5))

    fig.update_xaxes(title="Longitud de onda λ  [nm]")
    fig.update_yaxes(title="Eficiencia cuántica interna  [%]", range=[0, 102])
    fig.update_layout(
        title=_titulo("Qué parte del espectro informa sobre el volumen",
                      "lámina 30 de la Unidad 3, reproducida con nuestro modelo"),
        legend=dict(orientation="h", y=-0.26, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=400, margen_superior=58)


def relieve_sectores(mapa, lambda_nm):
    """
    Mapa de eficiencia cuántica interna local como relieve tridimensional.

    La altura y el color son la misma magnitud: un hundimiento del relieve es un
    sector que colecta peor. En un mapa plano esas diferencias pasan
    desapercibidas cuando son suaves.
    """
    n = mapa.shape[0]
    ejes = np.arange(n) + 0.5

    fig = go.Figure(go.Surface(
        x=ejes, y=ejes, z=100 * mapa, colorscale=ESCALA_IQE,
        colorbar=dict(title=dict(text="IQE [%]", side="right"), thickness=12, len=0.8),
        contours=dict(z=dict(show=True, usecolormap=True, project_z=True,
                             width=1, highlightwidth=2)),
        hovertemplate="sector (%{x:.0f}, %{y:.0f})<br>IQE %{z:.1f} %<extra></extra>",
    ))
    fig.update_layout(
        scene=dict(
            xaxis=dict(title="sector →", gridcolor=REJILLA, showbackground=False),
            yaxis=dict(title="sector ↑", gridcolor=REJILLA, showbackground=False),
            zaxis=dict(title="IQE local [%]", gridcolor=REJILLA, showbackground=False),
            camera=dict(eye=dict(x=1.6, y=-1.5, z=0.9)),
            aspectratio=dict(x=1, y=1, z=0.55),
        ),
        height=430, margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA, size=12),
        title=_titulo(f"Relieve de la eficiencia cuántica interna local a {lambda_nm:.0f} nm"),
    )
    return fig


def barrido_lbic(mapa, lambda_nm, tau_local_us, sf_local):
    """
    Barrido tipo mapeo por haz de luz inducido.

    Imita el instrumento real: una sonda de luz recorre la celda sector por
    sector y va revelando el mapa a medida que mide. La animación es temporal de
    verdad —hay un progreso en el tiempo— y cada valor que aparece es el cálculo
    real de ese sector.
    """
    n = mapa.shape[0]
    ejes = np.arange(n)
    orden = [(i, j) for i in range(n) for j in (range(n) if i % 2 == 0 else range(n - 1, -1, -1))]

    base_heat = dict(
        x=ejes, y=ejes, colorscale=ESCALA_IQE, zmin=100 * mapa.min(),
        zmax=100 * mapa.max(), xgap=2, ygap=2,
        colorbar=dict(title=dict(text="IQE [%]", side="right"), thickness=12, len=0.85),
        hovertemplate="sector (%{x}, %{y})<br>IQE %{z:.1f} %<extra></extra>",
    )

    cuadros = []
    revelado = np.full((n, n), np.nan)
    for paso, (i, j) in enumerate(orden):
        revelado = revelado.copy()
        revelado[i, j] = 100 * mapa[i, j]
        cuadros.append(go.Frame(
            name=str(paso),
            data=[
                go.Heatmap(z=revelado.copy(), **base_heat),
                go.Scatter(x=[j], y=[i], mode="markers",
                           marker=dict(size=22, color="rgba(0,0,0,0)",
                                       line=dict(color=TINTA, width=2.5))),
            ],
            traces=[0, 1],
            layout=go.Layout(annotations=[dict(
                x=0.5, y=1.06, xref="paper", yref="paper", showarrow=False,
                font=dict(color=TINTA, size=12),
                text=(f"sector ({j}, {i})  ·  τₙ local {tau_local_us[i, j]:.1f} µs  ·  "
                      f"S_f local {sf_local[i, j]:.1e} cm/s  ·  IQE {100 * mapa[i, j]:.1f} %"),
            )]),
        ))

    fig = go.Figure(
        data=[
            go.Heatmap(z=np.full((n, n), np.nan), **base_heat),
            go.Scatter(x=[0], y=[0], mode="markers", showlegend=False,
                       marker=dict(size=22, color="rgba(0,0,0,0)",
                                   line=dict(color=TINTA, width=2.5))),
        ],
        frames=cuadros,
    )
    fig.update_xaxes(title="sector", dtick=1, showgrid=False, zeroline=False)
    fig.update_yaxes(title="sector", dtick=1, showgrid=False, zeroline=False,
                     scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=470, margin=dict(l=14, r=18, t=76, b=48),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA, size=12),
        title=_titulo(f"Sonda recorriendo la celda a {lambda_nm:.0f} nm",
                      "como un mapeo por haz de luz inducido: se mide sector por sector"),
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.02, y=1.14, xanchor="left",
            bgcolor="#1C2531", bordercolor=REJILLA, font=dict(color=TINTA),
            buttons=[
                dict(label="▶  Iniciar barrido", method="animate",
                     args=[None, dict(frame=dict(duration=70, redraw=True),
                                      fromcurrent=False, mode="immediate")]),
                dict(label="⏸", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
    )
    return fig


def histograma_sectores(mapa, lambda_nm):
    """Distribución de la eficiencia local entre los sectores."""
    valores = 100 * mapa.ravel()
    fig = go.Figure(go.Histogram(
        x=valores, nbinsx=16, marker=dict(color=COLOR_IQE, line=dict(width=0)),
        hovertemplate="IQE %{x:.1f} %<br>%{y} sectores<extra></extra>",
    ))
    fig.add_vline(x=valores.mean(), line=dict(color=ACENTO, width=2))
    fig.add_annotation(x=valores.mean(), y=1.0, yref="paper",
                       text=f"media {valores.mean():.1f} %", showarrow=False,
                       font=dict(color=ACENTO, size=11), xanchor="left",
                       yanchor="bottom", xshift=5)
    fig.update_xaxes(title=f"Eficiencia cuántica interna local a {lambda_nm:.0f} nm  [%]")
    fig.update_yaxes(title="Número de sectores")
    fig.update_layout(title=_titulo(
        "Cuánto varía la calidad de un sector a otro",
        f"dispersión entre {valores.min():.1f} % y {valores.max():.1f} %"))
    return _base(fig, alto=340)
