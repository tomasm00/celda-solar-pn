"""Pestaña 2 - Ensayo de eficiencia cuántica por sectores."""

import numpy as np
import streamlit as st

import config
from physics.collection import probabilidad_coleccion, transporte as armar_transporte
from physics.material import juntura as resolver_juntura
from physics.optics import campo_optico
from physics.quantum_efficiency import (
    cota_superior,
    iqe_referida_a_absorcion,
    corriente_de_cortocircuito,
    curvas_por_tiempo_de_vida,
    eficiencia_cuantica,
    generar_sectores,
    mapa_iqe_local,
)
from units import celsius_a_kelvin, cm_a_um, um_a_cm
from visualization import qe_plots

NODOS_EN_DEPLEXION = 12
TAUS_COMPARACION_US = (1.0, 10.0, 100.0, 1000.0)


@st.cache_data(show_spinner=False, max_entries=6)
def _resolver(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia,
              mu_p, tau_p_us, mu_n, tau_n_us, s_f, s_r):
    d_n, W_p = um_a_cm(d_n_um), um_a_cm(W_p_um)
    t_k = celsius_a_kelvin(t_c)
    W = d_n + W_p
    union = resolver_juntura(d_n, na, nd, t_k)
    campo = campo_optico(d_n, W_p, reflector, irradiancia,
                         np.linspace(union.x_n, union.x_p, NODOS_EN_DEPLEXION))
    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    fc = probabilidad_coleccion(campo.x_cm, union, W, tr)
    eqe, iqe = eficiencia_cuantica(campo, fc)
    return campo, union, tr, W, eqe, iqe


@st.cache_data(show_spinner=False, max_entries=24)
def _mapa(_campo, _union, W, _tr, huella, tau_n_us, s_f, dispersion,
          i_lambda, n_sectores):
    sectores = generar_sectores(n_sectores, tau_n_us * 1e-6, s_f, dispersion)
    return sectores, mapa_iqe_local(_campo, _union, W, _tr, sectores, i_lambda)


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

    campo, union, tr, W, eqe, iqe = _resolver(
        s.d_n_um, s.W_p_um, s.NA, s.ND, s.T_c, s.reflector_trasero,
        s.irradiancia_soles, s.mu_p, s.tau_p_us, s.mu_n, s.tau_n_us, s.S_f, s.S_r)

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

    st.markdown("#### La celda por sectores")
    st.write(
        "Una oblea real no es homogénea: el tiempo de vida y la pasivación varían de un "
        "punto a otro por el proceso de fabricación. Cada sector se resuelve con su "
        "propio tiempo de vida local y su propia recombinación superficial local."
    )

    ctrl1, ctrl2 = st.columns([2, 3])
    with ctrl1:
        dispersion = st.slider(
            "Dispersión de fabricación", 0.0, 0.6, 0.20, 0.05,
            help="Desviación logarítmica de la variación entre sectores. En cero, la "
                 "celda queda perfectamente homogénea.",
        )
    with ctrl2:
        lam_mapa = st.slider(
            "Color con el que se mide el mapa  [nm]",
            *config.RANGOS["lambda_nm"], value=float(s.lambda_nm), step=10.0,
            help="En el azul el mapa retrata la superficie frontal; en el rojo, el "
                 "volumen de la base.",
        )

    i_mapa = int(np.argmin(np.abs(campo.lambda_nm - lam_mapa)))
    sectores, mapa = _mapa(campo, union, W, tr, huella, s.tau_n_us, s.S_f,
                           dispersion, i_mapa, config.N_SECTORES)

    m1, m2, m3 = st.columns(3)
    m1.metric("IQE local mínima", f"{100 * mapa.min():.1f} %")
    m2.metric("IQE local media", f"{100 * mapa.mean():.1f} %")
    m3.metric("IQE local máxima", f"{100 * mapa.max():.1f} %")

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
        "instrumento real. Cada valor que aparece es el cálculo completo de ese sector, "
        "con su propio tiempo de vida y su propia pasivación."
    )

    st.plotly_chart(qe_plots.histograma_sectores(mapa, campo.lambda_nm[i_mapa]),
                    use_container_width=True)

    st.caption(
        "La corriente que esta pestaña calcula por la vía óptica se compara contra la "
        "leída de la curva eléctrica de la Pestaña 3: es la verificación V3, el criterio "
        "más importante del problema."
    )
