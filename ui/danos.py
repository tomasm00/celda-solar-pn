"""
La celda con fallas, resuelta una sola vez para las Pestañas 3 y 4.

La Pestaña 4 introduce las fallas y las muestra sobre el mapa; la Pestaña 3 dibuja
la curva que resulta. Las dos tienen que describir la misma celda, así que el
cálculo vive aquí y las dos lo piden por su caché: quien llegue segundo no paga
nada (D-48).
"""

import numpy as np
import streamlit as st

import config
import constants as C
from physics.collection import transporte as armar_transporte
from physics.defectos import (Defectos, generar_sectores_finos, mapa_de_fallas,
                              promedio_por_bloques)
from physics.front_grid import malla
from physics.material import juntura as resolver_juntura
from physics.optics import campo_optico
from physics.quantum_efficiency import LARGO_CORRELACION_SECTORES
from physics.sectors import armar_celda, curva_global, parametros_de_curva
from units import celsius_a_kelvin, um_a_cm

NODOS_EN_DEPLECION = 12
SIN_FALLAS = Defectos(grieta_activa=False, contaminacion_activa=False)


def defectos_de(estado) -> Defectos:
    """Lee del estado compartido las fallas que el usuario introdujo."""
    return Defectos(
        grieta_activa=bool(estado["grieta_activa"]),
        severidad_grieta=float(estado["severidad_grieta"]),
        contaminacion_activa=bool(estado["contaminacion_activa"]),
        severidad_contaminacion=float(estado["severidad_contaminacion"]),
        semilla=int(estado["semilla_falla"]),
    )


@st.cache_data(show_spinner=False, max_entries=6)
def _base_fisica(d_n_um, W_p_um, na, nd, t_c, reflector, irradiancia, mu_p, tau_p_us,
                 mu_n, tau_n_us, s_f, s_r, r_fija):
    d_n, W_p = um_a_cm(d_n_um), um_a_cm(W_p_um)
    t_k = celsius_a_kelvin(t_c)
    union = resolver_juntura(d_n, na, nd, t_k)
    campo = campo_optico(d_n, W_p, reflector, irradiancia,
                         np.linspace(max(union.x_n, 0.0), union.x_p, NODOS_EN_DEPLECION),
                         reflectancia_fija=r_fija)
    tr = armar_transporte(mu_p, tau_p_us * 1e-6, mu_n, tau_n_us * 1e-6, s_f, s_r, t_k)
    return campo, union, tr, float(t_k), d_n + W_p


@st.cache_data(show_spinner=False, max_entries=4)
def _sectores(tau_n_us, s_f, dispersion):
    return generar_sectores_finos(config.N_SECTORES_FINOS, tau_n_us * 1e-6, s_f,
                                  dispersion, n_reporte=config.N_SECTORES)


@st.cache_data(show_spinner=False, max_entries=8)
def _fallas(defectos, n_dedos, ancho_dedo_um, rs_externa):
    largo = LARGO_CORRELACION_SECTORES * config.N_SECTORES_FINOS / config.N_SECTORES
    return mapa_de_fallas(defectos, config.N_SECTORES_FINOS, n_dedos,
                          ancho_dedo_um * 1e-4, rs_externa, largo)


@st.cache_data(show_spinner=False, max_entries=8)
def _celda_y_curva(_campo, _union, _tr, _sectores_finos, _fallas_mapa, huella, W, t_k,
                   na, nd, fraccion_sombra, rp, n_idealidad, irradiancia):
    celda = armar_celda(_campo, _union, W, _tr, _sectores_finos, _fallas_mapa,
                        fraccion_sombra, na, nd, t_k)
    v, j, v_oc = curva_global(celda, rp, n_idealidad, t_k)
    p = parametros_de_curva(v, j, C.IRRADIANCE_1SUN * irradiancia, v_oc)
    return celda, v, j, p


def resolver(estado, defectos=None):
    """
    Resuelve la celda con las fallas indicadas, o con las del estado compartido.

    Devuelve un diccionario con la celda, su curva, sus parámetros y el mapa de
    fallas. Todo pasa por caché, así que llamarlo desde dos pestañas cuesta lo
    mismo que llamarlo desde una.
    """
    s = estado
    r_fija = config.reflectancia_fija_de(s)
    campo, union, tr, t_k, W = _base_fisica(
        s["d_n_um"], s["W_p_um"], s["NA"], s["ND"], s["T_c"], s["reflector_trasero"],
        s["irradiancia_soles"], s["mu_p"], s["tau_p_us"], s["mu_n"], s["tau_n_us"],
        s["S_f"], s["S_r"], r_fija)
    finos = _sectores(s["tau_n_us"], s["S_f"], s["dispersion_sectores"])
    fallas = _fallas(defectos if defectos is not None else defectos_de(s),
                     s["n_dedos"], s["ancho_dedo_um"], s["R_s"])
    grid = malla(s["n_dedos"], s["ancho_dedo_um"] * 1e-4)

    huella = (s["d_n_um"], s["W_p_um"], s["NA"], s["ND"], s["T_c"], s["reflector_trasero"],
              s["irradiancia_soles"], s["mu_p"], s["tau_p_us"], s["mu_n"], s["tau_n_us"],
              s["S_f"], s["S_r"], s["dispersion_sectores"], r_fija, s["n_dedos"],
              s["ancho_dedo_um"], s["R_s"], s["R_p"], s["n_idealidad"],
              defectos if defectos is not None else defectos_de(s))
    celda, v, j, p = _celda_y_curva(
        campo, union, tr, finos, fallas, huella, W, t_k, s["NA"], s["ND"],
        grid.fraccion_sombra, s["R_p"], s["n_idealidad"], s["irradiancia_soles"])
    return dict(campo=campo, union=union, tr=tr, t_k=t_k, W=W, sectores=finos,
                fallas=fallas, celda=celda, v=v, j=j, p=p, grid=grid)


def mapa_reportado(matriz):
    """Lleva una magnitud de la malla fina a la grilla de 8 × 8 del enunciado."""
    return promedio_por_bloques(matriz, config.N_SECTORES)
