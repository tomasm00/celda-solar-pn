"""Pestaña 3 - Ensayo de curva I-V."""

import numpy as np
import streamlit as st

import constants as C
from physics.collection import probabilidad_coleccion, transporte as armar_transporte
from physics.diode import corriente_saturacion, curva_iv, factor_de_forma_ideal
from physics.front_grid import barrido_numero_de_dedos, malla
from physics.material import bandgap, juntura as resolver_juntura
from physics.optics import campo_optico
from physics.quantum_efficiency import corriente_de_cortocircuito, eficiencia_cuantica
from units import celsius_a_kelvin, cm_a_um, um_a_cm
from visualization import iv_plots

NODOS_EN_DEPLEXION = 12


@st.cache_data(show_spinner=False, max_entries=6)
def _fotocorriente(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia,
                   mu_p, tau_p_us, mu_n, tau_n_us, s_f, s_r):
    """
    Corriente fotogenerada y corriente de saturación, desde la cadena completa.

    La fotocorriente no es un parámetro libre: sale de integrar la eficiencia
    cuántica sobre el espectro, que a su vez sale de la generación y la colección
    de las Pestañas 1 y 2. Es lo que la verificación V3 exige.
    """
    d_n, W_p = um_a_cm(d_n_um), um_a_cm(W_p_um)
    t_k = celsius_a_kelvin(t_c)
    union = resolver_juntura(d_n, na, nd, t_k)
    campo = campo_optico(d_n, W_p, reflector, irradiancia,
                         np.linspace(union.x_n, union.x_p, NODOS_EN_DEPLEXION))
    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    fc = probabilidad_coleccion(campo.x_cm, union, d_n + W_p, tr)
    eqe, _ = eficiencia_cuantica(campo, fc)
    j_l = corriente_de_cortocircuito(campo, eqe)
    j0, termino_base, termino_emisor = corriente_saturacion(na, nd, tr, t_k)
    return j_l, j0, termino_base, termino_emisor, tr, t_k


@st.cache_data(show_spinner=False, max_entries=32)
def _curva(j_l, j0, rs, rp, n_idealidad, t_k, irradiancia):
    return curva_iv(j0, j_l, rs, rp, n_idealidad, t_k,
                    irradiancia_w_cm2=C.IRRADIANCE_1SUN * irradiancia)


@st.cache_data(show_spinner=False, max_entries=12)
def _compromiso(j_l_sin_sombra, j0, rs_extra, rp, n_idealidad, t_k, ancho_dedo_cm,
                irradiancia):
    """Recorre el número de dedos resolviendo la curva completa en cada punto."""
    n_dedos, mallas = barrido_numero_de_dedos(10, 200, ancho_dedo_cm, paso=8)
    sombras, resistencias, eficiencias = [], [], []
    for g in mallas:
        c = curva_iv(j0, j_l_sin_sombra * (1 - g.fraccion_sombra),
                     rs_extra + g.r_serie, rp, n_idealidad, t_k,
                     irradiancia_w_cm2=C.IRRADIANCE_1SUN * irradiancia,
                     n_puntos=140)
        sombras.append(g.fraccion_sombra)
        resistencias.append(rs_extra + g.r_serie)
        eficiencias.append(c.eficiencia)
    return n_dedos, sombras, resistencias, eficiencias


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
        "que entrega. De esa curva salen los cuatro números que resumen el desempeño "
        "de cualquier celda solar."
    )

    j_l_desnuda, j0, t_base, t_emisor, tr, t_k = _fotocorriente(
        s.d_n_um, s.W_p_um, s.NA, s.ND, s.T_c, s.reflector_trasero,
        s.irradiancia_soles, s.mu_p, s.tau_p_us, s.mu_n, s.tau_n_us, s.S_f, s.S_r)

    grid = malla(s.n_dedos, s.ancho_dedo_um * 1e-4)
    j_l = j_l_desnuda * (1.0 - grid.fraccion_sombra)
    rs_total = s.R_s + grid.r_serie

    curva = _curva(j_l, j0, rs_total, s.R_p, s.n_idealidad, t_k, s.irradiancia_soles)
    ideal = _curva(j_l, j0, 0.0, 1e12, 1.0, t_k, s.irradiancia_soles)
    ff0 = factor_de_forma_ideal(curva.v_oc, t_k)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Corriente de cortocircuito", f"{1e3 * curva.j_sc:.2f} mA/cm²")
    c2.metric("Voltaje de circuito abierto", f"{curva.v_oc:.4f} V")
    c3.metric("Factor de forma", f"{curva.ff:.4f}",
              delta=f"{curva.ff - ff0:+.4f} respecto del ideal {ff0:.3f}",
              delta_color="off")
    c4.metric("Eficiencia", f"{100 * curva.eficiencia:.2f} %",
              help="Potencia máxima dividida por la irradiancia incidente.")

    # Guarda fisica: el voltaje de circuito abierto no puede superar la banda
    # prohibida. Nuestro modelo trata el factor de idealidad y la corriente de
    # saturacion como parametros independientes, y no lo son: un factor de
    # idealidad alto nace de la recombinacion en la zona de deplexion, que trae
    # consigo una corriente de saturacion mucho mayor. Subir solo n produce una
    # mejora ficticia. Detectado en la prueba de esfuerzo E9.
    eg_v = float(bandgap(t_k))
    if curva.v_oc > eg_v:
        st.error(
            f"**Régimen no físico.** El voltaje de circuito abierto ({curva.v_oc:.4f} V) "
            f"supera la banda prohibida del silicio a esta temperatura ({eg_v:.4f} eV). "
            f"Ninguna celda puede hacer eso: la energía de cada par es a lo sumo E_g. "
            f"Ocurre porque el modelo trata el factor de idealidad y la corriente de "
            f"saturación como independientes, y no lo son — un factor de idealidad alto "
            f"nace de la recombinación en la zona de deplexión, que trae consigo una "
            f"corriente de saturación mucho mayor. Con n ≥ 1,95 los resultados de esta "
            f"pestaña dejan de ser confiables.",
            icon="⚠",
        )

    st.caption(
        f"Corriente de saturación **{j0:.3e} A/cm²**, con el término de la base "
        f"dominando al del emisor en razón **{t_base / t_emisor:.0f} a 1** — por eso el "
        f"emisor degenerado no compromete el resultado (D-05)  ·  resistencia serie "
        f"total **{rs_total:.3f} Ω·cm²**, de los cuales {grid.r_serie:.3f} vienen de la "
        f"malla  ·  sombreado **{100 * grid.fraccion_sombra:.2f} %**  ·  punto de máxima "
        f"potencia en {curva.v_mpp:.3f} V"
    )

    st.divider()

    g1, g2 = st.columns(2, gap="large")
    with g1:
        st.plotly_chart(iv_plots.curva_iv(curva, ideal), use_container_width=True)
        st.caption(
            "El rectángulo naranja tiene por área la potencia máxima extraíble; el gris, "
            "el producto Voc×Jsc que sería el ideal. El factor de forma es exactamente el "
            "cociente entre ambas áreas."
        )
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
        st.metric("Factor de forma correcto", f"{curva.ff:.4f}",
                  help="Resolviendo la ecuación implícita punto por punto.")
        st.metric("Ignorando el término Rs·J", f"{ff_ingenuo:.4f}",
                  delta=f"{100 * (ff_ingenuo / curva.ff - 1):+.1f} % de sobrestimación",
                  delta_color="inverse")
    with t2:
        st.write(
            "La ecuación del diodo tiene la corriente en ambos lados: aparece en el "
            "voltaje que realmente ve la juntura, que es el aplicado menos lo que se "
            "consume en la resistencia serie. Si se ignora ese término y se grafica la "
            "forma explícita, la curva **se ve correcta a simple vista** pero el factor "
            "de forma queda sistemáticamente sobrestimado, porque no se está "
            "descontando la caída de voltaje. El enunciado advierte de este error de "
            "forma explícita, y la verificación V4 está diseñada para detectarlo."
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

    st.markdown("#### La malla frontal de plata")
    st.write(
        f"Con {s.n_dedos} dedos de {s.ancho_dedo_um:.0f} µm sobre una oblea de "
        f"{C.LADO_CELDA:.1f} cm de lado, la separación entre dedos es "
        f"{10 * grid.separacion_cm:.2f} mm. La resistencia del emisor aporta "
        f"{grid.r_emisor:.3f} Ω·cm² y la de los propios dedos {grid.r_dedos:.3f} Ω·cm²."
    )

    n_dedos, sombras, resistencias, eficiencias = _compromiso(
        j_l_desnuda, j0, s.R_s, s.R_p, s.n_idealidad, t_k,
        s.ancho_dedo_um * 1e-4, s.irradiancia_soles)
    st.plotly_chart(
        iv_plots.compromiso_malla(n_dedos, sombras, resistencias, eficiencias,
                                  s.n_dedos),
        use_container_width=True)
    st.caption(
        "Al agregar dedos, la resistencia del emisor cae como el inverso del cuadrado "
        "del número —la corriente recorre menos distancia lateral— y la de los dedos como "
        "su inverso, mientras el sombreado crece proporcionalmente. De ahí que exista un "
        "óptimo, marcado con la línea naranja."
    )

    st.info(
        "Los defectos localizados y su propagación a esta curva son el Hito 6: una región "
        "de bajo tiempo de vida y un dedo de plata interrumpido, para ver que dañan la "
        "celda de maneras físicamente distintas.",
        icon="🔧",
    )
