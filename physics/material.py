"""
Propiedades del material y geometría eléctrica de la juntura.

Este módulo no sabe nada de luz: resuelve lo que el dopaje y la temperatura
determinan por sí solos. De aquí salen las difusividades, las longitudes de
difusión, el potencial de contacto y el ancho de la zona de depleción.

Cadena (U2, láminas 20 a 23 y 30):
    dopaje + temperatura -> concentración intrínseca -> potencial de contacto
                         -> ancho de la zona de depleción
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


def ancho_deplecion(na, nd, t_k):
    """
    Ancho total de la zona de depleción, en cm.

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
    W_dep: float        # ancho total de la zona de depleción
    x_n: float          # borde de la zona en el lado n
    x_p: float          # borde de la zona en el lado p
    psi0: float         # potencial de contacto, en volt
    ni: float           # concentración intrínseca a esta temperatura, 1/cm3
    reparto: str = "simetrico"
    aviso: str = ""     # no vacio si la geometria pedida no era representable


def _reparto_simetrico(d_n_cm, w):
    return d_n_cm - w / 2.0, d_n_cm + w / 2.0


def _reparto_por_neutralidad(d_n_cm, w, na, nd):
    """
    Reparto que respeta la neutralidad de carga: N_D·w_n = N_A·w_p.

    La zona se extiende hacia cada lado en razón inversa a su dopaje, porque hace
    falta menos espesor para acumular la misma carga donde hay más dopantes.
    """
    w_n = w * na / (na + nd)
    w_p = w * nd / (na + nd)
    return d_n_cm - w_n, d_n_cm + w_p


def juntura(d_n_cm, na, nd, t_k, reparto="simetrico"):
    """
    Resuelve la geometría de la juntura.

    DECISION D-02: el enunciado reparte la zona de depleción simétricamente a
    ambos lados. Físicamente el reparto correcto es el que respeta la neutralidad
    de carga, que la manda casi entera al lado menos dopado. Se ofrecen ambos y
    el enunciado es el que manda por defecto.

    Con el reparto simétrico hay combinaciones de dopaje y espesor de emisor en
    las que el borde del lado n **cae fuera de la celda**: la zona de depleción
    llega a medir más que el emisor. Eso no es una celda; es una geometría que el
    modelo no puede representar. Antes se aceptaba en silencio y la colección
    salía valiendo 1 en la superficie frontal, ocultando por completo el efecto de
    la recombinación superficial. Ahora se detecta y se cae al reparto por
    neutralidad, avisando (ver D-21).
    """
    w = float(ancho_deplecion(na, nd, t_k))
    psi0 = float(potencial_contacto(na, nd, t_k))
    ni = float(concentracion_intrinseca(t_k))

    if reparto == "neutralidad":
        x_n, x_p = _reparto_por_neutralidad(d_n_cm, w, na, nd)
        return Juntura(d_n_cm, w, x_n, x_p, psi0, ni, "neutralidad")

    x_n, x_p = _reparto_simetrico(d_n_cm, w)
    if x_n > 0.0:
        return Juntura(d_n_cm, w, x_n, x_p, psi0, ni, "simetrico")

    x_n, x_p = _reparto_por_neutralidad(d_n_cm, w, na, nd)
    ancho_txt = f"{w * 1e4:.3f}".replace(".", ",")
    emisor_txt = f"{d_n_cm * 1e4:.3f}".replace(".", ",")
    aviso = (
        f"Con este dopaje la zona de depleción mide {ancho_txt} µm, más que el emisor de "
        f"{emisor_txt} µm, así que el reparto simétrico del enunciado dejaría su borde fuera "
        f"de la celda. Se usa el reparto por neutralidad de carga, que es el físicamente "
        f"correcto."
    )
    return Juntura(d_n_cm, w, max(x_n, 0.0), x_p, psi0, ni, "neutralidad", aviso)


# ---------------------------------------------------------------------------
# Techo intrinseco de la vida media
# ---------------------------------------------------------------------------

@dataclass
class VidaIntrinseca:
    """Vidas medias que imponen la recombinacion radiativa y la de Auger, en s."""

    radiativa: float
    auger: float

    @property
    def limite(self) -> float:
        """La vida media mas larga posible con este dopaje: las dos tasas sumadas."""
        return 1.0 / (1.0 / self.radiativa + 1.0 / self.auger)


def vida_intrinseca(dopaje_cm3):
    """
    Vida media del portador minoritario si el cristal no tuviera ningun defecto.

    En baja inyeccion, un minoritario rodeado de N mayoritarios por centimetro
    cubico se recombina radiativamente a una tasa proporcional a N, y por Auger a
    una tasa proporcional a N al cuadrado, porque Auger necesita dos mayoritarios
    a la vez: uno para recombinarse y otro que se lleve la energia (U2, lamina 27).
    La vida media es el inverso de cada tasa.

    Por eso Auger domina en el emisor fuertemente dopado y es despreciable en la
    base: pasar de 4e16 a 6e19 multiplica N por 1500 y la tasa de Auger por dos
    millones.
    """
    n = float(dopaje_cm3)
    return VidaIntrinseca(radiativa=1.0 / (C.B_RADIATIVO * n),
                          auger=1.0 / (C.C_AUGER * n * n))


def reparto_por_mecanismo(tau_efectiva_s, dopaje_cm3):
    """
    Que fraccion de la recombinacion en el volumen aporta cada mecanismo.

    La Unidad 2 (lamina 25) suma los mecanismos como tasas: el inverso de la vida
    media en el volumen es la suma de los inversos de las vidas radiativa, Auger y
    SRH. Si el tiempo de vida del control se lee como esa vida efectiva, la parte
    SRH es lo que queda al restarle las dos intrinsecas, y cada mecanismo aporta en
    proporcion a su tasa.

    Devuelve None cuando la vida elegida supera el techo intrinseco: ahi la parte
    SRH saldria negativa, que es la forma matematica de decir que ningun silicio
    con ese dopaje puede vivir tanto.
    """
    vida = vida_intrinseca(dopaje_cm3)
    tasa_total = 1.0 / float(tau_efectiva_s)
    tasa_srh = tasa_total - 1.0 / vida.radiativa - 1.0 / vida.auger
    if tasa_srh < 0.0:
        return None
    return {
        "SRH": tasa_srh / tasa_total,
        "Auger": (1.0 / vida.auger) / tasa_total,
        "radiativa": (1.0 / vida.radiativa) / tasa_total,
    }
