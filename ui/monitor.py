"""Presentación del monitor en vivo: resumen en la barra lateral y tabla completa."""

import html

import pandas as pd
import streamlit as st

from validation.monitor import AVISO, EN_ORDEN, FALLA

_COLOR = {EN_ORDEN: "#5FC49B", AVISO: "#E5A33F", FALLA: "#E58063"}
_FONDO = {EN_ORDEN: "rgba(95,196,155,0.10)", AVISO: "rgba(229,163,63,0.12)",
          FALLA: "rgba(229,128,99,0.14)"}


def _peor(resultados):
    estados = {v.estado for v in resultados}
    if FALLA in estados:
        return FALLA
    if AVISO in estados:
        return AVISO
    return EN_ORDEN


def render_barra(contenedor, resultados):
    """Resumen permanente arriba de la barra lateral."""
    if not resultados:
        return
    peor = _peor(resultados)
    n_orden = sum(v.estado == EN_ORDEN for v in resultados)
    n_aviso = sum(v.estado == AVISO for v in resultados)
    n_falla = sum(v.estado == FALLA for v in resultados)

    partes = [f"{n_orden} en orden"]
    if n_aviso:
        partes.append(f"{n_aviso} {'aviso' if n_aviso == 1 else 'avisos'}")
    if n_falla:
        partes.append(f"{n_falla} {'falla' if n_falla == 1 else 'fallas'}")
    titular = {EN_ORDEN: "Todo en orden", AVISO: "Revisar los avisos",
               FALLA: "Resultados no confiables"}[peor]

    with contenedor:
        st.markdown(
            f"""
            <div style="border:1px solid {_COLOR[peor]}55; background:{_FONDO[peor]};
                        border-radius:8px; padding:10px 12px; margin-bottom:6px;">
              <div style="font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase;
                          color:#8894A8;">Monitor físico en vivo</div>
              <div style="font-size:1.0rem; font-weight:600; color:{_COLOR[peor]};
                          margin-top:2px;">{titular}</div>
              <div style="font-size:0.82rem; color:#BAC4D2;">{' · '.join(partes)}
                de {len(resultados)} vigilancias sobre los valores actuales</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        problemas = [v for v in resultados if v.estado != EN_ORDEN]
        with st.expander("Qué está vigilando", expanded=bool(n_falla)):
            for v in problemas + [v for v in resultados if v.estado == EN_ORDEN]:
                st.markdown(
                    f"<div style='margin:0 0 10px; font-size:0.82rem; line-height:1.45;'>"
                    f"<span style='color:{_COLOR[v.estado]}; font-weight:600;'>"
                    f"{v.estado}</span> · <b>{html.escape(v.nombre)}</b><br>"
                    f"<span style='color:#8894A8;'>{html.escape(v.medido)}</span><br>"
                    f"<span style='color:#BAC4D2;'>{html.escape(v.mensaje)}</span></div>",
                    unsafe_allow_html=True,
                )
        st.divider()


def render_tabla(resultados):
    """Tabla completa para la pestaña de Validación."""
    if not resultados:
        st.info("Las pestañas todavía no han publicado resultados en esta ejecución.")
        return
    tabla = pd.DataFrame([{
        "Código": v.codigo, "Pestaña": v.pestana, "Vigilancia": v.nombre,
        "Estado": v.estado, "Medido ahora": v.medido, "Criterio": v.criterio,
        "Qué significa": v.mensaje,
    } for v in resultados])
    st.dataframe(
        tabla.style.map(lambda s: f"color: {_COLOR.get(s, '')}; font-weight: 600",
                        subset=["Estado"]),
        hide_index=True, use_container_width=True,
    )
