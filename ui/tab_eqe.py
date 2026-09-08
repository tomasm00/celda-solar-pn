"""Pestaña 2 - Ensayo de eficiencia cuántica por sectores."""

import numpy as np
import streamlit as st

import config
from physics.collection import probabilidad_coleccion, transporte as armar_transporte
from physics.material import juntura as resolver_juntura
from physics.optics import campo_optico
from physics.quantum_efficiency import (
    cota_superior,
    coleccion_de_celda,
    iqe_referida_a_absorcion,
    corriente_de_cortocircuito,
    curvas_por_tiempo_de_vida,
    eficiencia_cuantica,
    generar_sectores,
    mapa_iqe_desde_locales,
)
from units import celsius_a_kelvin, cm_a_um, um_a_cm
from visualization import qe_plots

NODOS_EN_DEPLEXION = 12
TAUS_COMPARACION_US = (1.0, 10.0, 100.0, 1000.0)


@st.cache_data(show_spinner=False, max_entries=6)
def _resolver(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia,
              mu_p, tau_p_us, mu_n, tau_n_us, s_f, s_r, dispersion):
    """
    Resuelve LA celda, que es una sola.

    La respuesta de la celda no es la de un dispositivo nominal homogeneo por un
    lado y sesenta y cuatro dispositivos sueltos por otro. Es una sola curva: la
    que sale de la coleccion promediada por area sobre sus sectores. Con
    dispersion cero todos los sectores son identicos y esto se reduce
    exactamente al caso homogeneo.
    """
    d_n, W_p = um_a_cm(d_n_um), um_a_cm(W_p_um)
    t_k = celsius_a_kelvin(t_c)
    W = d_n + W_p
    union = resolver_juntura(d_n, na, nd, t_k)
    campo = campo_optico(d_n, W_p, reflector, irradiancia,
                         np.linspace(union.x_n, union.x_p, NODOS_EN_DEPLEXION))
    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    sectores = generar_sectores(config.N_SECTORES, tau_n_us * 1e-6, s_f, dispersion)
    fc_celda, fc_locales = coleccion_de_celda(campo, union, W, tr, sectores)
    eqe, iqe = eficiencia_cuantica(campo, fc_celda)
    return campo, union, tr, W, eqe, iqe, sectores, fc_locales


@st.cache_data(show_spinner=False, max_entries=12)
def _familia_curvas(_campo, _union, W, _tr, huella, taus_us):
    return curvas_por_tiempo_de_vida(_campo, _union, W, _tr,
                                     [t * 1e-6 for t in taus_us])


def render():
    s = st.session_state
    st.subheader("Ensayo de eficiencia cuántica por sectores")
    st.write(
        "De cada cien fotones de un color que llegan a la celda, cuántos terminan "
        "produciendo corriente. Es donde la óptica y la electricidad se encuentran: "
        "combina dónde nacen los pares con cuántos sobreviven hasta la juntura."
    )

    campo, union, tr, W, eqe, iqe, sectores, fc_locales = _resolver(
        s.d_n_um, s.W_p_um, s.NA, s.ND, s.T_c, s.reflector_trasero,
        s.irradiancia_soles, s.mu_p, s.tau_p_us, s.mu_n, s.tau_n_us, s.S_f, s.S_r,
        s.dispersion_sectores)

    huella = (s.d_n_um, s.W_p_um, s.NA, s.ND, s.T_c, s.reflector_trasero,
              s.irradiancia_soles, s.mu_p, s.tau_p_us, s.mu_n, s.S_r)

    cota = cota_superior(campo)
    jsc = corriente_de_cortocircuito(campo, eqe)
    util = (campo.lambda_nm >= 400) & (campo.lambda_nm <= 1000)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Corriente de cortocircuito", f"{1e3 * jsc:.2f} mA/cm²",
              help="q·∫Nph(λ)·EQE(λ)dλ — la vía óptica de la verificación V3.")
    c2.metric("EQE media (400–1000 nm)", f"{100 * eqe[util].mean():.1f} %")
    c3.metric("IQE media (400–1000 nm)", f"{100 * iqe[util].mean():.1f} %")
    c4.metric("IQE máxima", f"{100 * iqe.max():.1f} %",
              help=f"a {campo.lambda_nm[int(np.argmax(iqe))]:.0f} nm")

    i_azul = int(np.argmin(np.abs(campo.lambda_nm - 450)))
    i_rojo = int(np.argmin(np.abs(campo.lambda_nm - 900)))
    st.caption(
        f"Respuesta en el azul (450 nm) **{100 * iqe[i_azul]:.1f} %** frente al rojo "
        f"(900 nm) **{100 * iqe[i_rojo]:.1f} %**. La diferencia es el retrato de esta "
        f"celda: superficie frontal con S_f = {s.S_f:.0e} cm/s castigando el azul, y un "
        f"volumen sano con longitud de difusión de {cm_a_um(tr.L_n):.0f} µm sobre una "
        f"base de {s.W_p_um:.0f} µm."
    )

    st.divider()

    g1, g2 = st.columns(2, gap="large")
    with g1:
        st.plotly_chart(
            qe_plots.curvas_eficiencia(campo.lambda_nm, eqe, iqe, cota, s.lambda_nm,
                                       iqe_referida_a_absorcion(campo, eqe, W)),
            use_container_width=True)
        st.caption(
            "La cota punteada ya tiene descontada la reflexión: **la distancia entre "
            "ella y la curva externa no es reflexión**, sino la suma de la luz que "
            "atraviesa la celda sin absorberse más los pares que se recombinan. Por eso "
            "se dibuja también la eficiencia por fotón *absorbido*, que sí aísla la "
            "calidad de colección: en el infrarrojo las dos se separan muchísimo, y esa "
            "separación es absorción incompleta, no recombinación."
        )
    with g2:
        curvas = _familia_curvas(campo, union, W, tr, huella, TAUS_COMPARACION_US)
        st.plotly_chart(
            qe_plots.curvas_por_tiempo_de_vida(campo.lambda_nm, curvas, s.d_n_um),
            use_container_width=True)
        var_azul = max(c[i_azul] for c in curvas.values()) - min(c[i_azul] for c in curvas.values())
        var_rojo = max(c[i_rojo] for c in curvas.values()) - min(c[i_rojo] for c in curvas.values())
        st.caption(
            f"Multiplicando el tiempo de vida por mil, la respuesta en el azul cambia "
            f"{100 * var_azul:.2f} puntos y la del rojo {100 * var_rojo:.1f} puntos. "
            f"Ésa es la razón por la que la curva de eficiencia cuántica sirve para "
            f"diagnosticar: cada zona del espectro informa sobre una parte distinta."
        )

    st.divider()

    st.markdown("#### Una celda con respuesta que varía de un punto a otro")
    st.write(
        "Una oblea real no es homogénea: el tiempo de vida y la pasivación varían de un "
        "punto a otro por el proceso de fabricación. **Eso no la convierte en muchas "
        "celdas separadas.** Sigue siendo un solo dispositivo, con una sola curva de "
        "eficiencia cuántica, que es la que aparece arriba."
    )

    lam_mapa = st.slider(
        "Color con el que se mide el mapa  [nm]",
        *config.RANGOS["lambda_nm"], value=float(s.lambda_nm), step=10.0,
        help="En el azul el mapa retrata la superficie frontal; en el rojo, el "
             "volumen de la base.",
    )
    st.caption(
        f"La dispersión entre sectores se controla en la barra lateral y vale "
        f"**{s.dispersion_sectores:.2f}**. Es un único control para toda la aplicación: "
        f"la Pestaña 4 describe esta misma celda."
    )

    i_mapa = int(np.argmin(np.abs(campo.lambda_nm - lam_mapa)))
    mapa = mapa_iqe_desde_locales(campo, fc_locales, i_mapa)

    # La eficiencia de la celda a este color tiene que ser el promedio por area del
    # mapa. No es una coincidencia ni una aproximacion: la eficiencia cuantica es
    # lineal en la probabilidad de coleccion, asi que promediar las respuestas
    # locales y calcular una sola respuesta con la coleccion promedio dan lo mismo.
    iqe_celda_aqui = float(iqe[i_mapa])
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("IQE local mínima", f"{100 * mapa.min():.1f} %")
    m2.metric("IQE local máxima", f"{100 * mapa.max():.1f} %")
    m3.metric("Promedio del mapa", f"{100 * mapa.mean():.2f} %")
    m4.metric("IQE de la celda", f"{100 * iqe_celda_aqui:.2f} %",
              delta=f"{100 * (mapa.mean() - iqe_celda_aqui):+.4f} pp",
              delta_color="off",
              help="Tiene que coincidir con el promedio del mapa. Es la verificación "
                   "C-T7, y se cumple de forma exacta porque la eficiencia cuántica es "
                   "lineal en la probabilidad de colección.")

    v1, v2 = st.columns(2, gap="large")
    with v1:
        st.plotly_chart(qe_plots.relieve_sectores(mapa, campo.lambda_nm[i_mapa]),
                        use_container_width=True)
    with v2:
        st.plotly_chart(
            qe_plots.barrido_lbic(mapa, campo.lambda_nm[i_mapa],
                                  sectores.tau_n_s * 1e6, sectores.s_f),
            use_container_width=True)

    st.caption(
        "El barrido imita un mapeo por haz de luz inducido: la sonda recorre la celda "
        "sector por sector y va revelando el mapa a medida que mide, igual que el "
        "instrumento real. Lo que mide un mapeo así es precisamente **la respuesta local "
        "de un mismo dispositivo**, no la de dispositivos distintos: al promediarlo sobre "
        "el área se recupera exactamente la curva de la celda."
    )

    st.plotly_chart(qe_plots.histograma_sectores(mapa, campo.lambda_nm[i_mapa]),
                    use_container_width=True)

    st.caption(
        "La corriente que esta pestaña calcula por la vía óptica se compara contra la "
        "leída de la curva eléctrica de la Pestaña 3: es la verificación V3, el criterio "
        "más importante del problema."
    )
