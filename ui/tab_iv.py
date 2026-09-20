"""Pestaña 3 - Ensayo de curva I-V."""

import numpy as np
import streamlit as st

import config
import constants as C
from physics.balance import balance_de_potencia
from physics.collection import (probabilidad_coleccion, reparto_por_destino,
                                transporte as armar_transporte)
from physics.compromiso import barrido_de_mallas, caida_lateral, mejor_malla
from physics.diode import (corriente_saturacion, curva_iv, factor_de_forma_ideal,
                           resolver_corriente)
from physics.front_grid import malla
from physics.material import bandgap, juntura as resolver_juntura
from physics.optics import campo_optico
from physics.quantum_efficiency import (coleccion_de_celda, corriente_de_cortocircuito,
                                        destinos_de_celda, eficiencia_cuantica,
                                        generar_sectores)
from ui import danos
from units import celsius_a_kelvin, cm_a_um, um_a_cm, voltaje_termico
from data.loaders import espectro_am15g
from visualization import circuito, energia_plots, flujo, iv_plots, malla_plots
from visualization.figura_animada import FiguraAnimada
from visualization.optics_plots import _coma

NODOS_EN_DEPLECION = 12


@st.cache_data(show_spinner=False, max_entries=6)
def _fotocorriente(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia,
                   mu_p, tau_p_us, mu_n, tau_n_us, s_f, s_r, dispersion, r_fija=None):
    """
    Corriente fotogenerada y corriente de saturación, desde la cadena completa.

    La fotocorriente no es un parámetro libre: sale de integrar la eficiencia
    cuántica sobre el espectro, que a su vez sale de la generación y la colección
    de las Pestañas 1 y 2. Es lo que la verificación V3 exige.

    La colección es la de LA celda, promediada por área sobre sus sectores, que es
    la misma que usa la Pestaña 2. Si aquí se usara la celda homogénea nominal y
    allá la celda con dispersión, las dos pestañas estarían describiendo
    dispositivos distintos (ver D-28).
    """
    d_n, W_p = um_a_cm(d_n_um), um_a_cm(W_p_um)
    t_k = celsius_a_kelvin(t_c)
    union = resolver_juntura(d_n, na, nd, t_k)
    campo = campo_optico(d_n, W_p, reflector, irradiancia,
                         np.linspace(union.x_n, union.x_p, NODOS_EN_DEPLECION),
                         reflectancia_fija=r_fija)
    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    sectores = generar_sectores(config.N_SECTORES, tau_n_us * 1e-6, s_f, dispersion)
    fc, _ = coleccion_de_celda(campo, union, d_n + W_p, tr, sectores)
    eqe, _ = eficiencia_cuantica(campo, fc)
    j_l = corriente_de_cortocircuito(campo, eqe)
    j0, termino_base, termino_emisor = corriente_saturacion(
        na, nd, tr, t_k, union=union, W_cm=d_n + W_p)
    # El reparto de los fotones entre sus destinos es el mismo de la Pestaña 1, y es
    # lo que el balance de potencia necesita para repartir las pérdidas por causa.
    destinos = destinos_de_celda(campo, union, d_n + W_p, tr, sectores)
    reparto = reparto_por_destino(campo, destinos, union)
    return j_l, j0, termino_base, termino_emisor, tr, t_k, campo, reparto


@st.cache_data(show_spinner=False, max_entries=32)
def _curva(j_l, j0, rs, rp, n_idealidad, t_k, irradiancia):
    return curva_iv(j0, j_l, rs, rp, n_idealidad, t_k,
                    irradiancia_w_cm2=C.IRRADIANCE_1SUN * irradiancia)


@st.cache_data(show_spinner=False, max_entries=6)
def _compromiso(j_l_sin_sombra, j0, rs_extra, rp, n_idealidad, t_k, ancho_dedo_cm,
                irradiancia):
    """
    Recorre el número de dedos repartiendo la pérdida de cada malla en sus causas.

    Es lo más caro de la pestaña —resuelve tres curvas completas por cada malla—,
    así que va en su propia caché y no depende del número de dedos elegido: el
    barrido es el mismo y solo se mueve la marca.
    """
    return barrido_de_mallas(j_l_sin_sombra, j0, rs_extra, rp, n_idealidad, t_k,
                             ancho_dedo_cm, irradiancia)


@st.cache_data(show_spinner=False, max_entries=6)
def _balance(_campo, _reparto, _curva, huella, fraccion_sombra, eg_v, soles):
    return balance_de_potencia(espectro_am15g(), _campo, _reparto, fraccion_sombra, _curva,
                               eg_v, soles)


@st.cache_data(show_spinner=False, max_entries=6)
def _eficiencia_con_reflectancia(r_fija, d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia,
                                 mu_p, tau_p_us, mu_n, tau_n_us, s_f, s_r, dispersion,
                                 n_dedos, ancho_dedo_um, rs_extra, rp, n_idealidad):
    """
    La misma celda, pero con la reflectancia que da un antirreflejo con textura.

    Sirve para poner la pérdida óptica en perspectiva sin tocar los controles: es el
    mismo cálculo completo, cambiando solo la reflexión de la superficie frontal.
    """
    j_l, j0, _, _, _, t_k, _, _ = _fotocorriente(
        d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia, mu_p, tau_p_us, mu_n,
        tau_n_us, s_f, s_r, dispersion, r_fija)
    grid = malla(n_dedos, ancho_dedo_um * 1e-4)
    curva = curva_iv(j0, j_l * (1 - grid.fraccion_sombra), rs_extra + grid.r_serie, rp,
                     n_idealidad, t_k, irradiancia_w_cm2=C.IRRADIANCE_1SUN * irradiancia)
    return curva.eficiencia


@st.cache_data(show_spinner=False, max_entries=6)
def _figura_construccion(_curva, huella, j0, j_l, rs, rp, vt_n):
    return iv_plots.construccion_de_la_curva(_curva, j0, j_l, rs, rp, vt_n).to_dict()


@st.cache_data(show_spinner=False, max_entries=12)
def _familia_rs(j_l, j0, rp, n_idealidad, t_k, irradiancia):
    return {rs: curva_iv(j0, j_l, rs, rp, n_idealidad, t_k,
                         irradiancia_w_cm2=C.IRRADIANCE_1SUN * irradiancia,
                         n_puntos=200)
            for rs in (0.0, 0.5, 1.5, 4.0)}


def render():
    s = st.session_state
    st.subheader("Ensayo de curva I-V")
    st.write(
        "Una fuente barre el voltaje sobre la celda iluminada y registra la corriente "
        "que entrega. De esa curva salen los números que resumen el desempeño de cualquier "
        "celda solar, y el recorrido de abajo los ordena de la corriente a la potencia."
    )

    j_l_desnuda, j0, t_base, t_emisor, tr, t_k, campo, reparto = _fotocorriente(
        s.d_n_um, s.W_p_um, s.NA, s.ND, s.T_c, s.reflector_trasero,
        s.irradiancia_soles, s.mu_p, s.tau_p_us, s.mu_n, s.tau_n_us, s.S_f, s.S_r,
        s.dispersion_sectores, config.reflectancia_fija_de(s))

    grid = malla(s.n_dedos, s.ancho_dedo_um * 1e-4)
    j_l = j_l_desnuda * (1.0 - grid.fraccion_sombra)
    rs_total = s.R_s + grid.r_serie
    st.session_state["_bus"]["curva_iv"] = {"j_l": j_l}

    curva = _curva(j_l, j0, rs_total, s.R_p, s.n_idealidad, t_k, s.irradiancia_soles)
    huella_electrica = (round(j_l, 12), round(j0, 18), round(rs_total, 9), s.R_p,
                        s.n_idealidad, round(t_k, 6), s.irradiancia_soles)
    ideal = _curva(j_l, j0, 0.0, 1e12, 1.0, t_k, s.irradiancia_soles)
    ff0 = factor_de_forma_ideal(curva.v_oc, t_k)

    eg_v = float(bandgap(t_k))
    st.markdown(flujo.diagrama_html(
        flujo.pasos_de_la_curva(curva, ff0, j_l_desnuda, grid.fraccion_sombra, j0, eg_v,
                                s.irradiancia_soles),
        f"de la corriente que genera la luz, {_coma(1e3 * j_l_desnuda, 2)} mA/cm²"),
        unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Corriente de cortocircuito", f"{_coma(1e3 * curva.j_sc, 2)} mA/cm²",
              help="Leída de la curva en cero volts. La verificación V3 la compara con la "
                   "corriente que entrega la eficiencia cuántica de la Pestaña 2.")
    c2.metric("Voltaje de circuito abierto", f"{_coma(curva.v_oc, 4)} V",
              help="Donde la corriente se anula. Depende de la corriente de saturación, que "
                   "mide la recombinación de la celda en oscuridad.")
    c3.metric("Factor de forma", _coma(curva.ff, 4),
              delta=f"{'+' if curva.ff >= ff0 else '−'}{_coma(abs(curva.ff - ff0), 4)} "
                    f"respecto del ideal {_coma(ff0, 3)}",
              delta_color="off",
              help="Cuán cuadrada es la curva. El ideal es la expresión empírica de la Unidad 4 "
                   "para este voltaje de circuito abierto, sin resistencias parásitas.")
    c4, c5, c6 = st.columns(3)
    c4.metric("Eficiencia", f"{_coma(100 * curva.eficiencia, 2)} %",
              help="Potencia máxima dividida por la irradiancia incidente.")
    c5.metric("Potencia máxima", f"{_coma(1e3 * curva.p_max, 2)} mW/cm²",
              help=f"En el punto de trabajo: {_coma(curva.v_mpp, 3)} V y "
                   f"{_coma(1e3 * curva.j_mpp, 2)} mA/cm².")
    c6.metric("Resistencia serie", f"{_coma(rs_total, 3)} Ω·cm²",
              help=f"{_coma(grid.r_serie, 3)} de la malla frontal y {_coma(s.R_s, 3)} del resto "
                   f"del circuito, que se controla en la barra lateral.")

    # Guarda fisica: el voltaje de circuito abierto no puede superar la banda
    # prohibida. Nuestro modelo trata el factor de idealidad y la corriente de
    # saturacion como parametros independientes, y no lo son: un factor de
    # idealidad alto nace de la recombinacion en la zona de deplecion, que trae
    # consigo una corriente de saturacion mucho mayor. Subir solo n produce una
    # mejora ficticia. Detectado en la prueba de esfuerzo E9.
    if curva.v_oc > eg_v:
        st.error(
            f"**Régimen no físico.** El voltaje de circuito abierto ({_coma(curva.v_oc, 4)} V) "
            f"supera la banda prohibida del silicio a esta temperatura ({_coma(eg_v, 4)} eV). "
            f"El voltaje extraíble está limitado por la separación de los cuasi-niveles "
            f"de Fermi, y los portadores termalizan a los bordes de banda en picosegundos, "
            f"así que esa separación no puede superar E_g en un dispositivo convencional. "
            f"Ocurre porque el modelo trata el factor de idealidad y la corriente de "
            f"saturación como independientes, y no lo son — un factor de idealidad alto "
            f"nace de la recombinación en la zona de depleción, que trae consigo una "
            f"corriente de saturación mucho mayor. Con n ≥ 1,95 los resultados de esta "
            f"pestaña dejan de ser confiables.",
            icon="⚠",
        )

    st.caption(
        f"Corriente de saturación **{f'{j0:.3e}'.replace('.', ',')} A/cm²**, con el término de "
        f"la base dominando al del emisor en razón **{_coma(t_base / t_emisor, 0)} a 1** — por eso "
        f"el emisor degenerado no compromete el resultado (D-05)  ·  resistencia serie "
        f"total **{_coma(rs_total, 3)} Ω·cm²**, de los cuales {_coma(grid.r_serie, 3)} vienen de "
        f"la malla  ·  sombreado **{_coma(100 * grid.fraccion_sombra, 2)} %**  ·  punto de máxima "
        f"potencia en {_coma(curva.v_mpp, 3)} V"
    )

    # ------------------------------------------------------------------ balance de potencia
    st.divider()
    st.markdown("### A dónde va la energía del sol")
    st.write(
        "Las cifras de arriba dicen cuánta potencia entrega la celda. Ésta dice dónde quedó el resto. "
        "El reparto usa una regla, y conviene tenerla clara: **cada par que llega a la juntura vale la "
        "energía de la banda prohibida**, y todo lo que el fotón traía de más ya se contó como calor. "
        "Con esa convención, cada fotón perdido cuesta lo mismo —la banda prohibida por su carga— y las "
        "pérdidas eléctricas se miden sobre lo que sobrevive. Es la contabilidad del límite de eficiencia "
        "de la Unidad 4, aplicada a esta celda en vez de a una ideal."
    )

    balance = _balance(campo, reparto, curva, huella_electrica, grid.fraccion_sombra, eg_v,
                       s.irradiancia_soles)
    st.session_state["_bus"]["curva_iv"].update(
        curva=curva, j0=j0, rs=rs_total, rp=s.R_p, n_idealidad=s.n_idealidad, t_k=t_k,
        ff0=ff0, eg_v=eg_v, NA=s.NA, balance=balance, irradiancia=s.irradiancia_soles)
    st.plotly_chart(energia_plots.cascada_de_potencia(balance), use_container_width=True)

    r_tratada = 0.05
    eficiencia_tratada = _eficiencia_con_reflectancia(
        r_tratada, s.d_n_um, s.W_p_um, s.NA, s.ND, s.T_c, s.reflector_trasero,
        s.irradiancia_soles, s.mu_p, s.tau_p_us, s.mu_n, s.tau_n_us, s.S_f, s.S_r,
        s.dispersion_sectores, s.n_dedos, s.ancho_dedo_um, s.R_s, s.R_p, s.n_idealidad)
    perdidas = {f: balance.por_familia(f) for f in ("fundamental", "optica", "recombinacion",
                                                    "electrica")}
    st.caption(
        f"Las dos primeras pérdidas no dependen del diseño de esta celda: los fotones de más de "
        f"{balance.lambda_banda_nm:.0f} nm no tienen energía para crear un par, y de los que sí la tienen "
        f"solo sobrevive la banda prohibida. Entre las dos se llevan "
        f"{_coma(perdidas['fundamental'], 1)} mW/cm², y dejan {_coma(balance.disponible, 1)} disponibles, "
        f"que equivalen a {_coma(1e3 * balance.j_maxima, 1)} mA/cm² si cada fotón útil diera una carga.  ·  "
        f"De ahí en adelante manda la óptica: {_coma(perdidas['optica'], 1)} mW/cm² se pierden como luz, "
        f"contra {_coma(perdidas['recombinacion'], 1)} de recombinación y {_coma(perdidas['electrica'], 1)} "
        f"de pérdidas eléctricas. La reflexión sola se lleva "
        f"{_coma(balance.etapas[3].potencia, 1)} mW/cm², más del doble de lo que la celda entrega: es la "
        f"consecuencia directa de una superficie pulida y sin recubrimiento antirreflejo, como pide el "
        f"enunciado. **Con una superficie tratada**, del tipo que refleja un {_coma(100 * r_tratada, 0)} % "
        f"en vez del {_coma(100 * float(np.trapezoid(campo.Nph * campo.R, campo.lambda_nm) / np.trapezoid(campo.Nph, campo.lambda_nm)), 0)} % "
        f"promedio de hoy, esta misma celda daría **{_coma(100 * eficiencia_tratada, 2)} %** en lugar de "
        f"{_coma(100 * curva.eficiencia, 2)} %; se prueba con el control de reflectancia de la barra "
        f"lateral.  ·  El balance cierra contra la potencia incidente con un error de "
        f"menos de una milésima de mW/cm²."
    )

    st.divider()

    defectos = danos.defectos_de(s)
    con_fallas = danos.resolver(s) if defectos.hay_defectos else None

    g1, g2 = st.columns(2, gap="large")
    with g1:
        st.plotly_chart(
            iv_plots.curva_iv(curva, ideal,
                              danada=None if con_fallas is None else
                              (con_fallas["v"], con_fallas["j"], "con las fallas de la Pestaña 4")),
            use_container_width=True)
        pie = ("El rectángulo naranja tiene por área la potencia máxima extraíble; el gris, "
               "el producto Voc×Jsc que sería el ideal. El factor de forma es exactamente el "
               "cociente entre ambas áreas.")
        if con_fallas is not None:
            pf = con_fallas["p"]
            pie += (f"  La curva punteada es la misma celda con las fallas que introduce la "
                    f"Pestaña 4: la eficiencia baja de {_coma(100 * curva.eficiencia, 2)} % a "
                    f"**{_coma(100 * pf['eficiencia'], 2)} %**, con la corriente en "
                    f"{_coma(1e3 * pf['j_sc'], 2)} mA/cm² y el factor de forma en "
                    f"{_coma(pf['ff'], 3)}.")
        st.caption(pie)
    with g2:
        st.plotly_chart(iv_plots.barrido_animado(curva), use_container_width=True)
        st.caption(
            "Cada punto que aparece es la solución numérica de la ecuación implícita para "
            "ese voltaje exacto, resuelta buscando la raíz. No es una curva precalculada "
            "que se revela con un efecto visual."
        )

    st.divider()

    st.markdown("#### La trampa de la ecuación implícita")
    vt_n = s.n_idealidad * C.KB_EV * t_k
    j_ingenua = j_l - j0 * (np.exp(np.clip(curva.v / vt_n, 0, 600)) - 1) - curva.v / s.R_p
    p_ingenua = curva.v * np.maximum(j_ingenua, 0.0)
    ff_ingenuo = float(p_ingenua.max() / (curva.v_oc * curva.j_sc))

    t1, t2 = st.columns([2, 3])
    with t1:
        st.metric("Factor de forma correcto", _coma(curva.ff, 4),
                  help="Resolviendo la ecuación implícita punto por punto.")
        st.metric("Ignorando el término Rs·J", _coma(ff_ingenuo, 4),
                  delta=f"+{_coma(100 * (ff_ingenuo / curva.ff - 1), 1)} % de sobrestimación",
                  delta_color="inverse")
    with t2:
        st.write(
            "La ecuación del diodo tiene la corriente en ambos lados: aparece en el "
            "voltaje que realmente ve la juntura, que es el aplicado menos lo que se "
            "consume en la resistencia serie. Si se ignora ese término y se grafica la "
            "forma explícita, la curva **se ve correcta a simple vista** pero el factor "
            "de forma queda sistemáticamente sobrestimado, porque no se está "
            "descontando la caída de voltaje. El enunciado advierte de este error. La "
            "verificación que lo detecta es C-T5, no V4: V4 se evalúa sin resistencia "
            "serie, y sin ella el término desaparece y las dos formas coinciden, así que "
            "un programa con el error aprobaría V4 igual (D-27)."
        )

    st.plotly_chart(
        iv_plots.efecto_resistencia_serie(
            _familia_rs(j_l, j0, s.R_p, s.n_idealidad, t_k, s.irradiancia_soles)),
        use_container_width=True)
    st.caption(
        "Todas las curvas terminan en el mismo punto del eje horizontal. En circuito "
        "abierto no circula corriente, y la caída sobre una resistencia en serie es "
        "proporcional a la corriente: sin corriente no hay caída, así que la resistencia "
        "serie no puede afectar al voltaje de circuito abierto."
    )

    st.divider()

    st.markdown("### La malla frontal de plata")
    st.write(
        "La malla hace dos cosas opuestas. Tapa luz, y con ella corriente, en proporción al número de "
        "dedos; y recoge la corriente que la celda genera, con una resistencia que baja al agregar "
        "dedos. El enunciado pide que se vea ese compromiso."
    )

    largo_dedo = C.LADO_CELDA / (2 * C.N_BARRAS_COLECTORAS)
    _, caida = caida_lateral(grid.separacion_cm, curva.j_mpp)
    st.write(
        f"Con {s.n_dedos} dedos de {s.ancho_dedo_um:.0f} µm sobre una oblea de "
        f"{_coma(C.LADO_CELDA, 1)} cm de lado, los dedos quedan a "
        f"{_coma(10 * grid.separacion_cm, 2)} mm uno de otro. Una carga recogida en el peor lugar, "
        f"justo a medio camino entre dos dedos, viaja {_coma(5 * grid.separacion_cm, 2)} mm de lado "
        f"por el emisor y después hasta {_coma(largo_dedo, 2)} cm por el dedo hasta la barra "
        f"colectora. En el punto de máxima potencia ese viaje le cuesta "
        f"{_coma(1e3 * caida.max(), 2)} mV en el emisor y "
        f"{_coma(1e3 * malla_plots._caida_dedo(largo_dedo, curva.j_mpp, grid.separacion_cm, grid.ancho_dedo_cm), 2)} "
        f"mV en el dedo, sobre un voltaje de trabajo de {_coma(curva.v_mpp, 3)} V. El promedio de esa "
        f"pérdida es lo que el modelo resume en la resistencia serie de la malla: "
        f"{_coma(grid.r_emisor, 3)} Ω·cm² del emisor y {_coma(grid.r_dedos, 3)} de los dedos."
    )

    referencia, puntos = _compromiso(
        j_l_desnuda, j0, s.R_s, s.R_p, s.n_idealidad, t_k,
        s.ancho_dedo_um * 1e-4, s.irradiancia_soles)
    actual = min(puntos, key=lambda p: abs(p.n_dedos - s.n_dedos))
    optima = mejor_malla(puntos)

    st.write(
        "**El compromiso que pide el enunciado.** Comparar un porcentaje de área tapada con una "
        "resistencia en ohm no dice cuál de las dos pesa más. Las dos se llevan a la misma unidad, "
        "puntos de eficiencia, resolviendo la curva completa: se parte de la celda sin malla y se le "
        "agrega primero la sombra, después la resistencia del emisor y al final la de los dedos. Cada "
        "pérdida es lo que baja la eficiencia en ese paso, así que las tres suman la distancia entre la "
        "celda sin malla y la celda real, y el número de dedos que menos pierde es el óptimo."
    )
    st.plotly_chart(malla_plots.perdidas_de_la_malla(referencia, puntos, s.n_dedos),
                    use_container_width=True)
    st.caption(
        f"Con {actual.n_dedos} dedos, la malla cuesta {_coma(actual.perdida_total, 3)} puntos de "
        f"eficiencia: {_coma(actual.perdida_sombra, 3)} por la luz que tapa, "
        f"{_coma(actual.perdida_emisor, 3)} por la resistencia del emisor y "
        f"{_coma(actual.perdida_dedos, 3)} por la de los dedos. El mínimo está en "
        f"{optima.n_dedos} dedos, que cuestan {_coma(optima.perdida_total, 3)} puntos y dejan la celda "
        f"en {_coma(100 * optima.eficiencia, 3)} %. A la izquierda del mínimo manda la resistencia, "
        f"porque la del emisor crece con el cuadrado de la separación; a la derecha manda la sombra, "
        f"que crece en línea recta con el número de dedos."
    )

    # ------------------------------------------------------------------ cómo se resuelve
    st.divider()
    st.markdown("### Cómo se resuelve la curva")
    st.markdown(
        "**De qué trata esta sección.** Las secciones anteriores muestran el resultado: la curva y los "
        "números que salen de ella. Ésta muestra el cálculo que la produce. La ecuación del enunciado "
        "tiene la corriente en los dos lados —aparece sola y también dentro de la exponencial, a través "
        "del voltaje que ve la juntura— así que no se puede despejar: hay que buscar, para cada voltaje, "
        "la corriente que la hace cierta."
    )
    st.markdown(
        "**Los tres pasos, para un voltaje.**\n\n"
        "1. **Se propone una corriente.** Con ella se calcula el voltaje que realmente ve la juntura: el "
        "de los terminales más lo que se pierde en la resistencia serie.\n"
        "2. **Se comprueba la cuenta.** Con ese voltaje interno se calcula cuánta corriente se lleva el "
        "diodo, cuánta se fuga por la resistencia paralela y cuánta queda para el circuito. Si la que "
        "queda no es la que se propuso, la propuesta estaba mal.\n"
        "3. **Se busca la que cierra.** La diferencia entre lo que queda y lo propuesto siempre baja al "
        "subir la corriente, así que cruza el cero una sola vez. El programa encierra ese cruce entre dos "
        "valores y lo afina hasta que la diferencia es menor que una parte en un billón."
    )

    vt_n = s.n_idealidad * voltaje_termico(t_k)
    fraccion = st.slider(
        "Voltaje del ensayo  [% del voltaje de circuito abierto]", 0.0, 100.0,
        value=round(100 * curva.v_mpp / curva.v_oc, 1), step=0.5, key="v_ensayo_iv",
        help="El punto de la curva que se dibuja en el circuito. Al 0 % la celda está en "
             "cortocircuito y al 100 %, en circuito abierto.")
    v_sel = float(curva.v_oc) * fraccion / 100.0
    j_sel = -resolver_corriente(v_sel, j0, j_l, rs_total, s.R_p, s.n_idealidad, t_k)
    v_juntura = v_sel + rs_total * j_sel
    j_diodo = j0 * (np.exp(np.clip(v_juntura / vt_n, -600, 600)) - 1.0)
    j_fuga = v_juntura / s.R_p

    st.markdown(circuito.diagrama_html(v_sel, j_sel, j_l, j_diodo, j_fuga, rs_total, v_juntura),
                unsafe_allow_html=True)
    reparto = (f"De los {_coma(1e3 * j_l, 2)} mA/cm² que genera la luz, a "
               f"{_coma(v_sel, 3)} V el diodo se lleva {_coma(1e3 * j_diodo, 2)} y la resistencia "
               f"paralela {_coma(1e3 * j_fuga, 3)}; quedan {_coma(1e3 * j_sel, 2)} para el circuito, "
               f"y la resistencia serie se come {_coma(1e3 * (v_juntura - v_sel), 1)} mV en el camino.")
    if fraccion <= 0.5:
        reparto += (" En cortocircuito el diodo casi no conduce, así que sale casi toda la corriente "
                    "generada: por eso la corriente de cortocircuito mide la parte óptica de la celda.")
    elif fraccion >= 99.5:
        reparto += (" En circuito abierto no sale corriente: el diodo y la fuga se llevan todo lo que "
                    "genera la luz, y como no circula nada, la resistencia serie no consume nada. Por eso "
                    "no puede afectar al voltaje de circuito abierto.")
    else:
        reparto += (f" En el punto de máxima potencia, {_coma(curva.v_mpp, 3)} V, la celda entrega "
                    f"{_coma(1e3 * curva.j_mpp, 2)} mA/cm².")
    st.caption(reparto)

    st.plotly_chart(FiguraAnimada.desde_diccionario(_figura_construccion(
        curva, (round(j_l, 12), round(j0, 18), round(rs_total, 9), s.R_p, s.n_idealidad,
                round(t_k, 6)), j0, j_l, rs_total, s.R_p, vt_n)), use_container_width=True)
    st.caption(
        "A la izquierda, para el voltaje del cuadro, la función que el programa anula: cruza el cero en "
        "la corriente que la celda entrega a ese voltaje. La cruz gris es lo que daría la forma explícita, "
        "la que ignora la caída en la resistencia serie; a voltaje bajo coincide con la raíz, y cerca del "
        "punto de máxima potencia se separa. A la derecha, la curva armada con las raíces ya encontradas, "
        "y punteada la que daría el atajo: se ve correcta, pero está por encima de la verdadera donde más "
        "importa."
    )

    st.caption(
        "Los defectos localizados y su propagación a esta curva están en la Pestaña 4."
    )
