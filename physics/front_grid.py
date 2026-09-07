"""
Malla frontal de dedos de plata.

Los contactos no pueden cubrir toda la superficie porque bloquearían la luz, así
que son dedos delgados. Pero mientras más separados están, más lejos tiene que
viajar la corriente lateralmente por el emisor —que es mal conductor— antes de
alcanzar un dedo. De ahí el compromiso que el enunciado pide mostrar:

    más dedos  ->  menos resistencia serie, pero más superficie tapada
    menos dedos ->  más luz entra, pero cuesta más sacar la corriente

[EXTERNO] Este modelo no aparece en las Unidades 2 ni 3 del curso. Se usa la
formulación estándar de la ingeniería fotovoltaica, con dos contribuciones:

  Resistencia del emisor. La corriente fotogenerada entra al emisor repartida
  uniformemente entre dos dedos y viaja lateralmente hasta el más cercano. El
  promedio de esa resistencia distribuida da rho_cuadro * S^2 / 12, donde S es
  la separación entre dedos.

  Resistencia de los dedos. Cada dedo va recogiendo corriente a lo largo de su
  recorrido, así que la corriente que transporta crece hacia la barra colectora.
  El promedio da rho * L^2 * S / (3 * ancho * espesor).

Ambas caen al agregar dedos —la del emisor como 1/N^2 y la de los dedos como
1/N— mientras el sombreado crece como N. Por eso existe un óptimo.
"""

from dataclasses import dataclass

import constants as C


@dataclass
class MallaFrontal:
    n_dedos: int
    ancho_dedo_cm: float
    separacion_cm: float
    fraccion_sombra: float       # adimensional
    r_emisor: float              # ohm*cm2
    r_dedos: float               # ohm*cm2

    @property
    def r_serie(self) -> float:
        """Resistencia serie total aportada por la malla, en ohm*cm2."""
        return self.r_emisor + self.r_dedos


def malla(n_dedos, ancho_dedo_cm, rho_cuadro=C.RHO_CUADRO_EMISOR,
          factor_separacion=1.0):
    """
    Resuelve la geometría y la resistencia de la malla frontal.

    La fracción de sombra es simplemente el área que tapan los dedos dividida por
    el área de la celda. No se incluye el sombreado de las barras colectoras, para
    que duplicar el ancho de los dedos duplique exactamente la sombra: así la
    verificación V7 mide lo que dice medir.

    `factor_separacion` alarga la distancia que la corriente debe recorrer sin
    cambiar el sombreado. Sirve para modelar dedos interrumpidos: el metal sigue
    ahí tapando la luz, pero ya no conduce, así que la corriente tiene que llegar
    hasta el siguiente dedo intacto. Como la resistencia del emisor crece con el
    cuadrado de esa distancia, romper varios dedos seguidos la dispara.
    """
    n_dedos = max(int(n_dedos), 1)
    separacion = C.LADO_CELDA / n_dedos
    separacion_efectiva = separacion * max(factor_separacion, 1.0)
    largo_efectivo = C.LADO_CELDA / (2.0 * C.N_BARRAS_COLECTORAS)

    fraccion_sombra = n_dedos * ancho_dedo_cm / C.LADO_CELDA

    r_emisor = rho_cuadro * separacion_efectiva ** 2 / 12.0
    r_dedos = (C.RHO_PLATA_SERIGRAFIA * largo_efectivo ** 2 * separacion_efectiva
               / (3.0 * ancho_dedo_cm * C.ESPESOR_DEDO))

    return MallaFrontal(
        n_dedos=n_dedos, ancho_dedo_cm=ancho_dedo_cm, separacion_cm=separacion,
        fraccion_sombra=min(fraccion_sombra, 0.95),
        r_emisor=r_emisor, r_dedos=r_dedos,
    )


def barrido_numero_de_dedos(n_min, n_max, ancho_dedo_cm, paso=1):
    """Recorre el número de dedos para dibujar el compromiso sombra-resistencia."""
    valores = list(range(int(n_min), int(n_max) + 1, paso))
    mallas = [malla(n, ancho_dedo_cm) for n in valores]
    return valores, mallas
