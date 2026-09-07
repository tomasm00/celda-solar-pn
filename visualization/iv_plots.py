"""Gráficos del ensayo eléctrico: curva corriente-voltaje y malla frontal."""

import numpy as np
import plotly.graph_objects as go

from visualization.optics_plots import ACENTO, BASE, EMISOR, REJILLA, SUAVE, TINTA, _base, _titulo

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


def curva_iv(curva, curva_ideal=None, mostrar_potencia=True):
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


def compromiso_malla(n_dedos, sombras, resistencias, eficiencias, n_actual):
    """
    El compromiso de la malla frontal: sombra contra resistencia.

    Al agregar dedos la resistencia serie cae —la del emisor como el inverso del
    cuadrado del número, la de los dedos como su inverso— pero el sombreado crece
    proporcionalmente. La eficiencia tiene por eso un máximo.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=n_dedos, y=100 * np.array(sombras), mode="lines", name="Sombreado",
        line=dict(color=SUAVE, width=2),
        hovertemplate="%{x} dedos<br>tapan el %{y:.2f} % del área<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=n_dedos, y=resistencias, mode="lines", name="Resistencia serie",
        line=dict(color=EMISOR, width=2), yaxis="y2",
        hovertemplate="%{x} dedos<br>Rs = %{y:.3f} Ω·cm²<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=n_dedos, y=100 * np.array(eficiencias), mode="lines", name="Eficiencia",
        line=dict(color=ACENTO, width=3), yaxis="y3",
        hovertemplate="%{x} dedos<br>η = %{y:.3f} %<extra></extra>",
    ))

    k = int(np.argmax(eficiencias))
    fig.add_vline(x=n_dedos[k], line=dict(color=ACENTO, width=1.5, dash="dash"))
    fig.add_annotation(x=n_dedos[k], y=1.0, yref="paper",
                       text=f"óptimo · {n_dedos[k]} dedos", showarrow=False,
                       font=dict(color=ACENTO, size=11), xanchor="left",
                       yanchor="bottom", xshift=4)
    fig.add_vline(x=n_actual, line=dict(color=TINTA, width=1.4, dash="dot"))

    fig.update_xaxes(title="Número de dedos de plata")
    fig.update_yaxes(title="Área sombreada  [%]")
    fig.update_layout(
        yaxis2=dict(title="Rs  [Ω·cm²]", overlaying="y", side="right",
                    gridcolor="rgba(0,0,0,0)", title_standoff=8),
        yaxis3=dict(overlaying="y", side="right", position=1.0, showgrid=False,
                    showticklabels=False),
        title=_titulo("El compromiso de la malla frontal",
                      "más dedos extraen mejor la corriente pero tapan más luz"),
        legend=dict(orientation="h", y=-0.26, x=0, font=dict(size=10.5)),
        margin=dict(r=62),
    )
    return _base(fig, alto=420, margen_superior=62)


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
