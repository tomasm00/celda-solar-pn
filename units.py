"""
Conversiones de unidades explicitas.

Ninguna conversion ocurre al paso dentro de un calculo fisico: toda la aritmetica
de unidades vive aqui, con nombre. Es la disciplina que evita el error mas comun
de este tipo de simulacion (mezclar m con cm, o nm con um, silenciosamente).
"""

import numpy as np

from constants import C_LIGHT, H_PLANCK, KB_EV, Q

# --- longitud ---------------------------------------------------------------

UM_POR_CM = 1e4
NM_POR_CM = 1e7
NM_POR_UM = 1e3


def um_a_cm(x_um):
    return np.asarray(x_um, dtype=float) / UM_POR_CM


def cm_a_um(x_cm):
    return np.asarray(x_cm, dtype=float) * UM_POR_CM


def nm_a_cm(lam_nm):
    return np.asarray(lam_nm, dtype=float) / NM_POR_CM


def um_a_nm(lam_um):
    return np.asarray(lam_um, dtype=float) * NM_POR_UM


# --- temperatura ------------------------------------------------------------

def celsius_a_kelvin(t_c):
    return np.asarray(t_c, dtype=float) + 273.15


def kelvin_a_celsius(t_k):
    return np.asarray(t_k, dtype=float) - 273.15


def voltaje_termico(t_k):
    """Energia termica kB*T/q, en volt. A 300 K entrega 25.85 mV (Anexo B)."""
    return KB_EV * np.asarray(t_k, dtype=float)


# --- corriente --------------------------------------------------------------

def a_cm2_a_ma_cm2(j):
    return np.asarray(j, dtype=float) * 1e3


def ma_cm2_a_a_cm2(j):
    return np.asarray(j, dtype=float) / 1e3


# --- optica y fotones -------------------------------------------------------

def irradiancia_m2_a_cm2(e_w_m2_nm):
    """Irradiancia espectral de W/(m2*nm) a W/(cm2*nm). Factor 1e-4."""
    return np.asarray(e_w_m2_nm, dtype=float) * 1e-4


def energia_foton_ev(lam_nm):
    """Energia de un foton en eV a partir de su longitud de onda en nm."""
    lam_m = np.asarray(lam_nm, dtype=float) * 1e-9
    return H_PLANCK * C_LIGHT / (lam_m * Q)


def irradiancia_a_flujo_fotones(e_w_m2_nm, lam_nm):
    """
    Convierte irradiancia espectral en flujo espectral de fotones.

    Entrada : E en W/(m2*nm), longitud de onda en nm
    Salida  : Nph en fotones/(cm2*s*nm)

    Cada foton carga energia h*c/lambda, asi que un vatio de luz roja trae mas
    fotones que un vatio de luz azul. Se divide la potencia por la energia del
    foton y se pasa de m2 a cm2.
    """
    lam_m = np.asarray(lam_nm, dtype=float) * 1e-9
    energia_foton_j = H_PLANCK * C_LIGHT / lam_m          # J por foton
    flujo_m2 = np.asarray(e_w_m2_nm, dtype=float) / energia_foton_j  # 1/(m2*s*nm)
    return flujo_m2 * 1e-4                                 # 1/(cm2*s*nm)


def k_a_alpha(k, lam_nm):
    """
    Coeficiente de absorcion a partir del indice de extincion.

    alpha = 4*pi*k/lambda   (Anexo B del enunciado, U2)

    Entrada : k adimensional, longitud de onda en nm
    Salida  : alpha en 1/cm
    """
    return 4.0 * np.pi * np.asarray(k, dtype=float) / nm_a_cm(lam_nm)


def profundidad_absorcion_um(alpha_cm):
    """Profundidad caracteristica de absorcion 1/alpha, de 1/cm a um."""
    return cm_a_um(1.0 / np.asarray(alpha_cm, dtype=float))
