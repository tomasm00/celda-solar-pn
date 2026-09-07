"""
Vista tridimensional de la celda con fotones penetrando.

La animación no es decorativa. Cada fotón individual se sortea del modelo real:

  - En modo de un solo color, la profundidad a la que muere sale de la
    distribución de Beer-Lambert de ese color, y la probabilidad de rebotar es
    la reflectancia medida de Green (2008).

  - En modo espectro completo, además se sortea la longitud de onda de cada
    fotón con probabilidad proporcional al flujo espectral AM1.5G real. Es un
    muestreo de Monte Carlo del espectro: pocos fotones dibujados, pero
    estadísticamente fieles al espectro solar.

Sorteo de la profundidad: la probabilidad de que un fotón sobreviva hasta x es
e^{-alpha x}, así que basta tomar un número uniforme U en (0,1) y despejar
x = -ln(U)/alpha. Los que caen más allá del espesor son los que atraviesan.

El número de fotones dibujados es proporcional a la irradiancia, porque eso es
literalmente lo que significa subir o bajar los soles: más o menos fotones por
segundo llegando a la misma superficie.
"""

import numpy as np
import plotly.graph_objects as go

from units import cm_a_um
from visualization.colors import hex_de_longitud_onda

ANCHO_LATERAL = 100.0
FOTONES_POR_SOL = 190
N_CUADROS = 42
ALTURA_ENTRADA = 0.22

COLOR_EMISOR = "#2E6F8E"
COLOR_DEPLEXION = "#E5A33F"
COLOR_BASE = "#1B3A4B"
COLOR_CONTACTO = "#8A8F98"
COLOR_PAR = "#F2F5F8"
COLOR_RECOMBINADO = "#7A8598"


def _caja(z0, z1, color, opacidad, nombre, mostrar_leyenda=True):
    a = ANCHO_LATERAL
    xs = [0, a, a, 0, 0, a, a, 0]
    ys = [0, 0, a, a, 0, 0, a, a]
    zs = [z0, z0, z0, z0, z1, z1, z1, z1]
    return go.Mesh3d(
        x=xs, y=ys, z=zs,
        i=[0, 0, 0, 0, 4, 4, 6, 6, 1, 1, 2, 2],
        j=[1, 2, 4, 5, 5, 6, 7, 2, 5, 2, 3, 6],
        k=[2, 3, 5, 1, 6, 7, 3, 3, 6, 6, 7, 7],
        color=color, opacity=opacidad, name=nombre,
        flatshading=True, hoverinfo="name", showlegend=mostrar_leyenda,
    )


def _muestrear_longitudes(lam, nph, n, rng):
    """
    Sortea longitudes de onda con probabilidad proporcional al flujo de fotones.

    No se sortea uniformemente en el espectro: se sortea según cuántos fotones
    de cada color trae realmente el Sol, de modo que la nube de puntos reproduce
    la composición del espectro AM1.5G.
    """
    pesos = nph * np.gradient(lam)
    acumulada = np.cumsum(pesos)
    acumulada = acumulada / acumulada[-1]
    indices = np.searchsorted(acumulada, rng.random(n))
    return np.clip(indices, 0, len(lam) - 1)


def _sortear_fotones(n, alpha, reflectancia, W_cm, rng):
    """Destino de cada fotón: rebota, muere a cierta profundidad, o atraviesa."""
    rebota = rng.random(n) < reflectancia
    u = rng.random(n)
    x_abs_cm = -np.log(np.clip(u, 1e-12, 1.0)) / alpha
    return rebota, x_abs_cm > W_cm, cm_a_um(x_abs_cm)


def figura_celda_3d(lambda_nm, alpha_cm, reflectancia, d_n_um, W_um, juntura=None,
                    profundidad_vista_um=None, irradiancia=1.0, modo="mono",
                    espectro=None, exagerar_deplexion=False, coleccion=None,
                    semilla=7):
    """
    Bloque de la celda con fotones cayendo.

    modo='mono'      : todos los fotones del color seleccionado
    modo='espectro'  : cada fotón con su color sorteado del espectro solar real
    espectro         : dict con lambda_nm, alpha, R, Nph (requerido en modo espectro)
    juntura          : objeto Juntura, para dibujar la zona de deplexión a escala
    coleccion        : tupla (x_um, fc) con el perfil de probabilidad de colección.
                       Si se entrega, cada par generado se sortea contra la
                       probabilidad de su propia profundidad y se dibuja como
                       colectado o como recombinado.
    """
    rng = np.random.default_rng(semilla)
    n = int(np.clip(round(FOTONES_POR_SOL * irradiancia), 18, 420))

    W_cm = W_um * 1e-4
    z_fondo = -(profundidad_vista_um or W_um)
    z_entrada = -z_fondo * ALTURA_ENTRADA

    if modo == "espectro":
        idx = _muestrear_longitudes(espectro["lambda_nm"], espectro["Nph"], n, rng)
        lam_foton = espectro["lambda_nm"][idx]
        alpha_foton = espectro["alpha"][idx]
        refl_foton = espectro["R"][idx]
        colores = [hex_de_longitud_onda(l) for l in lam_foton]
        etiqueta = "Fotones del espectro AM1.5G"
    else:
        lam_foton = np.full(n, lambda_nm)
        alpha_foton = np.full(n, alpha_cm)
        refl_foton = np.full(n, reflectancia)
        colores = hex_de_longitud_onda(lambda_nm)
        etiqueta = f"Fotones de {lambda_nm:.0f} nm"

    rebota, atraviesa, x_abs_um = _sortear_fotones(n, alpha_foton, refl_foton, W_cm, rng)
    lat_x = rng.uniform(4, ANCHO_LATERAL - 4, n)
    lat_y = rng.uniform(4, ANCHO_LATERAL - 4, n)

    destino = np.where(rebota, 0.0, np.minimum(x_abs_um, W_um))
    color_par = colores if modo == "espectro" else COLOR_PAR

    # Destino del par: se sortea contra la probabilidad de colección de su propia
    # profundidad, igual que todo lo demás en esta animación.
    if coleccion is not None:
        x_perfil_um, fc_perfil = coleccion
        prob = np.interp(x_abs_um, x_perfil_um, fc_perfil)
        se_colecta = rng.random(n) < prob
    else:
        se_colecta = np.ones(n, dtype=bool)

    cuadros = []
    for c in range(N_CUADROS):
        t = c / (N_CUADROS - 1)
        avance_sup = min(t / 0.35, 1.0)
        avance_int = max(0.0, (t - 0.35) / 0.65)

        z_foton = np.where(
            avance_sup < 1.0,
            z_entrada * (1.0 - avance_sup),
            np.where(rebota, z_entrada * avance_int, -destino * avance_int),
        )
        ya_absorbido = ~rebota & ~atraviesa & (avance_int >= 1.0 - 1e-9)
        vivos = ~ya_absorbido
        colectados = ya_absorbido & se_colecta
        recombinados = ya_absorbido & ~se_colecta

        cuadros.append(go.Frame(
            name=str(c),
            data=[
                go.Scatter3d(
                    x=lat_x[vivos], y=lat_y[vivos], z=z_foton[vivos], mode="markers",
                    marker=dict(
                        size=3.4, opacity=0.95, line=dict(width=0),
                        color=(list(np.array(colores)[vivos]) if modo == "espectro"
                               else colores),
                    ),
                ),
                go.Scatter3d(
                    x=lat_x[colectados], y=lat_y[colectados],
                    z=-x_abs_um[colectados], mode="markers",
                    marker=dict(
                        size=3.4, symbol="diamond", opacity=0.95,
                        color=(list(np.array(color_par)[colectados])
                               if modo == "espectro" else color_par),
                    ),
                ),
                go.Scatter3d(
                    x=lat_x[recombinados], y=lat_y[recombinados],
                    z=-x_abs_um[recombinados], mode="markers",
                    marker=dict(size=2.8, symbol="x", opacity=0.5,
                                color=COLOR_RECOMBINADO),
                ),
            ],
            traces=[0, 1, 2],
        ))

    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=lat_x, y=lat_y, z=np.full(n, z_entrada), mode="markers",
                name=etiqueta,
                marker=dict(size=3.4, color=colores, opacity=0.95),
            ),
            go.Scatter3d(
                x=[], y=[], z=[], mode="markers",
                name=("Pares colectados" if coleccion is not None
                      else "Pares electrón-hueco generados"),
                marker=dict(size=3.4, color=COLOR_PAR, symbol="diamond", opacity=0.95),
            ),
            go.Scatter3d(
                x=[], y=[], z=[], mode="markers",
                name="Pares recombinados",
                marker=dict(size=2.8, color=COLOR_RECOMBINADO, symbol="x", opacity=0.5),
                visible=coleccion is not None,
                showlegend=coleccion is not None,
            ),
        ],
        frames=cuadros,
    )

    # --- las tres regiones del dispositivo ---------------------------------
    fondo_vista = -z_fondo
    if juntura is not None:
        x_n = cm_a_um(juntura.x_n)
        x_p = cm_a_um(juntura.x_p)
        w_dep_real = cm_a_um(juntura.W_dep)
        if exagerar_deplexion:
            medio = 0.5 * (x_n + x_p)
            grosor = max(w_dep_real, 0.035 * fondo_vista)
            x_n, x_p = medio - grosor / 2, medio + grosor / 2
    else:
        x_n = x_p = d_n_um
        w_dep_real = 0.0

    fig.add_trace(_caja(0, -min(x_n, fondo_vista), COLOR_EMISOR, 0.26,
                        f"Emisor tipo n · {d_n_um:.2f} µm"))
    if x_p > x_n and x_n < fondo_vista:
        fig.add_trace(_caja(-min(x_n, fondo_vista), -min(x_p, fondo_vista),
                            COLOR_DEPLEXION, 0.55,
                            f"Zona de deplexión · {w_dep_real:.3f} µm"))
    if x_p < fondo_vista:
        fig.add_trace(_caja(-x_p, z_fondo, COLOR_BASE, 0.20,
                            f"Base tipo p · {W_um - d_n_um:.0f} µm"))
    if fondo_vista >= W_um:
        fig.add_trace(_caja(-W_um, -W_um * 1.03, COLOR_CONTACTO, 0.55,
                            "Contacto trasero de aluminio"))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title="", showticklabels=False, showgrid=False, zeroline=False,
                       showbackground=False, range=[-2, ANCHO_LATERAL + 2]),
            yaxis=dict(title="", showticklabels=False, showgrid=False, zeroline=False,
                       showbackground=False, range=[-2, ANCHO_LATERAL + 2]),
            zaxis=dict(title="Profundidad [µm]", gridcolor="#2A3542",
                       showbackground=False, zeroline=False,
                       range=[z_fondo * 1.06, z_entrada * 1.2]),
            camera=dict(eye=dict(x=1.75, y=1.65, z=0.75),
                        center=dict(x=0, y=0, z=-0.08)),
            aspectratio=dict(x=1, y=1, z=0.95),
        ),
        margin=dict(l=0, r=0, t=8, b=0),
        height=470,
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.12, x=0,
                    font=dict(size=10.5), bgcolor="rgba(0,0,0,0)"),
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.02, y=1.0, xanchor="left",
            bgcolor="#1C2531", bordercolor="#2A3542", font=dict(color="#E8ECF2"),
            buttons=[
                dict(label=f"▶  Lanzar {n} fotones", method="animate",
                     args=[None, dict(frame=dict(duration=55, redraw=True),
                                      fromcurrent=False, mode="immediate")]),
                dict(label="⏸", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
    )
    return fig, n


def resumen_sorteo(alpha_cm, reflectancia, W_cm, d_n_cm):
    """Reparto analítico de los fotones de un color, para contrastar con la animación."""
    entra = 1.0 - reflectancia
    en_emisor = entra * (1.0 - np.exp(-alpha_cm * d_n_cm))
    hasta_el_fondo = entra * np.exp(-alpha_cm * W_cm)
    return {
        "reflejados": reflectancia,
        "en_emisor": en_emisor,
        "en_base": entra - en_emisor - hasta_el_fondo,
        "atraviesan": hasta_el_fondo,
    }
