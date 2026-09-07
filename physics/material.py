"""
Propiedades del material y geometría eléctrica de la juntura.

Este módulo no sabe nada de luz: resuelve lo que el dopaje y la temperatura
determinan por sí solos. De aquí salen las difusividades, las longitudes de
difusión, el potencial de contacto y el ancho de la zona de deplexión.

Cadena (U2, láminas 20 a 23 y 30):
    dopaje + temperatura -> concentración intrínseca -> potencial de contacto
                         -> ancho de la zona de deplexión
    movilidad + temperatura -> difusividad (Einstein) -> longitud de difusión
"""

from dataclasses import dataclass

import numpy as np

import constants as C
from units import voltaje_termico


def bandgap(t_k):
    """
    Banda prohibida en función de la temperatura, en eV.

    Eg(T) = 1,206 - 0,000273*T con T en kelvin (Anexo B, U4). A 300 K entrega
    1,124 eV, consistente con el valor canónico de 1,12 eV.
    """
    return C.EG_T_A - C.EG_T_B * np.asarray(t_k, dtype=float)


def concentracion_intrinseca(t_k):
    """
    Concentración intrínseca en función de la temperatura, en 1/cm3.

    Se ancla al valor del curso: n_i = 1e10 a 300 K (Anexo B). La dependencia
    térmica viene de dos factores: las densidades efectivas de estados crecen
    como T^(3/2), y el factor exponencial e^(-Eg/2kT) crece fuertísimo con la
    temperatura porque cada vez más electrones logran cruzar la banda prohibida.

    Este segundo factor es el que, más adelante, dará el signo negativo correcto
    al coeficiente de temperatura del voltaje de circuito abierto (ver D-08).
    """
    t = np.asarray(t_k, dtype=float)
    t_ref = C.T_REF_300K

    factor_estados = (t / t_ref) ** 1.5
    exponente = (bandgap(t_ref) / (2 * C.KB_EV * t_ref)
                 - bandgap(t) / (2 * C.KB_EV * t))
    return C.NI_300K * factor_estados * np.exp(exponente)


def difusividad(movilidad, t_k):
    """
    Coeficiente de difusión a partir de la movilidad (relación de Einstein).

    D = (kB*T/q) * mu. En palabras: qué tan bien difunde un portador es
    proporcional a qué tan bien se mueve bajo un campo, con la energía térmica
    como constante de proporcionalidad. Unidad cm2/s.
    """
    return voltaje_termico(t_k) * np.asarray(movilidad, dtype=float)


def longitud_difusion(d, tau_s):
    """
    Distancia media que recorre un minoritario antes de recombinarse (U2, lámina 30).

    L = sqrt(D*tau). Unidad cm.
    """
    return np.sqrt(np.asarray(d, dtype=float) * np.asarray(tau_s, dtype=float))


def potencial_contacto(na, nd, t_k):
    """
    Potencial de contacto de la juntura, en volt (U2, lámina 23).

    Psi0 = (kB*T/q) * ln(NA*ND/ni^2). Es la barrera que se establece sola cuando
    los dos materiales dopados se ponen en contacto y las cargas difunden hasta
    equilibrarse.
    """
    ni = concentracion_intrinseca(t_k)
    return voltaje_termico(t_k) * np.log(na * nd / ni ** 2)


def ancho_deplexion(na, nd, t_k):
    """
    Ancho total de la zona de deplexión, en cm.

    Se obtiene resolviendo las expresiones de campo y potencial de la lámina 21
    de la U2 con dos condiciones: la carga total de la zona es neutra, y el
    potencial acumulado a través de ella es Psi0. El resultado es

        W = sqrt( (2*eps*Psi0/q) * (1/NA + 1/ND) )

    en palabras: la zona es más ancha cuanto mayor es la barrera de potencial, y
    más angosta cuanto más dopado está el material, porque hace falta menos
    espesor para acumular la misma carga.

    DECISION D-01: se usa la permitividad del silicio, no la del vacío que
    aparece escrita en la lámina.
    """
    psi0 = potencial_contacto(na, nd, t_k)
    return np.sqrt((2.0 * C.EPS_SI * psi0 / C.Q) * (1.0 / na + 1.0 / nd))


@dataclass
class Juntura:
    """Geometría eléctrica de la celda, toda en cm."""

    x_j: float          # posición de la juntura = espesor del emisor
    W_dep: float        # ancho total de la zona de deplexión
    x_n: float          # borde de la zona en el lado n
    x_p: float          # borde de la zona en el lado p
    psi0: float         # potencial de contacto, en volt
    ni: float           # concentración intrínseca a esta temperatura, 1/cm3


def juntura(d_n_cm, na, nd, t_k):
    """
    Resuelve la geometría de la juntura.

    DECISION D-02: el enunciado reparte la zona de deplexión simétricamente a
    ambos lados de la juntura. Físicamente se extendería casi enteramente hacia
    el lado menos dopado, pero ambas cifras son despreciables frente al emisor,
    así que se sigue el enunciado y se declara la simplificación.
    """
    w = float(ancho_deplexion(na, nd, t_k))
    return Juntura(
        x_j=d_n_cm,
        W_dep=w,
        x_n=d_n_cm - w / 2.0,
        x_p=d_n_cm + w / 2.0,
        psi0=float(potencial_contacto(na, nd, t_k)),
        ni=float(concentracion_intrinseca(t_k)),
    )
