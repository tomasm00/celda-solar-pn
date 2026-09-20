"""Pestaña 4 - Mapa de la celda por sectores: fallas localizadas y su efecto."""

import numpy as np
import pandas as pd
import streamlit as st

import config
import constants as C
from physics.defectos import Defectos, promedio_por_bloques
from physics.quantum_efficiency import generar_sectores
from physics.sectors import voltajes_de_juntura
from ui import danos
from units import voltaje_termico
from visualization import defect_plots
from visualization.optics_plots import _coma


def _controles():
    """Las dos fallas, con una severidad cada una y un sorteo compartido."""
    s = st.session_state
    st.markdown("#### Introducir fallas")
    izq, der, boton = st.columns([5, 5, 2], gap="large")

    with izq:
        st.toggle("Grieta", key="grieta_activa",
                  help="Una grieta que se propaga desde un borde o desde un punto de "
                       "impacto, y corta los dedos de plata que cruza.")
        st.slider("Severidad de la grieta", *config.RANGOS["severidad_grieta"], step=0.05,
                  key="severidad_grieta", disabled=not s.grieta_activa,
                  help="Cuánto avanza y cuánto se ramifica. Desde 0,5 la grieta nace de "
                       "un impacto y sale en tres direcciones.")
    with der:
        st.toggle("Contaminación metálica", key="contaminacion_activa",
                  help="Una mancha de forma orgánica donde el tiempo de vida se "
                       "desploma.")
        st.slider("Severidad de la contaminación", *config.RANGOS["severidad_contaminacion"],
                  step=0.05, key="severidad_contaminacion",
                  disabled=not s.contaminacion_activa,
                  help="Mueve a la vez cuánta área cubre la mancha y cuánto cae el "
                       "tiempo de vida dentro, hasta mil veces menos.")
    with boton:
        st.write("")
        st.write("")
        if st.button("Otra falla", use_container_width=True,
                     help="Vuelve a sortear el trazado de la grieta y la forma de la "
                          "mancha, con la misma severidad."):
            s.semilla_falla = int(np.random.default_rng().integers(1, 10_000))


def render():
    s = st.session_state
    st.subheader("Mapa de la celda por sectores")
    st.write(
        "Una celda real no es homogénea, y eso es lo que revelan la electroluminiscencia y la "
        "termografía. Aquí se le introducen fallas localizadas y se ve su efecto sobre el mapa y "
        "sobre la curva. Las fallas no se dibujan sector por sector: la grieta se propaga sola y "
        "corta los dedos que cruza, la mancha tiene forma orgánica, y las zonas que se apagan las "
        "encuentra el cálculo, porque se quedaron sin camino hasta la barra colectora."
    )

    _controles()

    defectos = danos.defectos_de(s)
    sano = danos.resolver(s, danos.SIN_FALLAS)
    danada = danos.resolver(s, defectos)
    celda, fallas, p, p_sana = danada["celda"], danada["fallas"], danada["p"], sano["p"]
    # La malla fina tiene que seguir describiendo la celda de la Pestaña 2: la media
    # geométrica de cada bloque de 6 × 6 es el sector de 8 × 8 que ella usa.
    grueso = generar_sectores(config.N_SECTORES, s.tau_n_us * 1e-6, s.S_f,
                              s.dispersion_sectores)
    media_geometrica = np.exp(promedio_por_bloques(np.log(danada["sectores"].tau_n_s),
                                                   config.N_SECTORES))
    error_bloques = float(np.max(np.abs(media_geometrica / grueso.tau_n_s - 1.0)))
    r_sana = sano["celda"].r_s
    st.session_state["_bus"]["defectos"] = dict(
        hay=defectos.hay_defectos, v=danada["v"], j=danada["j"], p=p, p_sana=p_sana,
        area_aislada=fallas.area_aislada, area_contaminada=fallas.area_contaminada,
        error_bloques=error_bloques, r_calculada=float(np.mean(r_sana)),
        r_analitica=float(s.R_s + danada["grid"].r_serie),
        n_fino=config.N_SECTORES_FINOS)

    st.divider()

    def delta(clave, factor=1.0, unidad=""):
        d = factor * (p[clave] - p_sana[clave])
        return f"{'+' if d >= 0 else '−'}{_coma(abs(d), 3)}{unidad}" if abs(d) > 5e-4 else "sin cambio"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Corriente de cortocircuito", f"{_coma(1e3 * p['j_sc'], 3)} mA/cm²",
              delta=delta("j_sc", 1e3), delta_color="normal")
    c2.metric("Voltaje de circuito abierto", f"{_coma(p['v_oc'], 4)} V",
              delta=delta("v_oc"), delta_color="normal")
    c3.metric("Factor de forma", _coma(p["ff"], 4), delta=delta("ff"), delta_color="normal")
    c4.metric("Eficiencia", f"{_coma(100 * p['eficiencia'], 3)} %",
              delta=delta("eficiencia", 100, " pts"), delta_color="normal")

    sanos = ~celda.aislados
    st.caption(
        f"Malla de {config.N_SECTORES_FINOS} × {config.N_SECTORES_FINOS} celdas de "
        f"{_coma(10 * C.LADO_CELDA / config.N_SECTORES_FINOS, 1)} mm de lado, "
        f"{config.N_SECTORES_FINOS // config.N_SECTORES} por cada sector de los "
        f"{config.N_SECTORES} × {config.N_SECTORES} con que pide reportar el enunciado  ·  "
        f"la grieta parte el **{_coma(100 * fallas.grieta.mean(), 2)} %** del área y corta "
        f"**{fallas.dedos_cortados} de {fallas.dedos_totales}** columnas de dedos  ·  se quedó sin "
        f"camino a la barra el **{_coma(100 * fallas.area_aislada, 2)} %**  ·  la mancha cubre el "
        f"**{_coma(100 * fallas.area_contaminada, 2)} %**  ·  resistencia serie local entre "
        f"{_coma(float(celda.r_s[sanos].min()), 3)} y {_coma(float(celda.r_s[sanos].max()), 2)} Ω·cm² "
        f"en lo que sigue conectado"
    )

    m1, m2 = st.columns(2, gap="large")
    with m1:
        st.plotly_chart(defect_plots.mapa_de_la_celda(celda, fallas), use_container_width=True)
        st.caption(
            "La corriente que genera cada trozo. La mancha se ve como una zona apagada; la grieta, "
            "como una línea negra. Las cruces marcan los trozos que se quedaron aislados: el "
            "cálculo los encontró siguiendo el camino de la corriente, no se dibujaron."
        )
    with m2:
        st.plotly_chart(defect_plots.mapa_resistencia(celda, fallas), use_container_width=True)
        st.caption(
            "Lo que le cuesta a cada trozo llegar a la barra colectora. Donde la grieta cortó el "
            "dedo, la corriente tiene que cruzar de lado por el emisor hasta el siguiente dedo "
            "entero, y la resistencia sube con el cuadrado de esa distancia."
        )

    # ------------------------------------------------------------------ electroluminiscencia
    st.divider()
    st.markdown("#### La celda vista con electroluminiscencia")
    st.write(
        "Es el ensayo con que se inspeccionan paneles: se polariza la celda en directa, a oscuras, "
        "y se fotografía la luz que emite al recombinarse. El brillo va con la exponencial del "
        "voltaje que ve cada juntura, así que un trozo que no recibe voltaje sale negro. Detecta "
        "justamente lo que el mapa de corriente no puede ver: los defectos de resistencia."
    )
    fraccion = st.slider("Voltaje de la inspección  [% del circuito abierto]", 50.0, 110.0,
                         value=95.0, step=5.0, key="v_el",
                         help="Las cámaras de electroluminiscencia trabajan cerca del circuito "
                              "abierto, donde la celda emite más.")
    v_el = float(p["v_oc"]) * fraccion / 100.0
    v_juntura = voltajes_de_juntura(v_el, celda, s.R_p, s.n_idealidad, danada["t_k"])
    vt_n = s.n_idealidad * voltaje_termico(danada["t_k"])
    st.plotly_chart(
        defect_plots.electroluminiscencia(v_juntura, celda.aislados, vt_n, v_el, fallas),
        use_container_width=True)
    contraste = float(np.exp((v_juntura[~celda.aislados].min() - v_juntura.max()) / vt_n))
    st.caption(
        f"A {_coma(v_el, 3)} V, el voltaje que ve la juntura va de "
        f"{_coma(float(v_juntura[~celda.aislados].min()), 3)} a "
        f"{_coma(float(v_juntura.max()), 3)} V entre los trozos conectados: los más lejanos del "
        f"metal brillan {_coma(1 / max(contraste, 1e-9), 1)} veces menos que los mejores, aunque "
        f"generan la misma corriente. Los aislados no reciben voltaje y salen negros."
    )

    # ------------------------------------------------------------------ la curva
    st.divider()
    st.plotly_chart(
        defect_plots.comparacion_curvas(sano["v"], sano["j"], danada["v"], danada["j"],
                                        p_sana, p),
        use_container_width=True)
    st.caption(
        "La misma curva que dibuja la Pestaña 3, ahora con las fallas puestas. Allá aparece "
        "superpuesta a la de la celda sana."
    )

    st.markdown("#### Por qué los dos defectos dañan de maneras distintas")
    st.write(
        "Ésta es la pregunta que el enunciado pide explicar, y el modelo la responde solo, sin que "
        "la hayamos programado a mano: los sectores están en paralelo compartiendo el mismo voltaje "
        "de terminal, y de esa única condición sale toda la asimetría."
    )

    izq, der = st.columns(2, gap="large")
    with izq:
        st.markdown(
            "**El defecto de colección se lleva la corriente.** Los trozos contaminados generan los "
            "mismos pares que antes, pero con la longitud de difusión acortada la mayoría se "
            "recombina antes de alcanzar la juntura. Entregan menos corriente **en todo el "
            "barrido**, incluido el cortocircuito, así que la curva entera baja."
        )
    with der:
        st.markdown(
            "**El defecto de resistencia se lleva el factor de forma.** Los trozos que perdieron su "
            "dedo generan y colectan exactamente lo mismo. Cerca de cortocircuito el voltaje sobre "
            "su resistencia es pequeño y entregan casi toda su corriente. Pero al acercarse al "
            "punto de máxima potencia se ahogan, y lo que se hunde es la esquina de la curva. Solo "
            "cuando quedan del todo aislados dejan también de aportar corriente."
        )

    # Cada falla por separado, para poder atribuir el daño sin ambigüedad. Si solo hay
    # una activa, la celda dañada ya es ese caso y no hace falta resolverla de nuevo.
    solo_grieta = danada["p"] if not defectos.contaminacion_activa else danos.resolver(
        s, Defectos(grieta_activa=defectos.grieta_activa,
                    severidad_grieta=defectos.severidad_grieta,
                    contaminacion_activa=False, semilla=defectos.semilla))["p"]
    solo_mancha = danada["p"] if not defectos.grieta_activa else danos.resolver(
        s, Defectos(grieta_activa=False,
                    contaminacion_activa=defectos.contaminacion_activa,
                    severidad_contaminacion=defectos.severidad_contaminacion,
                    semilla=defectos.semilla))["p"]

    def caida(pp, clave):
        if p_sana[clave] == 0:
            return 0.0
        return 100.0 * (p_sana[clave] - pp[clave]) / p_sana[clave]

    valores_mancha = [100 * fallas.area_contaminada, caida(solo_mancha, "j_sc"),
                      caida(solo_mancha, "ff"), caida(solo_mancha, "eficiencia")]
    valores_grieta = [100 * (fallas.grieta.mean() + fallas.area_aislada),
                      caida(solo_grieta, "j_sc"), caida(solo_grieta, "ff"),
                      caida(solo_grieta, "eficiencia")]

    st.dataframe(
        pd.DataFrame({
            "": ["Área dañada", "Caída de Jsc", "Caída del factor de forma",
                 "Caída de eficiencia"],
            "Solo la mancha": [f"{_coma(x, 2)} %" for x in valores_mancha],
            "Solo la grieta": [f"{_coma(x, 2)} %" for x in valores_grieta],
        }),
        hide_index=True, use_container_width=True)

    st.plotly_chart(
        defect_plots.asimetria_de_los_defectos(
            {"coleccion": valores_mancha, "resistencia": valores_grieta}),
        use_container_width=True)

    if valores_mancha[0] > 0 and valores_grieta[0] > 0:
        razon_j = valores_mancha[1] / max(valores_grieta[1], 1e-6)
        razon_ff = valores_grieta[2] / max(valores_mancha[2], 1e-6)
        if razon_j > 1.2 and razon_ff > 1.2:
            st.success(
                f"Con áreas dañadas parecidas, la mancha hunde la corriente "
                f"**{_coma(razon_j, 1)} veces más** que la grieta, y la grieta hunde el factor de "
                f"forma **{_coma(razon_ff, 1)} veces más** que la mancha. Dos fallas de tamaño "
                f"comparable, daños de naturaleza opuesta."
            )

    st.caption(
        "Límites declarados. El camino eléctrico se calcula como el recorrido de menor distancia "
        "hasta el dedo útil más cercano, no resolviendo la red completa de resistencias: sin grieta "
        "reproduce la resistencia de la malla del modelo analítico dentro de un 0,2 %. **No se "
        "modela el acoplamiento lateral** entre trozos vecinos —cada celda de 3,25 mm es diez veces "
        "la longitud de difusión, así que los portadores no cruzan—, ni ningún balance térmico: "
        "este modelo no calcula temperatura, así que no predice puntos calientes. Sí reproduce que "
        "un trozo de poca fotocorriente **consuma** corriente cuando el conjunto opera por encima de "
        "su circuito abierto local, que es disipación en directa y no requiere polarización inversa."
    )
