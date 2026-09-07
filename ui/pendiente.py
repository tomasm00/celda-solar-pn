"""Marcador de pestaña aun no construida, con lo que traera cada hito."""

import streamlit as st


def render(hito: str, titulo: str, descripcion: str, elementos: list[str]):
    items = "".join(f"<li>{e}</li>" for e in elementos)
    st.markdown(
        f"""
        <div class="pendiente">
          <h4>{titulo} · se construye en el {hito}</h4>
          <p>{descripcion}</p>
          <ul>{items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
