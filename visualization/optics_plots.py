"""Gráficos cuantitativos de la óptica de la celda."""

import numpy as np
import plotly.graph_objects as go

from units import cm_a_um
from visualization.colors import hex_de_longitud_onda, rgba_de_longitud_onda

TINTA = "#E8ECF2"
REJILLA = "#2A3542"
SUAVE = "#8894A8"
ACENTO = "#E5A33F"
EMISOR = "#2E6F8E"
BASE = "#5FC49B"
FUGA = "#A0A8B6"
PERDIDA = "#969EAC"

BANDAS = (
    ("Ultravioleta", 300, 400, "#7A5BD0"),
    ("Azul", 400, 500, "#3A76D8"),
    ("Verde", 500, 600, "#3FAE6B"),
    ("Rojo", 600, 700, "#D8632F"),
    ("Infrarrojo cercano", 700, 1200, "#8E3B2A"),
)


def _base(fig, alto=380, margen_superior=54):
    """Márgenes generosos arriba: los títulos y las anotaciones necesitan aire."""
    fig.update_layout(
        height=alto,
        margin=dict(l=14, r=18, t=margen_superior, b=48),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA, size=12),
        xaxis=dict(gridcolor=REJILLA, zerolinecolor=REJILLA, title_standoff=10),
        yaxis=dict(gridcolor=REJILLA, zerolinecolor=REJILLA, title_standoff=10),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10.5)),
        hoverlabel=dict(font_size=12),
    )
    return fig


def _titulo(texto, subtitulo=None):
    if subtitulo:
        texto = f"{texto}<br><span style='font-size:11.5px;color:{SUAVE}'>{subtitulo}</span>"
    return dict(text=texto, font=dict(size=14.5), x=0, xanchor="left", y=0.97, yanchor="top")


def perfil_generacion(x_cm, g, lambda_nm, d_n_um, W_um, y_max=None, juntura=None):
    """
    Perfil de generación contra profundidad, para un color.

    El eje vertical se fija al máximo que alcanzaría con la irradiancia más alta
    del rango, de modo que bajar los soles se vea como una curva que efectivamente
    se encoge, y no como la misma curva con otra escala.
    """
    x_um = cm_a_um(x_cm)
    color = hex_de_longitud_onda(lambda_nm)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_um, y=g, mode="lines", name=f"{lambda_nm:.0f} nm",
        line=dict(color=color, width=2.4), fill="tozeroy",
        fillcolor=rgba_de_longitud_onda(lambda_nm, 0.20), showlegend=False,
        hovertemplate="x = %{x:.3f} µm<br>G = %{y:.3e} 1/(cm³·s·nm)<extra></extra>",
    ))

    if juntura is not None:
        fig.add_vrect(x0=cm_a_um(juntura.x_n), x1=cm_a_um(juntura.x_p),
                      fillcolor=ACENTO, opacity=0.30, line_width=0, layer="below")
    fig.add_vline(x=d_n_um, line=dict(color=ACENTO, width=1.5, dash="dash"))
    fig.add_annotation(x=np.log10(d_n_um), y=1.0, yref="paper", text="juntura p-n",
                       showarrow=False, font=dict(color=ACENTO, size=11),
                       xanchor="left", yanchor="bottom", xshift=4)

    fig.update_xaxes(title="Profundidad x  [µm]", type="log",
                     range=[np.log10(max(x_um[1], 1e-4)), np.log10(W_um)])
    fig.update_yaxes(title="Generación G  [pares / cm³·s·nm]",
                     range=[0, y_max] if y_max else None)
    fig.update_layout(title=_titulo(
        "Dónde nacen los pares electrón-hueco",
        "el área bajo la curva a la izquierda de la juntura son los pares del emisor"))
    return _base(fig)


def generacion_con_coleccion(x_cm, g, fc, lambda_nm, d_n_um, W_um,
                             y_max=None, juntura=None):
    """
    Perfil de generación separado en lo que se colecta y lo que se recombina.

    El área de abajo son los pares que alcanzan la juntura y producen corriente;
    la de arriba, los que se recombinan antes de llegar. La suma de ambas es la
    generación total, idéntica a la del modelo óptico solo.
    """
    x_um = cm_a_um(x_cm)
    color = hex_de_longitud_onda(lambda_nm)
    colectada = g * fc
    perdida = g * (1.0 - fc)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_um, y=colectada, mode="lines", name="Se colecta",
        stackgroup="g", line=dict(width=0.5, color=color),
        fillcolor=rgba_de_longitud_onda(lambda_nm, 0.55),
        hovertemplate="x = %{x:.3f} µm<br>colectado %{y:.3e}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x_um, y=perdida, mode="lines", name="Se recombina antes de llegar",
        stackgroup="g", line=dict(width=0.5, color=PERDIDA),
        fillcolor="rgba(150,158,172,0.42)",
        hovertemplate="x = %{x:.3f} µm<br>perdido %{y:.3e}<extra></extra>",
    ))

    if juntura is not None:
        fig.add_vrect(x0=cm_a_um(juntura.x_n), x1=cm_a_um(juntura.x_p),
                      fillcolor=ACENTO, opacity=0.30, line_width=0, layer="below")
    fig.add_vline(x=d_n_um, line=dict(color=ACENTO, width=1.5, dash="dash"))
    fig.add_annotation(x=np.log10(d_n_um), y=1.0, yref="paper", text="juntura p-n",
                       showarrow=False, font=dict(color=ACENTO, size=11),
                       xanchor="left", yanchor="bottom", xshift=4)

    fig.update_xaxes(title="Profundidad x  [µm]", type="log",
                     range=[np.log10(max(x_um[1], 1e-4)), np.log10(W_um)])
    fig.update_yaxes(title="Generación G  [pares / cm³·s·nm]",
                     range=[0, y_max] if y_max else None)
    fig.update_layout(
        title=_titulo(f"Destino de los pares nacidos a cada profundidad · {lambda_nm:.0f} nm",
                      "el área gris es lo que se recombina antes de alcanzar la juntura"),
        legend=dict(orientation="h", y=-0.26, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=400, margen_superior=58)


def perfil_coleccion(x_cm, fc, juntura, d_n_um, W_um, transporte=None):
    """
    Probabilidad de colección contra profundidad, con las tres regiones marcadas.

    Vale 1 en ambos bordes de la zona de deplexión y decae hacia las superficies
    según cuánto pese cada velocidad de recombinación frente a la difusión.
    """
    x_um = cm_a_um(x_cm)
    x_n_um, x_p_um = cm_a_um(juntura.x_n), cm_a_um(juntura.x_p)

    fig = go.Figure()
    fig.add_vrect(x0=max(x_um[0], 1e-4), x1=x_n_um, fillcolor=EMISOR, opacity=0.11,
                  line_width=0, layer="below")
    fig.add_vrect(x0=x_n_um, x1=x_p_um, fillcolor=ACENTO, opacity=0.30,
                  line_width=0, layer="below")
    fig.add_vrect(x0=x_p_um, x1=W_um, fillcolor=BASE, opacity=0.11,
                  line_width=0, layer="below")

    fig.add_trace(go.Scatter(
        x=x_um, y=100 * fc, mode="lines", showlegend=False,
        line=dict(color=TINTA, width=2.6),
        hovertemplate="x = %{x:.3f} µm<br>se colecta el %{y:.1f} %<extra></extra>",
    ))

    for x_pos, texto, color in ((np.sqrt(max(x_um[1], 1e-3) * x_n_um), "emisor", EMISOR),
                                (np.sqrt(x_p_um * W_um), "base", BASE)):
        fig.add_annotation(x=np.log10(x_pos), y=0.04, yref="paper", text=texto,
                           showarrow=False, font=dict(color=color, size=11))
    fig.add_annotation(x=np.log10(d_n_um), y=1.0, yref="paper",
                       text="zona de deplexión", showarrow=False,
                       font=dict(color=ACENTO, size=11), xanchor="left",
                       yanchor="bottom", xshift=4)

    subtitulo = "vale 100 % en los bordes de la deplexión y cae hacia las superficies"
    if transporte is not None:
        subtitulo = (f"peso de la superficie frontal S_f·L_p/D_p = "
                     f"{transporte.peso_superficie_frontal:.1f}  ·  "
                     f"trasera S_r·L_n/D_n = {transporte.peso_superficie_trasera:.2f}")

    fig.update_xaxes(title="Profundidad x  [µm]", type="log",
                     range=[np.log10(max(x_um[1], 1e-4)), np.log10(W_um)])
    fig.update_yaxes(title="Probabilidad de colección  [%]", range=[0, 104])
    fig.update_layout(title=_titulo(
        "Qué fracción de los pares nacidos a cada profundidad llega viva a la juntura",
        subtitulo))
    return _base(fig, alto=400)


def penetracion_por_color(lambda_nm, prof_um, d_n_um, W_um, lambda_marcada=None):
    """
    Profundidad característica de penetración, con las tres regiones sombreadas.

    Las bandas de color dicen directamente qué le pasa a cada color: si la curva
    cae en la banda de abajo, ese color se absorbe dentro del emisor; si cae en
    la del medio, llega a la base; si cae arriba, atraviesa la celda.
    """
    fig = go.Figure()
    techo = float(np.max(prof_um)) * 1.5

    for y0, y1, color, etiqueta in (
        (1e-4, d_n_um, EMISOR, "se absorbe dentro del emisor"),
        (d_n_um, W_um, BASE, "alcanza la base"),
        (W_um, techo, FUGA, "atraviesa la celda"),
    ):
        fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=0.13,
                      line_width=0, layer="below")
        fig.add_annotation(
            x=1.0, xref="paper", y=np.log10(np.sqrt(y0 * y1)),
            text=etiqueta, showarrow=False, xanchor="right", xshift=-6,
            font=dict(color=color, size=10.5),
        )

    fig.add_trace(go.Scatter(
        x=lambda_nm, y=prof_um, mode="lines", name="1/α",
        line=dict(color=ACENTO, width=2.6), showlegend=False,
        hovertemplate="λ = %{x:.0f} nm<br>penetra %{y:.3g} µm<extra></extra>",
    ))
    if lambda_marcada is not None:
        fig.add_vline(x=lambda_marcada,
                      line=dict(color=hex_de_longitud_onda(lambda_marcada),
                                width=2, dash="dot"))

    fig.update_xaxes(title="Longitud de onda λ  [nm]")
    fig.update_yaxes(title="Profundidad de penetración 1/α  [µm]", type="log",
                     range=[np.log10(max(np.min(prof_um) * 0.5, 1e-4)), np.log10(techo)])
    fig.update_layout(title=_titulo(
        "Cuán profundo entra cada color antes de apagarse",
        "1/α es la profundidad donde el flujo cae a un 37 % del que entró"))
    return _base(fig, alto=400)


def acumulado_espectral(x_cm, lambda_nm, G, d_n_um, W_um):
    """
    Fracción acumulada de pares generados por encima de cada profundidad.

    Responde de un vistazo la pregunta central de la pestaña: a qué profundidad
    ya nació la mitad de los pares, y cómo cambia esa respuesta según el color.
    Cada banda espectral tiene su propia curva, integrada sobre sus longitudes
    de onda con el peso real del espectro solar.
    """
    x_um = cm_a_um(x_cm)
    fig = go.Figure()

    def acumulada(mascara):
        g = np.trapezoid(G[:, mascara], lambda_nm[mascara], axis=1)
        acum = np.concatenate([[0.0], np.cumsum(np.diff(x_um) * (g[:-1] + g[1:]) / 2)])
        return acum / acum[-1] if acum[-1] > 0 else acum

    for etiqueta, lo, hi, color in BANDAS:
        m = (lambda_nm >= lo) & (lambda_nm < hi)
        if not np.any(m):
            continue
        fig.add_trace(go.Scatter(
            x=x_um, y=100 * acumulada(m), mode="lines", name=etiqueta,
            line=dict(color=color, width=1.9),
            hovertemplate="%{y:.1f} % de los pares de esta banda<br>"
                          "nacen antes de %{x:.3g} µm<extra></extra>",
        ))

    total = 100 * acumulada(np.ones_like(lambda_nm, dtype=bool))
    fig.add_trace(go.Scatter(
        x=x_um, y=total, mode="lines", name="Todo el espectro",
        line=dict(color=TINTA, width=3),
        hovertemplate="%{y:.1f} % de todos los pares<br>"
                      "nacen antes de %{x:.3g} µm<extra></extra>",
    ))

    fig.add_vline(x=d_n_um, line=dict(color=ACENTO, width=1.5, dash="dash"))
    fig.add_annotation(x=np.log10(d_n_um), y=1.0, yref="paper", text="juntura p-n",
                       showarrow=False, font=dict(color=ACENTO, size=11),
                       xanchor="left", yanchor="bottom", xshift=4)
    fig.add_hline(y=50, line=dict(color=SUAVE, width=1, dash="dot"))

    fig.update_xaxes(title="Profundidad x  [µm]", type="log",
                     range=[np.log10(max(x_um[1], 1e-4)), np.log10(W_um)])
    fig.update_yaxes(title="Pares ya generados  [% del total de su banda]",
                     range=[0, 102])
    fig.update_layout(
        title=_titulo("A qué profundidad ya nació cada mitad de los pares",
                      "cada curva llega al 100 % cuando esa banda terminó de absorberse"),
        legend=dict(orientation="h", y=-0.24, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=420, margen_superior=58)


def mapa_generacion(x_cm, lambda_nm, G, d_n_um, W_um, n_lam=190, n_x=170):
    """Mapa de generación en el plano color-profundidad."""
    idx_l = np.linspace(0, len(lambda_nm) - 1, n_lam).astype(int)
    idx_x = np.linspace(0, len(x_cm) - 1, n_x).astype(int)
    x_um = cm_a_um(x_cm[idx_x])
    z = G[np.ix_(idx_x, idx_l)].T
    if np.any(z > 0):
        z = np.log10(np.clip(z, z[z > 0].max() * 1e-6, None))

    fig = go.Figure(go.Heatmap(
        x=x_um, y=lambda_nm[idx_l], z=z, colorscale="Inferno",
        colorbar=dict(title=dict(text="log₁₀ G", side="right"), thickness=12,
                      len=0.85, y=0.45),
        hovertemplate="x = %{x:.2f} µm<br>λ = %{y:.0f} nm<br>"
                      "log₁₀G = %{z:.2f}<extra></extra>",
    ))
    fig.add_vline(x=d_n_um, line=dict(color="#8FD6FF", width=1.5, dash="dash"))
    fig.add_annotation(x=np.log10(d_n_um), y=1.0, yref="paper", text="juntura p-n",
                       showarrow=False, font=dict(color="#8FD6FF", size=11),
                       xanchor="left", yanchor="bottom", xshift=4)
    fig.update_xaxes(title="Profundidad x  [µm]", type="log")
    fig.update_yaxes(title="Longitud de onda λ  [nm]")
    fig.update_layout(title=_titulo(
        "A qué profundidad se absorbe cada color",
        "la franja brillante arriba es el azul muriendo; la cola tenue, el rojo penetrando"))
    return _base(fig, alto=430)


def balance_espectral(balance, lambda_marcada=None):
    """Reparto de los fotones incidentes color por color. Es la verificación V1."""
    fig = go.Figure()
    for clave, etiqueta, color in (
        ("reflejada", "Reflejada en la superficie", SUAVE),
        ("absorbida", "Absorbida en el silicio", ACENTO),
        ("transmitida", "Llega al contacto trasero", EMISOR),
    ):
        fig.add_trace(go.Scatter(
            x=balance["lambda_nm"], y=balance[clave], mode="lines", name=etiqueta,
            stackgroup="uno", line=dict(width=0.5, color=color), fillcolor=color,
            hovertemplate="λ = %{x:.0f} nm<br>%{y:.3f}<extra>" + etiqueta + "</extra>",
        ))
    if lambda_marcada is not None:
        fig.add_vline(x=lambda_marcada, line=dict(color=TINTA, width=1.5, dash="dot"))

    fig.update_xaxes(title="Longitud de onda λ  [nm]")
    fig.update_yaxes(title="Fracción de los fotones incidentes", range=[0, 1])
    fig.update_layout(
        title=_titulo("Destino de cada fotón",
                      "las tres franjas deben llenar exactamente la altura 1: es la verificación V1"),
        legend=dict(orientation="h", y=-0.26, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=400, margen_superior=58)


def espectro_y_absorcion(lambda_nm, nph, alpha, lambda_marcada=None):
    """Flujo de fotones disponible y coeficiente de absorción en ejes separados."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=lambda_nm, y=nph, mode="lines", name="Fotones que llegan del Sol",
        line=dict(color=BASE, width=2),
        hovertemplate="λ = %{x:.0f} nm<br>%{y:.3e} fotones/(cm²·s·nm)<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=lambda_nm, y=alpha, mode="lines", name="Cuánto absorbe el silicio (α)",
        line=dict(color=ACENTO, width=2), yaxis="y2",
        hovertemplate="λ = %{x:.0f} nm<br>α = %{y:.3e} 1/cm<extra></extra>",
    ))
    if lambda_marcada is not None:
        fig.add_vline(x=lambda_marcada, line=dict(color=TINTA, width=1.5, dash="dot"))

    fig.update_xaxes(title="Longitud de onda λ  [nm]")
    fig.update_yaxes(title="Flujo  [fotones / cm²·s·nm]")
    fig.update_layout(
        yaxis2=dict(title="α  [1/cm]", overlaying="y", side="right", type="log",
                    gridcolor="rgba(0,0,0,0)", title_standoff=10),
        title=_titulo("Lo que llega del Sol y cuánto lo absorbe el silicio",
                      "donde más fotones hay, el silicio ya casi no absorbe: ése es su límite"),
        legend=dict(orientation="h", y=-0.26, x=0, font=dict(size=10.5)),
        margin=dict(r=58),
    )
    return _base(fig, alto=400, margen_superior=58)
