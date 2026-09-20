"""Pestaña 2 - Eficiencia cuántica: la respuesta de la celda y de sus sectores, color por color."""

import numpy as np
import streamlit as st

import config
from physics.collection import probabilidad_coleccion, transporte as armar_transporte
from physics.front_grid import malla
from physics.material import juntura as resolver_juntura
from physics.optics import campo_optico
from physics.quantum_efficiency import (
    coleccion_de_celda,
    corriente_de_cortocircuito,
    cota_superior,
    eficiencia_cuantica,
    generar_sectores,
    iqe_referida_a_absorcion,
    mapa_iqe_desde_locales,
    transporte_de_sector,
)
from units import celsius_a_kelvin, um_a_cm
from validation.monitor import EN_ORDEN, vigilar_eqe
from visualization import flujo, qe_plots
from visualization.figura_animada import FiguraAnimada
from visualization.optics_plots import _coma

NODOS_EN_DEPLECION = 12
TAUS_LAMINA_30_US = (10.0, 50.0, 200.0)      # Unidad 3, lámina 30


def _parametros(s):
    return dict(d_n_um=s.d_n_um, W_p_um=s.W_p_um, na=s.NA, nd=s.ND, t_c=s.T_c,
                reflector=s.reflector_trasero, irradiancia=s.irradiancia_soles, mu_p=s.mu_p,
                tau_p_us=s.tau_p_us, mu_n=s.mu_n, tau_n_us=s.tau_n_us, s_f=s.S_f, s_r=s.S_r,
                dispersion=s.dispersion_sectores, r_fija=config.reflectancia_fija_de(s))


@st.cache_data(show_spinner=False, max_entries=6)
def _resolver(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia, mu_p, tau_p_us, mu_n,
              tau_n_us, s_f, s_r, dispersion, r_fija):
    """
    Resuelve LA celda, que es una sola.

    La respuesta de la celda no es la de un dispositivo nominal por un lado y 64
    dispositivos sueltos por otro: es una sola curva, la que sale de la colección
    promediada por área sobre sus sectores (D-28). El mapa usa las colecciones locales
    de esos mismos sectores, así que su promedio es exactamente la curva.
    """
    d_n, W_p = um_a_cm(d_n_um), um_a_cm(W_p_um)
    t_k = celsius_a_kelvin(t_c)
    W = d_n + W_p
    union = resolver_juntura(d_n, na, nd, t_k)
    campo = campo_optico(d_n, W_p, reflector, irradiancia,
                         np.linspace(union.x_n, union.x_p, NODOS_EN_DEPLECION),
                         reflectancia_fija=r_fija)
    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    sectores = generar_sectores(config.N_SECTORES, tau_n_us * 1e-6, s_f, dispersion)
    fc_celda, fc_locales = coleccion_de_celda(campo, union, W, tr, sectores)
    eqe, iqe = eficiencia_cuantica(campo, fc_celda)
    return campo, union, tr, W, eqe, iqe, sectores, fc_celda, fc_locales


@st.cache_data(show_spinner=False, max_entries=6)
def _familias(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia, mu_p, tau_p_us, mu_n,
              tau_n_us, s_f, s_r, dispersion, r_fija):
    """
    Curvas de eficiencia interna cambiando un solo parámetro a la vez.

    Se calculan sobre la celda sin variación entre sectores, para que cada panel
    muestre el efecto del parámetro y nada más.
    """
    t_k = celsius_a_kelvin(t_c)
    d_n = um_a_cm(d_n_um)
    union = resolver_juntura(d_n, na, nd, t_k)
    nodos = np.linspace(union.x_n, union.x_p, NODOS_EN_DEPLECION)
    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    campos = {W_p_um: campo_optico(d_n, um_a_cm(W_p_um), reflector, irradiancia, nodos,
                                   reflectancia_fija=r_fija)}

    def iqe(wp_um=W_p_um, tau_us=tau_n_us, sf=s_f):
        if wp_um not in campos:
            campos[wp_um] = campo_optico(d_n, um_a_cm(wp_um), reflector, irradiancia, nodos,
                                         reflectancia_fija=r_fija)
        campo = campos[wp_um]
        tr_var = transporte_de_sector(tr, tau_us * 1e-6, sf)
        fc = probabilidad_coleccion(campo.x_cm, union, d_n + um_a_cm(wp_um), tr_var)
        return eficiencia_cuantica(campo, fc)[1]

    def valores(fijos, actual):
        return sorted(set(float(v) for v in fijos) | {float(actual)})

    return dict(
        lambda_nm=campos[W_p_um].lambda_nm,
        sf=[(v, iqe(sf=v), abs(v - s_f) < 1e-9) for v in valores((10.0, 1e3, 1e6), s_f)],
        tau=[(v, iqe(tau_us=v), abs(v - tau_n_us) < 1e-9)
             for v in valores(TAUS_LAMINA_30_US, tau_n_us)],
        wp=[(v, iqe(wp_um=v), abs(v - W_p_um) < 1e-9) for v in valores((20.0, 50.0, 300.0), W_p_um)],
        # La lámina 30 con una base gruesa: ahí la vida media sí compite con el espesor.
        tau_base_300=[iqe(wp_um=300.0, tau_us=v) for v in TAUS_LAMINA_30_US],
    )


@st.cache_data(show_spinner=False, max_entries=8)
def _figura_lbic(_mapa, huella, lambda_nm, _tau_us, _sf):
    return qe_plots.barrido_lbic(_mapa, lambda_nm, _tau_us, _sf).to_dict()


@st.cache_data(show_spinner=False, max_entries=8)
def _figura_construccion(_campo, _fc, _eqe, _iqe, _union, huella, lambda_nm):
    return qe_plots.construccion_eqe(_campo, _fc, _eqe, _iqe, _union, lambda_reposo=lambda_nm).to_dict()


def _pct(x, dec=1):
    return f"{100 * x:.{dec}f}".replace(".", ",") + " %"


def render():
    s = st.session_state
    p = _parametros(s)
    campo, union, tr, W, eqe, iqe, sectores, fc_celda, fc_locales = _resolver(**p)
    grid = malla(s.n_dedos, s.ancho_dedo_um * 1e-4)
    huella = tuple(p.values())

    # ------------------------------------------------------------------ portada
    st.subheader("Eficiencia cuántica: la respuesta de la celda color por color")
    st.write(
        "La eficiencia cuántica es el ensayo que mira dentro de la celda sin abrirla. Se ilumina con "
        "luz de un solo color, se mide cuánta corriente sale y se cuenta qué fracción de los fotones "
        "que llegaron terminó como carga en el circuito; después se repite para cada color del "
        "espectro. Como cada color se absorbe a una profundidad distinta, la curva que resulta dice "
        "qué tan bien funciona cada capa de la celda: el azul informa sobre el emisor y la superficie "
        "frontal, el rojo sobre el volumen de la base, y el infrarrojo sobre su espesor. Esta pestaña "
        "calcula esa curva desde el perfil de generación de la Pestaña 1, la descompone por sectores "
        "de la celda y muestra paso a paso cómo se obtiene."
    )

    s.setdefault("lambda_eqe", float(s.lambda_nm))
    lam_sel = st.slider("Color del ensayo  [nm]", *config.RANGOS["lambda_nm"], step=5.0,
                        key="lambda_eqe",
                        help="El color con que se describe el recorrido, se dibuja el mapa de "
                             "sectores y se marca la curva.")
    i = int(np.argmin(np.abs(campo.lambda_nm - lam_sel)))
    lam = float(campo.lambda_nm[i])
    R = float(campo.R[i])
    absorbida = float(np.trapezoid(campo.G[:, i], campo.x_cm) / campo.Nph[i])
    jsc = corriente_de_cortocircuito(campo, eqe)
    j_con_malla = jsc * (1.0 - grid.fraccion_sombra)

    pasos = [
        dict(titulo="Un solo color ilumina la celda", cifra="100", unidad=f"fotones de {lam:.0f} nm",
             texto="La eficiencia cuántica se mide color por color: se ilumina con un color, se mide "
                   "la corriente y se pasa al siguiente.", perdida=None),
        dict(titulo="Cruza la superficie", cifra=_pct(1 - R), unidad="entra al silicio",
             texto="La reflexión frontal decide cuántos fotones llegan a intentarlo.",
             perdida=f"{_pct(R)} se refleja"),
        dict(titulo="Se absorbe", cifra=_pct(absorbida), unidad="crea un par",
             texto=f"A {lam:.0f} nm, el 63 % de lo que entra se absorbe antes de "
                   f"{qe_plots._profundidad_texto(1e4 / float(campo.alpha[i]))}.",
             perdida=(f"{_pct(1 - R - absorbida)} atraviesa la celda" if 1 - R - absorbida > 5e-4 else None)),
        dict(titulo="Llega a la juntura", cifra=_pct(float(eqe[i])), unidad="EQE",
             texto="Cada par pesa por su probabilidad de colección: esa suma, dividida por los fotones "
                   "que llegaron, es la eficiencia cuántica externa.",
             perdida=f"{_pct(absorbida - float(eqe[i]))} se recombina antes", tono="perdida"),
        dict(titulo="Descontada la reflexión", cifra=_pct(float(iqe[i])), unidad="IQE",
             texto="Dividir por la fracción que entró aísla la calidad interna de la celda.",
             perdida=None),
        dict(titulo="Con todo el espectro solar", cifra=_coma(1e3 * jsc, 2), unidad="mA/cm²",
             texto="Integrar la EQE con los fotones que trae el Sol da la corriente de cortocircuito "
                   "(Unidad 3, lámina 26).", perdida=None, final=True,
             nota=f"con la sombra de la malla, {_coma(1e3 * j_con_malla, 2)} mA/cm², la misma de las "
                  f"Pestañas 1 y 3"),
    ]
    st.markdown(flujo.diagrama_html(pasos, f"de cada 100 fotones de {lam:.0f} nm que llegan a la "
                                           f"parte iluminada"), unsafe_allow_html=True)

    util = (campo.lambda_nm >= 400) & (campo.lambda_nm <= 1000)
    i450 = int(np.argmin(np.abs(campo.lambda_nm - 450)))
    i900 = int(np.argmin(np.abs(campo.lambda_nm - 900)))
    mapa = mapa_iqe_desde_locales(campo, fc_locales, i)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("EQE media, 400–1000 nm", _pct(float(eqe[util].mean())),
              help="Promedio simple de la curva externa en el rango donde el silicio responde bien.")
    c2.metric("IQE en el azul · 450 nm", _pct(float(iqe[i450])),
              help="Informa sobre el emisor y la superficie frontal.")
    c3.metric("IQE en el rojo · 900 nm", _pct(float(iqe[i900])),
              help="Informa sobre el volumen de la base.")
    c4.metric(f"Rango entre sectores · {lam:.0f} nm",
              f"{_coma(100 * mapa.min(), 1)}–{_coma(100 * mapa.max(), 1)} %",
              help="IQE local del peor y del mejor sector al color del ensayo.")

    familias = _familias(**p)
    iqe_abs = iqe_referida_a_absorcion(campo, eqe)
    st.session_state["_bus"]["eqe"] = dict(
        campo=campo, eqe=eqe, iqe=iqe, iqe_abs=iqe_abs, mapa=mapa, i_lam=i, sectores=sectores,
        NA=s.NA, iqe_por_tau=[c[1] for c in familias["tau"]], j_con_malla=j_con_malla)
    for v in vigilar_eqe(st.session_state["_bus"]["eqe"]):
        if v.estado != EN_ORDEN:
            st.warning(f"**Monitor físico · {v.nombre}.** {v.mensaje}", icon="⚠")

    # ------------------------------------------------------------------ curvas
    st.divider()
    st.markdown("### Las eficiencias cuánticas de la celda")
    st.plotly_chart(qe_plots.curvas_eficiencia(campo.lambda_nm, eqe, iqe, cota_superior(campo), lam,
                                               iqe_abs),
                    use_container_width=True)
    st.caption(
        "La eficiencia externa (EQE) cuenta respecto de todos los fotones que llegan; la interna (IQE) "
        "descuenta los que se reflejaron, siguiendo la definición de la Unidad 3, lámina 25. La cota "
        "punteada es la fracción que entra: ninguna curva externa puede superarla. La distancia entre la "
        "cota y la EQE no es solo recombinación: en el infrarrojo, gran parte es luz que atraviesa la "
        "celda sin absorberse. Por eso se dibuja también la eficiencia por fotón absorbido, que divide por "
        "lo que el silicio absorbe de verdad —con el reflector, contando la luz que vuelve del aluminio— y "
        "aísla la calidad de la colección; donde se separa de la IQE, la pérdida es de absorción, no de "
        "recombinación."
    )

    # ------------------------------------------------------------------ qué informa cada parte
    st.divider()
    st.markdown("### Qué parte de la curva informa sobre qué parte de la celda")
    st.write(
        "Esta es la razón por la que la eficiencia cuántica sirve para diagnosticar. Cada panel cambia un "
        "solo parámetro y deja todo lo demás fijo. Donde las curvas se separan está la parte del espectro "
        "que informa sobre ese parámetro; donde se superponen, esa zona de la curva no dice nada sobre él."
    )

    sup = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")

    def formato_s(v):
        e = int(np.floor(np.log10(v)))
        m = v / 10 ** e
        base = "10" + str(e).translate(sup)
        return (base if abs(m - 1) < 1e-9 else f"{_coma(m, 0)}×{base}") + " cm/s"

    fam = [
        dict(titulo="Superficie frontal S_f", leyenda="S_f", color="#E4664A",
             formato=formato_s, curvas=familias["sf"]),
        dict(titulo="Vida media de la base τₙ", leyenda="τₙ", color="#5FC49B",
             formato=lambda v: f"{_coma(v, 0)} µs", curvas=familias["tau"]),
        dict(titulo="Espesor de la base", leyenda="base", color="#5AA8D6",
             formato=lambda v: f"{_coma(v, 0)} µm", curvas=familias["wp"]),
    ]
    st.plotly_chart(qe_plots.que_informa_cada_parte(familias["lambda_nm"], fam), use_container_width=True)

    def cambio_en(curvas, lam_nm):
        k = int(np.argmin(np.abs(familias["lambda_nm"] - lam_nm)))
        valores = [100 * c[1][k] for c in curvas]
        return max(valores) - min(valores)

    st.caption(
        f"**Superficie frontal.** Pasar S_f de 10 a 10⁶ cm/s mueve la respuesta a 450 nm "
        f"{_coma(cambio_en(familias['sf'], 450), 0)} puntos y a 1000 nm "
        f"{_coma(cambio_en(familias['sf'], 1000), 1)}: el azul se absorbe en el emisor, a décimas de micra "
        f"de esa superficie. **Vida media de la base.** Con las vidas medias de la lámina 30 de la Unidad 3 "
        f"(10, 50 y 200 µs) el azul cambia {_coma(cambio_en(familias['tau'], 450), 2)} puntos y el rojo de "
        f"950 nm {_coma(cambio_en(familias['tau'], 950), 0)}: el azul nunca llega a la base. En esta celda el "
        f"efecto en el rojo es moderado porque incluso con 10 µs la longitud de difusión, "
        f"{_coma(1e4 * np.sqrt(tr.D_n * 10e-6), 0)} µm, supera el espesor de la base; con una base de 300 µm "
        f"las mismas tres vidas medias separan el rojo de 950 nm en "
        f"{_coma(cambio_en([(0, c) for c in familias['tau_base_300']], 950), 0)} puntos, como en la lámina. "
        f"**Espesor de la "
        f"base.** Entre 20 y 300 µm, el infrarrojo de 1050 nm cambia {_coma(cambio_en(familias['wp'], 1050), 0)} "
        f"puntos, porque una base delgada deja escapar la luz que se absorbe lento, mientras el azul no se "
        f"entera. Es la respuesta a la pregunta de la presentación sobre qué parte de la curva informa sobre "
        f"el emisor, sobre el espesor de la base y sobre la vida media del volumen."
    )

    # ------------------------------------------------------------------ sectores
    st.divider()
    st.markdown("### La celda por sectores")
    if s.dispersion_sectores > 0:
        st.write(
            f"La celda se divide en una grilla de {sectores.n} × {sectores.n} sectores, y cada uno tiene su "
            f"propia vida media en la base y su propia velocidad de recombinación frontal, como exige el "
            f"enunciado. Los valores de la barra lateral son su media geométrica: la celda sigue siendo la "
            f"de la semilla, con sectores repartidos a su alrededor según la variación de fabricación, hoy en "
            f"**{_coma(s.dispersion_sectores, 2)}**. La variación es suave, con correlación espacial —sectores "
            f"vecinos se parecen, como en una oblea real, porque sus causas actúan sobre regiones extensas— y el "
            f"sorteo es fijo, así que es la misma celda en todas las pestañas."
        )
    else:
        st.info("Con la variación de fabricación en cero todos los sectores son idénticos y el mapa es "
                "plano. Súbela en la barra lateral, en «Variación de fabricación».")

    escala = st.toggle("Escala vertical completa, de 0 a 100 %", value=False,
                       help="Por defecto el eje se ajusta al rango de los sectores, para que se vean "
                            "variaciones de pocos puntos.")
    iqe_celda = float(iqe[i])
    st.plotly_chart(qe_plots.relieve_sectores(mapa, lam, iqe_celda, sectores.tau_n_s * 1e6,
                                                  sectores.s_f, escala), use_container_width=True)

    log_tau = np.log(sectores.tau_n_s).ravel()
    log_sf = np.log(sectores.s_f).ravel()
    valores = mapa.ravel()
    if s.dispersion_sectores > 0 and np.std(valores) > 0:
        r_tau = float(np.corrcoef(valores, log_tau)[0, 1])
        r_sf = float(np.corrcoef(valores, log_sf)[0, 1])
        dominante = ("la vida media de la base" if abs(r_tau) >= abs(r_sf)
                     else "la velocidad de recombinación frontal")
        st.caption(
            f"A {lam:.0f} nm el mapa sigue sobre todo a **{dominante}**: la correlación entre la IQE local y "
            f"la vida media es {_coma(r_tau, 2)}, y con la recombinación frontal {_coma(r_sf, 2)} (un valor "
            f"cercano a 1 significa que suben juntas; cercano a −1, que una baja cuando la otra sube). Mueve el "
            f"color del ensayo al azul y al rojo y compara con los dos mapas de abajo: el mapa cambia de dueño. "
            f"El promedio del relieve sobre los 64 sectores es {_coma(100 * float(mapa.mean()), 4)} % y la IQE de la celda "
            f"completa {_coma(100 * iqe_celda, 4)} %: coinciden porque la eficiencia cuántica es lineal en la "
            f"probabilidad de colección."
        )

    m1, m2 = st.columns(2, gap="large")
    with m1:
        st.plotly_chart(qe_plots.mapa_de_sectores(
            sectores.tau_n_s * 1e6, "Vida media local en la base",
            "más alta, mejor: los pares viven más", "µs", lambda v: _coma(v, 0)),
            use_container_width=True)
    with m2:
        st.plotly_chart(qe_plots.mapa_de_sectores(
            sectores.s_f / 1e4, "Recombinación frontal local",
            "más baja, mejor: la escala está invertida para que claro siga siendo mejor", "×10⁴ cm/s",
            lambda v: _coma(v, 1), invertir=True),
            use_container_width=True)

    b1, b2 = st.columns([3, 2], gap="large")
    with b1:
        st.plotly_chart(FiguraAnimada.desde_diccionario(
            _figura_lbic(mapa, huella + (lam,), lam, sectores.tau_n_s * 1e6, sectores.s_f)),
            use_container_width=True)
    with b2:
        st.plotly_chart(qe_plots.histograma_sectores(mapa, lam, iqe_celda), use_container_width=True)
    st.caption(
        "El barrido imita un mapeo por haz de luz inducido: una sonda de luz de un color recorre la celda y "
        "mide la corriente de cada punto. Lo que mide es la respuesta local de un mismo dispositivo, no la de "
        "dispositivos distintos, y por eso el promedio del mapa es la curva de la celda. El histograma "
        "muestra cuántos sectores hay de cada calidad; la línea marca la celda completa."
    )

    # ------------------------------------------------------------------ cómo se calcula
    st.divider()
    st.markdown("### Cómo se calcula la eficiencia cuántica")

    def lectura(lam_nm):
        j = int(np.argmin(np.abs(campo.lambda_nm - lam_nm)))
        r_ = float(campo.R[j])
        abs_ = float(np.trapezoid(campo.G[:, j], campo.x_cm) / campo.Nph[j])
        return dict(lam=float(campo.lambda_nm[j]), R=r_, entra=1 - r_, abs=abs_, eqe=float(eqe[j]),
                    iqe=float(iqe[j]), atraviesa=max(1 - r_ - abs_, 0.0))

    azul, rojo, ir = lectura(450), lectura(850), lectura(1100)
    st.markdown(
        "**De qué trata esta sección.** Las secciones anteriores muestran el resultado: la curva de "
        "eficiencia cuántica y cómo cambia. Esta muestra el cálculo que la produce, color por color, "
        "para que se vea de dónde sale cada punto de la curva y por qué tiene la forma que tiene. La "
        "animación de abajo hace, para cada color del espectro, los mismos cuatro pasos con que la "
        "aplicación calcula la curva desde el perfil de generación de la Pestaña 1, como exige el "
        "enunciado."
    )
    st.markdown(
        "**Los cuatro pasos, para un color.**\n\n"
        "1. **Cuántos fotones entran.** De los que llegan, se descuenta la fracción que refleja la "
        "superficie.\n"
        "2. **Dónde se absorben.** La ley de Beer-Lambert reparte esos fotones en profundidad: el azul, "
        "pegado a la superficie; el infrarrojo, a lo largo de toda la celda.\n"
        "3. **Cuántos de esos pares llegan a la juntura.** Cada par nacido a una profundidad se "
        "multiplica por su probabilidad de colección a esa profundidad.\n"
        "4. **Se suma y se divide.** La suma sobre toda la profundidad, dividida por los fotones que "
        "llegaron, es la eficiencia cuántica externa de ese color; dividida además por la fracción que "
        "entró, es la interna."
    )
    st.markdown(
        "**Qué observar al recorrer el espectro.**\n\n"
        f"- **En el azul, {azul['lam']:.0f} nm.** Se absorbe el {_pct(azul['abs'])} de los fotones que "
        f"llegan, pero solo el {_pct(azul['eqe'])} llega a la juntura: el área verde es mucho más chica "
        f"que la gris, porque los pares nacen a décimas de micra de una superficie que los captura.\n"
        f"- **En el rojo cercano, {rojo['lam']:.0f} nm.** La luz se absorbe en la base, donde los pares "
        f"viven lo suficiente: el área verde casi cubre la gris y la eficiencia interna llega a "
        f"{_pct(rojo['iqe'])}. Es el máximo de la curva.\n"
        f"- **En el infrarrojo, {ir['lam']:.0f} nm.** El área gris se achica: solo se absorbe el "
        f"{_pct(ir['abs'])} de los fotones, y el {_pct(ir['atraviesa'])} atraviesa la celda sin absorberse. "
        f"Los pares que sí nacen se colectan bien; la curva cae por falta de absorción, no por "
        f"recombinación."
    )
    st.markdown(
        "**Cómo usarla.** El botón recorre el espectro de 300 a 1200 nm; la barra permite detenerse en "
        "cualquier color. En reposo muestra el color del ensayo elegido arriba. El recuadro superior da, para "
        "cada color, cuánto se refleja, cuánto se absorbe, cuánto llega a la juntura, y la **respuesta "
        "espectral**: la corriente por cada watt de luz de ese color, que es lo que mide de verdad un "
        "instrumento de laboratorio y se convierte en eficiencia cuántica multiplicando por la energía de un "
        "fotón (Unidad 3, lámina 27)."
    )
    st.plotly_chart(FiguraAnimada.desde_diccionario(
        _figura_construccion(campo, fc_celda, eqe, iqe, union, huella, lam)), use_container_width=True)
    st.caption(
        "A la izquierda, para el color del cuadro: el área gris son los fotones que se absorben a cada "
        "profundidad y el área verde, los pares que además llegan a la juntura. Como el eje de profundidad es "
        "logarítmico, se dibuja la cantidad de fotones por cada factor diez de profundidad, de modo que el "
        "tamaño de cada área es proporcional a lo que representa: la razón entre el área verde y los fotones "
        "que llegaron es la EQE. La línea ámbar es la juntura. A la derecha, la curva se construye con cada "
        "color ya calculado. La barra permite detenerse en cualquier color; en reposo, la figura muestra el "
        "color del ensayo."
    )
