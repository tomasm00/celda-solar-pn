"""
Laboratorio virtual de caracterizacion de una celda p-n de silicio.

Proyecto 1 - Problema 2.2 - Celdas Solares Fotovoltaicas 2026-2

Esta capa es solo interfaz y orquestacion: no contiene fisica. Todo calculo vive
en los modulos de physics/, data/ y validation/.
"""

import streamlit as st

import config
import constants as C
from ui import sidebar, tab_absorcion, tab_eqe, tab_iv, tab_sectores, tab_validacion

st.set_page_config(
    page_title="Laboratorio virtual de celda p-n",
    page_icon="☀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem; max-width: 1400px;}
      h1 {font-size: 1.9rem !important; letter-spacing: -0.01em;}
      .stTabs [data-baseweb="tab-list"] {gap: 2px;}
      .stTabs [data-baseweb="tab"] {padding: 10px 18px; font-size: 0.92rem;}
      .pendiente {
        border-left: 3px solid #E5A33F; background: #151D28;
        border-radius: 6px; padding: 16px 20px; margin-top: 8px;
      }
      .pendiente h4 {margin: 0 0 8px; font-size: 1rem; color: #E8ECF2;}
      .pendiente p {margin: 0 0 6px; color: #BAC4D2; font-size: 0.9rem; line-height: 1.55;}
      .pendiente ul {margin: 6px 0 0 18px; color: #BAC4D2; font-size: 0.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def inicializar_estado():
    """Carga el estado inicial asignado por la semilla, una sola vez por sesion."""
    for clave, valor in config.ESTADO_INICIAL.items():
        st.session_state.setdefault(clave, valor)


inicializar_estado()

st.title("Laboratorio virtual de caracterización de una celda p-n de silicio")
st.caption(
    f"Semilla S = {config.SEMILLA_S}  ·  emisor tipo n sobre base tipo p, "
    f"sin recubrimiento antirreflejo  ·  espectro AM1.5G (ASTM G173-03)"
)

sidebar.render()

pestanas = st.tabs([
    "1 · Absorción y generación",
    "2 · Eficiencia cuántica",
    "3 · Curva I-V",
    "4 · Mapa por sectores",
    "5 · Validación",
])

with pestanas[0]:
    tab_absorcion.render()
with pestanas[1]:
    tab_eqe.render()
with pestanas[2]:
    tab_iv.render()
with pestanas[3]:
    tab_sectores.render()
with pestanas[4]:
    tab_validacion.render()
