"""
Gráficos de la Pestaña 2: la eficiencia cuántica de la celda y de sus sectores.

Ninguna función calcula física. Reciben curvas y mapas ya resueltos por la capa de
física y deciden cómo dibujarlos.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from units import cm_a_um
from visualization.figura_animada import FiguraAnimada
from visualization.optics_plots import (ACENTO, C_BASE, C_EMISOR, C_JUNTURA, REJILLA, SUAVE,
                                        TINTA, _base, _coma, _profundidad_texto, _rgba,
                                        _ticks_log, _titulo)

COLOR_EQE = "#E5A33F"
COLOR_IQE = "#5FC49B"
COLOR_COTA = "#8894A8"
COLOR_ABS = "#9B8BE0"
COLOR_ABSORBIDO = "#6C7C96"
ESCALA_IQE = [
    [0.00, "#1B1F2A"], [0.20, "#2E3F63"], [0.40, "#2E6F8E"],
    [0.60, "#3FAE8B"], [0.80, "#C9C05A"], [1.00, "#F2D399"],
]


# ---------------------------------------------------------------------------
# Curvas de la celda
# ---------------------------------------------------------------------------

def curvas_eficiencia(lambda_nm, eqe, iqe, cota, lambda_marcada=None, iqe_abs=None):
    """
    Las eficiencias cuánticas de la celda contra el color, con su cota física.

    La externa cuenta respecto de todos los fotones que llegan; la interna descuenta
    los reflejados; la referida a absorción descuenta además los que atraviesan la
    celda, así que aísla la calidad de la colección.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=lambda_nm, y=100 * cota, mode="lines", name="Cota física 1 − R",
        line=dict(color=COLOR_COTA, width=1.6, dash="dot"),
        hovertemplate="λ = %{x:.0f} nm<br>tope %{y:.1f} %<extra></extra>"))
    if iqe_abs is not None:
        fig.add_trace(go.Scatter(
            x=lambda_nm, y=100 * iqe_abs, mode="lines", name="Por fotón absorbido",
            line=dict(color=COLOR_ABS, width=2.0, dash="dash"),
            hovertemplate="λ = %{x:.0f} nm<br>por fotón absorbido %{y:.1f} %<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=lambda_nm, y=100 * iqe, mode="lines", name="Interna (IQE) = EQE / (1 − R)",
        line=dict(color=COLOR_IQE, width=2.4),
        hovertemplate="λ = %{x:.0f} nm<br>IQE %{y:.1f} %<extra></extra>"))
    fig.add_trace(go.Scatter(
        x=lambda_nm, y=100 * eqe, mode="lines", name="Externa (EQE)",
        line=dict(color=COLOR_EQE, width=2.6),
        hovertemplate="λ = %{x:.0f} nm<br>EQE %{y:.1f} %<extra></extra>"))
    if lambda_marcada is not None:
        fig.add_vline(x=lambda_marcada, line=dict(color=TINTA, width=1.4, dash="dot"))
    fig.update_xaxes(title="Longitud de onda λ  [nm]")
    fig.update_yaxes(title="Eficiencia cuántica  [%]", range=[0, 102])
    fig.update_layout(
        title=_titulo("De cada 100 fotones de cada color, cuántos dan corriente",
                      "la externa nunca puede superar la cota punteada: es la verificación V5"),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, font=dict(size=10.5)))
    return _base(fig, alto=440, margen_superior=62, margen_inferior=100)


def que_informa_cada_parte(lambda_nm, familias, umbral_pp=3.0):
    """
    Tres paneles: qué parte de la curva se mueve al cambiar cada parámetro.

    `familias` es una lista de dicts con `titulo`, `color`, `unidad` y `curvas`, una
    lista de (valor, iqe, es_el_actual). En cada panel se sombrea la zona del espectro
    donde las curvas se separan más de `umbral_pp` puntos: es la parte de la curva que
    informa sobre ese parámetro.
    """
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.03,
                        subplot_titles=[f["titulo"] for f in familias])
    for col, fam in enumerate(familias, start=1):
        curvas = fam["curvas"]
        matriz = 100 * np.array([c[1] for c in curvas])
        separacion = matriz.max(axis=0) - matriz.min(axis=0)
        dentro = separacion > umbral_pp
        i = 0
        while i < len(dentro):
            if dentro[i]:
                j = i
                while j + 1 < len(dentro) and dentro[j + 1]:
                    j += 1
                fig.add_vrect(x0=lambda_nm[i], x1=lambda_nm[j], fillcolor=fam["color"],
                              opacity=0.22, line_width=0, layer="below", row=1, col=col)
                i = j + 1
            else:
                i += 1
        k = int(np.argmax(separacion))
        fig.add_annotation(
            x=750, y=6, xref=f"x{col}" if col > 1 else "x", yref=f"y{col}" if col > 1 else "y",
            yanchor="bottom",
            text=f"cambia hasta {_coma(separacion[k], 0)} puntos, a {lambda_nm[k]:.0f} nm",
            showarrow=False, font=dict(color=fam["color"], size=10.5),
            bgcolor="rgba(13,19,28,0.65)")
        n = len(curvas)
        for m, (valor, iqe, actual) in enumerate(curvas):
            tono = 0.35 + 0.65 * m / max(n - 1, 1)
            fig.add_trace(go.Scatter(
                x=lambda_nm, y=100 * iqe, mode="lines",
                name=f"{fam['formato'](valor)}" + (" · actual" if actual else ""),
                legendgroup=fam["titulo"], legendgrouptitle_text=fam["leyenda"],
                line=dict(color=_rgba(fam["color"], tono), width=3.0 if actual else 1.8,
                          dash="solid"),
                hovertemplate=(f"{fam['leyenda']} {fam['formato'](valor)}<br>"
                               "λ = %{x:.0f} nm<br>IQE %{y:.1f} %<extra></extra>"),
            ), row=1, col=col)
        fig.update_xaxes(title="λ  [nm]", range=[300, 1200], dtick=200, row=1, col=col,
                         gridcolor=REJILLA, zerolinecolor=REJILLA)
    fig.update_yaxes(title="Eficiencia cuántica interna  [%]", range=[0, 102], row=1, col=1)
    fig.update_yaxes(gridcolor=REJILLA, zerolinecolor=REJILLA)
    for anotacion in fig.layout.annotations[:3]:
        anotacion.font = dict(size=12.5, color=TINTA)
    fig.update_layout(
        title=_titulo("Qué parte de la curva informa sobre qué parte de la celda",
                      f"cambia un parámetro por panel; la franja marca dónde las curvas se "
                      f"separan más de {_coma(umbral_pp, 0)} puntos"),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, font=dict(size=10.5),
                    groupclick="toggleitem"))
    return _base(fig, alto=470, margen_superior=96, margen_inferior=120)


# ---------------------------------------------------------------------------
# La celda por sectores
# ---------------------------------------------------------------------------

def relieve_sectores(mapa, lambda_nm, iqe_celda, tau_us, sf, escala_completa=False):
    """
    La eficiencia cuántica interna local como un relieve sobre la celda.

    La superficie pasa por los centros de los sectores; su altura y su color son la IQE
    local, y un plano translúcido marca la IQE de la celda completa, así que los cerros
    que asoman sobre él son zonas que colectan mejor que el promedio. Unir los sectores
    con una superficie es razonable porque la variación de fabricación es suave (D-41).
    Por defecto el eje vertical se ajusta al rango de los sectores; con
    `escala_completa` va de 0 a 100 %.
    """
    n = mapa.shape[0]
    ejes = np.arange(n) + 0.5
    valores = 100 * mapa
    vmin, vmax = float(valores.min()), float(valores.max())
    rango = max(vmax - vmin, 0.5)
    if escala_completa:
        z0, z_techo = 0.0, 100.0
    else:
        z0 = max(vmin - 0.45 * rango, 0.0)
        z_techo = min(vmax + 0.3 * rango, 100.0)

    datos = np.dstack([tau_us, sf])
    fig = go.Figure()
    fig.add_trace(go.Surface(
        x=ejes, y=ejes, z=valores, colorscale=ESCALA_IQE, cmin=vmin, cmax=vmax,
        customdata=datos, name="IQE local",
        colorbar=dict(title=dict(text="IQE local [%]", side="right"), thickness=12, len=0.7),
        contours=dict(z=dict(show=True, usecolormap=True, project_z=True, width=1,
                             highlightwidth=2)),
        lighting=dict(ambient=0.6, diffuse=0.75, specular=0.2, roughness=0.7),
        hovertemplate=("sector (%{x:.0f}, %{y:.0f})<br>IQE %{z:.2f} %<br>"
                       "τₙ local %{customdata[0]:.1f} µs<br>S_f local %{customdata[1]:.2e} cm/s"
                       "<extra></extra>")))
    fig.add_trace(go.Surface(
        x=[0, n], y=[0, n], z=[[100 * iqe_celda] * 2] * 2, showscale=False, opacity=0.28,
        colorscale=[[0, "#E8ECF2"], [1, "#E8ECF2"]], hoverinfo="skip",
        name="IQE de la celda completa", showlegend=True))

    ejes_3d = dict(gridcolor=REJILLA, showbackground=False, zeroline=False)
    fig.update_layout(
        scene=dict(
            xaxis=dict(title="columna", tickvals=list(ejes), ticktext=[str(v) for v in range(n)],
                       range=[0, n], **ejes_3d),
            yaxis=dict(title="fila", tickvals=list(ejes), ticktext=[str(v) for v in range(n)],
                       range=[0, n], **ejes_3d),
            zaxis=dict(title="IQE local [%]", range=[z0, z_techo], **ejes_3d),
            camera=dict(eye=dict(x=1.55, y=-1.5, z=0.95)),
            aspectratio=dict(x=1, y=1, z=0.8)),
        height=600, margin=dict(l=0, r=0, t=76, b=0),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TINTA, size=12),
        legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", bgcolor="rgba(0,0,0,0)",
                    font=dict(size=11)),
        title=_titulo(
            f"Relieve de la eficiencia cuántica interna a {lambda_nm:.0f} nm",
            "la superficie pasa por el centro de cada sector; el plano translúcido es la celda completa"
            + ("" if escala_completa else f"; el eje vertical parte en {_coma(z0, 1)} %, no en cero")))
    return fig


def mapa_de_sectores(valores, titulo, subtitulo, unidad, formato, invertir=False):
    """Mapa plano de una magnitud por sector, con su valor escrito en cada casilla."""
    n = valores.shape[0]
    texto = [[formato(valores[f, c]) for c in range(n)] for f in range(n)]
    escala = [[1 - p, c] for p, c in reversed(ESCALA_IQE)] if invertir else ESCALA_IQE
    fig = go.Figure(go.Heatmap(
        z=valores, x=list(range(n)), y=list(range(n)), colorscale=escala, xgap=2, ygap=2,
        text=texto, texttemplate="%{text}", textfont=dict(size=10, color="#0D131C"),
        colorbar=dict(title=dict(text=unidad, side="right"), thickness=10, len=0.85),
        hovertemplate="sector (%{x}, %{y})<br>%{text} " + unidad + "<extra></extra>"))
    fig.update_xaxes(title="columna", dtick=1, showgrid=False, zeroline=False)
    fig.update_yaxes(title="fila", dtick=1, showgrid=False, zeroline=False,
                     scaleanchor="x", scaleratio=1)
    fig.update_layout(title=_titulo(titulo, subtitulo))
    return _base(fig, alto=430, margen_superior=64)


def barrido_lbic(mapa, lambda_nm, tau_local_us, sf_local):
    """
    Barrido tipo mapeo por haz de luz inducido.

    Imita el instrumento real: una sonda de luz recorre la celda sector por sector y
    va revelando el mapa a medida que mide. Cada valor que aparece es el cálculo real
    de ese sector.
    """
    n = mapa.shape[0]
    ejes = list(range(n))
    orden = [(i, j) for i in range(n) for j in (range(n) if i % 2 == 0 else range(n - 1, -1, -1))]
    comun = dict(type="heatmap", x=ejes, y=ejes, colorscale=ESCALA_IQE, zmin=100 * float(mapa.min()),
                 zmax=100 * float(mapa.max()), xgap=2, ygap=2,
                 colorbar=dict(title=dict(text="IQE [%]", side="right"), thickness=12, len=0.85),
                 hovertemplate="sector (%{x}, %{y})<br>IQE %{z:.2f} %<extra></extra>")
    anillo = dict(size=24, color="rgba(0,0,0,0)", line=dict(color=TINTA, width=2.5))
    cuadros = []
    revelado = np.full((n, n), np.nan)
    for paso, (i, j) in enumerate(orden):
        revelado[i, j] = 100 * mapa[i, j]
        cuadros.append(dict(
            name=str(paso),
            data=[dict(comun, z=revelado.tolist()),
                  dict(type="scatter", x=[j], y=[i], mode="markers", marker=anillo)],
            traces=[0, 1],
            layout=dict(annotations=[dict(
                x=0.5, y=1.06, xref="paper", yref="paper", showarrow=False,
                font=dict(color=TINTA, size=12),
                text=(f"sector ({j}, {i}) · τₙ local {_coma(tau_local_us[i, j], 1)} µs · "
                      f"S_f local {sf_local[i, j]:.1e} cm/s · IQE {_coma(100 * mapa[i, j], 2)} %"))]),
        ))
    base = go.Figure()
    base.update_xaxes(title="columna", dtick=1, showgrid=False, zeroline=False)
    base.update_yaxes(title="fila", dtick=1, showgrid=False, zeroline=False, scaleanchor="x", scaleratio=1)
    base.update_layout(
        height=470, margin=dict(l=14, r=18, t=86, b=48),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA, size=12),
        title=_titulo(f"Sonda recorriendo la celda a {lambda_nm:.0f} nm",
                      "como un mapeo por haz de luz inducido: se mide sector por sector"),
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.02, y=1.16, xanchor="left",
            bgcolor="#1C2531", bordercolor=REJILLA, font=dict(color=TINTA),
            buttons=[
                dict(label="▶  Iniciar barrido", method="animate",
                     args=[None, dict(frame=dict(duration=70, redraw=True), fromcurrent=False,
                                      mode="immediate")]),
                dict(label="⏸", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
            ])])
    completo = (100 * mapa).tolist()
    datos = [dict(comun, z=completo),
             dict(type="scatter", x=[None], y=[None], mode="markers", marker=anillo, showlegend=False)]
    return FiguraAnimada(data=datos, layout=base.to_dict()["layout"], cuadros=cuadros)


def histograma_sectores(mapa, lambda_nm, iqe_celda):
    """Distribución de la eficiencia local entre los sectores."""
    valores = 100 * mapa.ravel()
    fig = go.Figure(go.Histogram(
        x=valores, nbinsx=16, marker=dict(color=COLOR_IQE, line=dict(width=0)),
        hovertemplate="IQE %{x:.2f} %<br>%{y} sectores<extra></extra>"))
    fig.add_vline(x=100 * iqe_celda, line=dict(color=ACENTO, width=2))
    fig.add_annotation(x=100 * iqe_celda, y=1.0, yref="paper",
                       text=f"celda completa {_coma(100 * iqe_celda, 2)} %", showarrow=False,
                       font=dict(color=ACENTO, size=11), xanchor="left", yanchor="bottom", xshift=5)
    fig.update_xaxes(title=f"IQE local a {lambda_nm:.0f} nm  [%]")
    fig.update_yaxes(title="Número de sectores")
    fig.update_layout(title=_titulo(
        "Cuántos sectores hay de cada calidad",
        f"entre {_coma(valores.min(), 2)} % y {_coma(valores.max(), 2)} %"))
    return _base(fig, alto=470, margen_superior=86)


# ---------------------------------------------------------------------------
# Cómo se calcula la eficiencia cuántica
# ---------------------------------------------------------------------------

def construccion_eqe(campo, fc, eqe, iqe, union, lambda_reposo=450.0, paso_nm=15.0):
    """
    La curva de eficiencia cuántica construida color por color.

    A la izquierda, para el color de cada cuadro: dónde se absorben los fotones que
    llegan y cuáles de los pares nacidos llegan a la juntura. Como el eje de
    profundidad es logarítmico, se dibuja la fracción de fotones por cada factor diez
    de profundidad, de modo que el área bajo cada curva es proporcional a la fracción
    que representa: el área verde, dividida por los fotones que llegaron, es la EQE.
    A la derecha, la curva se va dibujando con los colores ya medidos.
    """
    x = campo.x_cm
    x_um = cm_a_um(x)
    W_um = float(cm_a_um(campo.W_cm))
    validos = np.where(x_um >= 1e-3)[0]
    objetivo = np.logspace(-3, np.log10(W_um), 150)
    sel = np.unique(validos[np.clip(np.searchsorted(x_um[validos], objetivo), 0, len(validos) - 1)])
    xs = x_um[sel]
    ln10 = np.log(10.0)
    fc = np.asarray(fc)

    def columna(j):
        g = campo.G[:, j] / campo.Nph[j]
        dens = ln10 * x * g
        absorbida = float(np.trapezoid(g, x))
        return dens[sel], (dens * fc)[sel], absorbida

    lam = campo.lambda_nm
    marcas = np.arange(300.0, 1200.0 + 1e-6, paso_nm)
    indices = [int(np.argmin(np.abs(lam - m))) for m in marcas]
    techo = max(float(np.max(columna(j)[0])) for j in indices) * 1.08
    submuestra = np.arange(0, lam.size, 9)

    def narracion(j):
        R = float(campo.R[j])
        _, _, absorbida = columna(j)
        sr = float(eqe[j]) * float(lam[j]) / 1239.84
        return (f"<b>{lam[j]:.0f} nm</b> · de cada 100 fotones que llegan<br>"
                f"{_coma(100 * R, 1)} se reflejan · {_coma(100 * absorbida, 1)} se absorben · "
                f"{_coma(100 * eqe[j], 1)} llegan a la juntura<br>"
                f"EQE {_coma(100 * eqe[j], 1)} % · IQE {_coma(100 * iqe[j], 1)} % · "
                f"respuesta espectral {_coma(sr, 3)} A/W")

    fig = make_subplots(rows=1, cols=2, column_widths=[0.47, 0.53], horizontal_spacing=0.09,
                        subplot_titles=["Dentro de la celda", "La curva que resulta"])
    titulos = [a.to_plotly_json() for a in fig.layout.annotations]
    for a in titulos:
        a["font"] = dict(size=12.5, color=TINTA)
        a["y"] = 1.0

    x_n, x_p = float(cm_a_um(union.x_n)), float(cm_a_um(union.x_p))
    fig.add_vrect(x0=1e-3, x1=max(x_n, 1e-3), fillcolor=C_EMISOR, opacity=0.10, line_width=0, row=1, col=1)
    fig.add_vrect(x0=x_p, x1=W_um, fillcolor=C_BASE, opacity=0.08, line_width=0, row=1, col=1)
    fig.add_vline(x=x_p, line=dict(color="#E5A33F", width=1.2), row=1, col=1)

    j0 = int(np.argmin(np.abs(lam - lambda_reposo)))
    d0, c0, _ = columna(j0)
    fig.add_trace(go.Scatter(x=xs, y=d0, mode="lines", fill="tozeroy", name="Fotones absorbidos",
                             line=dict(color=COLOR_ABSORBIDO, width=1.2),
                             fillcolor=_rgba(COLOR_ABSORBIDO, 0.45), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=xs, y=c0, mode="lines", fill="tozeroy", name="Pares que llegan a la juntura",
                             line=dict(color=C_JUNTURA, width=1.4),
                             fillcolor=_rgba(C_JUNTURA, 0.65), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=lam, y=100 * (1 - campo.R), mode="lines", name="Cota 1 − R",
                             line=dict(color=COLOR_COTA, width=1.4, dash="dot"),
                             hoverinfo="skip"), row=1, col=2)
    fig.add_trace(go.Scatter(x=lam[submuestra], y=100 * eqe[submuestra], mode="lines", name="EQE",
                             line=dict(color=COLOR_EQE, width=2.6),
                             hovertemplate="λ = %{x:.0f} nm<br>EQE %{y:.1f} %<extra></extra>"), row=1, col=2)
    fig.add_trace(go.Scatter(x=lam[submuestra], y=100 * iqe[submuestra], mode="lines", name="IQE",
                             line=dict(color=COLOR_IQE, width=2.2),
                             hovertemplate="λ = %{x:.0f} nm<br>IQE %{y:.1f} %<extra></extra>"), row=1, col=2)
    fig.add_trace(go.Scatter(x=[lam[j0]], y=[100 * eqe[j0]], mode="markers", showlegend=False,
                             marker=dict(size=11, color=COLOR_EQE, line=dict(color="#FFFFFF", width=1.5)),
                             hoverinfo="skip"), row=1, col=2)
    fig.add_trace(go.Scatter(x=[lam[j0]], y=[100 * iqe[j0]], mode="markers", showlegend=False,
                             marker=dict(size=9, color=COLOR_IQE, line=dict(color="#FFFFFF", width=1.2)),
                             hoverinfo="skip"), row=1, col=2)

    vals, textos = _ticks_log(-3, np.log10(W_um))
    fig.update_xaxes(type="log", range=[-3, np.log10(W_um)], tickvals=[10.0 ** v for v in vals],
                     ticktext=textos, title="profundidad [escala logarítmica]", row=1, col=1)
    fig.update_yaxes(title="fotones por cada factor diez de profundidad", range=[0, techo], row=1, col=1)
    fig.update_xaxes(title="longitud de onda λ  [nm]", range=[300, 1200], row=1, col=2)
    fig.update_yaxes(title="eficiencia cuántica  [%]", range=[0, 102], row=1, col=2)
    fig.update_xaxes(gridcolor=REJILLA, zerolinecolor=REJILLA)
    fig.update_yaxes(gridcolor=REJILLA, zerolinecolor=REJILLA)

    def caja_narracion(j):
        return dict(x=0.0, y=1.2, xref="paper", yref="paper", xanchor="left", yanchor="bottom",
                    align="left", showarrow=False, bgcolor="rgba(19,27,38,0.92)",
                    bordercolor=REJILLA, borderpad=7, text=narracion(j),
                    font=dict(color=TINTA, size=12.5))

    cuadros = []
    for m, j in enumerate(indices):
        d, c, _ = columna(j)
        hasta = submuestra[lam[submuestra] <= lam[j]]
        cuadros.append(dict(
            name=str(m),
            data=[dict(type="scatter", x=xs, y=d), dict(type="scatter", x=xs, y=c),
                  dict(type="scatter", x=lam[hasta], y=100 * eqe[hasta]),
                  dict(type="scatter", x=lam[hasta], y=100 * iqe[hasta]),
                  dict(type="scatter", x=[lam[j]], y=[100 * eqe[j]]),
                  dict(type="scatter", x=[lam[j]], y=[100 * iqe[j]])],
            traces=[0, 1, 3, 4, 5, 6],
            layout=dict(annotations=titulos + [caja_narracion(j)])))

    pasos_slider = [dict(label=(f"{marcas[m]:.0f}" if marcas[m] % 150 == 0 else ""), method="animate",
                         args=[[str(m)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                    for m in range(len(indices))]
    fig.update_layout(
        annotations=titulos + [caja_narracion(j0)],
        height=620, margin=dict(l=14, r=18, t=150, b=150),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA, size=12),
        legend=dict(orientation="h", yanchor="top", y=-0.46, x=0, font=dict(size=10.5)),
        updatemenus=[dict(
            type="buttons", showactive=False, direction="left", x=0.0, y=-0.22, xanchor="left",
            yanchor="top", bgcolor="#1C2531", bordercolor=REJILLA, font=dict(color=TINTA, size=12),
            buttons=[dict(label="▶  Recorrer el espectro", method="animate",
                          args=[None, dict(frame=dict(duration=180, redraw=True), fromcurrent=False,
                                           transition=dict(duration=0), mode="immediate")]),
                     dict(label="⏸", method="animate",
                          args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
        sliders=[dict(active=int(np.argmin(np.abs(marcas - lam[j0]))), x=0.3, y=-0.2, len=0.7,
                      xanchor="left", yanchor="top", pad=dict(t=0, b=0),
                      currentvalue=dict(visible=False), font=dict(color=SUAVE, size=10),
                      bgcolor="#1C2531", activebgcolor="#E5A33F", bordercolor=REJILLA,
                      tickcolor=REJILLA, steps=pasos_slider)])
    datos = fig.to_dict()
    return FiguraAnimada(data=datos["data"], layout=datos["layout"], cuadros=cuadros)
