"""Gráficos del ensayo eléctrico: curva corriente-voltaje y malla frontal."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from visualization.figura_animada import FiguraAnimada
from visualization.optics_plots import (ACENTO, BASE, EMISOR, REJILLA, SUAVE, TINTA, _base,
                                        _coma, _titulo)

COLOR_J = "#E5A33F"
COLOR_P = "#5FC49B"
COLOR_IDEAL = "#8894A8"
COLOR_MPP = "#F2F5F8"
CUADROS = 64


def _ejes_iv(fig, j_max, p_max):
    fig.update_xaxes(title="Voltaje aplicado V  [V]")
    fig.update_yaxes(title="Densidad de corriente J  [mA/cm²]", range=[0, j_max * 1.12])
    fig.update_layout(yaxis2=dict(
        title="Potencia P  [mW/cm²]", overlaying="y", side="right",
        range=[0, p_max * 1.12], gridcolor="rgba(0,0,0,0)", title_standoff=10))
    return fig


def curva_iv(curva, curva_ideal=None, mostrar_potencia=True, danada=None):
    """
    Curva corriente-voltaje con la de potencia superpuesta y el punto de máxima
    potencia marcado.

    La curva ideal de fondo es la misma celda sin resistencias parásitas: la
    distancia entre ambas en la esquina es exactamente lo que la resistencia
    serie está costando.
    """
    v, j, p = curva.v, 1e3 * curva.j, 1e3 * curva.p
    fig = go.Figure()

    if curva_ideal is not None:
        fig.add_trace(go.Scatter(
            x=curva_ideal.v, y=1e3 * curva_ideal.j, mode="lines",
            name="Sin resistencias parásitas",
            line=dict(color=COLOR_IDEAL, width=1.6, dash="dot"),
            hovertemplate="V = %{x:.3f} V<br>J = %{y:.2f} mA/cm²<extra></extra>",
        ))

    fig.add_trace(go.Scatter(
        x=v, y=j, mode="lines", name="Corriente J-V",
        line=dict(color=COLOR_J, width=2.8),
        hovertemplate="V = %{x:.3f} V<br>J = %{y:.2f} mA/cm²<extra></extra>",
    ))

    if mostrar_potencia:
        fig.add_trace(go.Scatter(
            x=v, y=p, mode="lines", name="Potencia P-V", yaxis="y2",
            line=dict(color=COLOR_P, width=2.2),
            hovertemplate="V = %{x:.3f} V<br>P = %{y:.2f} mW/cm²<extra></extra>",
        ))

    # Rectangulo de maxima potencia: su area es literalmente Pmax, y la del
    # rectangulo completo Voc x Jsc. El cociente entre ambas es el factor de forma.
    fig.add_shape(type="rect", x0=0, y0=0, x1=curva.v_mpp, y1=1e3 * curva.j_mpp,
                  line=dict(color=ACENTO, width=1.2, dash="dot"),
                  fillcolor=ACENTO, opacity=0.13, layer="below")
    fig.add_shape(type="rect", x0=0, y0=0, x1=curva.v_oc, y1=1e3 * curva.j_sc,
                  line=dict(color=SUAVE, width=1, dash="dot"), layer="below")

    fig.add_trace(go.Scatter(
        x=[curva.v_mpp], y=[1e3 * curva.j_mpp], mode="markers+text",
        name="Máxima potencia", marker=dict(size=11, color=COLOR_MPP,
                                            line=dict(color=ACENTO, width=2)),
        text=[f"  {1e3 * curva.p_max:.2f} mW/cm²"], textposition="middle right",
        textfont=dict(color=TINTA, size=11),
        hovertemplate="MPP<br>V = %{x:.3f} V<br>J = %{y:.2f} mA/cm²<extra></extra>",
    ))

    fig.update_layout(
        title=_titulo("Curva del ensayo eléctrico",
                      "el rectángulo naranja es la potencia extraíble; el gris, "
                      "el ideal Voc×Jsc. Su cociente es el factor de forma"),
        legend=dict(orientation="h", y=-0.26, x=0, font=dict(size=10.5)),
        margin=dict(r=62),
    )
    if danada is not None:
        v_d, j_d, etiqueta = danada
        fig.add_trace(go.Scatter(
            x=v_d, y=1e3 * np.asarray(j_d), mode="lines", name=etiqueta,
            line=dict(color="#E4664A", width=2, dash="dash"),
            hovertemplate="V = %{x:.3f} V<br>J = %{y:.2f} mA/cm²<extra></extra>"))

    return _base(_ejes_iv(fig, 1e3 * curva.j_sc, 1e3 * curva.p_max),
                 alto=440, margen_superior=62)


def barrido_animado(curva):
    """
    El ensayo como lo hace un trazador de curvas real: la fuente barre el voltaje
    y la corriente se registra punto por punto, en tiempo real.

    Es una animación temporal genuina, no un gráfico que cambia con un deslizador:
    hay un barrido que progresa en el tiempo, y cada punto que aparece es la
    solución numérica de la ecuación implícita para ese voltaje exacto.
    """
    v, j, p = curva.v, 1e3 * curva.j, 1e3 * curva.p
    indices = np.linspace(1, len(v) - 1, CUADROS).astype(int)

    cuadros = []
    for k in indices:
        vv, jj, pp = v[:k], j[:k], p[:k]
        alcanzo_mpp = v[k - 1] >= curva.v_mpp
        cuadros.append(go.Frame(
            name=str(k),
            data=[
                go.Scatter(x=vv, y=jj, mode="lines", line=dict(color=COLOR_J, width=2.8)),
                go.Scatter(x=vv, y=pp, mode="lines", yaxis="y2",
                           line=dict(color=COLOR_P, width=2.2)),
                go.Scatter(x=[v[k - 1]], y=[j[k - 1]], mode="markers",
                           marker=dict(size=10, color=COLOR_MPP,
                                       line=dict(color=ACENTO, width=2))),
                go.Scatter(
                    x=[curva.v_mpp] if alcanzo_mpp else [],
                    y=[1e3 * curva.j_mpp] if alcanzo_mpp else [],
                    mode="markers", marker=dict(size=13, symbol="star",
                                                color=ACENTO)),
            ],
            traces=[0, 1, 2, 3],
            layout=go.Layout(annotations=[dict(
                x=0.98, y=0.96, xref="paper", yref="paper", showarrow=False,
                xanchor="right", font=dict(color=TINTA, size=13,
                                           family="IBM Plex Mono, monospace"),
                text=(f"V = {v[k - 1]:.3f} V<br>J = {j[k - 1]:6.2f} mA/cm²"
                      f"<br>P = {p[k - 1]:6.2f} mW/cm²"),
            )]),
        ))

    fig = go.Figure(
        data=[
            go.Scatter(x=[v[0]], y=[j[0]], mode="lines", name="Corriente",
                       line=dict(color=COLOR_J, width=2.8)),
            go.Scatter(x=[v[0]], y=[p[0]], mode="lines", name="Potencia",
                       yaxis="y2", line=dict(color=COLOR_P, width=2.2)),
            go.Scatter(x=[v[0]], y=[j[0]], mode="markers", showlegend=False,
                       marker=dict(size=10, color=COLOR_MPP,
                                   line=dict(color=ACENTO, width=2))),
            go.Scatter(x=[], y=[], mode="markers", name="Máxima potencia",
                       marker=dict(size=13, symbol="star", color=ACENTO)),
        ],
        frames=cuadros,
    )
    fig.update_layout(
        title=_titulo("Trazador de curvas en funcionamiento",
                      "la fuente barre el voltaje y registra la corriente, punto a punto"),
        legend=dict(orientation="h", y=-0.26, x=0, font=dict(size=10.5)),
        margin=dict(r=62),
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.02, y=1.16, xanchor="left",
            bgcolor="#1C2531", bordercolor=REJILLA, font=dict(color=TINTA),
            buttons=[
                dict(label="▶  Iniciar barrido", method="animate",
                     args=[None, dict(frame=dict(duration=55, redraw=True),
                                      fromcurrent=False, mode="immediate")]),
                dict(label="⏸", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
    )
    return _base(_ejes_iv(fig, 1e3 * curva.j_sc, 1e3 * curva.p_max),
                 alto=460, margen_superior=78)


def efecto_resistencia_serie(curvas_por_rs):
    """
    Familia de curvas para distintas resistencias serie.

    Muestra el efecto característico: la resistencia serie aplasta la esquina de
    la curva sin tocar el voltaje de circuito abierto, porque en circuito abierto
    no circula corriente y por lo tanto no hay caída sobre ella.
    """
    fig = go.Figure()
    rs_valores = sorted(curvas_por_rs)
    for k, rs in enumerate(rs_valores):
        c = curvas_por_rs[rs]
        tono = 0.35 + 0.65 * (1 - k / max(len(rs_valores) - 1, 1))
        fig.add_trace(go.Scatter(
            x=c.v, y=1e3 * c.j, mode="lines",
            name=f"Rs = {rs:.2f} Ω·cm²  ·  FF {c.ff:.3f}",
            line=dict(color=f"rgba(229,163,63,{tono:.2f})", width=2.2),
            hovertemplate="V = %{x:.3f} V<br>J = %{y:.2f} mA/cm²<extra></extra>",
        ))
    fig.update_xaxes(title="Voltaje aplicado V  [V]")
    fig.update_yaxes(title="Densidad de corriente J  [mA/cm²]")
    fig.update_layout(
        title=_titulo("Por qué la resistencia serie no toca el voltaje de circuito abierto",
                      "todas las curvas terminan en el mismo punto del eje horizontal"),
        legend=dict(orientation="v", y=0.95, x=0.02, font=dict(size=10.5)),
    )
    return _base(fig, alto=400, margen_superior=58)


def construccion_de_la_curva(curva, j0, j_l, rs, rp, vt_n, cuadros=56):
    """
    Cómo se resuelve la curva: una raíz por cada voltaje.

    A la izquierda, para el voltaje del cuadro, la función que el programa anula.
    Cruza el cero una sola vez, porque crece con la corriente sin volver atrás, y
    ese cruce es la corriente que la celda entrega a ese voltaje. La cruz marca lo
    que daría la forma explícita, la que ignora que la juntura ve un voltaje menor
    por la caída en la resistencia serie: a voltaje bajo coincide, y cerca del punto
    de máxima potencia se separa. A la derecha, la curva que se va armando con las
    raíces ya encontradas.
    """
    j_tope = 1e3 * curva.j_sc * 1.18
    js = np.linspace(0.0, j_tope, 160)                      # mA/cm2

    def residuo(v, j_ma):
        j = j_ma * 1e-3
        v_j = v + rs * j
        expo = np.clip(v_j / vt_n, -600.0, 600.0)
        return 1e3 * (j_l - j0 * (np.exp(expo) - 1.0) - v_j / rp - j)

    def ingenua(v):
        expo = np.clip(v / vt_n, -600.0, 600.0)
        return 1e3 * (j_l - j0 * (np.exp(expo) - 1.0) - v / rp)

    indices = np.unique(np.linspace(0, len(curva.v) - 1, cuadros).astype(int))
    k_mpp = int(np.argmin(np.abs(curva.v - curva.v_mpp)))
    inicial = int(np.argmin(np.abs(indices - k_mpp)))

    def narracion(k):
        v, j = float(curva.v[k]), float(curva.j[k])
        v_j = v + rs * j
        j_d = 1e3 * j0 * (np.exp(np.clip(v_j / vt_n, -600, 600)) - 1.0)
        j_p = 1e3 * v_j / rp
        j_n = ingenua(v)
        exceso = 100.0 * (j_n / (1e3 * j) - 1.0) if j > 1e-9 else 0.0
        return (f"<b>V = {_coma(v, 3)} V</b> · la juntura ve {_coma(v_j, 3)} V, "
                f"{_coma(1e3 * (v_j - v), 1)} mV más que los terminales<br>"
                f"entrega {_coma(1e3 * j, 2)} mA/cm² · el diodo se lleva {_coma(j_d, 2)} y la "
                f"resistencia paralela {_coma(j_p, 3)}<br>"
                f"la forma explícita daría {_coma(j_n, 2)} mA/cm², un {_coma(exceso, 1)} % de más")

    def caja(k):
        return dict(x=0.0, y=1.16, xref="paper", yref="paper", xanchor="left", yanchor="bottom",
                    align="left", showarrow=False, bgcolor="rgba(19,27,38,0.92)",
                    bordercolor=REJILLA, borderpad=7, text=narracion(k),
                    font=dict(color=TINTA, size=12.5))

    fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5], horizontal_spacing=0.1,
                        subplot_titles=["La función que se anula, a ese voltaje",
                                        "La curva que se va armando"])
    titulos = [a.to_plotly_json() for a in fig.layout.annotations]
    for a in titulos:
        a["font"] = dict(size=12.5, color=TINTA)
        a["y"] = 1.0

    k0 = int(indices[inicial])
    fig.add_trace(go.Scatter(x=js, y=residuo(curva.v[k0], js), mode="lines", name="residuo",
                             line=dict(color=COLOR_IDEAL, width=2), showlegend=False,
                             hovertemplate="si la corriente fuera %{x:.2f} mA/cm²<br>"
                                           "faltaría %{y:.2f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=[1e3 * curva.j[k0]], y=[0.0], mode="markers", name="raíz",
                             marker=dict(size=12, color=COLOR_J, line=dict(color="#FFFFFF", width=1.5)),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=[ingenua(curva.v[k0])], y=[0.0], mode="markers", name="explícita",
                             marker=dict(size=11, color=COLOR_IDEAL, symbol="x", line=dict(width=1)),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_hline(y=0, line=dict(color=REJILLA, width=1.2), row=1, col=1)

    fig.add_trace(go.Scatter(x=curva.v[:k0 + 1], y=1e3 * curva.j[:k0 + 1], mode="lines",
                             name="curva", line=dict(color=COLOR_J, width=2.6), showlegend=False,
                             hovertemplate="V = %{x:.3f} V<br>J = %{y:.2f} mA/cm²<extra></extra>"),
                  row=1, col=2)
    fig.add_trace(go.Scatter(x=[curva.v[k0]], y=[1e3 * curva.j[k0]], mode="markers", showlegend=False,
                             marker=dict(size=11, color=COLOR_J, line=dict(color="#FFFFFF", width=1.5)),
                             hoverinfo="skip"), row=1, col=2)
    fig.add_trace(go.Scatter(x=curva.v, y=[ingenua(v) for v in curva.v], mode="lines",
                             name="forma explícita", line=dict(color=COLOR_IDEAL, width=1.4, dash="dot"),
                             showlegend=False, hoverinfo="skip"), row=1, col=2)

    fig.update_xaxes(title="Corriente que se prueba  [mA/cm²]", range=[0, j_tope], row=1, col=1)
    fig.update_yaxes(title="Lo que falta para cerrar la ecuación", row=1, col=1)
    fig.update_xaxes(title="Voltaje V  [V]", range=[0, float(curva.v_oc) * 1.02], row=1, col=2)
    fig.update_yaxes(title="Densidad de corriente  [mA/cm²]", range=[0, j_tope], row=1, col=2)
    fig.update_xaxes(gridcolor=REJILLA, zerolinecolor=REJILLA)
    fig.update_yaxes(gridcolor=REJILLA, zerolinecolor=REJILLA)

    marcos = []
    for m, k in enumerate(indices):
        k = int(k)
        marcos.append(dict(
            name=str(m),
            data=[dict(type="scatter", x=list(js), y=list(residuo(curva.v[k], js))),
                  dict(type="scatter", x=[1e3 * float(curva.j[k])], y=[0.0]),
                  dict(type="scatter", x=[float(ingenua(curva.v[k]))], y=[0.0]),
                  dict(type="scatter", x=list(curva.v[:k + 1]), y=list(1e3 * curva.j[:k + 1])),
                  dict(type="scatter", x=[float(curva.v[k])], y=[1e3 * float(curva.j[k])])],
            traces=[0, 1, 2, 3, 4],
            layout=dict(annotations=titulos + [caja(k)])))

    pasos = [dict(label=(_coma(curva.v[int(k)], 1) if m % 8 == 0 else ""), method="animate",
                  args=[[str(m)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
             for m, k in enumerate(indices)]

    fig.update_layout(
        annotations=titulos + [caja(k0)],
        height=560, margin=dict(l=14, r=18, t=150, b=100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA, size=12),
        updatemenus=[dict(
            type="buttons", showactive=False, direction="left", x=0.0, y=-0.2, xanchor="left",
            yanchor="top", bgcolor="#1C2531", bordercolor=REJILLA, font=dict(color=TINTA, size=12),
            buttons=[dict(label="▶  Recorrer el barrido", method="animate",
                          args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True,
                                           transition=dict(duration=0), mode="immediate")]),
                     dict(label="⏸", method="animate",
                          args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
        sliders=[dict(active=inicial, x=0.3, y=-0.18, len=0.7, xanchor="left", yanchor="top",
                      pad=dict(t=0, b=0), currentvalue=dict(visible=False),
                      font=dict(color=SUAVE, size=10), bgcolor="#1C2531", activebgcolor=ACENTO,
                      bordercolor=REJILLA, tickcolor=REJILLA, steps=pasos)])
    datos = fig.to_dict()
    return FiguraAnimada(data=datos["data"], layout=datos["layout"], cuadros=marcos)
