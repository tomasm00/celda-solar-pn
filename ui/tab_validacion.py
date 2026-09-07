"""
Pestaña 5 - Validación.

Se ejecuta automáticamente al abrirse y muestra, para cada verificación, el valor
calculado por la simulación, el de referencia, el error porcentual y un veredicto.
"""

import pandas as pd
import streamlit as st

import constants as C
from validation import checks

_COLOR = {"APRUEBA": "#5FC49B", "INFORMATIVO": "#D9A63F", "FALLA": "#E58063"}


def render():
    st.subheader("Validación")
    st.write(
        "Estas verificaciones corren solas cada vez que se abre la pestaña. El valor "
        "calculado sale siempre del modelo; solo el de referencia está almacenado."
    )

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

    st.info(
        "Estado del proyecto: estas son las verificaciones de datos del Hito 1. "
        "Las siete verificaciones V1 a V7 del enunciado se van agregando a medida "
        "que la física que cada una comprueba pasa sus propias pruebas.",
        icon="🔧",
    )

    st.divider()
    st.caption("Procedencia de los datos")
    st.markdown(f"**Espectro solar.** {C.FUENTE_ESPECTRO}")
    st.markdown(f"**Constantes ópticas del silicio.** {C.FUENTE_NK_SILICIO}")
