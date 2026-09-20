"""
Gráficos de la Pestaña 1: dónde se absorbe la luz y qué les pasa a los pares.

Ninguna función de este módulo calcula física. Reciben los objetos que ya resolvió
la capa de física —campo óptico, juntura, probabilidades de destino, reparto— y
solo deciden cómo dibujarlos.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from units import cm_a_um
from visualization.colors import escala_espectral, hex_de_longitud_onda

TINTA = "#E8ECF2"
REJILLA = "#2A3542"
SUAVE = "#8894A8"
ACENTO = "#E5A33F"

# Paleta que usan las figuras de las Pestañas 2, 3 y 4.
EMISOR = "#2E6F8E"
BASE = "#5FC49B"
FUGA = "#A0A8B6"
PERDIDA = "#969EAC"

# Regiones del dispositivo. Se usan como fondos, con poca opacidad.
C_EMISOR = "#3B82A8"
C_DEPLECION = "#E5A33F"
C_BASE = "#2F8A7E"
C_ALUMINIO = "#8A8F98"

# Destino de un par. Verde lo que produce corriente; tonos cálidos lo que se pierde.
C_JUNTURA = "#4CC38A"
C_SUPERFICIE = "#E4664A"
C_VOLUMEN = "#C25B8E"

# Pérdidas ópticas: luz que nunca creó un par.
C_MALLA = "#C9CED6"
C_REFLEJO = "#8894A8"
C_FONDO = "#65717F"
C_ESCAPE = "#A9B4C4"


def _base(fig, alto=380, margen_superior=54, margen_inferior=48):
    """
    Estilo común de las figuras planas de toda la aplicación.

    Las Pestañas 2, 3 y 4 importan esta función: su comportamiento sobre los ejes
    primarios no debe cambiar al rehacer las figuras de la Pestaña 1.
    """
    fig.update_layout(
        height=alto,
        margin=dict(l=14, r=18, t=margen_superior, b=margen_inferior),
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


def _rgba(hex_color, alfa):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alfa})"


def _coma(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


def _profundidad_texto(um):
    """Profundidad legible: nanómetros por debajo de la micra, micras por encima."""
    if um < 1.0:
        return f"{um * 1e3:.3g} nm".replace(".", ",")
    return f"{um:.3g} µm".replace(".", ",")


def _ticks_log(lo, hi):
    vals = list(range(int(np.floor(lo)), int(np.ceil(hi)) + 1))
    return vals, [_profundidad_texto(10.0 ** v) for v in vals]


# ---------------------------------------------------------------------------
# Recorrido completo de los fotones
# ---------------------------------------------------------------------------

def sankey_de_fotones(fracciones, fraccion_sombra, j_maxima_ma=None, modo="espectro",
                      lambda_nm=None):
    """
    El recorrido de cien fotones, de la llegada a la corriente, como flujo.

    Cada banda tiene un grosor proporcional a la cantidad de fotones que la
    recorren. Los nodos intermedios son las etapas físicas —cruzar la superficie,
    absorberse en una región— y los de la derecha son los destinos finales. Los
    porcentajes se refieren a todos los fotones que llegan a la celda, incluida la
    parte tapada por la malla.
    """
    k = 1.0 - fraccion_sombra
    f = {c: 100.0 * k * v for c, v in fracciones.items()}
    umbral = 0.005

    def pct(v):
        return _coma(v, 2 if v < 1 else 1) + " %"

    em = f["emisor_superficie"] + f["emisor_volumen"] + f["emisor_colectados"]
    ba = f["base_volumen"] + f["base_superficie"] + f["base_colectados"]
    col = f["emisor_colectados"] + f["deplecion"] + f["base_colectados"]
    entran = 100.0 * k - f["reflejados"]

    corriente = "Corriente eléctrica"
    if modo == "espectro" and j_maxima_ma is not None:
        corriente += f" · {_coma(j_maxima_ma * col / 100.0, 2)} mA/cm²"

    # (clave, etiqueta, valor, color, columna)
    candidatos = [
        ("llegan", "Fotones que llegan", 100.0, "#AEB8C6", 0),
        ("malla", "Chocan con la malla de plata", 100.0 * fraccion_sombra, C_MALLA, 1),
        ("silicio", "Llegan al silicio", 100.0 * k, "#9AA6B6", 1),
        ("refleja", "Se reflejan en la superficie", f["reflejados"], C_REFLEJO, 2),
        ("entran", "Entran al silicio", entran, "#6FA8DC", 2),
        ("aluminio", "Llegan al fondo y los absorbe el aluminio", f["aluminio"], C_FONDO, 3),
        ("escapan", "Rebotan en el aluminio y escapan", f["escapan"], C_ESCAPE, 3),
        ("emisor", "Se absorben en el emisor", em, C_EMISOR, 3),
        ("deplecion", "Se absorben en la zona de depleción", f["deplecion"], C_DEPLECION, 3),
        ("base", "Se absorben en la base", ba, C_BASE, 3),
        ("sup_f", "Mueren en la superficie frontal", f["emisor_superficie"], C_SUPERFICIE, 4),
        ("vol_e", "Se recombinan en el volumen del emisor", f["emisor_volumen"], C_VOLUMEN, 4),
        ("vol_b", "Se recombinan en el volumen de la base", f["base_volumen"], C_VOLUMEN, 4),
        ("sup_t", "Mueren en la cara trasera", f["base_superficie"], C_SUPERFICIE, 4),
        ("juntura", "Llegan a la juntura p-n", col, C_JUNTURA, 4),
        ("corriente", corriente, col, C_JUNTURA, 5),
    ]
    nodos = [c for c in candidatos if c[2] >= umbral]
    indice = {c[0]: i for i, c in enumerate(nodos)}

    enlaces_def = [
        ("llegan", "malla", 100.0 * fraccion_sombra), ("llegan", "silicio", 100.0 * k),
        ("silicio", "refleja", f["reflejados"]), ("silicio", "entran", entran),
        ("entran", "aluminio", f["aluminio"]), ("entran", "escapan", f["escapan"]),
        ("entran", "emisor", em), ("entran", "deplecion", f["deplecion"]),
        ("entran", "base", ba),
        ("emisor", "sup_f", f["emisor_superficie"]), ("emisor", "vol_e", f["emisor_volumen"]),
        ("emisor", "juntura", f["emisor_colectados"]),
        ("deplecion", "juntura", f["deplecion"]),
        ("base", "vol_b", f["base_volumen"]), ("base", "sup_t", f["base_superficie"]),
        ("base", "juntura", f["base_colectados"]),
        ("juntura", "corriente", col),
    ]
    enlaces = [(a, b, v) for a, b, v in enlaces_def
               if v >= umbral and a in indice and b in indice]

    columnas_x = (0.001, 0.15, 0.31, 0.50, 0.75, 0.999)
    x_nodo, y_nodo = [], []
    for columna in range(6):
        en_col = [c for c in nodos if c[4] == columna]
        total = sum(c[2] for c in en_col)
        margen = 0.06 * max(total, 1e-9)
        altura = total + margen * max(len(en_col) - 1, 0)
        acumulado = 0.0
        for c in en_col:
            centro = (acumulado + c[2] / 2.0) / max(altura, 1e-9)
            y_nodo.append(0.04 + 0.92 * centro)
            x_nodo.append(columnas_x[columna])
            acumulado += c[2] + margen
    # Reordenar x,y según el orden de `nodos`, que es el de `candidatos` filtrado
    orden = [c for columna in range(6) for c in nodos if c[4] == columna]
    posicion = {c[0]: (x_nodo[i], y_nodo[i]) for i, c in enumerate(orden)}

    j_por_pct = (j_maxima_ma / 100.0) if (modo == "espectro" and j_maxima_ma) else None
    hover_enlace = [
        (f"{pct(v)} de los fotones que llegan"
         + (f"<br>equivale a {_coma(j_por_pct * v, 2)} mA/cm²" if j_por_pct else ""))
        for _, _, v in enlaces
    ]

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        valueformat=".2f",
        node=dict(
            label=[f"{c[1]} · {pct(c[2])}" if c[0] != "corriente" else c[1] for c in nodos],
            color=[c[3] for c in nodos],
            x=[posicion[c[0]][0] for c in nodos],
            y=[posicion[c[0]][1] for c in nodos],
            pad=14, thickness=16,
            line=dict(color="rgba(0,0,0,0)", width=0),
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=[indice[a] for a, _, _ in enlaces],
            target=[indice[b] for _, b, _ in enlaces],
            value=[v for _, _, v in enlaces],
            color=[_rgba(nodos[indice[b]][3], 0.38) for _, b, _ in enlaces],
            customdata=hover_enlace,
            hovertemplate="%{source.label}<br>→ %{target.label}<br>%{customdata}<extra></extra>",
        ),
        textfont=dict(color=TINTA, size=11.5),
    ))
    titulo = ("El recorrido de 100 fotones del Sol hasta la corriente" if modo == "espectro"
              else f"El recorrido de 100 fotones de {lambda_nm:.0f} nm hasta la corriente")
    fig.update_layout(title=_titulo(
        titulo, "el grosor de cada banda es proporcional a la cantidad de fotones que la "
                "recorre; a la derecha quedan los destinos finales"))
    return _base(fig, alto=580, margen_superior=64, margen_inferior=16)


# ---------------------------------------------------------------------------
# Dónde se absorbe cada color
# ---------------------------------------------------------------------------

# Escala perceptual «inferno», escrita punto por punto, con un solo cambio: su negro
# original, #000004, es uno de los colores que el tema de Streamlit usa como marcador
# interno y reemplaza por un color de su paleta. El cero del mapa salía rojo. Se usa
# un negro equivalente que no coincide con esos marcadores.
_ESCALA_INFERNO = [
    [0.000, "#03020C"], [0.111, "#1B0C41"], [0.222, "#4A0C6B"], [0.333, "#781C6D"],
    [0.444, "#A52C60"], [0.556, "#CF4446"], [0.667, "#ED6925"], [0.778, "#FB9B06"],
    [0.889, "#F7D13D"], [1.000, "#FCFFA4"],
]


def _absorcion_acumulada(campo, indices):
    """
    Fracción de los fotones que entraron ya absorbida antes de cada profundidad.

    Se integra la generación del modelo, no la exponencial cerrada, para que con el
    reflector encendido la figura incluya también la luz que vuelve del aluminio.
    """
    x = campo.x_cm
    G = campo.G[:, indices]
    entra = campo.Nph[indices] * (1.0 - campo.R[indices])
    paso = np.diff(x)[:, None]
    acum = np.concatenate([np.zeros((1, len(indices))),
                           np.cumsum(paso * (G[:-1] + G[1:]) / 2.0, axis=0)])
    return acum / np.maximum(entra, 1e-300)


def _profundidad_de_fraccion(x_cm, acum, objetivo):
    """Profundidad en µm a la que la absorción acumulada alcanza un objetivo; NaN si no llega."""
    salida = np.full(acum.shape[1], np.nan)
    for j in range(acum.shape[1]):
        col = acum[:, j]
        if col[-1] < objetivo:
            continue
        i = int(np.argmax(col >= objetivo))
        if i == 0:
            salida[j] = cm_a_um(x_cm[1])
            continue
        salida[j] = cm_a_um(np.interp(objetivo, [col[i - 1], col[i]], [x_cm[i - 1], x_cm[i]]))
    return salida


def mapa_absorcion(campo, union, lambda_marcada=None, paso_lambda=3, capas_por_decada=12):
    """
    Mapa λ-x: probabilidad de que un fotón que entró se absorba en cada capa.

    La celda se divide en capas cada vez más gruesas hacia el fondo, todas del mismo
    ancho en escala logarítmica (doce por década de profundidad). Con esa división,
    la probabilidad por capa es comparable entre colores sin ninguna normalización
    artificial: cada color dibuja una franja brillante centrada en su profundidad
    característica, y la franja se corre hacia el fondo de la celda a medida que
    aumenta la longitud de onda.
    """
    idx = np.arange(0, campo.lambda_nm.size, paso_lambda)
    lam = campo.lambda_nm[idx]
    acum = _absorcion_acumulada(campo, idx)

    W_um = float(cm_a_um(campo.W_cm))
    lo, hi = -3.0, float(np.log10(W_um))
    n_capas = int(np.ceil((hi - lo) * capas_por_decada))
    bordes_log = np.linspace(lo, hi, n_capas + 1)
    bordes_cm = (10.0 ** bordes_log) * 1e-4

    F = np.empty((n_capas + 1, lam.size))
    for j in range(lam.size):
        F[:, j] = np.interp(bordes_cm, campo.x_cm, acum[:, j])
    prob = np.diff(F, axis=0)
    prob[0, :] += F[0, :]          # el primer nanómetro se suma a la primera capa
    centros = 0.5 * (bordes_log[:-1] + bordes_log[1:])
    z = 100.0 * prob

    desde = [_profundidad_texto(10.0 ** b) for b in bordes_log[:-1]]
    hasta = [_profundidad_texto(10.0 ** b) for b in bordes_log[1:]]
    # Filas: colores; columnas: capas. La profundidad va en el eje horizontal y la
    # longitud de onda en el vertical, de modo que al avanzar hacia adentro de la celda
    # se lee cómo la absorción pasa a colores cada vez más largos.
    z = z.T
    customdata = np.empty((lam.size, n_capas, 2), dtype=object)
    for i in range(n_capas):
        customdata[:, i, 0] = "la superficie" if i == 0 else desde[i]
        customdata[:, i, 1] = hasta[i]

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.022, 0.978],
                        horizontal_spacing=0.006)
    fig.add_trace(go.Heatmap(
        x=[0], y=lam, z=[[l] for l in lam], colorscale=escala_espectral(lam), showscale=False,
        hoverinfo="skip"), row=1, col=1)
    zmax = float(max(7.5, np.percentile(z, 99.0)))
    fig.add_trace(go.Heatmap(
        x=centros, y=lam, z=z, colorscale=_ESCALA_INFERNO, zmin=0.0, zmax=zmax,
        customdata=customdata,
        colorbar=dict(title=dict(text="% absorbido<br>en la capa", side="top"),
                      thickness=12, len=0.85, ticksuffix=" %"),
        hovertemplate=("λ = %{y:.0f} nm<br>capa desde %{customdata[0]} hasta "
                       "%{customdata[1]}<br>aquí se absorbe el %{z:.2f} % de los "
                       "fotones de este color que entraron<extra></extra>"),
    ), row=1, col=2)

    for objetivo, nombre, estilo in ((0.5, "50 % ya absorbido", dict(color=TINTA, width=1.6, dash="dash")),
                                     (0.9, "90 % ya absorbido", dict(color="#8FD6FF", width=1.8))):
        prof = _profundidad_de_fraccion(campo.x_cm, acum, objetivo)
        fig.add_trace(go.Scatter(
            x=np.log10(prof), y=lam, mode="lines", name=nombre, line=estilo,
            hovertemplate="λ = %{y:.0f} nm<br>" + nombre + " a %{customdata}<extra></extra>",
            customdata=[_profundidad_texto(p) if np.isfinite(p) else "—" for p in prof],
        ), row=1, col=2)

    x_n = float(cm_a_um(union.x_n))
    x_p = float(cm_a_um(union.x_p))
    fig.add_vrect(x0=np.log10(max(x_n, 1e-3)), x1=np.log10(x_p), fillcolor=C_DEPLECION,
                  opacity=0.35, line_width=0, row=1, col=2)
    fig.add_vline(x=np.log10(x_p), line=dict(color=C_DEPLECION, width=1.2), row=1, col=2)
    fig.add_vline(x=hi, line=dict(color="#C4C9D1", width=2), row=1, col=2)
    for x, texto, color in ((0.5 * (lo + np.log10(max(x_n, 1e-3))), "emisor n", "#8FC3E0"),
                            (0.5 * (np.log10(x_p) + hi), "base p", "#8FD6C6")):
        fig.add_annotation(x=x, xref="x2", y=1.0, yref="paper", text=texto, showarrow=False,
                           yanchor="bottom", font=dict(color=color, size=11))
    for x, texto, color in ((np.log10(x_p), "juntura p-n", C_DEPLECION),
                            (hi, "contacto de aluminio", "#C4C9D1")):
        fig.add_annotation(x=x, xref="x2", y=0.97, yref="paper", text=texto, showarrow=False,
                           textangle=-90, xanchor="right", yanchor="top", xshift=-3,
                           font=dict(color=color, size=10.5), bgcolor="rgba(13,19,28,0.6)")

    if lambda_marcada is not None:
        fig.add_hline(y=lambda_marcada, line=dict(color=hex_de_longitud_onda(lambda_marcada),
                                                  width=2, dash="dot"), row=1, col=2)

    vals, textos = _ticks_log(lo, hi)
    fig.update_xaxes(gridcolor=REJILLA, zerolinecolor=REJILLA)
    fig.update_yaxes(gridcolor=REJILLA, zerolinecolor=REJILLA)
    fig.update_xaxes(visible=False, row=1, col=1)
    fig.update_xaxes(title="Profundidad desde la superficie iluminada  [escala logarítmica]",
                     range=[lo, hi], tickvals=vals, ticktext=textos, row=1, col=2)
    fig.update_yaxes(title="Longitud de onda λ  [nm]", range=[float(lam[0]), float(lam[-1])],
                     row=1, col=1)
    fig.update_layout(
        title=_titulo("¿A qué profundidad se absorbe cada color?",
                      "probabilidad de que un fotón que entró al silicio se absorba en cada capa<br>"
                      "las líneas marcan dónde ya se absorbió el 50 % y el 90 % de cada color"),
        legend=dict(orientation="h", yanchor="top", y=-0.13, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=620, margen_superior=112, margen_inferior=100)

LAMBDAS_RAYOS = (350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850,
                 900, 950, 1000, 1050, 1100, 1150)


def rayos_de_penetracion(campo, union, lambda_marcada=None):
    """
    Un rayo por color, bajando por un corte de la celda hasta donde se apaga.

    El tramo grueso llega a la profundidad 1/α, donde ya se absorbió el 63 % de los
    fotones que entraron; el tramo fino sigue hasta donde se absorbió el 90 %. La
    curva punteada es la misma profundidad 1/α para todos los colores, que es la
    salida que pide el enunciado superpuesta al espesor de la celda.
    """
    W_um = float(cm_a_um(campo.W_cm))
    x_n = float(cm_a_um(union.x_n))
    x_p = float(cm_a_um(union.x_p))
    lo = -3.0
    fondo = float(np.log10(W_um))
    abajo = float(np.log10(W_um * 6.0))

    fig = go.Figure()
    bandas = (
        (lo, np.log10(max(x_n, 1e-3)), C_EMISOR, 0.20, "emisor n"),
        (np.log10(max(x_n, 1e-3)), np.log10(x_p), C_DEPLECION, 0.55, None),
        (np.log10(x_p), fondo, C_BASE, 0.16, "base p"),
        (fondo, fondo + 0.07, C_ALUMINIO, 0.75, None),
        (fondo + 0.07, abajo, "#0D131C", 0.0, None),
    )
    for y0, y1, color, opacidad, texto in bandas:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=opacidad, line_width=0,
                      layer="below")
        if texto:
            fig.add_annotation(x=1.0, xref="paper", y=0.5 * (y0 + y1), text=texto,
                               showarrow=False, xanchor="right", xshift=-4,
                               font=dict(color=TINTA, size=11))
    fig.add_annotation(x=1.0, xref="paper", y=np.log10(x_p), text="juntura p-n",
                       showarrow=False, xanchor="right", xshift=-4, yshift=-9,
                       font=dict(color=C_DEPLECION, size=11))
    fig.add_annotation(x=1.0, xref="paper", y=fondo + 0.035, text="aluminio",
                       showarrow=False, xanchor="right", xshift=-4,
                       font=dict(color="#0D131C", size=10.5))
    fig.add_annotation(x=1.0, xref="paper", y=0.5 * (fondo + 0.07 + abajo),
                       text="fuera de la celda", showarrow=False, xanchor="right",
                       xshift=-4, font=dict(color=SUAVE, size=11))

    # Curva continua 1/α(λ), recortada al rango dibujado
    prof = cm_a_um(1.0 / campo.alpha)
    y_curva = np.log10(prof)
    y_curva = np.where(y_curva <= abajo, y_curva, np.nan)
    fig.add_trace(go.Scatter(
        x=campo.lambda_nm, y=y_curva, mode="lines", name="1/α para todos los colores",
        line=dict(color=TINTA, width=1.2, dash="dot"),
        hovertemplate="λ = %{x:.0f} nm<br>1/α = %{customdata}<extra></extra>",
        customdata=[_profundidad_texto(p) for p in prof],
    ))

    colores = sorted(set(LAMBDAS_RAYOS) | ({int(round(lambda_marcada))} if lambda_marcada else set()))
    for lam in colores:
        i = int(np.argmin(np.abs(campo.lambda_nm - lam)))
        a = float(campo.alpha[i])
        d63 = float(cm_a_um(1.0 / a))
        d90 = float(cm_a_um(np.log(10.0) / a))
        llega_fondo = float(np.exp(-a * campo.W_cm))
        color = hex_de_longitud_onda(lam)
        marcado = lambda_marcada is not None and lam == int(round(lambda_marcada))
        ancho = 13 if marcado else 8
        texto_hover = (f"{lam} nm<br>el 63 % se absorbe antes de {_profundidad_texto(d63)}"
                       f"<br>el 90 % antes de {_profundidad_texto(d90)}"
                       f"<br>llega al fondo el {_coma(100 * llega_fondo, 1)} % de los que entran")

        fin_grueso = np.log10(min(d63, W_um))
        fig.add_trace(go.Scatter(
            x=[lam, lam], y=[lo, fin_grueso], mode="lines", showlegend=False,
            line=dict(color=color, width=ancho), hovertemplate=texto_hover + "<extra></extra>"))
        if d63 < W_um:
            fig.add_trace(go.Scatter(
                x=[lam, lam], y=[fin_grueso, np.log10(min(d90, W_um))], mode="lines",
                showlegend=False, opacity=0.55, line=dict(color=color, width=max(ancho - 5, 3)),
                hovertemplate=texto_hover + "<extra></extra>"))
        if d90 > W_um:
            simbolo = "triangle-up" if campo.reflector else "x"
            fig.add_trace(go.Scatter(
                x=[lam], y=[fondo], mode="markers", showlegend=False,
                marker=dict(symbol=simbolo, size=11, color=color, line=dict(color="#0D131C", width=1)),
                hovertemplate=texto_hover + ("<br>rebota en el aluminio" if campo.reflector
                                             else "<br>lo absorbe el aluminio") + "<extra></extra>"))
            if campo.reflector:
                # El haz de vuelta: recorre lo que le queda hasta el 90 % hacia arriba.
                resto = d90 - W_um
                tope = np.log10(max(W_um - resto, 1e-3)) if resto < W_um else lo
                fig.add_trace(go.Scatter(
                    x=[lam + 12, lam + 12], y=[fondo, tope], mode="lines", showlegend=False,
                    line=dict(color=color, width=2, dash="dot"), hoverinfo="skip"))
        fig.add_annotation(x=lam, y=lo, text=f"{lam}", showarrow=False, yshift=12,
                           font=dict(color=color if lam > 380 else TINTA,
                                     size=12 if marcado else 10.5))

    for nombre, estilo in (("tramo grueso: se absorbió el 63 %", dict(color=TINTA, width=8)),
                           ("tramo fino: se absorbió el 90 %", dict(color=TINTA, width=3))):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=nombre, line=estilo))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers", name=("▲ rebota en el aluminio" if campo.reflector
                                                   else "× lo absorbe el aluminio"),
        marker=dict(symbol="triangle-up" if campo.reflector else "x", size=10, color=TINTA)))

    vals, textos = _ticks_log(lo, abajo)
    fig.update_yaxes(title="Profundidad desde la superficie iluminada",
                     range=[abajo, lo - 0.18], tickvals=vals, ticktext=textos, showgrid=False)
    fig.update_xaxes(title="Longitud de onda λ  [nm]", range=[315, 1250], showgrid=False)
    fig.update_layout(
        title=_titulo("¿Hasta dónde llega cada color?",
                      "cada rayo baja por un corte de la celda hasta donde el silicio ya absorbió "
                      "casi toda su luz"),
        legend=dict(orientation="h", yanchor="top", y=-0.14, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=580, margen_superior=78, margen_inferior=100)


# ---------------------------------------------------------------------------
# Dónde nacen los pares y qué les pasa
# ---------------------------------------------------------------------------

def _fondos_de_region(fig, union, W_um, x_min_um, etiquetas=True, sub=None):
    x_n = float(cm_a_um(union.x_n))
    x_p = float(cm_a_um(union.x_p))
    sub = sub or {}
    for x0, x1, color, opacidad, texto in (
        (x_min_um, x_n, C_EMISOR, 0.12, "Emisor n" + sub.get("emisor", "")),
        (x_n, x_p, C_DEPLECION, 0.35, None),
        (x_p, W_um, C_BASE, 0.10, "Base p" + sub.get("base", "")),
    ):
        if x1 <= x0:
            continue
        fig.add_vrect(x0=x0, x1=x1, fillcolor=color, opacity=opacidad, line_width=0,
                      layer="below")
        if etiquetas and texto:
            fig.add_annotation(x=np.log10(np.sqrt(x0 * x1)), y=1.0, yref="paper", text=texto,
                               showarrow=False, yanchor="bottom", font=dict(color=TINTA, size=11))
    if etiquetas:
        fig.add_annotation(x=np.log10(0.5 * (x_n + x_p)), y=0.97, yref="paper",
                           text="zona de depleción<br>(juntura p-n)", showarrow=False,
                           yanchor="top", xanchor="right", xshift=-4,
                           font=dict(color=C_DEPLECION, size=10.5),
                           bgcolor="rgba(13,19,28,0.7)")


def generacion_por_destino(x_cm, g, destinos, union, W_um, titulo, unidad, y_max=None):
    """
    La tasa de generación a cada profundidad, repartida según el destino del par.

    La altura total de la curva en cada punto es la tasa de generación G(x) del
    enunciado. Esa altura se divide en tres bandas con las probabilidades de destino
    de un par nacido ahí: la verde son los pares que llegarán a la juntura y se
    convertirán en corriente; las otras dos, los que se recombinarán antes.
    """
    x_um = cm_a_um(x_cm)
    m = x_um >= 1e-3
    xs = x_um[m]
    partes = (
        (g * destinos.fc, "Llegan a la juntura: producen corriente", C_JUNTURA),
        (g * destinos.p_volumen, "Se recombinan en el volumen", C_VOLUMEN),
        (g * destinos.p_superficie, "Mueren en una superficie", C_SUPERFICIE),
    )
    total = float(np.trapezoid(g, x_cm))

    fig = go.Figure()
    for y, nombre, color in partes:
        frac = float(np.trapezoid(y, x_cm)) / total if total > 0 else 0.0
        fig.add_trace(go.Scatter(
            x=xs, y=y[m], mode="lines", stackgroup="g",
            name=f"{nombre} · {_coma(100 * frac, 1)} % de los pares",
            line=dict(width=0.6, color=color), fillcolor=_rgba(color, 0.62),
            hovertemplate="x = %{x:.3g} µm<br>%{y:.3e} " + unidad + "<extra>" + nombre + "</extra>",
        ))
    _fondos_de_region(fig, union, W_um, float(xs[0]))

    fig.update_xaxes(title="Profundidad desde la superficie  [µm, escala logarítmica]",
                     type="log", range=[np.log10(xs[0]), np.log10(W_um)])
    fig.update_yaxes(title=f"Tasa de generación  [{unidad}]",
                     range=[0, y_max] if y_max else None, exponentformat="power")
    fig.update_layout(
        title=_titulo(titulo, "altura total: la tasa de generación G(x); cada banda, los pares "
                              "nacidos a esa profundidad que terminan en cada destino"),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=470, margen_superior=84, margen_inferior=104)


def destino_segun_profundidad(x_cm, destinos, union, W_um, tr, marca_um=None, marca_texto=None):
    """
    De cada cien pares nacidos a una profundidad, cuántos terminan en cada destino.

    El borde superior de la banda verde es la probabilidad de colección f_c(x) del
    enunciado. Las otras dos bandas la completan: lo que le falta a la colección
    para llegar a cien se reparte entre la superficie más cercana y el volumen.
    """
    x_um = cm_a_um(x_cm)
    m = x_um >= 1e-3
    xs = x_um[m]
    fig = go.Figure()
    for y, nombre, color in (
        (destinos.fc, "Llega a la juntura", C_JUNTURA),
        (destinos.p_volumen, "Se recombina en el volumen", C_VOLUMEN),
        (destinos.p_superficie, "Muere en la superficie más cercana", C_SUPERFICIE),
    ):
        fig.add_trace(go.Scatter(
            x=xs, y=100 * y[m], mode="lines", stackgroup="p", name=nombre,
            line=dict(width=0.6, color=color), fillcolor=_rgba(color, 0.62),
            hovertemplate="nacido a %{x:.3g} µm<br>%{y:.1f} de cada 100<extra>" + nombre + "</extra>",
        ))
    fig.add_trace(go.Scatter(
        x=xs, y=100 * destinos.fc[m], mode="lines", name="Probabilidad de colección f_c(x)",
        line=dict(color=TINTA, width=2), hoverinfo="skip"))

    _fondos_de_region(fig, union, W_um, float(xs[0]), sub={
        "emisor": f" · L_p = {_profundidad_texto(cm_a_um(tr.L_p))}",
        "base": f" · L_n = {_profundidad_texto(cm_a_um(tr.L_n))}",
    })
    if marca_um is not None and np.isfinite(marca_um):
        fig.add_vline(x=marca_um, line=dict(color=ACENTO, width=1.6, dash="dot"))
        fig.add_annotation(x=np.log10(marca_um), y=0.06, yref="paper", text=marca_texto,
                           showarrow=False, xanchor="left", xshift=5,
                           font=dict(color=ACENTO, size=11), bgcolor="rgba(13,19,28,0.65)")

    fig.update_xaxes(title="Profundidad a la que nació el par  [µm, escala logarítmica]",
                     type="log", range=[np.log10(xs[0]), np.log10(W_um)])
    fig.update_yaxes(title="Destino de cada 100 pares nacidos ahí", range=[0, 100.5])
    fig.update_layout(
        title=_titulo("Si un par nace a esta profundidad, ¿qué le pasa?",
                      "de cada 100 pares nacidos en cada punto: cuántos llegan a la juntura, "
                      "cuántos se recombinan en el volumen y cuántos mueren en una superficie"),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, font=dict(size=10.5)),
    )
    return _base(fig, alto=470, margen_superior=84, margen_inferior=104)
