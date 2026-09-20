"""
Vista tridimensional de la celda con fotones que la atraviesan.

La animación no es decorativa: cada fotón y cada par se sortean del mismo modelo
que calcula las cifras de la pestaña, uno por uno, como en un Monte Carlo.

  1. El color del fotón es el elegido, o se sortea del espectro AM1.5G con
     probabilidad proporcional al flujo real de cada longitud de onda.
  2. Cae en un punto al azar de la superficie. Si ese punto está bajo un dedo de
     plata, se detiene ahí: los dedos ocupan exactamente la fracción de sombra
     de la malla.
  3. Si no, rebota con probabilidad igual a la reflectancia de la superficie.
  4. Si entra, se sortea el largo total de camino que alcanza a recorrer antes de
     absorberse, de la distribución de Beer-Lambert de su color. El fotón baja;
     si llega al fondo, el aluminio lo absorbe o, con el reflector encendido, lo
     devuelve con probabilidad R_Al; si vuelve a la cara frontal, sale o se
     refleja hacia adentro con probabilidad R. Así hasta absorberse o salir.
  5. Donde se absorbe nace un par, cuyo destino se sortea con las tres
     probabilidades del modelo a esa profundidad: llegar a la juntura, morir en
     la superficie más cercana, o recombinarse en el volumen.

Al terminar, cada par queda marcado donde nació, con el color de su destino, y
una línea recta lo une con el lugar donde terminó: el plano de la juntura o la
superficie más cercana. La marca en el lugar de nacimiento conserva lo que dice
dónde se absorbe cada color; la línea, lo que le pasó al par. El camino real del
portador es una difusión al azar, no una recta: la línea indica solo el destino.

Sortear un único largo de camino para todo el recorrido es exacto, no una
aproximación: la absorción no tiene memoria, así que da lo mismo sortear un
tramo por pasada o uno solo para el total.
"""

from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go

from units import cm_a_um
from visualization.colors import hex_de_longitud_onda
from visualization.figura_animada import FiguraAnimada

ANCHO_LATERAL = 100.0
FOTONES_POR_SOL = 160
N_CUADROS = 56
N_DEDOS_VISIBLES = 4
MAXIMO_DE_PASADAS = 40

COLOR_EMISOR = "#3B82A8"
COLOR_DEPLECION = "#E5A33F"
COLOR_BASE = "#2F8A7E"
COLOR_CONTACTO = "#8A8F98"
COLOR_PLATA = "#D6DBE2"
COLOR_PAR = "#F2F5F8"
COLOR_JUNTURA = "#4CC38A"
COLOR_SUPERFICIE = "#E4664A"
COLOR_VOLUMEN = "#C25B8E"
COLOR_ALUMINIO = "#9AA3AD"
COLOR_SALE = "#B8C2CF"

FIN_FASE_CAIDA = 0.22
FIN_FASE_VIAJE = 0.56
FIN_FASE_PAR = 0.86


@dataclass
class Tanda:
    """Conteo de destinos de los fotones lanzados, con las claves del reparto del modelo."""

    n: int
    cuentas: dict


def _caja(z0, z1, color, opacidad, nombre, x0=0.0, x1=ANCHO_LATERAL, y0=0.0, y1=ANCHO_LATERAL,
          mostrar_leyenda=True):
    xs = [x0, x1, x1, x0, x0, x1, x1, x0]
    ys = [y0, y0, y1, y1, y0, y0, y1, y1]
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
    """Sortea colores con probabilidad proporcional a cuántos fotones trae el Sol de cada uno."""
    pesos = nph * np.gradient(lam)
    acumulada = np.cumsum(pesos)
    acumulada = acumulada / acumulada[-1]
    return np.clip(np.searchsorted(acumulada, rng.random(n)), 0, len(lam) - 1)


def _posiciones_de_dedos(fraccion_sombra):
    """Dedos repartidos a lo ancho, cuyo ancho total es la fracción de sombra de la malla."""
    ancho = ANCHO_LATERAL * fraccion_sombra / N_DEDOS_VISIBLES
    separacion = ANCHO_LATERAL / N_DEDOS_VISIBLES
    centros = separacion * (np.arange(N_DEDOS_VISIBLES) + 0.5)
    return [(c - ancho / 2.0, c + ancho / 2.0) for c in centros]


def _transportar(alpha_cm, R, W_cm, R_trasera, rng):
    """
    Recorrido de un fotón que entró: quiebres del camino y cómo termina.

    Devuelve (destino, profundidades de los quiebres en µm, profundidad final en µm).
    """
    s = -np.log(max(rng.random(), 1e-300)) / alpha_cm
    z, bajando = 0.0, True
    quiebres = [0.0]
    for _ in range(MAXIMO_DE_PASADAS):
        if bajando:
            d = W_cm - z
            if s < d:
                z += s
                quiebres.append(z)
                return "absorbido", np.array(quiebres) * 1e4, z * 1e4
            s -= d
            z = W_cm
            quiebres.append(z)
            if rng.random() >= R_trasera:
                return "aluminio", np.array(quiebres) * 1e4, z * 1e4
            bajando = False
        else:
            if s < z:
                z -= s
                quiebres.append(z)
                return "absorbido", np.array(quiebres) * 1e4, z * 1e4
            s -= z
            z = 0.0
            quiebres.append(z)
            if rng.random() >= R:
                return "escapa", np.array(quiebres) * 1e4, 0.0
            bajando = True
    return "aluminio", np.array(quiebres) * 1e4, W_cm * 1e4


def _punto_en_camino(quiebres, lateral0, avance):
    """
    Posición a una fracción del camino recorrido.

    Cada pasada se corre unas unidades hacia el costado para que un rebote se vea
    como una V y no como una línea que se superpone consigo misma.
    """
    tramos = np.abs(np.diff(quiebres))
    total = tramos.sum()
    if total <= 0:
        return lateral0, quiebres[0]
    objetivo = avance * total
    acumulado = 0.0
    for i, largo in enumerate(tramos):
        if acumulado + largo >= objetivo or i == len(tramos) - 1:
            f = 0.0 if largo <= 0 else (objetivo - acumulado) / largo
            f = min(max(f, 0.0), 1.0)
            prof = quiebres[i] + f * (quiebres[i + 1] - quiebres[i])
            return lateral0 + 3.0 * (i + f), prof
        acumulado += largo
    return lateral0 + 3.0 * len(tramos), quiebres[-1]


def figura_celda_3d(campo, union, destinos, fraccion_sombra, d_n_um, W_um,
                    modo="espectro", lambda_nm=450.0, irradiancia=1.0,
                    profundidad_vista_um=None, exagerar_deplecion=False,
                    mostrar_trayectorias=True, semilla=7):
    """
    Bloque de la celda con fotones y pares sorteados del modelo.

    `destinos` son las probabilidades de destino de un par a cada profundidad, las
    mismas que usa el reparto de la pestaña. Devuelve la figura y el conteo de la
    tanda, para compararlo con el reparto exacto.
    """
    rng = np.random.default_rng(semilla)
    n = int(np.clip(round(FOTONES_POR_SOL * irradiancia), 16, 360))
    W_cm = W_um * 1e-4
    x_n_um = float(cm_a_um(union.x_n))
    x_p_um = float(cm_a_um(union.x_p))
    x_j_um = float(cm_a_um(union.x_j))
    vista = float(profundidad_vista_um or W_um)
    z_entrada = 0.26 * vista

    if modo == "espectro":
        idx = _muestrear_longitudes(campo.lambda_nm, campo.Nph, n, rng)
    else:
        idx = np.full(n, int(np.argmin(np.abs(campo.lambda_nm - lambda_nm))))
    lam = campo.lambda_nm[idx]
    colores = np.array([hex_de_longitud_onda(l) for l in lam])

    # Uniforme sobre todo el ancho, para que la fracción que cae bajo un dedo sea
    # exactamente la fracción de sombra de la malla.
    lat_x = rng.uniform(0.0, ANCHO_LATERAL, n)
    lat_y = rng.uniform(3, ANCHO_LATERAL - 3, n)
    retraso = rng.uniform(0.0, 0.30, n)

    dedos = _posiciones_de_dedos(fraccion_sombra)
    bajo_dedo = np.zeros(n, dtype=bool)
    for a, b in dedos:
        bajo_dedo |= (lat_x >= a) & (lat_x <= b)

    x_perfil_um = cm_a_um(campo.x_cm)
    final = np.empty(n, dtype=object)
    quiebres = [None] * n
    prof_final = np.zeros(n)
    for k in range(n):
        if bajo_dedo[k]:
            final[k] = "malla"
            continue
        if rng.random() < campo.R[idx[k]]:
            final[k] = "reflejados"
            continue
        destino, qs, z = _transportar(float(campo.alpha[idx[k]]), float(campo.R[idx[k]]),
                                      W_cm, campo.R_trasera, rng)
        quiebres[k] = qs
        prof_final[k] = z
        if destino == "aluminio":
            final[k] = "aluminio"
        elif destino == "escapa":
            final[k] = "escapan"
        else:
            fc = np.interp(z, x_perfil_um, destinos.fc)
            ps = np.interp(z, x_perfil_um, destinos.p_superficie)
            u = rng.random()
            if z <= x_n_um:
                region = "emisor"
            elif z < x_p_um:
                region = "deplecion"
            else:
                region = "base"
            if region == "deplecion" or u < fc:
                final[k] = "deplecion" if region == "deplecion" else f"{region}_colectados"
            elif u < fc + ps:
                final[k] = f"{region}_superficie"
            else:
                final[k] = f"{region}_volumen"

    claves = ("malla", "reflejados", "aluminio", "escapan", "emisor_superficie",
              "emisor_volumen", "base_volumen", "base_superficie", "emisor_colectados",
              "deplecion", "base_colectados")
    tanda = Tanda(n=n, cuentas={c: int(np.sum(final == c)) for c in claves})

    colectado = np.array([str(f).endswith("colectados") or f == "deplecion" for f in final])
    en_superficie = np.array([str(f).endswith("_superficie") for f in final])
    en_volumen = np.array([str(f).endswith("_volumen") for f in final])
    prof_superficie = np.where(prof_final <= x_n_um, 0.0, W_um)

    destino_texto = {
        "malla": "chocó con la malla de plata", "reflejados": "se reflejó en la superficie",
        "aluminio": "lo absorbió el aluminio", "escapan": "rebotó en el aluminio y escapó",
        "emisor_colectados": "llegó a la juntura", "deplecion": "se separó en la zona de depleción",
        "base_colectados": "llegó a la juntura",
        "emisor_superficie": "murió en la superficie frontal",
        "base_superficie": "murió en la cara trasera",
        "emisor_volumen": "se recombinó en el volumen", "base_volumen": "se recombinó en el volumen",
    }

    def _prof_txt(um):
        return (f"{um * 1e3:.3g} nm" if um < 1 else f"{um:.3g} µm").replace(".", ",")

    hover = [
        f"{l:.0f} nm · el par nació a {_prof_txt(z)} y {destino_texto[f]}"
        if f not in ("malla", "reflejados", "aluminio", "escapan")
        else f"{l:.0f} nm · {destino_texto[f]}"
        for l, z, f in zip(lam, prof_final, final)
    ]

    def estado(t):
        tau = np.clip((t - retraso) / (1.0 - 0.30), 0.0, 1.0)
        px, pz = lat_x.copy(), np.zeros(n)
        vuelo = np.zeros(n, dtype=bool)
        par_mueve = np.zeros(n, dtype=bool)
        fin_col, fin_sup, fin_vol = (np.zeros(n, dtype=bool) for _ in range(3))
        fin_al, fin_sale, fin_malla = (np.zeros(n, dtype=bool) for _ in range(3))
        trazos_x, trazos_y, trazos_z, trazos_c = [], [], [], []
        caminos_x, caminos_y, caminos_z, caminos_c = [], [], [], []

        for k in range(n):
            tk = tau[k]
            if tk < FIN_FASE_CAIDA:
                pz[k] = z_entrada * (1.0 - tk / FIN_FASE_CAIDA)
                vuelo[k] = tk > 0
                continue
            f = final[k]
            if f == "malla":
                pz[k] = 0.012 * vista
                fin_malla[k] = True
                continue
            if f == "reflejados":
                a = min((tk - FIN_FASE_CAIDA) / (FIN_FASE_VIAJE - FIN_FASE_CAIDA), 1.0)
                pz[k] = z_entrada * 0.85 * a
                px[k] = lat_x[k] + 10.0 * a
                if a < 1.0:
                    vuelo[k] = True
                else:
                    fin_sale[k] = True
                continue

            a = min((tk - FIN_FASE_CAIDA) / (FIN_FASE_VIAJE - FIN_FASE_CAIDA), 1.0)
            qs = quiebres[k]
            lx, prof = _punto_en_camino(qs, lat_x[k], a)
            vista_prof = min(prof, vista)
            if mostrar_trayectorias and (a < 1.0 or len(qs) > 2):
                muestras = np.linspace(0.0, a, max(3, 2 + 3 * (len(qs) - 1)))
                for m_ in muestras:
                    xx, zz = _punto_en_camino(qs, lat_x[k], m_)
                    trazos_x.append(xx)
                    trazos_y.append(lat_y[k])
                    trazos_z.append(-min(zz, vista))
                    trazos_c.append(colores[k])
                trazos_x.append(None)
                trazos_y.append(None)
                trazos_z.append(None)
                trazos_c.append(colores[k])
            if a < 1.0:
                px[k], pz[k] = lx, -vista_prof
                vuelo[k] = True
                continue

            if f == "aluminio":
                px[k], pz[k] = lx, -min(W_um, vista)
                fin_al[k] = True
                continue
            if f == "escapan":
                b = min((tk - FIN_FASE_VIAJE) / (FIN_FASE_PAR - FIN_FASE_VIAJE), 1.0)
                px[k], pz[k] = lx, z_entrada * 0.85 * b
                if b < 1.0:
                    vuelo[k] = True
                else:
                    fin_sale[k] = True
                continue

            b = min(max((tk - FIN_FASE_VIAJE) / (FIN_FASE_PAR - FIN_FASE_VIAJE), 0.0), 1.0)
            if colectado[k]:
                destino_prof = x_j_um
            elif en_superficie[k]:
                destino_prof = prof_superficie[k]
            else:
                destino_prof = prof
            actual = prof + b * (destino_prof - prof)
            if mostrar_trayectorias and not en_volumen[k] and b > 0.0:
                color_linea = COLOR_JUNTURA if colectado[k] else COLOR_SUPERFICIE
                caminos_x += [lx, lx, None]
                caminos_y += [lat_y[k], lat_y[k], None]
                caminos_z += [-min(prof, vista), -min(actual, vista), None]
                caminos_c += [color_linea, color_linea, color_linea]
            if b < 1.0 and not (en_volumen[k] and b > 0.55):
                # mientras difunde, el par se ve como un punto blanco que avanza
                px[k], pz[k] = lx, -min(actual, vista)
                par_mueve[k] = True
                continue
            # al terminar, la marca vuelve al lugar donde nació, con el color de su destino
            px[k], pz[k] = lx, -min(prof, vista)
            if colectado[k]:
                fin_col[k] = True
            elif en_superficie[k]:
                fin_sup[k] = True
            else:
                fin_vol[k] = True

        def marcas(mascara, simbolo, tamano, color, opacidad=0.95):
            color_valor = list(colores[mascara]) if color is None else color
            return dict(
                type="scatter3d",
                x=px[mascara], y=lat_y[mascara], z=pz[mascara], mode="markers",
                text=np.array(hover)[mascara],
                hovertemplate="%{text}<extra></extra>",
                marker=dict(size=tamano, symbol=simbolo, color=color_valor, opacity=opacidad,
                            line=dict(width=0)),
            )

        return [
            marcas(vuelo, "circle", 3.2, None),
            dict(type="scatter3d", x=trazos_x, y=trazos_y, z=trazos_z, mode="lines",
                 hoverinfo="skip", line=dict(width=2.2, color=trazos_c or ["#FFFFFF"]),
                 opacity=0.55),
            marcas(par_mueve, "circle", 2.6, COLOR_PAR),
            marcas(fin_col, "diamond", 4.2, COLOR_JUNTURA),
            marcas(fin_sup, "x", 3.6, COLOR_SUPERFICIE),
            marcas(fin_vol, "x", 3.6, COLOR_VOLUMEN),
            marcas(fin_al, "square", 3.4, COLOR_ALUMINIO),
            marcas(fin_sale, "circle-open", 3.4, COLOR_SALE, 0.7),
            marcas(fin_malla, "square", 3.4, COLOR_PLATA),
            dict(type="scatter3d", x=caminos_x, y=caminos_y, z=caminos_z, mode="lines",
                 hoverinfo="skip", line=dict(width=1.6, color=caminos_c or ["#FFFFFF"]),
                 opacity=0.45),
        ]

    tiempos = np.linspace(0.0, 1.0, N_CUADROS)
    # Cuadros como diccionarios y figura sin validación de Plotly: validar las nueve
    # trazas de cada uno de los cuadros tomaba varios segundos (ver D-39).
    cuadros = [dict(name=str(c), data=estado(t), traces=list(range(10)))
               for c, t in enumerate(tiempos)]

    c = tanda.cuentas
    n_col = c["emisor_colectados"] + c["deplecion"] + c["base_colectados"]
    n_sup = c["emisor_superficie"] + c["base_superficie"]
    n_vol = c["emisor_volumen"] + c["base_volumen"]
    nombres = [
        "Fotones en camino",
        "Trayectorias",
        "Pares difundiendo",
        f"Llegan a la juntura · {n_col}",
        f"Mueren en una superficie · {n_sup}",
        f"Se recombinan en el volumen · {n_vol}",
        f"Los absorbe el aluminio · {c['aluminio']}",
        f"Rebotan o escapan · {c['reflejados'] + c['escapan']}",
        f"Chocan con la malla · {c['malla']}",
        "Caminos de los pares",
    ]
    # En reposo la figura muestra el resultado final de la tanda; el botón la anima
    # desde el comienzo.
    iniciales = estado(1.0)
    for traza, nombre in zip(iniciales, nombres):
        traza["name"] = nombre
        traza["showlegend"] = nombre not in ("Trayectorias", "Caminos de los pares")
    fig = FiguraAnimada(data=iniciales, cuadros=cuadros)

    # --- geometría de la celda ------------------------------------------------
    if exagerar_deplecion:
        medio = 0.5 * (x_n_um + x_p_um)
        grosor = max(x_p_um - x_n_um, 0.03 * vista)
        zn, zp = medio - grosor / 2.0, medio + grosor / 2.0
    else:
        zn, zp = x_n_um, x_p_um
    fig.add_trace(_caja(0, -min(zn, vista), COLOR_EMISOR, 0.22, f"Emisor n · {d_n_um:.2f} µm"))
    if zn < vista:
        fig.add_trace(_caja(-zn, -min(zp, vista), COLOR_DEPLECION, 0.6,
                            f"Zona de depleción (juntura p-n) · {x_p_um - x_n_um:.3f} µm"))
    if zp < vista:
        fig.add_trace(_caja(-zp, -vista, COLOR_BASE, 0.16, f"Base p · {W_um - d_n_um:.0f} µm"))
    if vista >= W_um:
        fig.add_trace(_caja(-W_um, -W_um * 1.035, COLOR_CONTACTO, 0.6,
                            "Contacto de aluminio" + (" · refleja" if campo.reflector else "")))
    for i, (a, b) in enumerate(dedos):
        fig.add_trace(_caja(0.0, 0.012 * vista, COLOR_PLATA, 0.95,
                            "Dedos de plata" if i == 0 else "", x0=a, x1=b,
                            mostrar_leyenda=(i == 0)))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title="", showticklabels=False, showgrid=False, zeroline=False,
                       showbackground=False, range=[-2, ANCHO_LATERAL + 14]),
            yaxis=dict(title="", showticklabels=False, showgrid=False, zeroline=False,
                       showbackground=False, range=[-2, ANCHO_LATERAL + 2]),
            zaxis=dict(title="Profundidad [µm]", gridcolor="#2A3542", showbackground=False,
                       zeroline=False, range=[-vista * 1.08, z_entrada * 1.15]),
            camera=dict(eye=dict(x=1.55, y=1.55, z=0.62), center=dict(x=0, y=0, z=-0.1)),
            aspectratio=dict(x=1.05, y=1, z=1.05),
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        height=720,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E8ECF2"),
        legend=dict(orientation="v", yanchor="top", y=0.98, x=0.0, font=dict(size=11),
                    bgcolor="rgba(13,19,28,0.55)"),
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.99, y=0.99, xanchor="right", yanchor="top",
            bgcolor="#1C2531", bordercolor="#2A3542", font=dict(color="#E8ECF2", size=12),
            buttons=[
                dict(label=f"▶  Lanzar {n} fotones", method="animate",
                     args=[None, dict(frame=dict(duration=70, redraw=True),
                                      fromcurrent=False, mode="immediate")]),
                dict(label="⏸  Pausa", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ],
        )],
    )
    return fig, tanda
