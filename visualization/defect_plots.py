"""Gráficos del mapa por sectores con defectos localizados."""

import numpy as np
import plotly.graph_objects as go

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


def mapa_fotocorriente_local(j_l, contaminacion, dedo_roto, referencia=None):
    """
    Mapa de fotocorriente local por sector, con escala visual tipo infrarrojo.

    **No es una imagen de electroluminiscencia.** La electroluminiscencia se mide
    inyectando corriente en directa y observando la recombinación radiativa, y
    detecta perfectamente los defectos de resistencia serie: es una técnica
    estándar para eso. Este mapa dibuja otra cosa, la fotocorriente local, que por
    construcción no cambia cuando el defecto es resistivo.

    Se conserva porque muestra bien el daño de colección, pero llamarlo
    electroluminiscencia era incorrecto y llevaba a una conclusión falsa sobre lo
    que un instrumento real vería (ver D-25).
    """
    n = j_l.shape[0]
    escala = referencia if referencia is not None else j_l
    z = 100.0 * j_l / escala.max()

    fig = go.Figure(go.Heatmap(
        z=z, colorscale=ESCALA_EL, zmin=0, zmax=100, xgap=1.5, ygap=1.5,
        colorbar=dict(title=dict(text="emisión<br>relativa [%]", side="right"),
                      thickness=12, len=0.85),
        hovertemplate="sector (%{x}, %{y})<br>emisión %{z:.1f} %<extra></extra>",
    ))

    # Contorno de las zonas dañadas, para que se distingan del ruido de fabricación
    for mascara, color, guion in ((contaminacion, "#7ED0FF", "solid"),
                                  (dedo_roto, "#FF9E9E", "dot")):
        for i in range(n):
            for j in range(n):
                if mascara[i, j]:
                    fig.add_shape(type="rect", x0=j - 0.5, x1=j + 0.5,
                                  y0=i - 0.5, y1=i + 0.5,
                                  line=dict(color=color, width=1.6, dash=guion))

    fig.update_xaxes(title="sector", dtick=1, showgrid=False, zeroline=False)
    fig.update_yaxes(title="sector", dtick=1, showgrid=False, zeroline=False,
                     scaleanchor="x", scaleratio=1)
    fig.update_layout(title=_titulo(
        "Fotocorriente local por sector",
        "azul: contaminación metálica  ·  rojo punteado: dedos interrumpidos"))
    return _base(fig, alto=440, margen_superior=62)


def mapa_resistencia(r_s):
    """Resistencia serie local por sector, en escala logarítmica."""
    fig = go.Figure(go.Heatmap(
        z=np.log10(r_s), colorscale=ESCALA_RS, xgap=1.5, ygap=1.5,
        colorbar=dict(title=dict(text="log₁₀ Rs<br>[Ω·cm²]", side="right"),
                      thickness=12, len=0.85),
        hovertemplate="sector (%{x}, %{y})<br>Rs = %{customdata:.3f} Ω·cm²<extra></extra>",
        customdata=r_s,
    ))
    fig.update_xaxes(title="sector", dtick=1, showgrid=False, zeroline=False)
    fig.update_yaxes(title="sector", dtick=1, showgrid=False, zeroline=False,
                     scaleanchor="x", scaleratio=1)
    fig.update_layout(title=_titulo(
        "Resistencia serie local",
        "los sectores que perdieron su dedo tienen que mandar la corriente mucho más lejos"))
    return _base(fig, alto=440, margen_superior=62)


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
