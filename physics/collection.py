"""
Probabilidad de colección: qué fracción de los pares nacidos a cada profundidad
llega viva hasta la juntura.

Un par electrón-hueco solo sirve si alcanza la zona de depleción, donde el campo
eléctrico lo separa y lo manda a los contactos. Mientras difunde al azar compite
contra dos destinos: recombinarse en el volumen, o ser capturado por una
superficie. Estas expresiones, que el enunciado entrega ya resueltas, son la
solución de la ecuación de difusión con esas dos condiciones de borde.

Se leen así: en cada región, el cociente S·L/D compara qué tan ávida es la
superficie contra qué tan bien difunde el material. Cuando ese número es grande
la superficie gana y la colección se desploma; cuando es pequeño el material
gana y casi todo se colecta.

Convención de portador minoritario, la del enunciado:
    emisor tipo n -> huecos -> D_p, L_p, compiten contra S_f (cara frontal)
    base tipo p   -> electrones -> D_n, L_n, compiten contra S_r (cara trasera)
"""

from dataclasses import dataclass

import numpy as np

import constants as C
from physics.material import difusividad, longitud_difusion


@dataclass
class Transporte:
    """Parámetros de transporte del portador minoritario en cada región."""

    D_p: float      # cm2/s   huecos en el emisor
    L_p: float      # cm      longitud de difusión en el emisor
    S_f: float      # cm/s    recombinación en la cara frontal
    D_n: float      # cm2/s   electrones en la base
    L_n: float      # cm      longitud de difusión en la base
    S_r: float      # cm/s    recombinación en la cara trasera

    @property
    def peso_superficie_frontal(self) -> float:
        """S_f·L_p/D_p — cuánto pesa la superficie frontal frente a la difusión."""
        return self.S_f * self.L_p / self.D_p

    @property
    def peso_superficie_trasera(self) -> float:
        return self.S_r * self.L_n / self.D_n


def transporte(mu_p, tau_p_s, mu_n, tau_n_s, s_f, s_r, t_k):
    """Arma los parámetros de transporte desde movilidades, tiempos de vida y T."""
    d_p = float(difusividad(mu_p, t_k))
    d_n = float(difusividad(mu_n, t_k))
    return Transporte(
        D_p=d_p, L_p=float(longitud_difusion(d_p, tau_p_s)), S_f=float(s_f),
        D_n=d_n, L_n=float(longitud_difusion(d_n, tau_n_s)), S_r=float(s_r),
    )


def _razon_hiperbolica(a, b, k):
    """
    Calcula [cosh(a) + k·sinh(a)] / [cosh(b) + k·sinh(b)] con 0 <= a <= b.

    Escrito de forma directa, esto desborda: con una base gruesa y un tiempo de
    vida corto, b puede llegar a 16, donde el coseno hiperbólico ya vale diez
    millones, y con valores mayores se va a infinito. Aquí se saca el factor
    e^b de numerador y denominador, con lo que todos los exponentes quedan
    negativos y el cálculo es estable en todo el rango de los deslizadores.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    numerador = (1.0 + k) * np.exp(a - b) + (1.0 - k) * np.exp(-a - b)
    denominador = (1.0 + k) + (1.0 - k) * np.exp(-2.0 * b)
    return numerador / denominador


def probabilidad_coleccion(x_cm, union, W_cm, tr: Transporte, recortar=True):
    """
    Probabilidad de colección en cada punto de la grilla de profundidad.

    Adimensional, acotada entre 0 y 1. Vale exactamente 1 en ambos bordes de la
    zona de depleción y decae hacia las dos superficies.
    """
    x = np.asarray(x_cm, dtype=float)
    fc = np.ones_like(x)

    en_emisor = x <= union.x_n
    en_base = x >= union.x_p

    if np.any(en_emisor) and union.x_n > 0:
        fc[en_emisor] = _razon_hiperbolica(
            x[en_emisor] / tr.L_p, union.x_n / tr.L_p, tr.peso_superficie_frontal)

    ancho_base = W_cm - union.x_p
    if np.any(en_base) and ancho_base > 0:
        u = x[en_base] - union.x_p
        fc[en_base] = _razon_hiperbolica(
            (ancho_base - u) / tr.L_n, ancho_base / tr.L_n,
            tr.peso_superficie_trasera)

    # El recorte es una red de seguridad, no parte del modelo: las expresiones
    # deben entregar ya un valor en [0,1]. Poder pedir el valor SIN recortar es lo
    # que permite que la verificacion C-T1 compruebe algo de verdad; comprobar el
    # resultado ya recortado no puede fallar nunca (ver D-26).
    return np.clip(fc, 0.0, 1.0) if recortar else fc


def colecciones_por_sector(x_cm, union, W_cm, tr: Transporte, tau_n_s, s_f):
    """
    Probabilidad de colección de muchos sectores de una sola vez.

    Es la misma expresión de `probabilidad_coleccion`, evaluada sobre arreglos en
    lugar de un sector por llamada. Lo que cambia de un sector a otro es la vida
    media de la base —y con ella su longitud de difusión— y la recombinación de la
    superficie frontal; el emisor comparte la longitud de difusión de los huecos,
    que no depende de esos dos.

    Con 48 × 48 sectores, hacerlo en bucle costaba casi un segundo por ejecución.
    `tau_n_s` y `s_f` son arreglos de igual forma; devuelve (sectores, profundidad).
    """
    x = np.asarray(x_cm, dtype=float)
    tau = np.asarray(tau_n_s, dtype=float).ravel()
    sf = np.asarray(s_f, dtype=float).ravel()

    L_n = np.sqrt(tr.D_n * tau)
    peso_frontal = sf * tr.L_p / tr.D_p
    peso_trasero = tr.S_r * L_n / tr.D_n

    fc = np.ones((tau.size, x.size))

    en_emisor = x <= union.x_n
    if np.any(en_emisor) and union.x_n > 0:
        fc[:, en_emisor] = _razon_hiperbolica(
            x[en_emisor][None, :] / tr.L_p, union.x_n / tr.L_p, peso_frontal[:, None])

    ancho_base = W_cm - union.x_p
    en_base = x >= union.x_p
    if np.any(en_base) and ancho_base > 0:
        u = x[en_base] - union.x_p
        fc[:, en_base] = _razon_hiperbolica(
            (ancho_base - u)[None, :] / L_n[:, None], ancho_base / L_n[:, None],
            peso_trasero[:, None])

    return np.clip(fc, 0.0, 1.0)


def reparto_generacion(G, fc):
    """
    Separa la generación en la parte que se colecta y la que se recombina.

    G tiene forma (profundidad, color) y fc solo (profundidad), así que la
    probabilidad se aplica a cada color por igual: la colección depende de dónde
    nació el par, no del color del fotón que lo creó.
    """
    fc_col = np.asarray(fc)[:, None]
    return G * fc_col, G * (1.0 - fc_col)


def fraccion_colectada(x_cm, G, lambda_nm, fc):
    """Fracción del total de pares generados que termina siendo colectada."""
    colectada, _ = reparto_generacion(G, fc)
    total = np.trapezoid(np.trapezoid(G, lambda_nm, axis=1), x_cm)
    util = np.trapezoid(np.trapezoid(colectada, lambda_nm, axis=1), x_cm)
    return float(util / total) if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Los tres destinos posibles de un par: juntura, superficie o volumen
# ---------------------------------------------------------------------------

def _captura_superficial(y, H, L, k):
    """
    Probabilidad de que un par a distancia y de la superficie muera en ella.

    Es la misma ecuación de difusión que resuelve la probabilidad de colección, con
    los papeles cambiados: ahora la superficie es el destino que se cuenta y la
    juntura es un sumidero que se lleva el par antes. Con H el ancho de la región
    cuasi-neutra, L la longitud de difusión y k = S·L/D, la solución es

        k · senh((H - y)/L) / [cosh(H/L) + k · senh(H/L)]

    En palabras: vale cero en el borde de la zona de depleción, porque ahí el par
    ya fue separado, y crece hacia la superficie tanto más cuanto más ávida sea la
    superficie frente a la capacidad de difundir del material.

    Se escribe sacando el factor e^(H/L) de numerador y denominador, igual que la
    razón hiperbólica de la colección, para que no desborde con bases gruesas y
    vidas cortas. Verificada contra una solución por diferencias finitas de la
    ecuación de difusión: coincide hasta 1e-9 (ver D-34).
    """
    y = np.asarray(y, dtype=float)
    b = H / L
    numerador = k * (np.exp(-y / L) - np.exp(y / L - 2.0 * b))
    denominador = (1.0 + k) + (1.0 - k) * np.exp(-2.0 * b)
    return numerador / denominador


@dataclass
class Destinos:
    """
    Qué le pasa a un par según la profundidad a la que nació.

    En cada punto de la grilla las tres probabilidades suman exactamente uno: el
    par llega a la juntura, o muere en una superficie, o se recombina en el volumen
    antes de alcanzar ninguna de las dos. No hay cuarta posibilidad.
    """

    fc: np.ndarray             # llega a la juntura (probabilidad de colección)
    p_superficie: np.ndarray   # muere en la superficie: frontal en el emisor, trasera en la base
    p_volumen: np.ndarray      # se recombina en el volumen


def probabilidades_de_destino(x_cm, union, W_cm, tr: Transporte) -> Destinos:
    """
    Las tres probabilidades de destino en cada punto de la grilla.

    La colección es la del enunciado. La captura superficial sale de la misma
    ecuación con otras condiciones de borde, y la del volumen es lo que falta para
    completar uno. En la zona de depleción la colección vale uno y las otras dos
    cero, porque el campo separa el par antes de que pueda recombinarse.
    """
    x = np.asarray(x_cm, dtype=float)
    fc = probabilidad_coleccion(x, union, W_cm, tr)
    p_sup = np.zeros_like(x)

    en_emisor = x <= union.x_n
    if np.any(en_emisor) and union.x_n > 0:
        p_sup[en_emisor] = _captura_superficial(
            x[en_emisor], union.x_n, tr.L_p, tr.peso_superficie_frontal)

    ancho_base = W_cm - union.x_p
    en_base = x >= union.x_p
    if np.any(en_base) and ancho_base > 0:
        distancia_al_fondo = W_cm - x[en_base]
        p_sup[en_base] = _captura_superficial(
            distancia_al_fondo, ancho_base, tr.L_n, tr.peso_superficie_trasera)

    p_sup = np.clip(p_sup, 0.0, 1.0)
    p_vol = np.clip(1.0 - fc - p_sup, 0.0, 1.0)
    return Destinos(fc=fc, p_superficie=p_sup, p_volumen=p_vol)


# ---------------------------------------------------------------------------
# Reparto de los fotones incidentes entre sus destinos posibles
# ---------------------------------------------------------------------------

# Cada destino con su etiqueta y su familia. Las familias ordenan los gráficos:
# primero lo que nunca generó un par, después los pares que se pierden, y al
# final los que llegan a la juntura y producen corriente.
DESTINOS = (
    ("reflejados", "Se reflejan en la superficie", "optica"),
    ("aluminio", "Llegan al fondo y los absorbe el aluminio", "optica"),
    ("escapan", "Rebotan en el aluminio y escapan por el frente", "optica"),
    ("emisor_superficie", "Nacen en el emisor y mueren en la superficie frontal", "recombinacion"),
    ("emisor_volumen", "Nacen en el emisor y se recombinan en su volumen", "recombinacion"),
    ("base_volumen", "Nacen en la base y se recombinan en su volumen", "recombinacion"),
    ("base_superficie", "Nacen en la base y mueren en la cara trasera", "recombinacion"),
    ("emisor_colectados", "Nacen en el emisor y llegan a la juntura", "corriente"),
    ("deplecion", "Nacen en la zona de depleción y se separan de inmediato", "corriente"),
    ("base_colectados", "Nacen en la base y llegan a la juntura", "corriente"),
)

ETIQUETA_DESTINO = {clave: etiqueta for clave, etiqueta, _ in DESTINOS}
CLAVES_COLECTADAS = tuple(c for c, _, familia in DESTINOS if familia == "corriente")
CLAVES_RECOMBINADAS = tuple(c for c, _, familia in DESTINOS if familia == "recombinacion")
CLAVES_OPTICAS = tuple(c for c, _, familia in DESTINOS if familia == "optica")


@dataclass
class Reparto:
    """
    A dónde va a parar cada fotón que llega a la parte iluminada de la celda.

    `espectral` guarda, para cada destino, la fracción de los fotones de ese color
    que terminan ahí. `integrado` guarda la fracción respecto del total de fotones
    incidentes de todo el espectro. Las dos están referidas a lo que llega a la
    superficie de silicio, no a lo que entra, de modo que la reflexión es un destino
    más y no un descuento previo. La sombra de la malla de plata no está aquí: es un
    área que la luz nunca alcanza, y se descuenta aparte.
    """

    lambda_nm: np.ndarray
    espectral: dict           # clave -> (nl,) fracción de los fotones de ese color
    integrado: dict           # clave -> float, fracción del total incidente
    incidentes_cm2_s: float   # 1/(cm2 s), fotones que llegan en todo el rango

    @property
    def suma_espectral(self) -> np.ndarray:
        """Todos los destinos, sumados color por color. Tiene que valer 1."""
        return sum(self.espectral.values())

    @property
    def colectado(self) -> float:
        """Fracción de todos los fotones incidentes que termina dando corriente."""
        return sum(self.integrado[clave] for clave in CLAVES_COLECTADAS)

    def en_color(self, indice_lambda) -> dict:
        """Las fracciones de un solo color, con las mismas claves que `integrado`."""
        return {c: float(v[indice_lambda]) for c, v in self.espectral.items()}

    @property
    def j_sc(self) -> float:
        """Corriente fotogenerada, en A/cm2. Cada fotón colectado aporta una carga."""
        return C.Q * self.incidentes_cm2_s * self.colectado

    @property
    def j_maxima(self) -> float:
        """
        Corriente si cada fotón incidente del rango diera un par colectado, en A/cm2.

        Es el techo absoluto contra el que se mide todo lo demás.
        """
        return C.Q * self.incidentes_cm2_s


def reparto_por_destino(campo, destinos: Destinos, union) -> Reparto:
    """
    Reparte los fotones incidentes entre todos sus destinos posibles.

    Es el balance de fotones del módulo de óptica llevado hasta el final. Aquel se
    detenía en «reflejado, absorbido, transmitido»; éste separa lo que deja la celda
    sin generar (reflejado, absorbido por el aluminio, escapado tras rebotar), parte
    lo absorbido en las tres regiones del dispositivo y, dentro de cada una, separa
    los pares que llegan a la juntura de los que mueren en una superficie o en el
    volumen.

    La partición es exacta y no aproximada. Los tramos de integración comparten sus
    extremos —el emisor termina en el mismo nodo en que empieza la zona de
    depleción, y ésta en el mismo en que empieza la base—, así que las tres
    integrales parciales suman exactamente la integral sobre toda la celda. Por eso
    la grilla tiene que traer nodos forzados en los bordes de la zona de depleción,
    que es lo que ya hace `grilla_profundidad`.

    Los pares que nacen en la zona de depleción aparecen en un solo destino, el de
    colectados. No se impone al dibujar: se deduce de que ahí la colección vale uno
    y las probabilidades de recombinación cero. Si alguna vez dejara de ser así, la
    suma de destinos no cerraría y la verificación asociada lo detectaría.
    """
    x = np.asarray(campo.x_cm, dtype=float)
    nph = np.asarray(campo.Nph, dtype=float)

    i_n = int(np.argmin(np.abs(x - union.x_n)))
    i_p = int(np.argmin(np.abs(x - union.x_p)))
    ultimo = x.size - 1

    def tramo(desde, hasta, peso):
        """Pares nacidos en [desde, hasta] y ponderados, referidos al flujo incidente."""
        if hasta <= desde:
            return np.zeros_like(nph)
        corte = slice(desde, hasta + 1)
        g = campo.G[corte] * np.asarray(peso)[corte, None]
        return np.trapezoid(g, x[corte], axis=0) / nph

    balance = _balance_de_fotones(campo)
    fc, ps, pv = destinos.fc, destinos.p_superficie, destinos.p_volumen

    espectral = {
        "reflejados": np.asarray(campo.R, dtype=float),
        "aluminio": np.asarray(balance["aluminio"], dtype=float),
        "escapan": np.asarray(balance["escapa_frente"], dtype=float),
        "emisor_superficie": tramo(0, i_n, ps),
        "emisor_volumen": tramo(0, i_n, pv),
        "base_volumen": tramo(i_p, ultimo, pv),
        "base_superficie": tramo(i_p, ultimo, ps),
        "emisor_colectados": tramo(0, i_n, fc),
        "deplecion": tramo(i_n, i_p, fc),
        "base_colectados": tramo(i_p, ultimo, fc),
    }

    incidentes = float(np.trapezoid(nph, campo.lambda_nm))
    integrado = {
        clave: float(np.trapezoid(valor * nph, campo.lambda_nm)) / incidentes
        for clave, valor in espectral.items()
    }

    return Reparto(lambda_nm=campo.lambda_nm, espectral=espectral,
                   integrado=integrado, incidentes_cm2_s=incidentes)


def _balance_de_fotones(campo):
    """Importación diferida: óptica no depende de colección, y así sigue sin hacerlo."""
    from physics.optics import balance_fotones
    return balance_fotones(campo)
