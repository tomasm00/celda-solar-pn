"""
El compromiso de la malla frontal, medido en puntos de eficiencia.

La malla frontal hace dos cosas opuestas. Tapa luz, y por lo tanto corriente, en
proporción al número de dedos; y recoge la corriente, con una resistencia que
baja al agregar dedos. Mirar las dos cosas por separado —una en porcentaje de
área y la otra en ohm por centímetro cuadrado— no permite compararlas. Este
módulo las lleva a una sola unidad, puntos de eficiencia perdidos, resolviendo la
curva I-V completa en cada caso (D-44).

La resta es secuencial y el orden está declarado: se parte de la celda sin malla,
se le agrega primero la sombra, después la resistencia del emisor y al final la de
los dedos. Cada pérdida es la caída de eficiencia que produce ese paso sobre el
anterior, así que las tres suman exactamente la distancia entre la celda sin malla
y la celda real. Con otro orden, el reparto entre las dos resistencias cambia en
centésimas de punto, porque las pérdidas resistivas no son aditivas: dependen del
cuadrado de la corriente, que a su vez cambia con la sombra.
"""

from dataclasses import dataclass

import numpy as np

import constants as C
from physics.diode import curva_iv
from physics.front_grid import malla


@dataclass
class PuntoDeMalla:
    """Una malla posible, con su geometría y lo que cuesta."""

    n_dedos: int
    separacion_cm: float
    fraccion_sombra: float
    r_emisor: float                  # ohm*cm2
    r_dedos: float                   # ohm*cm2
    eficiencia: float                # fraccion
    perdida_sombra: float            # puntos de eficiencia
    perdida_emisor: float
    perdida_dedos: float
    caida_maxima_v: float            # caida lateral en el punto mas lejano al dedo
    curva: object                    # CurvaIV de la celda con esta malla

    @property
    def perdida_total(self) -> float:
        return self.perdida_sombra + self.perdida_emisor + self.perdida_dedos


def caida_lateral(separacion_cm, j_a_cm2, rho_cuadro=C.RHO_CUADRO_EMISOR, puntos=81):
    """
    Perfil de la caída de voltaje en el emisor entre dos dedos vecinos.

    La corriente fotogenerada entra al emisor repartida de forma uniforme y viaja
    de lado hasta el dedo más cercano. A una distancia u del punto medio entre dos
    dedos, la corriente que ya se ha juntado es J·u por unidad de largo, así que
    el voltaje se pierde según

        ΔV(u) = ρ□ · J · [ (S/2)² − u² ] / 2

    una parábola que vale cero sobre el dedo y es máxima en el punto medio. El
    promedio de la potencia que esa caída disipa equivale a una resistencia serie
    de ρ□·S²/12, que es la que usa el modelo de la malla.

    Devuelve la posición medida desde un dedo, en cm, y la caída en volts.
    """
    mitad = separacion_cm / 2.0
    u = np.linspace(-mitad, mitad, puntos)
    caida = rho_cuadro * j_a_cm2 * (mitad ** 2 - u ** 2) / 2.0
    return u + mitad, caida


def _resolver(j_l_desnuda, j0, rs, rp, n_idealidad, t_k, sombra, irradiancia,
              n_puntos=70):
    """
    Una curva completa. Setenta voltajes bastan: el punto de máxima potencia se
    afina aparte, así que la eficiencia coincide con la de una grilla de 420
    puntos en la sexta cifra, y el barrido completo baja de siete segundos a dos.
    """
    return curva_iv(j0, j_l_desnuda * (1.0 - sombra), rs, rp, n_idealidad, t_k,
                    irradiancia_w_cm2=C.IRRADIANCE_1SUN * irradiancia,
                    n_puntos=n_puntos)


def barrido_de_mallas(j_l_desnuda, j0, rs_extra, rp, n_idealidad, t_k,
                      ancho_dedo_cm, irradiancia, n_min=10, n_max=200, paso=5):
    """
    Recorre el número de dedos y reparte la pérdida de cada malla en sus causas.

    Devuelve la eficiencia de la celda sin malla —la referencia contra la que se
    miden las pérdidas— y un punto por cada número de dedos.
    """
    referencia = _resolver(j_l_desnuda, j0, rs_extra, rp, n_idealidad, t_k,
                           0.0, irradiancia).eficiencia
    puntos = []
    for n in range(int(n_min), int(n_max) + 1, int(paso)):
        g = malla(n, ancho_dedo_cm)
        con_sombra = _resolver(j_l_desnuda, j0, rs_extra, rp, n_idealidad, t_k,
                               g.fraccion_sombra, irradiancia).eficiencia
        con_emisor = _resolver(j_l_desnuda, j0, rs_extra + g.r_emisor, rp,
                               n_idealidad, t_k, g.fraccion_sombra, irradiancia).eficiencia
        curva = _resolver(j_l_desnuda, j0, rs_extra + g.r_serie, rp,
                          n_idealidad, t_k, g.fraccion_sombra, irradiancia)
        _, caida = caida_lateral(g.separacion_cm, curva.j_mpp, puntos=3)
        puntos.append(PuntoDeMalla(
            n_dedos=n, separacion_cm=g.separacion_cm, fraccion_sombra=g.fraccion_sombra,
            r_emisor=g.r_emisor, r_dedos=g.r_dedos, eficiencia=curva.eficiencia,
            perdida_sombra=100.0 * (referencia - con_sombra),
            perdida_emisor=100.0 * (con_sombra - con_emisor),
            perdida_dedos=100.0 * (con_emisor - curva.eficiencia),
            caida_maxima_v=float(caida.max()), curva=curva,
        ))
    return referencia, puntos


def mejor_malla(puntos):
    """La malla de mayor eficiencia del barrido."""
    return max(puntos, key=lambda p: p.eficiencia)
