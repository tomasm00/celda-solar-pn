"""
El viaje de un fotón: desde que llega a la celda hasta que mueve una carga por el
circuito, o hasta que se pierde en el camino.

Es una simplificación deliberada para enseñar la secuencia, pero no inventa nada:
cada bifurcación del viaje se sortea con las probabilidades del mismo modelo que
calcula las cifras de la pestaña.

  - Si choca con la malla, si se refleja, a qué profundidad se absorbe y si llega
    al fondo: óptica de la celda para el color del fotón.
  - Qué le pasa al par nacido a esa profundidad: las tres probabilidades de destino.
  - Si se recombina en el volumen, por qué mecanismo: la proporción de cada tasa.

Lo que sí es ilustrativo es la forma exacta del camino de difusión. El modelo
entrega la probabilidad de cada destino, no la trayectoria de un portador; el
camino se dibuja como un paseo al azar que termina donde el sorteo dijo que
terminaba. Y la escala vertical es esquemática: cada región recibe un alto
suficiente para verse, con sus espesores reales rotulados al costado.
"""

import numpy as np

import constants as C
from physics.material import bandgap
from units import cm_a_um
from visualization.cell3d import _muestrear_longitudes, _transportar
from visualization.colors import hex_de_longitud_onda
from visualization.figura_animada import FiguraAnimada

# Geometría del dibujo, en unidades arbitrarias
X_IZQ, X_DER = 0.3, 9.0
Y_TECHO = 9.95
Y_SUP = 7.3
Y_N = 5.55
Y_P = 5.0
Y_FONDO = 1.75
Y_AL = 1.2
X_DEDO = (1.05, 1.95)
Y_CABLE = 9.35
X_CABLE = 9.55
X_CARGA = (4.7, 6.3)

COLOR_ELECTRON = "#5AA9FF"
COLOR_HUECO = "#FF8A7A"
COLOR_TEXTO = "#E8ECF2"
COLOR_SUAVE = "#8894A8"


def _coma(x, dec=2):
    return f"{x:.{dec}f}".replace(".", ",")


def _prof_texto(um):
    if um < 1.0:
        return f"{um * 1e3:.3g} nm".replace(".", ",")
    return f"{um:.3g} µm".replace(".", ",")


def _envolver(texto, ancho=92):
    lineas, actual = [], ""
    for palabra in texto.split():
        if len(actual) + len(palabra) + 1 > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    if actual:
        lineas.append(actual)
    return "<br>".join(lineas)


class _Escala:
    """Convierte profundidad real en µm a la altura esquemática del dibujo."""

    def __init__(self, x_n_um, x_p_um, W_um):
        self.x_n, self.x_p, self.W = x_n_um, x_p_um, W_um

    def y(self, prof_um):
        p = float(prof_um)
        if p <= self.x_n:
            return Y_SUP - (Y_SUP - Y_N) * p / max(self.x_n, 1e-12)
        if p <= self.x_p:
            return Y_N - (Y_N - Y_P) * (p - self.x_n) / max(self.x_p - self.x_n, 1e-12)
        return Y_P - (Y_P - Y_FONDO) * (p - self.x_p) / max(self.W - self.x_p, 1e-12)


def _paseo(rng, p0, p1, n, amplitud, y_min, y_max):
    """Paseo al azar que empieza en p0 y termina exactamente en p1."""
    t = np.linspace(0.0, 1.0, n)[:, None]
    ruido = np.cumsum(rng.normal(0.0, 1.0, (n, 2)), axis=0)
    ruido = ruido - t * ruido[-1]
    escala = np.max(np.abs(ruido))
    if escala > 0:
        ruido = ruido * (amplitud / escala)
    camino = np.asarray(p0)[None, :] + t * (np.asarray(p1) - np.asarray(p0))[None, :] + ruido
    camino[:, 0] = np.clip(camino[:, 0], X_IZQ + 0.15, X_DER - 0.15)
    camino[:, 1] = np.clip(camino[:, 1], y_min, y_max)
    camino[-1] = p1
    return camino


def _polilinea(puntos, n):
    """Reparte n muestras a lo largo de una polilínea, proporcional al largo de cada tramo."""
    puntos = np.asarray(puntos, dtype=float)
    largos = np.linalg.norm(np.diff(puntos, axis=0), axis=1)
    acum = np.concatenate([[0.0], np.cumsum(largos)])
    objetivo = np.linspace(0.0, acum[-1], n)
    x = np.interp(objetivo, acum, puntos[:, 0])
    y = np.interp(objetivo, acum, puntos[:, 1])
    return np.column_stack([x, y])


def viaje_de_un_foton(campo, union, tr, destinos, fraccion_sombra, t_k, j_sc_ma,
                      modo="espectro", lambda_nm=450.0, semilla=1, forzar="azar",
                      mecanismos=None):
    """
    Construye la animación del viaje y la ficha con los números que lo explican.

    `forzar` puede ser 'azar' (todo sorteado con las probabilidades del modelo),
    'juntura', 'superficie', 'volumen' o 'refleja'. Al forzar un destino de par, la
    profundidad de absorción se sortea entre las que conducen a ese destino, con el
    peso que les da el modelo, para que el viaje forzado siga siendo plausible.

    `mecanismos` es un dict por región ('emisor', 'base') con el reparto de la
    recombinación en el volumen entre SRH, Auger y radiativa, o None si la vida
    media elegida no es físicamente posible.
    """
    rng = np.random.default_rng(semilla)
    x_n_um = float(cm_a_um(union.x_n))
    x_p_um = float(cm_a_um(union.x_p))
    W_um = float(cm_a_um(campo.W_cm))
    esc = _Escala(x_n_um, x_p_um, W_um)
    x_perfil_um = cm_a_um(campo.x_cm)

    if modo == "espectro":
        i_lam = int(_muestrear_longitudes(campo.lambda_nm, campo.Nph, 1, rng)[0])
    else:
        i_lam = int(np.argmin(np.abs(campo.lambda_nm - lambda_nm)))
    lam = float(campo.lambda_nm[i_lam])
    color = hex_de_longitud_onda(lam)
    energia = 1239.84 / lam
    eg = float(bandgap(t_k))
    R = float(campo.R[i_lam])
    alpha = float(campo.alpha[i_lam])
    un_alfa_um = float(cm_a_um(1.0 / alpha))

    ficha = {"lambda_nm": lam, "energia_eV": energia, "R": R, "1/alpha_um": un_alfa_um,
             "forzado": forzar != "azar"}
    nota_forzado = ""

    # --- 1. destino óptico -----------------------------------------------------
    optico, prof_um, quiebres = None, None, None
    if forzar == "refleja":
        optico = "refleja"
    elif forzar in ("juntura", "superficie", "volumen"):
        peso = {"juntura": destinos.fc, "superficie": destinos.p_superficie,
                "volumen": destinos.p_volumen}[forzar] * campo.G[:, i_lam]
        dx = np.gradient(campo.x_cm)
        w = np.clip(peso * dx, 0.0, None)
        if w.sum() > 0:
            k = int(rng.choice(len(w), p=w / w.sum()))
            prof_um = float(x_perfil_um[k])
            optico = "absorbido"
            quiebres = np.array([0.0, prof_um])
        else:
            nota_forzado = ("A este color ese destino no ocurre nunca en esta celda, así que "
                            "el viaje se sorteó sin forzarlo. ")
            forzar = "azar"
    if optico is None:
        if rng.random() < fraccion_sombra:
            optico = "malla"
        elif rng.random() < R:
            optico = "refleja"
        else:
            optico, quiebres, prof_um = _transportar(alpha, R, campo.W_cm, campo.R_trasera, rng)

    # --- 2. destino del par ------------------------------------------------------
    region, destino_par, mecanismo = None, None, None
    if optico == "absorbido":
        region = ("emisor" if prof_um <= x_n_um else "deplecion" if prof_um < x_p_um else "base")
        fc = float(np.interp(prof_um, x_perfil_um, destinos.fc))
        ps = float(np.interp(prof_um, x_perfil_um, destinos.p_superficie))
        pv = max(1.0 - fc - ps, 0.0)
        ficha.update(prof_um=prof_um, region=region, fc=fc, ps=ps, pv=pv)
        if forzar in ("juntura", "superficie", "volumen"):
            destino_par = forzar
        elif region == "deplecion":
            destino_par = "juntura"
        else:
            u = rng.random()
            destino_par = "juntura" if u < fc else "superficie" if u < fc + ps else "volumen"
        if destino_par == "volumen":
            reparto = (mecanismos or {}).get(region)
            if reparto:
                nombres = list(reparto)
                mecanismo = str(rng.choice(nombres, p=np.array([reparto[m] for m in nombres])))
    ficha.update(optico=optico, destino_par=destino_par, mecanismo=mecanismo)

    # --- 3. guion del viaje --------------------------------------------------------
    etapas = []      # (nombre de la etapa, número de cuadros, narración)
    estados = []     # un dict por cuadro

    x0 = float(np.mean(X_DEDO)) if optico == "malla" else float(rng.uniform(3.4, 7.2))
    base_estado = dict(foton=None, rastro=True, e=None, h=None, e_ruta=[], h_ruta=[],
                       destello=None, emitido=None, carga=0.0)

    def agregar(nombre, cuadros, narracion, generador):
        etapas.append((nombre, len(estados), narracion))
        for i in range(cuadros):
            st_ = dict(base_estado)
            st_.update(generador(i / max(cuadros - 1, 1)))
            st_["narracion"] = narracion
            st_["etapa"] = nombre
            estados.append(st_)

    E_txt = _coma(energia)
    Eg_txt = _coma(eg, 3)
    llega = (f"Llega un fotón de {lam:.0f} nm, que transporta {E_txt} eV. "
             + (f"Supera los {Eg_txt} eV de la banda prohibida del silicio a esta temperatura, "
                f"así que puede crear un par electrón-hueco si se absorbe."
                if energia > eg else
                f"Tiene menos energía que la banda prohibida ({Eg_txt} eV): el silicio casi no "
                f"lo absorbe y lo más probable es que atraviese la celda."))
    if ficha["forzado"]:
        llega = ("Destino forzado para mostrar este camino; las probabilidades reales se "
                 "indican en cada paso. " + llega)
    llega = nota_forzado + llega

    agregar("Llega el fotón", 14, llega,
            lambda t: dict(foton=(x0, Y_TECHO - (Y_TECHO - (Y_SUP + (0.38 if optico == "malla" else 0.0))) * t)))

    if optico == "malla":
        agregar("Choca con la malla", 10,
                f"Cayó sobre un dedo de plata. Los dedos cubren el {_coma(100 * fraccion_sombra, 1)} % "
                f"de la superficie y son opacos: este fotón no entra al silicio. Es el precio "
                f"de poder sacar la corriente por el frente de la celda.",
                lambda t: dict(foton=(x0, Y_SUP + 0.38), destello=(x0, Y_SUP + 0.38, 1 - t, "#D6DBE2")))
    elif optico == "refleja":
        agregar("Se refleja", 14,
                f"Rebotó en la superficie. La interfaz entre el aire y el silicio refleja el "
                f"{_coma(100 * R, 1)} % de los fotones de este color, porque el índice de "
                f"refracción cambia bruscamente de un medio al otro. Sin recubrimiento "
                f"antirreflejo, es la mayor pérdida de esta celda.",
                lambda t: dict(foton=(x0 + 1.6 * t, Y_SUP + (Y_TECHO - Y_SUP) * t)))
    else:
        # Recorrido dentro del silicio, con rebotes si llegó al fondo
        puntos = [(x0 + 0.35 * i, esc.y(q)) for i, q in enumerate(quiebres)]
        camino = _polilinea(puntos, 16)
        if optico == "absorbido":
            texto_viaje = (f"Entró al silicio y avanzó hasta absorberse a {_prof_texto(prof_um)} "
                           f"de la superficie. Para este color, el 63 % de los fotones se absorbe "
                           f"antes de {_prof_texto(un_alfa_um)}; la profundidad exacta de cada uno "
                           f"es azarosa y sigue la ley de Beer-Lambert.")
            if len(quiebres) > 2:
                texto_viaje = ("Entró, cruzó la celda completa, rebotó en el aluminio y en el "
                               f"camino de vuelta se absorbió a {_prof_texto(prof_um)} de la superficie.")
        elif optico == "aluminio":
            texto_viaje = ("Entró y atravesó los " + _prof_texto(W_um) + " de silicio sin "
                           "absorberse. " + ("El aluminio no lo devolvió" if campo.reflector
                                            else "El contacto de aluminio lo absorbió")
                           + ": su energía terminó como calor en el metal.")
        else:
            texto_viaje = ("Cruzó la celda, rebotó en el aluminio, volvió a cruzarla sin "
                           "absorberse y salió por la cara frontal. El silicio es casi "
                           "transparente para este color.")
        agregar("Viaja por el silicio", 16, texto_viaje,
                lambda t: dict(foton=tuple(camino[min(int(t * 15), 15)])))
        if optico == "escapa":
            fin = camino[-1]
            agregar("Sale de la celda", 8, texto_viaje,
                    lambda t: dict(foton=(fin[0] + 0.6 * t, fin[1] + (Y_TECHO - fin[1]) * t)))

    if optico == "absorbido":
        pa = np.array(camino[-1])
        ya = pa[1]
        agregar("Nace un par electrón-hueco", 8,
                "El fotón desaparece: entrega su energía a un electrón ligado del cristal, que "
                "salta a la banda de conducción y queda libre de moverse. En su lugar queda un "
                "hueco, la ausencia de un electrón, que se comporta como una carga positiva móvil.",
                lambda t: dict(foton=None, destello=(pa[0], ya, 1 - t, color),
                               e=(pa[0] + 0.12 * t, ya), h=(pa[0] - 0.12 * t, ya)))

        # Portador minoritario y límites de su región
        if region == "emisor":
            minoritario, L_um, S = "hueco", float(cm_a_um(tr.L_p)), tr.S_f
            y_min, y_max = Y_N, Y_SUP
            sup_y, borde_y = Y_SUP, Y_N
            nombre_region, cara = "emisor tipo n", "superficie frontal"
        else:
            minoritario, L_um, S = "electrón", float(cm_a_um(tr.L_n)), tr.S_r
            y_min, y_max = Y_FONDO, Y_P
            sup_y, borde_y = Y_FONDO, Y_P
            nombre_region, cara = "base tipo p", "cara trasera"

        pe0, ph0 = pa + [0.12, 0.0], pa - [0.12, 0.0]
        if region == "deplecion":
            e_fin, h_fin = pe0, ph0
            diff_txt = ("Nació dentro de la zona de depleción, donde el campo eléctrico es "
                        "intenso: no alcanza a difundir, se separa de inmediato.")
            agregar("Difunde", 4, diff_txt, lambda t: dict(e=tuple(pe0), h=tuple(ph0)))
        else:
            if destino_par == "juntura":
                meta = np.array([pa[0] + rng.uniform(-1.2, 1.2), borde_y])
            elif destino_par == "superficie":
                meta = np.array([pa[0] + rng.uniform(-1.2, 1.2), sup_y])
            else:
                meta = np.array([pa[0] + rng.uniform(-0.9, 0.9),
                                 np.clip(ya + rng.uniform(-0.5, 0.5), y_min + 0.1, y_max - 0.1)])
            amplitud = 0.35 if region == "emisor" else 0.7
            ruta = _paseo(rng, pa, meta, 30, amplitud, y_min, y_max)
            probs = (f"Desde esta profundidad, de cada 100 pares {_coma(100 * ficha['fc'], 0)} "
                     f"llegan a la juntura, {_coma(100 * ficha['ps'], 0)} mueren en la {cara} y "
                     f"{_coma(100 * ficha['pv'], 0)} se recombinan en el volumen.")
            distancia_cm = abs(meta[1] - ya) / max(y_max - y_min, 1e-9) * (
                (x_n_um if region == "emisor" else W_um - x_p_um) * 1e-4)
            D = tr.D_p if region == "emisor" else tr.D_n
            t_dif = max(distancia_cm, 1e-7) ** 2 / (2.0 * D)
            t_txt = (f"{t_dif * 1e9:.2g} ns" if t_dif < 1e-6 else f"{t_dif * 1e6:.2g} µs").replace(".", ",")
            diff_txt = (f"En el {nombre_region} el {minoritario} es el portador minoritario, y su "
                        f"supervivencia decide todo. No hay campo que lo guíe: difunde al azar y "
                        f"recorre en promedio {_prof_texto(L_um)} antes de recombinarse. " + probs
                        + f" Un recorrido así toma del orden de {t_txt}.")

            def gen_difusion(t, ruta=ruta, region=region):
                i = min(int(t * (len(ruta) - 1)), len(ruta) - 1)
                pos = ruta[i]
                # El minoritario pasea; el mayoritario lo acompaña de cerca.
                acomp = pos + np.array([0.13, 0.05])
                if minoritario == "hueco":
                    return dict(h=tuple(pos), e=tuple(acomp), h_ruta=[tuple(p) for p in ruta[:i + 1]])
                return dict(e=tuple(pos), h=tuple(acomp), e_ruta=[tuple(p) for p in ruta[:i + 1]])

            agregar("Difunde al azar", 28, diff_txt, gen_difusion)
            final_pos = ruta[-1]
            e_fin = final_pos if minoritario == "electrón" else final_pos + [0.13, 0.05]
            h_fin = final_pos if minoritario == "hueco" else final_pos + [0.13, 0.05]

        if destino_par == "superficie":
            txt = (f"Llegó a la {cara}. Ahí el cristal termina y quedan enlaces rotos que atrapan "
                   f"portadores con una velocidad de recombinación de {S:.0e} cm/s. El electrón y "
                   f"el hueco se reencuentran y su energía se disipa como calor. Este par no "
                   f"aporta corriente.")
            pf = np.array(e_fin)
            agregar("Muere en la superficie", 10, txt,
                    lambda t: dict(e=None if t > 0.4 else tuple(pf), h=None if t > 0.4 else tuple(h_fin),
                                   destello=(pf[0], pf[1], 1 - t, "#E4664A")))
        elif destino_par == "volumen":
            explica = {
                "SRH": ("un defecto del cristal lo atrapó en un nivel dentro de la banda prohibida "
                        "(recombinación SRH) y la energía se liberó como vibraciones de la red, calor"),
                "Auger": ("le cedió su energía a un tercer portador cercano, que la perdió en "
                          "choques con la red (recombinación Auger)"),
                "radiativa": ("el electrón cayó directo a la banda de valencia y emitió un fotón "
                              "infrarrojo cercano a la banda prohibida (recombinación radiativa)"),
            }
            if mecanismo:
                reparto = mecanismos[region]
                txt = (f"Se recombinó dentro del {nombre_region} antes de llegar a ninguna parte: "
                       f"{explica[mecanismo]}. Con esta vida media, el "
                       f"{_coma(100 * reparto[mecanismo], 1)} % de la recombinación en este volumen "
                       f"ocurre por ese mecanismo.")
            else:
                txt = (f"Se recombinó dentro del {nombre_region} antes de llegar a ninguna parte. "
                       f"El reparto entre SRH, Auger y radiativa no se puede calcular porque la vida "
                       f"media elegida para esta región supera el límite físico: ver el monitor.")
            pf = np.array(e_fin)
            agregar("Se recombina en el volumen", 12, txt,
                    lambda t: dict(e=None if t > 0.35 else tuple(pf), h=None if t > 0.35 else tuple(h_fin),
                                   destello=(pf[0], pf[1], 1 - t, "#C25B8E"),
                                   emitido=((pf[0] + 2.2 * t, pf[1] + 1.4 * t) if mecanismo == "radiativa" else None)))
        else:
            # Separación en la zona de depleción
            ye_sep, yh_sep = Y_N + 0.05, Y_P - 0.05
            e0, h0 = np.array(e_fin, dtype=float), np.array(h_fin, dtype=float)
            e_sep = np.array([e0[0], ye_sep])
            h_sep = np.array([h0[0], yh_sep])
            agregar("La juntura separa el par", 10,
                    f"Alcanzó la zona de depleción, de {_prof_texto(x_p_um - x_n_um)} de ancho "
                    f"(aquí ampliada). Su campo eléctrico interno empuja al electrón hacia el emisor "
                    f"n y al hueco hacia la base p en picosegundos. Separados por la juntura, ya no "
                    f"pueden recombinarse: este par se colectó.",
                    lambda t: dict(e=tuple(e0 + (e_sep - e0) * t), h=tuple(h0 + (h_sep - h0) * t)))

            dedo = np.array([np.mean(X_DEDO), Y_SUP + 0.2])
            ruta_e = _polilinea([e_sep, [e_sep[0], Y_SUP - 0.18], [dedo[0], Y_SUP - 0.18], dedo], 18)
            ruta_h = _polilinea([h_sep, [h_sep[0], (Y_FONDO + Y_AL) / 2]], 18)
            agregar("Los contactos colectan", 18,
                    "Ahora cada carga viaja por la región donde es mayoritaria, sin riesgo de "
                    "recombinarse: el electrón por el emisor hasta el dedo de plata más cercano, y el "
                    "hueco por la base hasta el contacto de aluminio. Entre los dos contactos aparece "
                    "una diferencia de potencial.",
                    lambda t: dict(e=tuple(ruta_e[min(int(t * 17), 17)]),
                                   h=tuple(ruta_h[min(int(t * 17), 17)])))

            circuito = _polilinea([dedo, [dedo[0], Y_CABLE], [X_CARGA[0], Y_CABLE],
                                   [X_CARGA[1], Y_CABLE], [X_CABLE, Y_CABLE],
                                   [X_CABLE, (Y_FONDO + Y_AL) / 2], [X_DER - 0.1, (Y_FONDO + Y_AL) / 2],
                                   [ruta_h[-1][0] + 0.15, ruta_h[-1][1]]], 26)
            tasa = j_sc_ma * 1e-3 / C.Q
            exponente = int(np.floor(np.log10(tasa)))
            tasa_txt = f"{_coma(tasa / 10 ** exponente, 1)} × 10^{exponente}"
            agregar("La carga recorre el circuito", 24,
                    f"El electrón sale por el cable, entrega su energía en la carga conectada y vuelve "
                    f"por el contacto de aluminio, donde se reencuentra con el hueco. Una carga "
                    f"elemental completó el circuito. Esto, repetido {tasa_txt} veces por segundo en "
                    f"cada centímetro cuadrado, son los {_coma(j_sc_ma, 2)} mA/cm² de esta celda.",
                    lambda t: dict(e=tuple(circuito[min(int(t * 25), 25)]), h=tuple(ruta_h[-1]),
                                   carga=1.0 if X_CARGA[0] - 0.2 <= circuito[min(int(t * 25), 25)][0] <= X_CARGA[1] + 0.2
                                   and circuito[min(int(t * 25), 25)][1] > Y_CABLE - 0.1 else 0.35 if t > 0.4 else 0.0,
                                   destello=((ruta_h[-1][0], ruta_h[-1][1], 1.0, COLOR_ELECTRON) if t > 0.96 else None)))

    ficha["etapas"] = [e[0] for e in etapas]
    return _figura(estados, etapas, esc, x_n_um, x_p_um, W_um, color, campo.reflector), ficha


def _figura(estados, etapas, esc, x_n_um, x_p_um, W_um, color, reflector):
    formas = [
        dict(type="rect", x0=X_IZQ, x1=X_DER, y0=Y_N, y1=Y_SUP, fillcolor="rgba(59,130,168,0.28)", line_width=0, layer="below"),
        dict(type="rect", x0=X_IZQ, x1=X_DER, y0=Y_P, y1=Y_N, fillcolor="rgba(229,163,63,0.45)", line_width=0, layer="below"),
        dict(type="rect", x0=X_IZQ, x1=X_DER, y0=Y_FONDO, y1=Y_P, fillcolor="rgba(47,138,126,0.20)", line_width=0, layer="below"),
        dict(type="rect", x0=X_IZQ, x1=X_DER, y0=Y_AL, y1=Y_FONDO, fillcolor="rgba(154,163,173,0.85)", line_width=0, layer="below"),
        dict(type="rect", x0=X_DEDO[0], x1=X_DEDO[1], y0=Y_SUP, y1=Y_SUP + 0.38, fillcolor="#D6DBE2", line_width=0),
        dict(type="path", path=(f"M {np.mean(X_DEDO)},{Y_SUP + 0.38} L {np.mean(X_DEDO)},{Y_CABLE} "
                                f"L {X_CARGA[0]},{Y_CABLE} M {X_CARGA[1]},{Y_CABLE} L {X_CABLE},{Y_CABLE} "
                                f"L {X_CABLE},{(Y_FONDO + Y_AL) / 2} L {X_DER},{(Y_FONDO + Y_AL) / 2}"),
             line=dict(color="#9AA3AD", width=2)),
        dict(type="rect", x0=X_CARGA[0], x1=X_CARGA[1], y0=Y_CABLE - 0.25, y1=Y_CABLE + 0.25,
             line=dict(color="#E5A33F", width=1.5), fillcolor="rgba(0,0,0,0)"),
    ]
    etiquetas = [
        dict(x=X_DER - 0.1, y=(Y_SUP + Y_N) / 2, text="Emisor tipo n", xanchor="right", font=dict(color=COLOR_TEXTO, size=12), showarrow=False),
        dict(x=X_DER - 0.1, y=(Y_N + Y_P) / 2, text="Zona de depleción (ampliada)", xanchor="right", font=dict(color="#0D131C", size=11), showarrow=False),
        dict(x=X_DER - 0.1, y=(Y_P + Y_FONDO) / 2, text="Base tipo p", xanchor="right", font=dict(color=COLOR_TEXTO, size=12), showarrow=False),
        dict(x=X_DER - 0.1, y=(Y_FONDO + Y_AL) / 2, text="Contacto de aluminio" + (" (reflector)" if reflector else ""), xanchor="right", font=dict(color="#0D131C", size=11), showarrow=False),
        dict(x=np.mean(X_CARGA), y=Y_CABLE + 0.42, text="carga", font=dict(color="#E5A33F", size=11), showarrow=False),
        dict(x=np.mean(X_DEDO), y=Y_SUP + 0.62, text="dedo de plata", font=dict(color=COLOR_SUAVE, size=10.5), showarrow=False),
        dict(x=X_IZQ - 0.08, y=Y_SUP, text="0 µm", xanchor="right", font=dict(color=COLOR_SUAVE, size=10.5), showarrow=False),
        dict(x=X_IZQ - 0.08, y=Y_N, text=_prof_texto(x_n_um), xanchor="right", font=dict(color=COLOR_SUAVE, size=10.5), showarrow=False),
        dict(x=X_IZQ - 0.08, y=Y_P, text=_prof_texto(x_p_um), xanchor="right", font=dict(color=COLOR_SUAVE, size=10.5), showarrow=False, yshift=-6),
        dict(x=X_IZQ - 0.08, y=Y_FONDO, text=_prof_texto(W_um), xanchor="right", font=dict(color=COLOR_SUAVE, size=10.5), showarrow=False),
    ]
    for xf in (2.6, 4.4, 6.2):
        etiquetas.append(dict(x=xf, y=Y_P + 0.06, ax=xf, ay=Y_N - 0.06, xref="x", yref="y", axref="x", ayref="y",
                              showarrow=True, arrowhead=3, arrowsize=1.1, arrowwidth=1.5, arrowcolor="#0D131C", text=""))
    etiquetas.append(dict(x=7.2, y=(Y_N + Y_P) / 2, text="campo eléctrico ↓", font=dict(color="#0D131C", size=10.5), showarrow=False))

    def narracion(st_):
        return dict(x=0.0, y=1.0, xref="paper", yref="paper", xanchor="left", yanchor="top",
                    align="left", showarrow=False, bgcolor="rgba(19,27,38,0.92)",
                    bordercolor="#2A3542", borderpad=8,
                    text=f"<b>{st_['etapa']}</b><br>{_envolver(st_['narracion'])}",
                    font=dict(color=COLOR_TEXTO, size=12.5))

    def trazas(st_):
        foton = st_["foton"]
        if foton is not None:
            ys = np.linspace(foton[1], min(foton[1] + 1.9, Y_TECHO), 40)
            xs = foton[0] + 0.1 * np.sin((ys - foton[1]) * 18.0)
            rastro = dict(type="scatter", x=xs, y=ys, mode="lines", line=dict(color=color, width=2.2), hoverinfo="skip")
            cabeza = dict(type="scatter", x=[foton[0]], y=[foton[1]], mode="markers",
                                marker=dict(size=13, color=color, line=dict(color="#FFFFFF", width=1)), hoverinfo="skip")
        else:
            rastro = dict(type="scatter", x=[None], y=[None], mode="lines", hoverinfo="skip")
            cabeza = dict(type="scatter", x=[None], y=[None], mode="markers", hoverinfo="skip")

        def particula(pos, col, signo):
            if pos is None:
                return dict(type="scatter", x=[None], y=[None], mode="markers+text", hoverinfo="skip")
            return dict(type="scatter", x=[pos[0]], y=[pos[1]], mode="markers+text", text=[signo],
                              textfont=dict(color="#0D131C", size=13), textposition="middle center",
                              marker=dict(size=19, color=col, line=dict(color="#FFFFFF", width=1)), hoverinfo="skip")

        def ruta(puntos, col):
            if not puntos:
                return dict(type="scatter", x=[None], y=[None], mode="lines", hoverinfo="skip")
            p = np.array(puntos)
            return dict(type="scatter", x=p[:, 0], y=p[:, 1], mode="lines", line=dict(color=col, width=1.3, dash="dot"), hoverinfo="skip")

        d = st_["destello"]
        destello = (dict(type="scatter", x=[d[0]], y=[d[1]], mode="markers", hoverinfo="skip",
                               marker=dict(size=18 + 34 * (1 - d[2]), color=d[3], opacity=max(d[2], 0.05)))
                    if d else dict(type="scatter", x=[None], y=[None], mode="markers", hoverinfo="skip"))
        em = st_["emitido"]
        emitido = (dict(type="scatter", x=[em[0]], y=[em[1]], mode="markers", hoverinfo="skip",
                              marker=dict(size=11, color="#8E3B2A", line=dict(color="#FFFFFF", width=1)))
                   if em else dict(type="scatter", x=[None], y=[None], mode="markers", hoverinfo="skip"))
        carga = dict(type="scatter", x=[np.mean(X_CARGA)], y=[Y_CABLE], mode="markers", hoverinfo="skip",
                           marker=dict(symbol="square", size=26, color="#E5A33F", opacity=st_["carga"]))
        return [rastro, cabeza, ruta(st_["e_ruta"], COLOR_ELECTRON), ruta(st_["h_ruta"], COLOR_HUECO),
                particula(st_["e"], COLOR_ELECTRON, "−"), particula(st_["h"], COLOR_HUECO, "+"),
                destello, emitido, carga]

    # Los cuadros se arman como diccionarios y la figura se construye sin la validación
    # de Plotly: con más de cien cuadros, validar cada traza tomaba más de un segundo y
    # no aporta nada, porque todas salen de esta misma función.
    cuadros = [dict(name=str(i), data=trazas(st_),
                    layout=dict(annotations=etiquetas + [narracion(st_)]))
               for i, st_ in enumerate(estados)]

    ultimo = estados[-1]
    fig = FiguraAnimada(data=trazas(ultimo), cuadros=cuadros)
    fig.update_layout(
        shapes=formas, annotations=etiquetas + [narracion(ultimo)],
        xaxis=dict(range=[-0.6, 10.1], visible=False, fixedrange=True),
        yaxis=dict(range=[-0.35, 12.6], visible=False, fixedrange=True),
        showlegend=False, height=680, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,19,28,0.0)",
        updatemenus=[dict(
            type="buttons", showactive=False, x=1.0, y=0.02, xanchor="right", yanchor="bottom",
            bgcolor="#1C2531", bordercolor="#2A3542", font=dict(color=COLOR_TEXTO, size=12),
            direction="left",
            buttons=[
                dict(label="▶  Reproducir el viaje", method="animate",
                     args=[None, dict(frame=dict(duration=110, redraw=True), fromcurrent=False,
                                      transition=dict(duration=0), mode="immediate")]),
                dict(label="⏸", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
            ],
        )],
        sliders=[dict(
            active=len(etapas) - 1, x=0.0, y=0.02, len=0.62, xanchor="left", yanchor="bottom",
            pad=dict(t=0, b=0), currentvalue=dict(visible=False),
            font=dict(color=COLOR_SUAVE, size=10), bgcolor="#1C2531", activebgcolor="#E5A33F",
            bordercolor="#2A3542", tickcolor="#2A3542",
            steps=[dict(label=nombre, method="animate",
                        args=[[str(inicio)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                   for nombre, inicio, _ in etapas],
        )],
    )
    return fig
