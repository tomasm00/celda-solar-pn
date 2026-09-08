"""Pestaña 4 - Mapa de la celda por sectores y defectos localizados."""

import numpy as np
import pandas as pd
import streamlit as st

import config
import constants as C
from physics.collection import transporte as armar_transporte
from physics.material import juntura as resolver_juntura
from physics.optics import campo_optico
from physics.quantum_efficiency import generar_sectores
from physics.sectors import (
    Defectos,
    armar_celda,
    curva_global,
    parametros_de_curva,
)
from units import celsius_a_kelvin, um_a_cm
from visualization import defect_plots

NODOS_EN_DEPLEXION = 12


@st.cache_data(show_spinner=False, max_entries=6)
def _base_fisica(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia,
                 mu_p, tau_p_us, mu_n, tau_n_us, s_f, s_r):
    d_n, W_p = um_a_cm(d_n_um), um_a_cm(W_p_um)
    t_k = celsius_a_kelvin(t_c)
    union = resolver_juntura(d_n, na, nd, t_k)
    campo = campo_optico(d_n, W_p, reflector, irradiancia,
                         np.linspace(max(union.x_n, 0.0), union.x_p, NODOS_EN_DEPLEXION))
    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    return campo, union, tr, t_k, d_n + W_p


@st.cache_data(show_spinner=False, max_entries=16)
def _resolver(_campo, _union, W, _tr, huella, t_k, na, nd, tau_n_us, s_f, dispersion,
              defectos, n_dedos, ancho_dedo_um, rs_base, rp, n_idealidad,
              irradiancia):
    """
    `huella` reune los parametros fisicos que solo entran por objetos con guion
    bajo. Streamlit excluye esos del hash de cache, asi que sin ella un cambio de
    tau_p, S_r, temperatura o reflector devolveria un resultado viejo (ver D-22).
    """
    sectores = generar_sectores(config.N_SECTORES, tau_n_us * 1e-6, s_f, dispersion)
    celda = armar_celda(_campo, _union, W, _tr, sectores, defectos,
                        n_dedos, ancho_dedo_um * 1e-4, rs_base, na, nd, t_k)
    v, j, v_oc = curva_global(celda, rp, n_idealidad, t_k)
    p = parametros_de_curva(v, j, C.IRRADIANCE_1SUN * irradiancia, v_oc)
    return celda, v, j, p


def _controles_defectos():
    st.markdown("#### Introducir defectos")
    izq, der = st.columns(2, gap="large")

    with izq:
        contaminacion = st.toggle(
            "Región de bajo tiempo de vida", value=True,
            help="Contaminación metálica: acorta la longitud de difusión y hunde "
                 "la colección de esos sectores.")
        f0, f1 = st.select_slider(
            "Filas afectadas", options=list(range(config.N_SECTORES)),
            value=(2, 4), disabled=not contaminacion)
        c0, c1 = st.select_slider(
            "Columnas afectadas", options=list(range(config.N_SECTORES)),
            value=(2, 4), disabled=not contaminacion)
        severidad = st.select_slider(
            "El tiempo de vida local se multiplica por",
            options=[1.0, 0.3, 0.1, 0.03, 0.01, 0.003, 0.001],
            value=0.001, format_func=lambda x: f"{x:g}",
            disabled=not contaminacion)

    with der:
        dedo_roto = st.toggle(
            "Dedos de plata interrumpidos", value=True,
            help="El metal sigue tapando la luz pero deja de conducir: la corriente "
                 "tiene que alcanzar el siguiente dedo intacto.")
        columna = st.select_slider(
            "Columna de sectores que se queda sin dedo",
            options=list(range(config.N_SECTORES)), value=6,
            disabled=not dedo_roto)
        st.caption(
            "Se interrumpen los dedos que sirven a esa columna. Con 60 dedos sobre "
            "8 columnas son unos 7 u 8 dedos consecutivos, así que la corriente del "
            "centro de la franja debe recorrer varias separaciones hasta el primer "
            "dedo sano."
        )

    return Defectos(
        contaminacion_activa=contaminacion, fila_0=f0, fila_1=f1,
        columna_0=c0, columna_1=c1, factor_tau=severidad,
        dedo_roto_activo=dedo_roto, columna_dedo=columna,
    )


def render():
    s = st.session_state
    st.subheader("Mapa de la celda por sectores")
    st.write(
        "Una celda real no es homogénea, y eso es lo que revelan la "
        "electroluminiscencia y la termografía. Aquí se introducen defectos "
        "localizados y se observa su efecto tanto en el mapa como en la curva global."
    )

    campo, union, tr, t_k, W = _base_fisica(
        s.d_n_um, s.W_p_um, s.NA, s.ND, s.T_c, s.reflector_trasero,
        s.irradiancia_soles, s.mu_p, s.tau_p_us, s.mu_n, s.tau_n_us, s.S_f, s.S_r)

    # La dispersion es un unico control compartido, en la barra lateral: esta
    # pestaña y la Pestaña 2 tienen que describir la misma celda (ver D-28).
    dispersion = s.dispersion_sectores
    if dispersion > 0:
        st.caption(
            f"Dispersión entre sectores **{dispersion:.2f}**, fijada en la barra "
            f"lateral. Es la misma celda que retrata el mapa de la Pestaña 2.")
    else:
        st.caption(
            "Celda homogénea. Súbase la dispersión en la barra lateral para añadir "
            "variación de fabricación sobre la que actúan los defectos.")

    defectos = _controles_defectos()

    huella = (s.T_c, s.reflector_trasero, s.irradiancia_soles, s.mu_p, s.tau_p_us,
              s.mu_n, s.S_r, s.d_n_um, s.W_p_um)
    celda_sana, v0, j0_curva, p_sana = _resolver(
        campo, union, W, tr, huella, t_k, s.NA, s.ND, s.tau_n_us, s.S_f, dispersion,
        Defectos(), s.n_dedos, s.ancho_dedo_um, s.R_s, s.R_p, s.n_idealidad,
        s.irradiancia_soles)
    celda, v, j, p = _resolver(
        campo, union, W, tr, huella, t_k, s.NA, s.ND, s.tau_n_us, s.S_f, dispersion,
        defectos, s.n_dedos, s.ancho_dedo_um, s.R_s, s.R_p, s.n_idealidad,
        s.irradiancia_soles)

    st.divider()

    def delta(clave, factor=1.0, unidad=""):
        d = factor * (p[clave] - p_sana[clave])
        return f"{d:+.3f}{unidad}" if abs(d) > 5e-4 else "sin cambio"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Corriente de cortocircuito", f"{1e3 * p['j_sc']:.3f} mA/cm²",
              delta=delta("j_sc", 1e3), delta_color="normal")
    c2.metric("Voltaje de circuito abierto", f"{p['v_oc']:.4f} V",
              delta=delta("v_oc"), delta_color="normal")
    c3.metric("Factor de forma", f"{p['ff']:.4f}", delta=delta("ff"),
              delta_color="normal")
    c4.metric("Eficiencia", f"{100 * p['eficiencia']:.3f} %",
              delta=delta("eficiencia", 100, " pts"), delta_color="normal")

    area_col = float(celda.con_contaminacion.mean())
    area_res = float(celda.con_dedo_roto.mean())
    st.caption(
        f"Área con contaminación **{100 * area_col:.2f} %**  ·  área sin dedo "
        f"**{100 * area_res:.2f} %**  ·  resistencia serie local: "
        f"{celda.r_s.min():.3f} Ω·cm² en los sectores sanos y "
        f"**{celda.r_s.max():.3f} Ω·cm²** en los que perdieron su dedo"
    )

    m1, m2 = st.columns(2, gap="large")
    with m1:
        st.plotly_chart(
            defect_plots.mapa_fotocorriente_local(
                celda.j_l, celda.con_contaminacion, celda.con_dedo_roto,
                referencia=celda_sana.j_l),
            use_container_width=True)
        st.caption(
            "Este mapa dibuja **fotocorriente local**, no electroluminiscencia. La "
            "contaminación se ve porque colecta menos. Los sectores sin dedo no se ven "
            "aquí, pero eso es una consecuencia de lo que el mapa grafica, **no una "
            "predicción de lo que vería un instrumento**: la electroluminiscencia real "
            "sí detecta defectos de resistencia serie, y es una técnica estándar para eso."
        )
    with m2:
        st.plotly_chart(defect_plots.mapa_resistencia(celda.r_s),
                        use_container_width=True)
        st.caption(
            "Y aquí ocurre lo contrario: la columna sin dedo salta a la vista, mientras "
            "que la región contaminada es invisible. Cada defecto se ve en su propio mapa."
        )

    st.divider()

    st.plotly_chart(
        defect_plots.comparacion_curvas(v0, j0_curva, v, j, p_sana, p),
        use_container_width=True)

    st.markdown("#### Por qué los dos defectos dañan de maneras distintas")
    st.write(
        "Ésta es la pregunta que el enunciado pide explicar, y el modelo la responde "
        "solo, sin que la hayamos programado a mano: los 64 sectores están en paralelo "
        "compartiendo el mismo voltaje de terminal, y de esa única condición sale toda "
        "la asimetría."
    )

    izq, der = st.columns(2, gap="large")
    with izq:
        st.markdown(
            "**El defecto de colección se lleva la corriente.** Los sectores "
            "contaminados generan los mismos pares que antes, pero con la longitud de "
            "difusión acortada la mayoría se recombina antes de alcanzar la juntura. "
            "Entregan menos corriente **en todo el barrido**, incluido el "
            "cortocircuito, así que la curva entera baja."
        )
    with der:
        st.markdown(
            "**El defecto de resistencia se lleva el factor de forma.** Los sectores "
            "sin dedo generan y colectan exactamente lo mismo. Cerca de cortocircuito "
            "el voltaje sobre su resistencia es pequeño y entregan casi toda su "
            "corriente. Pero al acercarse al punto de máxima potencia se ahogan, y lo "
            "que se hunde es la esquina de la curva."
        )

    # Cada defecto por separado, para poder atribuir el daño sin ambiguedad.
    def _solo(defecto_aislado):
        _, _, _, pp = _resolver(
            campo, union, W, tr, huella, t_k, s.NA, s.ND, s.tau_n_us, s.S_f,
            dispersion, defecto_aislado, s.n_dedos, s.ancho_dedo_um, s.R_s,
            s.R_p, s.n_idealidad, s.irradiancia_soles)
        return pp

    p_col = _solo(Defectos(
        contaminacion_activa=defectos.contaminacion_activa,
        fila_0=defectos.fila_0, fila_1=defectos.fila_1,
        columna_0=defectos.columna_0, columna_1=defectos.columna_1,
        factor_tau=defectos.factor_tau))
    p_res = _solo(Defectos(dedo_roto_activo=defectos.dedo_roto_activo,
                           columna_dedo=defectos.columna_dedo))

    def caida(pp, clave):
        if p_sana[clave] == 0:
            return 0.0
        return 100.0 * (p_sana[clave] - pp[clave]) / p_sana[clave]

    filas = ["Área dañada", "Caída de Jsc", "Caída del factor de forma",
             "Caída de eficiencia"]
    valores_col = [100 * area_col, caida(p_col, "j_sc"), caida(p_col, "ff"),
                   caida(p_col, "eficiencia")]
    valores_res = [100 * area_res, caida(p_res, "j_sc"), caida(p_res, "ff"),
                   caida(p_res, "eficiencia")]

    st.dataframe(
        pd.DataFrame({
            "": filas,
            "Solo contaminación": [f"{x:.2f} %" for x in valores_col],
            "Solo dedos rotos": [f"{x:.2f} %" for x in valores_res],
        }),
        hide_index=True, use_container_width=True)

    st.plotly_chart(
        defect_plots.asimetria_de_los_defectos(
            {"coleccion": valores_col, "resistencia": valores_res}),
        use_container_width=True)

    if area_col > 0 and area_res > 0:
        razon_j = valores_col[1] / max(valores_res[1], 1e-6)
        razon_ff = valores_res[2] / max(valores_col[2], 1e-6)
        st.success(
            f"Con áreas dañadas comparables, la contaminación hunde la corriente "
            f"**{razon_j:.0f} veces más** que los dedos rotos, y los dedos rotos hunden "
            f"el factor de forma **{razon_ff:.0f} veces más** que la contaminación. "
            f"Dos defectos de tamaño parecido, daños de naturaleza opuesta."
        )

    st.info(
        "Para ver la asimetría con toda claridad, activa un defecto a la vez con la "
        "dispersión de fabricación en cero. Con la contaminación sola verás la corriente "
        "caer y el factor de forma casi intacto; con los dedos rotos solos, exactamente "
        "lo contrario.",
        icon="🔬",
    )

    st.caption(
        "Límites declarados. **No se modela el acoplamiento lateral** entre sectores "
        "vecinos, ni ningún balance térmico: este modelo no calcula temperatura, así que "
        "no predice puntos calientes. Sí reproduce que un sector de poca fotocorriente "
        "**consuma** corriente cuando el conjunto opera por encima de su circuito abierto "
        "local, que es disipación en directa y no requiere polarización inversa. El caso "
        "de inversión por sombreado es propio de celdas en **serie**, un problema distinto "
        "que este modelo tampoco resuelve."
    )
