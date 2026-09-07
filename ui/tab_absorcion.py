"""Pestaña 1 - Absorción de fotones, generación y colección de pares."""

import numpy as np
import streamlit as st

import config
import constants as C
from physics.collection import (
    fraccion_colectada,
    probabilidad_coleccion,
    transporte as armar_transporte,
)
from physics.material import juntura as resolver_juntura
from physics.optics import (
    balance_fotones,
    campo_optico,
    fracciones_por_region,
    profundidad_absorcion_cm,
    profundidad_para_fraccion,
)
from units import celsius_a_kelvin, cm_a_um, um_a_cm
from visualization import cell3d, optics_plots

NODOS_EN_DEPLEXION = 12


@st.cache_data(show_spinner=False, max_entries=6)
def _resolver(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia,
              mu_p, tau_p_us, mu_n, tau_n_us, s_f, s_r):
    """
    Resuelve la cadena completa en el orden en que las piezas dependen entre sí.

    La juntura va primero porque sus bordes de deplexión entran como nodos
    forzados de la grilla; sin ellos la probabilidad de colección no alcanza el
    valor unitario que debe tener exactamente en el borde.
    """
    d_n, W_p = um_a_cm(d_n_um), um_a_cm(W_p_um)
    t_k = celsius_a_kelvin(t_c)
    W = d_n + W_p

    union = resolver_juntura(d_n, na, nd, t_k)
    nodos = np.linspace(union.x_n, union.x_p, NODOS_EN_DEPLEXION)
    campo = campo_optico(d_n, W_p, reflector, irradiancia, nodos)

    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    fc = probabilidad_coleccion(campo.x_cm, union, W, tr)

    return (campo, balance_fotones(campo), fracciones_por_region(campo),
            union, tr, fc, fraccion_colectada(campo.x_cm, campo.G, campo.lambda_nm, fc))


def render():
    s = st.session_state
    st.subheader("Absorción, generación y colección de pares")
    st.write(
        "La luz entra, se absorbe a distintas profundidades según su color, y crea "
        "pares electrón-hueco. Pero un par solo sirve si alcanza vivo la juntura: "
        "esta pestaña muestra dónde nacen y cuántos sobreviven el viaje."
    )

    campo, balance, fracciones, union, tr, fc, f_colectada = _resolver(
        s.d_n_um, s.W_p_um, s.NA, s.ND, s.T_c, s.reflector_trasero,
        s.irradiancia_soles, s.mu_p, s.tau_p_us, s.mu_n, s.tau_n_us, s.S_f, s.S_r)
    W_um = s.d_n_um + s.W_p_um

    i_lam = int(np.argmin(np.abs(campo.lambda_nm - s.lambda_nm)))
    lam = float(campo.lambda_nm[i_lam])
    alpha = float(campo.alpha[i_lam])
    refl = float(campo.R[i_lam])
    prof_um = float(cm_a_um(profundidad_absorcion_cm(alpha)))
    prof90_um = float(cm_a_um(profundidad_para_fraccion(alpha, 0.90)))

    j_generada = 1e3 * C.Q * fracciones["pares_totales_cm2_s"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reflejados en la superficie", f"{100 * fracciones['reflejados']:.1f} %")
    c2.metric("Pares generados", f"{j_generada:.2f} mA/cm²",
              help="Corriente equivalente si se colectaran todos los pares.")
    c3.metric("Se colectan", f"{100 * f_colectada:.1f} %",
              help="Fracción de los pares generados que alcanza viva la juntura.")
    c4.metric("Corriente aprovechable", f"{j_generada * f_colectada:.2f} mA/cm²",
              delta=f"{j_generada * (f_colectada - 1):.2f} por recombinación",
              delta_color="inverse")

    st.caption(
        f"Zona de deplexión de **{cm_a_um(union.W_dep):.3f} µm** con potencial de contacto "
        f"{union.psi0:.3f} V  ·  longitud de difusión **{cm_a_um(tr.L_p):.2f} µm** en el "
        f"emisor y **{cm_a_um(tr.L_n):.0f} µm** en la base  ·  peso de la superficie "
        f"frontal S_f·L_p/D_p = **{tr.peso_superficie_frontal:.1f}**, trasera = "
        f"**{tr.peso_superficie_trasera:.2f}**"
    )

    st.divider()

    izq, der = st.columns([3, 2], gap="large")

    with izq:
        modo = st.radio("Qué lanzar sobre la celda",
                        options=["Un solo color", "Espectro solar completo"],
                        horizontal=True, label_visibility="collapsed")
        es_espectro = modo == "Espectro solar completo"

        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            solo_emisor = st.toggle("Acercar al emisor",
                                    value=(not es_espectro and prof_um < 0.4 * s.d_n_um))
        with cc2:
            exagerar = st.toggle(
                "Engrosar la deplexión", value=False,
                help=f"Solo efecto visual. Su ancho real es {cm_a_um(union.W_dep):.3f} µm.")
        with cc3:
            marcar_destino = st.toggle(
                "Marcar recombinados", value=True,
                help="Sortea el destino de cada par contra la probabilidad de "
                     "colección de su propia profundidad.")

        vista_um = s.d_n_um * 1.6 if solo_emisor else W_um
        fig3d, n_fotones = cell3d.figura_celda_3d(
            lam, alpha, refl, s.d_n_um, W_um, juntura=union,
            profundidad_vista_um=vista_um, irradiancia=s.irradiancia_soles,
            modo="espectro" if es_espectro else "mono",
            espectro={"lambda_nm": campo.lambda_nm, "alpha": campo.alpha,
                      "R": campo.R, "Nph": campo.Nph},
            exagerar_deplexion=exagerar,
            coleccion=(cm_a_um(campo.x_cm), fc) if marcar_destino else None,
        )
        st.plotly_chart(fig3d, use_container_width=True)

        base_txt = (
            f"Se dibujan **{n_fotones} fotones**, proporcional a los "
            f"{s.irradiancia_soles:.2f} soles de irradiancia. "
        )
        detalle = (
            "El color de cada uno se sortea con probabilidad proporcional al flujo real "
            "del espectro AM1.5G, y su profundidad de muerte con el α de *ese* color."
            if es_espectro else
            f"La profundidad de muerte se sortea de la distribución de Beer-Lambert de "
            f"{lam:.0f} nm, y la proporción que rebota es la reflectancia de Green (2008)."
        )
        destino = (" Cada par generado se sortea después contra la probabilidad de "
                   "colección de su profundidad: los rombos se colectaron, las cruces "
                   "grises se recombinaron." if marcar_destino else "")
        st.caption(base_txt + detalle + destino)

    with der:
        st.markdown("#### Las tres regiones")
        st.dataframe(
            {
                "Región": ["Emisor tipo n", "Zona de deplexión", "Base tipo p"],
                "Desde": ["0 µm", f"{cm_a_um(union.x_n):.3f} µm",
                          f"{cm_a_um(union.x_p):.3f} µm"],
                "Hasta": [f"{cm_a_um(union.x_n):.3f} µm",
                          f"{cm_a_um(union.x_p):.3f} µm", f"{W_um:.0f} µm"],
                "Colección": [f"{100 * fc[0]:.1f} % en la superficie", "100 %",
                              f"{100 * fc[-1]:.1f} % en la cara trasera"],
            },
            hide_index=True, use_container_width=True,
        )
        st.caption(
            "En la zona de deplexión el campo eléctrico separa el par antes de que "
            "alcance a recombinarse: todo par que nazca ahí se colecta con certeza."
        )

        if not es_espectro:
            st.markdown(f"#### El color de {lam:.0f} nm")
            reparto = cell3d.resumen_sorteo(alpha, refl, um_a_cm(W_um), um_a_cm(s.d_n_um))
            st.dataframe(
                {
                    "Destino del fotón": ["Rebota en la superficie",
                                          "Se absorbe en el emisor",
                                          "Se absorbe en la base", "Atraviesa la celda"],
                    "Fracción": [f"{100 * reparto['reflejados']:.1f} %",
                                 f"{100 * reparto['en_emisor']:.1f} %",
                                 f"{100 * reparto['en_base']:.1f} %",
                                 f"{100 * reparto['atraviesan']:.1f} %"],
                },
                hide_index=True, use_container_width=True,
            )
            m1, m2 = st.columns(2)
            m1.metric("Penetración 1/α", f"{prof_um:.4g} µm")
            m2.metric("90 % absorbido a", f"{prof90_um:.4g} µm")

            fc_donde_muere = float(np.interp(prof_um, cm_a_um(campo.x_cm), fc))
            if prof90_um < s.d_n_um:
                st.warning(
                    f"Este color se absorbe entero dentro del emisor, donde la colección "
                    f"vale apenas {100 * fc_donde_muere:.0f} %. La superficie frontal se "
                    f"come la mayor parte de estos pares.")
            elif prof_um > W_um:
                st.info(f"La penetración ({prof_um:.0f} µm) supera el espesor de la celda: "
                        f"la mayor parte de estos fotones la atraviesa sin absorberse.")
            else:
                st.success(f"Se absorbe principalmente en la base, donde la colección vale "
                           f"{100 * fc_donde_muere:.0f} %.")

    st.divider()

    perfil = campo.perfil_a(lam)
    y_techo = float(np.max(perfil)) / max(s.irradiancia_soles, 1e-6) \
        * config.RANGOS["irradiancia_soles"][1] * 1.05

    g1, g2 = st.columns(2, gap="large")
    with g1:
        st.plotly_chart(
            optics_plots.generacion_con_coleccion(campo.x_cm, perfil, fc, lam,
                                                  s.d_n_um, W_um, y_techo, union),
            use_container_width=True)
        st.caption(
            "El área de color son los pares que llegan vivos a la juntura; la gris, los "
            "que se recombinan antes. El eje vertical está fijo al máximo de 1,5 soles, "
            "así que bajar la irradiancia encoge la curva de verdad."
        )
    with g2:
        st.plotly_chart(
            optics_plots.perfil_coleccion(campo.x_cm, fc, union, s.d_n_um, W_um, tr),
            use_container_width=True)
        st.caption(
            "Sube hasta el 100 % en los bordes de la zona de deplexión y cae hacia las "
            "dos superficies. Cuánto cae lo decide el cociente entre la velocidad de "
            "recombinación superficial y la capacidad de difundir del material."
        )

    st.plotly_chart(
        optics_plots.acumulado_espectral(campo.x_cm, campo.lambda_nm, campo.G,
                                         s.d_n_um, W_um),
        use_container_width=True)

    st.plotly_chart(
        optics_plots.mapa_generacion(campo.x_cm, campo.lambda_nm, campo.G,
                                     s.d_n_um, W_um),
        use_container_width=True)

    st.divider()

    g3, g4 = st.columns(2, gap="large")
    with g3:
        st.plotly_chart(optics_plots.balance_espectral(balance, lam),
                        use_container_width=True)
        error_max = float(np.max(np.abs(balance["suma"] - 1.0)))
        st.caption(
            f"Verificación V1 · error máximo del balance **{100 * error_max:.4f} %** "
            f"(tolerancia 1 %). El balance es exacto sobre el papel, así que esta cifra "
            f"mide si la grilla resuelve bien la absorción."
        )
    with g4:
        st.plotly_chart(
            optics_plots.penetracion_por_color(
                campo.lambda_nm, cm_a_um(profundidad_absorcion_cm(campo.alpha)),
                s.d_n_um, W_um, lam),
            use_container_width=True)
        st.caption(
            "Donde la curva cae en la banda inferior, ese color se agota dentro del "
            "emisor; en la del medio, alcanza la base; arriba de la última, atraviesa "
            "la celda sin absorberse."
        )

    st.info(
        "La eficiencia cuántica, que combina esta colección con el espectro para dar la "
        "respuesta de la celda color por color, es el Hito 4. También la grilla de 8×8 "
        "sectores con su tiempo de vida local.",
        icon="🔧",
    )
