"""
Carga y verificacion de los dos archivos de datos externos del proyecto.

Regla del enunciado (Fase de datos): los datos no se inventan ni se ajustan a
mano. Aqui se leen tal cual vienen, se verifica que las columnas y unidades sean
las esperadas, y se dejan en el sistema de unidades interno del proyecto.

Los dos archivos viven en grillas de longitud de onda distintas, asi que se
proyectan sobre una grilla comun. Ver nota sobre interpolacion en
`constantes_opticas_silicio`.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from units import irradiancia_a_flujo_fotones, k_a_alpha, um_a_nm

DIR_DATOS = Path(__file__).resolve().parent

ARCHIVO_ESPECTRO = DIR_DATOS / "astmg173.xls"
ARCHIVO_NK = DIR_DATOS / "Green-2008_silicon_nk.csv"

# Rango espectral de trabajo del Problema 2.2 (enunciado, Pestaña 1)
LAMBDA_MIN_NM = 300.0
LAMBDA_MAX_NM = 1200.0


class ErrorDeDatos(Exception):
    """El archivo no tiene la estructura esperada."""


# ---------------------------------------------------------------------------
# Espectro solar AM1.5G
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def espectro_am15g():
    """
    Lee el espectro AM1.5G desde astmg173.xls.

    La planilla trae tres espectros; se usa la columna 'Global tilt', que es
    AM1.5G. Las otras dos son el extraterrestre y el directo+circumsolar.

    Devuelve un dict con:
        lambda_nm : longitud de onda, nm
        E         : irradiancia espectral, W/(m2*nm)
        Nph       : flujo espectral de fotones, 1/(cm2*s*nm)
    """
    if not ARCHIVO_ESPECTRO.exists():
        raise ErrorDeDatos(f"No se encuentra {ARCHIVO_ESPECTRO}")

    crudo = pd.read_excel(ARCHIVO_ESPECTRO, sheet_name="SMARTS2", header=None)

    # Fila 1 (indice 1) trae los encabezados reales; los datos parten en la fila 2.
    encabezados = [str(v) for v in crudo.iloc[1].tolist()]
    if not encabezados[0].startswith("Wvlgth") or "Global tilt" not in encabezados[2]:
        raise ErrorDeDatos(
            "Las columnas de astmg173.xls no son las esperadas. "
            f"Encontrado: {encabezados}"
        )

    datos = crudo.iloc[2:].astype(float)
    lambda_nm = datos.iloc[:, 0].to_numpy()
    e_espectral = datos.iloc[:, 2].to_numpy()   # Global tilt, W/(m2*nm)

    if lambda_nm.min() > LAMBDA_MIN_NM or lambda_nm.max() < LAMBDA_MAX_NM:
        raise ErrorDeDatos(
            f"El espectro cubre {lambda_nm.min()}-{lambda_nm.max()} nm, "
            f"insuficiente para {LAMBDA_MIN_NM}-{LAMBDA_MAX_NM} nm"
        )

    return {
        "lambda_nm": lambda_nm,
        "E": e_espectral,
        "Nph": irradiancia_a_flujo_fotones(e_espectral, lambda_nm),
    }


def irradiancia_total(lambda_min=None, lambda_max=None):
    """Integral de la irradiancia espectral, en W/m2. Sin limites, integra todo."""
    esp = espectro_am15g()
    lam, e = esp["lambda_nm"], esp["E"]
    if lambda_min is not None or lambda_max is not None:
        lo = lambda_min if lambda_min is not None else lam.min()
        hi = lambda_max if lambda_max is not None else lam.max()
        mascara = (lam >= lo) & (lam <= hi)
        lam, e = lam[mascara], e[mascara]
    return float(np.trapezoid(e, lam))


def flujo_fotones_sobre_bandgap(eg_ev):
    """
    Flujo de fotones con energia mayor que el bandgap, en 1/(cm2*s).

    Solo los fotones con energia sobre la banda prohibida pueden generar un par
    electron-hueco (U2, lamina 35). El corte en longitud de onda es 1240/Eg nm.
    """
    esp = espectro_am15g()
    lam, nph = esp["lambda_nm"], esp["Nph"]
    lambda_corte = 1239.841984 / float(eg_ev)   # h*c/q en eV*nm
    mascara = lam <= lambda_corte
    return float(np.trapezoid(nph[mascara], lam[mascara]))


# ---------------------------------------------------------------------------
# Constantes opticas del silicio (Green 2008)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _leer_nk_crudo():
    """Lee el CSV de Green, que trae dos bloques consecutivos: 'wl,n' y 'wl,k'."""
    if not ARCHIVO_NK.exists():
        raise ErrorDeDatos(f"No se encuentra {ARCHIVO_NK}")

    texto = ARCHIVO_NK.read_text(encoding="utf-8")
    bloques = [b.strip() for b in texto.split("wl,") if b.strip()]
    if len(bloques) != 2:
        raise ErrorDeDatos(
            f"Se esperaban dos bloques (n y k) en {ARCHIVO_NK.name}, "
            f"se encontraron {len(bloques)}"
        )

    def parsear(bloque):
        filas = [ln.split(",") for ln in bloque.splitlines()[1:] if ln.strip()]
        arr = np.array(filas, dtype=float)
        return arr[:, 0], arr[:, 1]

    lam_n_um, n = parsear(bloques[0])
    lam_k_um, k = parsear(bloques[1])

    if not np.allclose(lam_n_um, lam_k_um):
        raise ErrorDeDatos("Los bloques n y k no comparten la misma grilla de longitud de onda")

    return um_a_nm(lam_n_um), n, k


@lru_cache(maxsize=1)
def constantes_opticas_silicio():
    """
    Indice de refraccion y coeficiente de absorcion del silicio, sobre la grilla
    del espectro solar restringida a 300-1200 nm.

    Nota de interpolacion: n se interpola linealmente porque es una funcion suave
    de orden 1. k NO: recorre trece ordenes de magnitud entre el ultravioleta y
    el infrarrojo, y cae abruptamente cerca del borde de banda, asi que se
    interpola en escala logaritmica. Interpolar k linealmente entre puntos
    separados 10 nm falsearia la absorcion justo donde el silicio deja de
    absorber, que es la region que decide la corriente en el rojo.

    Devuelve un dict con:
        lambda_nm : nm
        n, k      : adimensionales
        alpha     : coeficiente de absorcion, 1/cm
        R         : reflectancia a incidencia normal aire-silicio, adimensional
    """
    lam_datos_nm, n_datos, k_datos = _leer_nk_crudo()

    if lam_datos_nm.min() > LAMBDA_MIN_NM or lam_datos_nm.max() < LAMBDA_MAX_NM:
        raise ErrorDeDatos(
            f"Los datos n,k cubren {lam_datos_nm.min():.0f}-{lam_datos_nm.max():.0f} nm, "
            f"insuficiente para {LAMBDA_MIN_NM}-{LAMBDA_MAX_NM} nm"
        )

    lam_esp = espectro_am15g()["lambda_nm"]
    lam = lam_esp[(lam_esp >= LAMBDA_MIN_NM) & (lam_esp <= LAMBDA_MAX_NM)]

    n = np.interp(lam, lam_datos_nm, n_datos)
    k = np.exp(np.interp(lam, lam_datos_nm, np.log(k_datos)))

    return {
        "lambda_nm": lam,
        "n": n,
        "k": k,
        "alpha": k_a_alpha(k, lam),
        "R": reflectancia_normal(n, k),
    }


def reflectancia_normal(n, k, n_medio=1.0):
    """
    Reflectancia a incidencia normal en la interfaz medio-silicio.

    R = ((n2 - n1)^2 + k^2) / ((n2 + n1)^2 + k^2)      (U2, lamina 33)

    El medio incidente es aire (n1 = 1). Adimensional, entre 0 y 1.
    """
    n = np.asarray(n, dtype=float)
    k = np.asarray(k, dtype=float)
    return ((n - n_medio) ** 2 + k ** 2) / ((n + n_medio) ** 2 + k ** 2)


def reflectancia_media_ponderada():
    """
    Reflectancia media del silicio desnudo, ponderada por el flujo de fotones
    AM1.5G (U2, lamina 34). El Anexo B da ~0.30 como referencia.

    Se pondera por fotones y no por potencia porque lo que se pierde por reflexion,
    para efectos de generacion de pares, son fotones.
    """
    opticas = constantes_opticas_silicio()
    lam = opticas["lambda_nm"]
    nph = np.interp(lam, espectro_am15g()["lambda_nm"], espectro_am15g()["Nph"])
    return float(np.trapezoid(opticas["R"] * nph, lam) / np.trapezoid(nph, lam))
