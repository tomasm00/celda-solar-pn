"""
Barra lateral: semilla visible y controles compartidos entre pestañas.

El enunciado exige que la semilla y los parámetros asignados sean visibles, y que
lo que el usuario modifica en una pestaña se refleje en las demás. Por eso los
controles compartidos viven aquí y escriben directamente en st.session_state.

Notación: se usa la de portador minoritario n/p, que es la que el enunciado
declara para todo el problema. La equivalencia con la notación e/h de la
Unidad 3 se muestra al pie de la barra.
"""

import numpy as np
import streamlit as st

import config
from physics.material import bandgap
from units import celsius_a_kelvin


def _opciones_log(vmin, vmax, incluir=()):
    """
    Valores log-espaciados para un deslizador discreto.

    Incluye explícitamente los valores que deben poder seleccionarse (los de la
    semilla). Si el valor asignado no estuviera en la lista, Streamlit caería
    silenciosamente al primer elemento y el estado inicial dejaría de ser el
    asignado, incumpliendo la sección 1.1 del enunciado.
    """
    mantisas = (1.0, 1.5, 2.0, 3.0, 5.0, 7.0)
    valores = [
        m * 10.0 ** e
        for e in range(int(np.floor(np.log10(vmin))), int(np.ceil(np.log10(vmax))) + 1)
        for m in mantisas
        if vmin <= m * 10.0 ** e <= vmax
    ]
    valores.extend(v for v in incluir if vmin <= v <= vmax)
    return sorted(set(valores))


def _restaurar_semilla():
    for clave, valor in config.ESTADO_INICIAL.items():
        st.session_state[clave] = valor


def _tabla_semilla():
    p = config.PARAMETROS_SEMILLA
    st.markdown(
        f"""
        | Parámetro asignado | Valor |
        |---|---|
        | Concentración de aceptores, N<sub>A</sub> | {p['NA']:.1e} cm⁻³ |
        | Concentración de donantes, N<sub>D</sub> | {p['ND']:.1e} cm⁻³ |
        | Tiempo de vida SRH en volumen, τ<sub>n</sub> | {p['tau_srh_us']:.0f} µs |
        | Velocidad de recomb. superficial frontal, S<sub>f</sub> | {p['s_frontal']:.0e} cm/s |
        | Temperatura de operación | {p['t_operacion_c']:.0f} °C |
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "El espesor de la Tabla A.1 no se usa en este problema: el enunciado fija "
        "la geometría de la celda y deja el espesor como control del usuario."
    )


def render():
    with st.sidebar:
        st.subheader(f"Semilla S = {config.SEMILLA_S}")
        _tabla_semilla()

        st.divider()

        with st.expander("Geometría de la celda", expanded=True):
            st.slider(
                "Espesor del emisor tipo n, dₙ [µm]",
                *config.RANGOS["d_n_um"], key="d_n_um", step=0.1,
                help="Posición de la juntura p-n medida desde la superficie iluminada.",
            )
            st.slider(
                "Espesor de la base tipo p, W_p [µm]",
                *config.RANGOS["W_p_um"], key="W_p_um", step=5.0,
                help="El enunciado deja este espesor libre entre 20 y 300 µm.",
            )

        with st.expander("Dopaje del material", expanded=True):
            st.number_input(
                "Concentración de aceptores en la base, N_A [cm⁻³]",
                key="NA", format="%.2e", step=1e15, min_value=1e14, max_value=1e18,
                help="Dopante tipo p. Determina la concentración de huecos mayoritarios.",
            )
            st.number_input(
                "Concentración de donantes en el emisor, N_D [cm⁻³]",
                key="ND", format="%.2e", step=1e19, min_value=1e18, max_value=1e21,
                help="Dopante tipo n. Con este valor el emisor queda degenerado.",
            )

        with st.expander("Recombinación", expanded=True):
            st.slider(
                "Tiempo de vida del minoritario en la base, τₙ [µs]",
                *config.RANGOS["tau_n_us"], key="tau_n_us",
                help="Electrones en la base tipo p. Domina la colección en el rojo.",
            )
            st.slider(
                "Tiempo de vida del minoritario en el emisor, τ_p [µs]",
                *config.RANGOS["tau_p_us"], key="tau_p_us",
                help="Huecos en el emisor tipo n.",
            )
            opciones_s = _opciones_log(
                *config.RANGOS["S_f"],
                incluir=(config.ESTADO_INICIAL["S_f"], config.ESTADO_INICIAL["S_r"]),
            )
            st.select_slider(
                "Velocidad de recombinación superficial frontal, S_f [cm/s]",
                options=opciones_s, key="S_f", format_func=lambda v: f"{v:.1e}",
                help="Superficie expuesta entre los dedos de plata. Domina la colección en el azul.",
            )
            st.select_slider(
                "Velocidad de recombinación superficial trasera, S_r [cm/s]",
                options=opciones_s, key="S_r", format_func=lambda v: f"{v:.1e}",
                help="Bajo el contacto de aluminio. Junto con W_p y Lₙ domina la colección en el rojo.",
            )

        with st.expander("Óptica", expanded=True):
            st.slider(
                "Longitud de onda, λ [nm]",
                *config.RANGOS["lambda_nm"], key="lambda_nm", step=5.0,
                help="Color con el que se dibujan los perfiles de la Pestaña 1.",
            )
            st.toggle(
                "Reflector trasero de aluminio",
                key="reflector_trasero",
                help=(
                    "Apagado: la eficiencia cuántica es la fórmula de un solo paso del "
                    "enunciado, y ahí corren las validaciones. Encendido: se suma el "
                    "segundo paso de la luz que rebota en el fondo."
                ),
            )

        with st.expander("Condiciones de operación", expanded=True):
            st.slider(
                "Temperatura de operación [°C]",
                *config.RANGOS["T_c"], key="T_c", step=1.0,
                help=(
                    "El enunciado fija 15-75 °C para la Pestaña 3 y para la verificación "
                    "V6. El rango se extiende hacia abajo para explorar clima frío; V6 "
                    "sigue barriendo 15-75 °C."
                ),
            )
            st.slider(
                "Irradiancia [soles]",
                *config.RANGOS["irradiancia_soles"], key="irradiancia_soles", step=0.05,
                help="1 sol = 100 mW/cm² bajo AM1.5G (condición estándar de medición).",
            )

        with st.expander("Circuito eléctrico"):
            st.slider(
                "Resistencia serie, R_s [Ω·cm²]",
                *config.RANGOS["R_s"], key="R_s", step=0.05,
                help="No afecta al voltaje de circuito abierto, porque ahí no circula corriente.",
            )
            st.slider(
                "Resistencia paralelo, R_p [Ω·cm²]",
                *config.RANGOS["R_p"], key="R_p", step=10.0,
                help="Caminos de fuga. Afecta sobre todo al voltaje y al factor de forma; "
                     "a la corriente de cortocircuito casi no, salvo con valores muy bajos "
                     "(con 10 Ω·cm² la baja un 9 %).",
            )
            st.slider(
                "Factor de idealidad del diodo, n",
                *config.RANGOS["n_idealidad"], key="n_idealidad", step=0.05,
            )

        with st.expander("Malla frontal de plata"):
            st.slider(
                "Número de dedos", *config.RANGOS["n_dedos"], key="n_dedos", step=1,
                help="Más dedos reducen la resistencia serie pero aumentan el sombreado.",
            )
            st.slider(
                "Ancho de cada dedo [µm]",
                *config.RANGOS["ancho_dedo_um"], key="ancho_dedo_um", step=5.0,
            )

        with st.expander("Parámetros del material (Anexo B)"):
            st.caption(
                "Valores fijados por el Anexo B del enunciado. Se exponen para poder "
                "explorar su efecto, pero la decisión D-09 es usarlos sin modelo de "
                "dependencia con el dopaje."
            )
            st.slider(
                "Movilidad de electrones en la base, µₙ [cm²/V·s]",
                *config.RANGOS["mu_n"], key="mu_n", step=10.0,
            )
            st.slider(
                "Movilidad de huecos en el emisor, µ_p [cm²/V·s]",
                *config.RANGOS["mu_p"], key="mu_p", step=5.0,
            )
            st.caption(
                f"Banda prohibida **{bandgap(celsius_a_kelvin(st.session_state.T_c)):.4f} eV** "
                f"a la temperatura actual. No es un control: cambiarla exigiría datos "
                f"ópticos de otro material, y los de Green son de silicio."
            )

        st.divider()
        with st.expander("Equivalencia de notación"):
            st.markdown(
                "El enunciado usa notación de **portador minoritario n/p** en todo el "
                "problema. La Unidad 3 usa notación de partícula e/h. Equivalen así:\n\n"
                "- Dₙ, Lₙ, τₙ (electrones en la base tipo p) ≡ D_e, L_e, τ_e\n"
                "- D_p, L_p, τ_p (huecos en el emisor tipo n) ≡ D_h, L_h, τ_h\n"
                "- S_f ≡ S_frontal · S_r ≡ S_trasera"
            )

        # El reinicio debe ir en un callback: Streamlit prohibe escribir en
        # session_state una clave ya ligada a un widget instanciado en este mismo
        # ciclo, y los callbacks corren antes del redibujado.
        st.button("Restaurar valores de la semilla", on_click=_restaurar_semilla,
                  use_container_width=True)
