"""Gráficos del mapa por sectores con defectos localizados."""

import numpy as np
import plotly.graph_objects as go

import constants as C
from visualization.optics_plots import ACENTO, REJILLA, SUAVE, TINTA, _base, _titulo

# Escala tipo electroluminiscencia: la celda emite en el infrarrojo cercano donde
# el material colecta bien, y se apaga donde hay defectos. Asi se ven las imagenes
# reales con las que se inspeccionan paneles.
ESCALA_EL = [
    [0.00, "#0A0608"], [0.25, "#3B1410"], [0.50, "#7A2E12"],
    [0.75, "#C46A1E"], [0.90, "#EEB44A"], [1.00, "#FFF0C4"],
]
ESCALA_RS = [
    [0.00, "#152920"], [0.35, "#2E6F8E"], [0.70, "#C46A1E"], [1.00, "#E58063"],
]
COLOR_SANA = "#8894A8"
COLOR_DANADA = "#E5A33F"


def _lienzo_de_celda(fig, n, fallas, n_reporte=8):
    """La grieta, los sectores aislados y la grilla con que se reporta."""
    lado = C.LADO_CELDA
    paso = lado / n

    if fallas is not None:
        f, c = np.nonzero(fallas.grieta)
        if f.size:
            fig.add_trace(go.Scatter(
                x=(c + 0.5) * paso, y=(f + 0.5) * paso, mode="markers",
                marker=dict(symbol="square", size=max(3.0, 260.0 / n), color="#0B0E13",
                            line=dict(width=0)),
                name="grieta", hovertemplate="grieta<extra></extra>"))
        solo_aislados = fallas.aislados & ~fallas.grieta
        f, c = np.nonzero(solo_aislados)
        if f.size:
            fig.add_trace(go.Scatter(
                x=(c + 0.5) * paso, y=(f + 0.5) * paso, mode="markers",
                marker=dict(symbol="x-thin", size=max(3.0, 200.0 / n),
                            line=dict(color="#E4664A", width=1.1)),
                name="sin camino a la barra",
                hovertemplate="sector aislado<extra></extra>"))

    for k in range(1, n_reporte):
        fig.add_shape(type="line", x0=k * lado / n_reporte, x1=k * lado / n_reporte,
                      y0=0, y1=lado, line=dict(color=REJILLA, width=0.8))
        fig.add_shape(type="line", x0=0, x1=lado, y0=k * lado / n_reporte,
                      y1=k * lado / n_reporte, line=dict(color=REJILLA, width=0.8))
    fig.update_xaxes(title="cm", range=[0, lado], constrain="domain")
    fig.update_yaxes(title="cm", range=[0, lado], scaleanchor="x", scaleratio=1,
                     constrain="domain")
    return fig


def mapa_de_la_celda(celda, fallas, titulo=None, n_reporte=8):
    """
    La corriente que entrega cada trozo de celda, sobre la malla fina.

    Encima van la grieta, los sectores que se quedaron sin camino a la barra
    colectora —que el cálculo encuentra solo— y la grilla de 8 × 8 con la que el
    enunciado pide reportar.
    """
    n = celda.n
    lado = C.LADO_CELDA
    ejes = (np.arange(n) + 0.5) * lado / n
    valores = 1e3 * celda.j_l

    fig = go.Figure(go.Heatmap(
        x=ejes, y=ejes, z=valores, colorscale=ESCALA_EL, zmin=0.0,
        zmax=float(valores.max()),
        colorbar=dict(title=dict(text="mA/cm²", side="right"), thickness=12, len=0.8),
        hovertemplate="x %{x:.1f} cm · y %{y:.1f} cm<br>%{z:.2f} mA/cm²<extra></extra>"))
    _lienzo_de_celda(fig, n, fallas, n_reporte)
    fig.update_layout(
        title=_titulo(titulo or "Corriente que genera cada trozo de celda",
                      f"malla de {n} × {n}; la grilla fina marca los {n_reporte} × {n_reporte} "
                      f"sectores con que se reporta"),
        legend=dict(orientation="h", y=-0.16, x=0, font=dict(size=10.5)))
    return _base(fig, alto=470, margen_superior=78)


def mapa_resistencia(celda, fallas, n_reporte=8):
    """
    La resistencia serie de cada trozo, que sale de su camino hasta la barra.

    La escala es logarítmica porque un sector que perdió su dedo puede tener cien
    veces la resistencia de uno sano, y los aislados, un millón.
    """
    n = celda.n
    lado = C.LADO_CELDA
    ejes = (np.arange(n) + 0.5) * lado / n
    finita = np.where(celda.aislados, np.nan, celda.r_s)
    z = np.log10(np.where(np.isnan(finita), np.nan, np.maximum(finita, 1e-3)))

    fig = go.Figure(go.Heatmap(
        x=ejes, y=ejes, z=z, colorscale=ESCALA_RS,
        colorbar=dict(title=dict(text="Ω·cm²", side="right"), thickness=12, len=0.8,
                      tickmode="array",
                      tickvals=[np.log10(v) for v in (0.5, 1, 2, 5, 10, 30, 100)],
                      ticktext=["0,5", "1", "2", "5", "10", "30", "100"]),
        hovertemplate="x %{x:.1f} cm · y %{y:.1f} cm<br>%{customdata:.2f} Ω·cm²<extra></extra>",
        customdata=finita))
    _lienzo_de_celda(fig, n, fallas, n_reporte)
    fig.update_layout(
        title=_titulo("Lo que le cuesta a cada trozo llegar a la barra",
                      "resistencia serie local, en escala logarítmica"),
        legend=dict(orientation="h", y=-0.16, x=0, font=dict(size=10.5)))
    return _base(fig, alto=470, margen_superior=78)


def electroluminiscencia(v_juntura, aislados, vt_n, voltaje, fallas, n_reporte=8):
    """
    La celda vista como la vería una cámara de electroluminiscencia.

    Se polariza la celda en directa y se fotografía la luz que emite al
    recombinarse: la emisión va con la exponencial del voltaje que ve cada juntura,
    así que un trozo que no recibe voltaje —porque su camino tiene mucha
    resistencia, o porque se quedó sin camino— sale oscuro. Es la técnica con la
    que se inspeccionan paneles, y detecta justamente los defectos de resistencia
    que el mapa de corriente no puede ver.
    """
    n = v_juntura.shape[0]
    lado = C.LADO_CELDA
    ejes = (np.arange(n) + 0.5) * lado / n
    brillo = np.exp((v_juntura - float(np.max(v_juntura))) / vt_n)
    brillo = np.where(aislados, 0.0, brillo)

    fig = go.Figure(go.Heatmap(
        x=ejes, y=ejes, z=brillo, colorscale=ESCALA_EL, zmin=0.0, zmax=1.0,
        colorbar=dict(title=dict(text="brillo", side="right"), thickness=12, len=0.8,
                      tickvals=[0, 0.5, 1], ticktext=["negro", "medio", "máximo"]),
        customdata=v_juntura,
        hovertemplate="x %{x:.1f} cm · y %{y:.1f} cm<br>la juntura ve %{customdata:.3f} V"
                      "<br>brillo relativo %{z:.3f}<extra></extra>"))
    _lienzo_de_celda(fig, n, fallas, n_reporte)
    fig.update_layout(
        title=_titulo(f"Electroluminiscencia simulada, con la celda a {voltaje:.3f} V".replace(".", ","),
                      "el brillo va con la exponencial del voltaje que ve cada juntura"),
        legend=dict(orientation="h", y=-0.16, x=0, font=dict(size=10.5)))
    return _base(fig, alto=470, margen_superior=78)


def comparacion_curvas(v_sana, j_sana, v_danada, j_danada, p_sana, p_danada,
                       etiqueta_danada="Con defecto"):
    """
    Curva global antes y después de introducir el defecto.

    Lo que hay que mirar no es cuánto baja la curva, sino **por dónde** baja: un
    defecto de colección la baja en el eje vertical, sobre la corriente; uno de
    resistencia le hunde la esquina, sobre el factor de forma.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=v_sana, y=1e3 * j_sana, mode="lines", name="Celda sana",
        line=dict(color=COLOR_SANA, width=2, dash="dot"),
        hovertemplate="V = %{x:.3f} V<br>J = %{y:.2f} mA/cm²<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=v_danada, y=1e3 * j_danada, mode="lines", name=etiqueta_danada,
        line=dict(color=COLOR_DANADA, width=2.8),
        hovertemplate="V = %{x:.3f} V<br>J = %{y:.2f} mA/cm²<extra></extra>",
    ))

    for p, color, guion in ((p_sana, COLOR_SANA, "dot"), (p_danada, COLOR_DANADA, "solid")):
        fig.add_shape(type="rect", x0=0, y0=0, x1=p["v_mpp"], y1=1e3 * p["j_mpp"],
                      line=dict(color=color, width=1.2, dash=guion),
                      fillcolor=color, opacity=0.10, layer="below")

    fig.add_trace(go.Scatter(
        x=[p_sana["v_mpp"], p_danada["v_mpp"]],
        y=[1e3 * p_sana["j_mpp"], 1e3 * p_danada["j_mpp"]],
        mode="markers", name="Máxima potencia",
        marker=dict(size=10, color=[COLOR_SANA, COLOR_DANADA],
                    line=dict(color=TINTA, width=1.5)),
        hovertemplate="MPP<br>V = %{x:.3f} V<br>J = %{y:.2f} mA/cm²<extra></extra>",
    ))

    fig.update_xaxes(title="Voltaje aplicado V  [V]")
    fig.update_yaxes(title="Densidad de corriente J  [mA/cm²]",
                     range=[0, 1e3 * max(j_sana[0], j_danada[0]) * 1.12])
    fig.update_layout(
        title=_titulo("El defecto propagado a la curva global",
                      "mira por dónde baja la curva, no solo cuánto"),
        legend=dict(orientation="h", y=-0.26, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=420, margen_superior=58)


def asimetria_de_los_defectos(datos):
    """
    Barras enfrentadas que resumen la diferencia física entre los dos defectos.

    Es la respuesta gráfica a lo que el enunciado pide explicar: por qué un sector
    muerto por colección sí reduce la corriente en proporción a su área, y uno
    muerto por resistencia serie no.
    """
    categorias = ["Área dañada", "Caída de Jsc", "Caída del factor de forma",
                  "Caída de eficiencia"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=categorias, x=datos["coleccion"], name="Defecto de colección",
        orientation="h", marker=dict(color="#7ED0FF"),
        hovertemplate="%{y}: %{x:.2f} %<extra>colección</extra>",
    ))
    fig.add_trace(go.Bar(
        y=categorias, x=datos["resistencia"], name="Defecto de resistencia serie",
        orientation="h", marker=dict(color=ACENTO),
        hovertemplate="%{y}: %{x:.2f} %<extra>resistencia</extra>",
    ))
    fig.update_xaxes(title="Porcentaje  [%]")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        barmode="group", bargap=0.28,
        title=_titulo("Dos defectos, dos daños distintos",
                      "uno se lleva la corriente, el otro el factor de forma"),
        legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=380, margen_superior=58)
