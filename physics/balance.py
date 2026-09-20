"""
A dónde va la energía del sol, desde que llega hasta que sale por los terminales.

El reparto se hace en potencia, en mW/cm², con una regla declarada: **cada par que
llega a la juntura vale la energía de la banda prohibida**, y todo lo que el fotón
traía de más ya se contó como termalización. Con esa convención, cada fotón que se
pierde —tapado por la malla, reflejado, no absorbido o recombinado— cuesta
exactamente la banda prohibida por su carga, y las pérdidas eléctricas se miden
sobre lo que sobrevive.

Es la contabilidad clásica del límite de eficiencia (Unidad 4), aplicada a esta
celda en lugar de a una ideal: las dos primeras pérdidas son las que impone el
silicio y no dependen del diseño, y las siguientes son las que sí.

Dos precisiones declaradas:

- El espectro se integra completo, incluidos los fotones de más de 1200 nm que el
  modelo óptico no recorre, porque su energía llega igual a la celda. Los de menos
  de 300 nm aportan menos de 0,001 mW/cm² y quedan dentro de la termalización.
- El modelo absorbe algo de luz de más de la longitud de onda de la banda
  prohibida, donde el coeficiente de absorción medido todavía no es cero. Esa
  corriente, del orden de 0,01 mA/cm², está contada en la energía que entra bajo la
  banda prohibida; su aporte a la potencia entregada aparece dentro de la etapa
  eléctrica. El balance cierra igual, porque la última pérdida se calcula como
  resto.
"""

from dataclasses import dataclass, field

import numpy as np

import constants as C
from physics.collection import CLAVES_COLECTADAS, CLAVES_OPTICAS, ETIQUETA_DESTINO

ENERGIA_FOTON_NM_EV = 1239.84


@dataclass
class Etapa:
    """Un escalón del balance: cuánta potencia se va, y por qué."""

    nombre: str
    familia: str        # fundamental | optica | recombinacion | electrica | entrega
    potencia: float     # mW/cm2
    detalle: str = ""


@dataclass
class BalanceDePotencia:
    incidente: float                 # mW/cm2 que trae el espectro
    disponible: float                # mW/cm2 que sobreviven a la termalizacion
    j_maxima: float                  # A/cm2 con los fotones sobre la banda prohibida
    lambda_banda_nm: float
    eg_v: float
    entregada: float                 # mW/cm2
    etapas: list = field(default_factory=list)

    @property
    def cierre(self) -> float:
        """Diferencia entre lo que entra y la suma de las etapas. Debe ser cero."""
        perdidas = sum(e.potencia for e in self.etapas if e.familia != "entrega")
        return self.incidente - perdidas - self.entregada

    def por_familia(self, familia) -> float:
        return sum(e.potencia for e in self.etapas if e.familia == familia)


def _integrar(x, y, mascara):
    return float(np.trapezoid(np.where(mascara, y, 0.0), x))


def balance_de_potencia(espectro, campo, reparto, fraccion_sombra, curva, eg_v, soles=1.0):
    """
    Reparte la potencia incidente en las etapas que van del sol a los terminales.

    `espectro` es el AM1.5G completo tal como viene del archivo, `campo` y
    `reparto` son los de la Pestaña 1 —de ahí salen los destinos de cada fotón— y
    `curva` es la curva I-V ya resuelta.
    """
    lam_g = ENERGIA_FOTON_NM_EV / eg_v

    lam = np.asarray(espectro["lambda_nm"], dtype=float)
    potencia_nm = np.asarray(espectro["E"], dtype=float) / 10.0 * soles   # mW/cm2 por nm
    incidente = float(np.trapezoid(potencia_nm, lam))
    bajo_la_banda = _integrar(lam, potencia_nm, lam > lam_g)

    # Corriente máxima: los fotones sobre la banda prohibida que el modelo recorre
    util = campo.lambda_nm <= lam_g
    j_maxima = C.Q * _integrar(campo.lambda_nm, campo.Nph, util)
    disponible = 1e3 * eg_v * j_maxima
    termalizacion = incidente - bajo_la_banda - disponible

    def potencia_de(clave):
        """Los mW/cm² que se lleva un destino, contando solo los fotones útiles."""
        j = C.Q * _integrar(campo.lambda_nm, campo.Nph * reparto.espectral[clave], util)
        return 1e3 * eg_v * j * (1.0 - fraccion_sombra)

    opticas = {c: potencia_de(c) for c in CLAVES_OPTICAS}
    colectada = sum(potencia_de(c) for c in CLAVES_COLECTADAS)
    recombinada = {c: potencia_de(c) for c in reparto.espectral
                   if c not in CLAVES_OPTICAS and c not in CLAVES_COLECTADAS}
    frontal = recombinada.get("emisor_superficie", 0.0)
    resto_recombinacion = sum(v for c, v in recombinada.items() if c != "emisor_superficie")

    # Lo que queda ya en la juntura se reparte entre voltaje, forma y entrega
    j_colectada = colectada / (1e3 * eg_v)
    deficit_voltaje = 1e3 * (eg_v - curva.v_oc) * j_colectada
    entregada = 1e3 * curva.p_max
    perdida_electrica = colectada - deficit_voltaje - entregada

    etapas = [
        Etapa("Bajo la banda prohibida", "fundamental", bajo_la_banda,
              f"fotones de más de {lam_g:.0f} nm: el silicio no los absorbe"),
        Etapa("Termalización", "fundamental", termalizacion,
              "de cada fotón útil solo sobrevive la energía de la banda prohibida"),
        Etapa("Malla de plata", "optica", disponible * fraccion_sombra,
              "la luz que tapan los dedos"),
        Etapa("Reflexión en la superficie", "optica", opticas.get("reflejados", 0.0),
              "sin recubrimiento antirreflejo"),
        Etapa("Luz que no se absorbe", "optica",
              sum(v for c, v in opticas.items() if c != "reflejados"),
              "la absorbe el contacto de aluminio o escapa tras rebotar"),
        Etapa("Recombinación en la superficie frontal", "recombinacion", frontal,
              ETIQUETA_DESTINO.get("emisor_superficie", "")),
        Etapa("Recombinación en el volumen y atrás", "recombinacion", resto_recombinacion,
              "pares que mueren antes de llegar a la juntura"),
        Etapa("Déficit de voltaje", "electrica", deficit_voltaje,
              f"la celda sostiene {curva.v_oc:.3f} V de un techo de {eg_v:.3f} V"),
        Etapa("Pérdida de forma y fuga", "electrica", perdida_electrica,
              "resistencia serie, resistencia paralela y la forma del diodo"),
        Etapa("Potencia entregada", "entrega", entregada,
              f"eficiencia {100 * curva.eficiencia:.2f} %"),
    ]
    return BalanceDePotencia(
        incidente=incidente, disponible=disponible, j_maxima=j_maxima,
        lambda_banda_nm=lam_g, eg_v=eg_v, entregada=entregada, etapas=etapas)
