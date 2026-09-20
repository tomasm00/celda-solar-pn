"""
Pestaña 5 - Validación.

Se ejecuta automáticamente al abrirse y muestra, para cada verificación, el valor
calculado por la simulación, el de referencia, el error porcentual y un veredicto.
"""

import pandas as pd
import streamlit as st

import constants as C
from ui import monitor as monitor_ui
from validation import checks

_COLOR = {"APRUEBA": "#5FC49B", "INFORMATIVO": "#D9A63F", "FALLA": "#E58063"}


def render(vigilancias=()):
    st.subheader("Validación")
    st.write(
        "La validación tiene dos partes con trabajos distintos. El **monitor en vivo** "
        "revisa, con los valores que están ahora en los controles, que lo que muestra la "
        "aplicación siga siendo físicamente posible y numéricamente correcto. La "
        "**certificación** corre siempre sobre la celda asignada por la semilla y "
        "respalda las cifras que se reportan, sin importar lo que se haya movido."
    )

    st.markdown("#### Monitor en vivo · valores actuales de los controles")
    monitor_ui.render_tabla(list(vigilancias))
    st.caption(
        "EN ORDEN: el invariante se cumple. AVISO: el cálculo es correcto, pero lo que se "
        "pidió no es físicamente posible o se sale de un supuesto del curso, así que los "
        "resultados hay que leerlos con cuidado. FALLA: se rompió algo que el modelo debe "
        "cumplir para cualquier parámetro; los resultados de esa pestaña no son confiables. "
        "Por ahora vigila la Pestaña 1 y su coherencia con la 3; las demás pestañas se "
        "incorporan a medida que se revisan."
    )

    st.divider()
    st.markdown("#### Certificación · celda asignada por la semilla")

    resultados = checks.ejecutar_todas()

    aprueban = sum(1 for v in resultados if v.veredicto == "APRUEBA")
    informativos = sum(1 for v in resultados if v.veredicto == "INFORMATIVO")
    fallan = sum(1 for v in resultados if v.veredicto == "FALLA")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Verificaciones", len(resultados))
    c2.metric("Aprueban", aprueban)
    c3.metric("Informativas", informativos)
    c4.metric("Fallan", fallan)

    tabla = pd.DataFrame([
        {
            "Código": v.codigo,
            "Verificación": v.nombre,
            "Calculado": f"{v.calculado:.4g}",
            "Referencia": f"{v.referencia:.4g}",
            "Unidad": v.unidad,
            "Error": f"{v.error_pct:+.1f} %",
            "Criterio": v.criterio,
            "Veredicto": v.veredicto,
        }
        for v in resultados
    ])

    st.dataframe(
        tabla.style.map(
            lambda s: f"color: {_COLOR.get(s, '')}; font-weight: 600",
            subset=["Veredicto"],
        ),
        hide_index=True,
        use_container_width=True,
    )

    with st.expander("Notas de cada verificación"):
        for v in resultados:
            if v.nota:
                st.markdown(f"**{v.codigo} — {v.nombre}.** {v.nota}")

    st.caption(
        "Incluye las siete verificaciones V1 a V7 del enunciado, los chequeos de los "
        "datos medidos y las pruebas de consistencia interna del modelo. El valor calculado "
        "sale siempre del modelo; solo el de referencia está almacenado."
    )

    st.divider()
    st.caption("Procedencia de los datos")
    st.markdown(f"**Espectro solar.** {C.FUENTE_ESPECTRO}")
    st.markdown(f"**Constantes ópticas del silicio.** {C.FUENTE_NK_SILICIO}")
