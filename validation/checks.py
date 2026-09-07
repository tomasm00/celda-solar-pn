"""
Verificaciones de la aplicacion.

Cada verificacion devuelve el valor que calculo el modelo, el valor de referencia,
el error y un veredicto. Regla R4: el valor calculado sale siempre del modelo,
nunca esta escrito a mano. Las referencias si se almacenan como referencias.

Estado: chequeos de datos (Hito 1). Las verificaciones V1 a V7 del enunciado se
agregan a medida que su fisica pasa sus pruebas.
"""

from dataclasses import dataclass

import numpy as np

import config
import constants as C
from data.loaders import (
    constantes_opticas_silicio,
    flujo_fotones_sobre_bandgap,
    irradiancia_total,
    reflectancia_media_ponderada,
)
from units import profundidad_absorcion_um


@dataclass
class Verificacion:
    """
    Una verificacion contra un valor de referencia.

    Modos de comparacion:
      'relativo' - el calculado debe caer dentro de una banda de tolerancia
      'minimo'   - el calculado debe superar la referencia (criterio de umbral)
      'maximo'   - el calculado debe quedar por debajo (cota fisica dura)
    """

    codigo: str
    nombre: str
    calculado: float
    referencia: float
    unidad: str
    tolerancia_rel: float = 0.0     # fraccion, p.ej. 0.05 para 5%. Solo en modo relativo.
    modo: str = "relativo"
    nota: str = ""
    solo_informativo: bool = False  # no cuenta como fallo si se sale de tolerancia

    @property
    def error_rel(self) -> float:
        if self.referencia == 0:
            return float("nan")
        return (self.calculado - self.referencia) / self.referencia

    @property
    def error_pct(self) -> float:
        return 100.0 * self.error_rel

    @property
    def criterio(self) -> str:
        if self.modo == "minimo":
            return f"> {self.referencia:.4g}"
        if self.modo == "maximo":
            return f"< {self.referencia:.4g}"
        return f"± {100 * self.tolerancia_rel:.0f} %"

    @property
    def aprueba(self) -> bool:
        if self.modo == "minimo":
            return self.calculado > self.referencia
        if self.modo == "maximo":
            return self.calculado < self.referencia
        return abs(self.error_rel) <= self.tolerancia_rel

    @property
    def veredicto(self) -> str:
        if self.aprueba:
            return "APRUEBA"
        return "INFORMATIVO" if self.solo_informativo else "FALLA"


# ---------------------------------------------------------------------------
# Chequeos de datos (Hito 1)
# ---------------------------------------------------------------------------

def chequeo_irradiancia_total() -> Verificacion:
    """La integral del espectro cargado debe dar la constante solar AM1.5G."""
    return Verificacion(
        codigo="C-D1",
        nombre="Integral del espectro AM1.5G",
        calculado=irradiancia_total(),
        referencia=C.REF_AM15G_IRRADIANCE,
        unidad="W/m2",
        tolerancia_rel=0.015,
        nota="Si falla, la columna leida o las unidades son las equivocadas.",
    )


def chequeo_flujo_fotones() -> Verificacion:
    """Flujo de fotones capaces de generar un par en silicio (E > Eg)."""
    return Verificacion(
        codigo="C-D2",
        nombre="Flujo de fotones con E > 1,12 eV",
        calculado=flujo_fotones_sobre_bandgap(C.EG_300K),
        referencia=C.REF_PHOTON_FLUX_1_12EV,
        unidad="1/(cm2 s)",
        tolerancia_rel=0.025,
        nota="Verifica la conversion de irradiancia a fotones y el corte en el bandgap.",
    )


def chequeo_jsc_maxima() -> Verificacion:
    """Cota superior de corriente: un electron por cada foton sobre el bandgap."""
    flujo = flujo_fotones_sobre_bandgap(C.EG_300K)
    return Verificacion(
        codigo="C-D3",
        nombre="Densidad de corriente maxima del silicio",
        calculado=C.Q * flujo * 1e3,   # A/cm2 -> mA/cm2
        referencia=C.REF_JSC_MAX_SI,
        unidad="mA/cm2",
        tolerancia_rel=0.025,
        nota="Limite absoluto: colección perfecta de todo foton absorbible.",
    )


def _profundidad_a(lambda_nm: float) -> float:
    op = constantes_opticas_silicio()
    i = int(np.argmin(np.abs(op["lambda_nm"] - lambda_nm)))
    return float(profundidad_absorcion_um(op["alpha"][i]))


def chequeo_profundidad_450nm() -> Verificacion:
    """
    Profundidad de absorcion en el azul.

    DECISION D-04: se reporta el dato medido de Green sin ajustarlo hacia la
    referencia del enunciado. Se sabe que esta comparacion sale fuera de
    tolerancia, y por que.
    """
    return Verificacion(
        codigo="V2a",
        nombre="Profundidad de absorcion a 450 nm",
        calculado=_profundidad_a(450.0),
        referencia=C.REF_ABS_DEPTH_450NM,
        unidad="um",
        tolerancia_rel=0.30,
        solo_informativo=True,
        nota=(
            "El enunciado da 'del orden de 1 um' como referencia aproximada. El dato "
            "medido de Green (2008) entrega ~0,42 um, que es el valor fisicamente "
            "correcto. Lo que la verificacion comprueba de verdad -que el azul se "
            "absorbe dentro del emisor de 5 um- se cumple con holgura. Ver D-04."
        ),
    )


def chequeo_profundidad_1000nm() -> Verificacion:
    """Profundidad de absorcion en el infrarrojo cercano: debe superar la base."""
    return Verificacion(
        codigo="V2b",
        nombre="Profundidad de absorcion a 1000 nm",
        calculado=_profundidad_a(1000.0),
        referencia=C.REF_ABS_DEPTH_1000NM,
        unidad="um",
        modo="minimo",
        nota=(
            "El enunciado pide 'superior a 100 um', que es un umbral y no una banda: "
            "el rojo cercano al infrarrojo debe atravesar la base entera."
        ),
    )


def chequeo_reflectancia_media() -> Verificacion:
    """Reflectancia media del silicio desnudo, ponderada por flujo de fotones."""
    return Verificacion(
        codigo="C-D6",
        nombre="Reflectancia media del silicio desnudo",
        calculado=reflectancia_media_ponderada(),
        referencia=C.REF_R_BARE_SI,
        unidad="-",
        tolerancia_rel=0.20,
        nota="Ponderada por fotones AM1.5G, no por potencia (U2, lamina 34).",
    )


CHEQUEOS_DE_DATOS = (
    chequeo_irradiancia_total,
    chequeo_flujo_fotones,
    chequeo_jsc_maxima,
    chequeo_profundidad_450nm,
    chequeo_profundidad_1000nm,
    chequeo_reflectancia_media,
)


# ---------------------------------------------------------------------------
# Verificaciones del enunciado
# ---------------------------------------------------------------------------

def v1_balance_de_fotones(d_n_um=5.0, W_p_um=100.0) -> Verificacion:
    """
    V1 - Balance de fotones de Beer-Lambert.

    Reflejada + absorbida + transmitida debe dar 1 para todo color entre 300 y
    1200 nm, dentro de 1%. La fraccion absorbida se obtiene integrando la
    generacion sobre la grilla de profundidad, no con la formula cerrada, de modo
    que esta verificacion mide si la discretizacion resuelve la absorcion
    (decision D-03). Se evalua con el reflector trasero apagado, que es el caso de
    un solo paso para el que la contabilidad de tres partes esta definida (D-06).
    """
    from physics.optics import balance_fotones, campo_optico
    from units import um_a_cm

    campo = campo_optico(um_a_cm(d_n_um), um_a_cm(W_p_um), reflector=False)
    balance = balance_fotones(campo)
    peor = float(np.max(np.abs(balance["suma"] - 1.0)))
    lam_peor = float(balance["lambda_nm"][int(np.argmax(np.abs(balance["suma"] - 1.0)))])

    return Verificacion(
        codigo="V1",
        nombre="Balance de fotones de Beer-Lambert",
        calculado=1.0 + peor,
        referencia=1.0,
        unidad="-",
        tolerancia_rel=0.01,
        nota=(
            f"Peor caso en todo el rango 300-1200 nm, a {lam_peor:.0f} nm. Mide la "
            "calidad de la grilla de profundidad: el balance es exacto "
            "analiticamente, asi que toda desviacion es error de discretizacion."
        ),
    )


def _perfil_coleccion_por_defecto(recortar=True):
    """Perfil de colección con los parametros de la semilla, para los chequeos."""
    from physics.collection import probabilidad_coleccion, transporte
    from physics.material import juntura
    from physics.optics import grilla_profundidad
    from units import celsius_a_kelvin, um_a_cm

    e = config.ESTADO_INICIAL
    d_n, W_p = um_a_cm(e["d_n_um"]), um_a_cm(e["W_p_um"])
    t_k = celsius_a_kelvin(e["T_c"])
    union = juntura(d_n, e["NA"], e["ND"], t_k)
    x = grilla_profundidad(d_n, W_p, np.linspace(union.x_n, union.x_p, 12))
    tr = transporte(e["mu_p"], e["tau_p_us"] * 1e-6, e["mu_n"],
                    e["tau_n_us"] * 1e-6, e["S_f"], e["S_r"], t_k)
    return x, union, probabilidad_coleccion(x, union, d_n + W_p, tr, recortar)


def chequeo_coleccion_acotada() -> Verificacion:
    """
    La probabilidad de coleccion es una probabilidad: no puede salirse de [0,1].

    Chequeo estructural. Si falla, hay un error de formula o de signo, no un
    problema de modelo fisico.
    """
    _, _, fc = _perfil_coleccion_por_defecto(recortar=False)
    peor = max(float(np.max(fc)) - 1.0, -float(np.min(fc)), 0.0)
    return Verificacion(
        codigo="C-T1",
        nombre="Probabilidad de coleccion acotada en [0,1]",
        calculado=1.0 + peor,
        referencia=1.0,
        unidad="-",
        tolerancia_rel=1e-9,
        nota=("Chequeo estructural sobre toda la grilla, evaluado ANTES del recorte "
              "de seguridad a [0,1]. Comprobarlo despues del recorte no podria "
              "fallar nunca y no verificaria nada."),
    )


def chequeo_coleccion_unitaria_en_deplexion() -> Verificacion:
    """
    En los bordes de la zona de deplexion la coleccion vale exactamente 1.

    Ahi el campo electrico separa el par antes de que pueda recombinarse. Es el
    empalme de las tres ramas del modelo: si no da 1, o la formula esta mal, o la
    grilla no tiene un nodo en el borde.
    """
    x, union, fc = _perfil_coleccion_por_defecto()
    i_n = int(np.argmin(np.abs(x - union.x_n)))
    i_p = int(np.argmin(np.abs(x - union.x_p)))
    peor = max(abs(fc[i_n] - 1.0), abs(fc[i_p] - 1.0))
    return Verificacion(
        codigo="C-T2",
        nombre="Coleccion unitaria en los bordes de la deplexion",
        calculado=1.0 + peor,
        referencia=1.0,
        unidad="-",
        tolerancia_rel=1e-9,
        nota=("Verifica de paso que la grilla tiene nodos exactamente en los "
              "bordes de la zona de deplexion."),
    )


def _celda_por_defecto():
    """Cadena completa resuelta con los parametros de la semilla."""
    from physics.collection import probabilidad_coleccion, transporte
    from physics.material import juntura
    from physics.optics import campo_optico
    from units import celsius_a_kelvin, um_a_cm

    e = config.ESTADO_INICIAL
    d_n, W_p = um_a_cm(e["d_n_um"]), um_a_cm(e["W_p_um"])
    t_k = celsius_a_kelvin(e["T_c"])
    union = juntura(d_n, e["NA"], e["ND"], t_k)
    campo = campo_optico(d_n, W_p, e["reflector_trasero"], 1.0,
                         np.linspace(union.x_n, union.x_p, 12))
    tr = transporte(e["mu_p"], e["tau_p_us"] * 1e-6, e["mu_n"],
                    e["tau_n_us"] * 1e-6, e["S_f"], e["S_r"], t_k)
    fc = probabilidad_coleccion(campo.x_cm, union, d_n + W_p, tr)
    return campo, fc


def v5_cota_eficiencia_cuantica() -> Verificacion:
    """
    V5 - La eficiencia cuantica externa no puede superar 1 - R, para todo color.

    Ningun foton reflejado en la superficie puede generar un par: la fraccion que
    entra al material es la cota absoluta de lo que puede aprovecharse. Es una
    verificacion estructural, sin tolerancia fisica: si falla, hay un error de
    formula, no un limite del modelo.
    """
    from physics.quantum_efficiency import cota_superior, eficiencia_cuantica

    campo, fc = _celda_por_defecto()
    eqe, _ = eficiencia_cuantica(campo, fc)
    cota = cota_superior(campo)
    exceso = float(np.max(eqe - cota))
    return Verificacion(
        codigo="V5",
        nombre="Cota superior de la eficiencia cuantica",
        calculado=1.0 + max(exceso, 0.0),
        referencia=1.0,
        unidad="-",
        tolerancia_rel=1e-9,
        nota=(f"Evaluada en las {campo.lambda_nm.size} longitudes de onda del rango "
              f"300-1200 nm. Holgura minima {float(np.min(cota - eqe)):.4f}."),
    )


def c_t3_consistencia_corriente() -> Verificacion:
    """
    Consistencia interna: la corriente calculada integrando la eficiencia cuantica
    debe coincidir con la generacion total multiplicada por la fraccion colectada.

    Son dos caminos distintos por el mismo modelo. Es el ensayo previo de la
    verificacion V3 del enunciado, que en el Hito 5 comparara contra la corriente
    leida de la curva electrica.
    """
    from physics.collection import fraccion_colectada
    from physics.optics import fracciones_por_region
    from physics.quantum_efficiency import corriente_de_cortocircuito, eficiencia_cuantica

    campo, fc = _celda_por_defecto()
    eqe, _ = eficiencia_cuantica(campo, fc)
    via_eqe = corriente_de_cortocircuito(campo, eqe)
    fr = fracciones_por_region(campo)
    via_generacion = (C.Q * fr["pares_totales_cm2_s"]
                      * fraccion_colectada(campo.x_cm, campo.G, campo.lambda_nm, fc))
    return Verificacion(
        codigo="C-T3",
        nombre="Corriente por dos vias del mismo modelo",
        calculado=1e3 * via_eqe,
        referencia=1e3 * via_generacion,
        unidad="mA/cm2",
        tolerancia_rel=1e-6,
        nota="Ensayo previo de V3: ambas vias deben dar exactamente lo mismo.",
    )


def _celda_electrica(t_c=None, s_f=None, ancho_dedo_cm=None):
    """
    Cadena completa hasta la corriente fotogenerada y la de saturacion.

    Permite variar temperatura, pasivacion o geometria de la malla sin repetir el
    montaje, que es lo que necesitan V6 y V7.
    """
    from physics.collection import probabilidad_coleccion, transporte
    from physics.diode import corriente_saturacion
    from physics.front_grid import malla
    from physics.material import juntura
    from physics.optics import campo_optico
    from physics.quantum_efficiency import corriente_de_cortocircuito, eficiencia_cuantica
    from units import celsius_a_kelvin, um_a_cm

    e = config.ESTADO_INICIAL
    t_k = celsius_a_kelvin(e["T_c"] if t_c is None else t_c)
    d_n, W_p = um_a_cm(e["d_n_um"]), um_a_cm(e["W_p_um"])
    union = juntura(d_n, e["NA"], e["ND"], t_k)
    campo = campo_optico(d_n, W_p, e["reflector_trasero"], 1.0,
                         np.linspace(union.x_n, union.x_p, 12))
    tr = transporte(e["mu_p"], e["tau_p_us"] * 1e-6, e["mu_n"],
                    e["tau_n_us"] * 1e-6,
                    e["S_f"] if s_f is None else s_f, e["S_r"], t_k)
    fc = probabilidad_coleccion(campo.x_cm, union, d_n + W_p, tr)
    eqe, _ = eficiencia_cuantica(campo, fc)
    j_l = corriente_de_cortocircuito(campo, eqe)
    j0, _, _ = corriente_saturacion(e["NA"], e["ND"], tr, t_k,
                                    union=union, W_cm=d_n + W_p)
    grid = malla(e["n_dedos"],
                 (e["ancho_dedo_um"] * 1e-4) if ancho_dedo_cm is None else ancho_dedo_cm)
    return j_l, j0, grid, t_k


def v3_consistencia_optica_electrica() -> Verificacion:
    """
    V3 - La corriente calculada por la via optica y la leida de la curva electrica
    deben coincidir dentro de 5%.

    El enunciado la califica como el criterio mas importante del problema, porque
    obliga a que la optica y la electricidad sean el mismo modelo y no dos
    calculos independientes que se parecen.

    La via optica integra el flujo de fotones ponderado por la eficiencia
    cuantica; la electrica lee la corriente en cortocircuito de la curva J-V
    resuelta con la ecuacion implicita. El sombreado de la malla se aplica de
    forma identica a ambas (ver D-07).
    """
    from physics.diode import curva_iv

    e = config.ESTADO_INICIAL
    j_l, j0, grid, t_k = _celda_electrica()
    via_optica = j_l * (1.0 - grid.fraccion_sombra)
    curva = curva_iv(j0, via_optica, e["R_s"] + grid.r_serie, e["R_p"],
                     e["n_idealidad"], t_k)
    return Verificacion(
        codigo="V3",
        nombre="Corriente optica frente a la leida de la curva J-V",
        calculado=1e3 * curva.j_sc,
        referencia=1e3 * via_optica,
        unidad="mA/cm2",
        tolerancia_rel=0.05,
        nota=("Criterio mas importante del problema. La diferencia residual viene "
              "de la resistencia paralelo, que desvia una fraccion minuscula de la "
              "corriente incluso en cortocircuito."),
    )


def v4_factor_de_forma_ideal() -> Verificacion:
    """
    V4 - Con Rs -> 0, Rp -> infinito y n = 1, el factor de forma calculado debe
    coincidir con la expresion empirica del Anexo B dentro de 1%.

    Es la verificacion que detecta el error de graficar la forma explicita
    ignorando el termino Rs*J: ese atajo produce un factor de forma
    sistematicamente sobrestimado.
    """
    from physics.diode import curva_iv, factor_de_forma_ideal

    j_l, j0, grid, t_k = _celda_electrica()
    curva = curva_iv(j0, j_l * (1.0 - grid.fraccion_sombra), 0.0, 1e12, 1.0, t_k)
    return Verificacion(
        codigo="V4",
        nombre="Factor de forma ideal frente a la expresion empirica",
        calculado=curva.ff,
        referencia=factor_de_forma_ideal(curva.v_oc, t_k),
        unidad="-",
        tolerancia_rel=0.01,
        nota=(f"Evaluada con Voc = {curva.v_oc:.4f} V. Requiere afinar el punto de "
              f"maxima potencia: con una grilla de voltaje gruesa el factor de forma "
              f"sale bajo por razones puramente numericas."),
    )


def v6_coeficiente_de_temperatura() -> Verificacion:
    """
    V6 - Pendiente del voltaje de circuito abierto con la temperatura, barriendo
    de 15 a 75 C. Debe caer entre -1,8 y -2,6 mV/C.

    El signo negativo proviene enteramente de que la concentracion intrinseca
    crece exponencialmente con la temperatura, lo que dispara la corriente de
    saturacion y hunde el voltaje (ver D-08). Si se congelara la corriente de
    saturacion, la pendiente saldria positiva.
    """
    from physics.diode import curva_iv

    e = config.ESTADO_INICIAL
    temperaturas = np.linspace(*config.T_RANGO_V6_C, 13)
    voltajes = []
    for t_c in temperaturas:
        j_l, j0, grid, t_k = _celda_electrica(t_c=t_c)
        curva = curva_iv(j0, j_l * (1.0 - grid.fraccion_sombra),
                         e["R_s"] + grid.r_serie, e["R_p"], e["n_idealidad"], t_k,
                         n_puntos=160)
        voltajes.append(curva.v_oc)

    pendiente = float(np.polyfit(temperaturas, voltajes, 1)[0] * 1e3)
    centro = -2.2
    return Verificacion(
        codigo="V6",
        nombre="Coeficiente de temperatura del voltaje de circuito abierto",
        calculado=pendiente,
        referencia=centro,
        unidad="mV/C",
        tolerancia_rel=0.4 / abs(centro),   # la banda -1,8 a -2,6 en torno a -2,2
        nota=(f"Barrido de {config.T_RANGO_V6_C[0]:.0f} a {config.T_RANGO_V6_C[1]:.0f} C, "
              f"que es el rango que fija el enunciado. Voc va de {voltajes[0]:.4f} V a "
              f"{voltajes[-1]:.4f} V."),
    )


def c_t5_trampa_de_la_forma_explicita() -> Verificacion:
    """
    Comprueba que el solver resuelve la ecuacion implicita y no su forma explicita.

    V4 no puede detectarlo: el enunciado la define con Rs -> 0, y sin resistencia
    serie el termino Rs*J desaparece y las dos formas coinciden exactamente. Un
    solver que ignorara el termino aprobaria V4 igual.

    Esta verificacion evalua con resistencia serie **no nula**, que es donde la
    trampa se manifiesta, y exige que el factor de forma correcto quede por debajo
    del que da el atajo. Detectado por auditoria externa (ver D-27).
    """
    from physics.diode import curva_iv

    e = config.ESTADO_INICIAL
    j_l, j0, grid, t_k = _celda_electrica()
    rs = e["R_s"] + grid.r_serie
    jl_neto = j_l * (1.0 - grid.fraccion_sombra)
    curva = curva_iv(j0, jl_neto, rs, e["R_p"], e["n_idealidad"], t_k)

    vt_n = e["n_idealidad"] * C.KB_EV * t_k
    j_ingenua = (jl_neto - j0 * (np.exp(np.clip(curva.v / vt_n, 0, 600)) - 1)
                 - curva.v / e["R_p"])
    ff_ingenuo = float((curva.v * np.maximum(j_ingenua, 0.0)).max()
                       / (curva.v_oc * curva.j_sc))

    return Verificacion(
        codigo="C-T5",
        nombre="El solver resuelve la ecuacion implicita, no su atajo",
        calculado=curva.ff,
        referencia=ff_ingenuo,
        unidad="-",
        modo="maximo",
        nota=(f"Con Rs = {rs:.3f} ohm*cm2 el atajo sobrestima el factor de forma en "
              f"{100 * (ff_ingenuo / curva.ff - 1):.1f} %. Si ambos coincidieran, el "
              f"solver estaria ignorando la caida de voltaje sobre la resistencia."),
    )


def c_t4_voltaje_bajo_el_bandgap() -> Verificacion:
    """
    Cota fisica: el voltaje de circuito abierto no puede superar la banda prohibida.

    Cada par electron-hueco nace con a lo sumo la energia del bandgap, asi que
    ninguna celda puede entregar mas voltaje que eso. Es una cota dura, no una
    aproximacion.

    Chequeo añadido tras la prueba de esfuerzo E9, que descubrio que el modelo la
    viola cuando el factor de idealidad pasa de 1,95: n y J0 se tratan como
    parametros independientes y no lo son. Con los valores de la semilla (n = 1)
    el margen es amplio.
    """
    from physics.diode import curva_iv
    from physics.material import bandgap

    e = config.ESTADO_INICIAL
    j_l, j0, grid, t_k = _celda_electrica()
    curva = curva_iv(j0, j_l * (1.0 - grid.fraccion_sombra),
                     e["R_s"] + grid.r_serie, e["R_p"], e["n_idealidad"], t_k)
    eg = float(bandgap(t_k))
    return Verificacion(
        codigo="C-T4",
        nombre="Voltaje de circuito abierto bajo la banda prohibida",
        calculado=curva.v_oc,
        referencia=eg,
        unidad="V",
        modo="maximo",
        nota=(f"Con n = {e['n_idealidad']:.1f} el voltaje usa el "
              f"{100 * curva.v_oc / eg:.1f} % del techo. La aplicacion avisa si el "
              f"usuario entra al regimen no fisico subiendo el factor de idealidad."),
    )


def v7_efecto_del_sombreado() -> Verificacion:
    """
    V7 - Al duplicar la fraccion de sombra, la corriente debe caer en la misma
    proporcion que el area sombreada añadida, dentro de 2%.

    La caida relativa esperada no es el incremento de sombra a secas, sino ese
    incremento dividido por la fraccion que antes estaba despejada: si de cada
    100 unidades de area habia 96,9 iluminadas y se tapan 3,1 mas, se pierde
    3,1/96,9 de la corriente.
    """
    from physics.diode import curva_iv

    e = config.ESTADO_INICIAL
    ancho = e["ancho_dedo_um"] * 1e-4

    def jsc_con(ancho_dedo_cm):
        j_l, j0, grid, t_k = _celda_electrica(ancho_dedo_cm=ancho_dedo_cm)
        curva = curva_iv(j0, j_l * (1.0 - grid.fraccion_sombra),
                         e["R_s"] + grid.r_serie, e["R_p"], e["n_idealidad"], t_k)
        return curva.j_sc, grid.fraccion_sombra

    j_simple, fs_simple = jsc_con(ancho)
    j_doble, fs_doble = jsc_con(2.0 * ancho)

    caida = (j_simple - j_doble) / j_simple
    esperada = (fs_doble - fs_simple) / (1.0 - fs_simple)
    return Verificacion(
        codigo="V7",
        nombre="Caida de corriente al duplicar el sombreado",
        calculado=100 * caida,
        referencia=100 * esperada,
        unidad="%",
        tolerancia_rel=0.02,
        nota=(f"El sombreado pasa de {100 * fs_simple:.2f} % a {100 * fs_doble:.2f} %. "
              f"El residuo viene de que al ensanchar los dedos tambien baja su "
              f"resistencia, lo que afecta levemente a la curva."),
    )


def c_t6_pestanas_coherentes() -> Verificacion:
    """
    Con la celda homogenea y sin defectos, el solver por sectores y el escalar
    deben entregar el mismo voltaje de circuito abierto.

    Son dos implementaciones distintas de la misma ecuacion, asi que discrepar
    significa que una de las dos esta mal. Antes discrepaban en 2,4 mV a 45 C y en
    99 mV a -15 C, por dos errores del solver vectorizado que esta verificacion no
    habria dejado pasar (ver D-18).
    """
    from physics.collection import transporte
    from physics.diode import curva_iv
    from physics.material import juntura
    from physics.optics import campo_optico
    from physics.quantum_efficiency import (corriente_de_cortocircuito,
                                            eficiencia_cuantica, generar_sectores)
    from physics.sectors import (Defectos, armar_celda, curva_global,
                                 parametros_de_curva)
    from units import celsius_a_kelvin, um_a_cm

    e = config.ESTADO_INICIAL
    t_k = celsius_a_kelvin(e["T_c"])
    d_n, W_p = um_a_cm(e["d_n_um"]), um_a_cm(e["W_p_um"])
    W = d_n + W_p
    union = juntura(d_n, e["NA"], e["ND"], t_k)
    campo = campo_optico(d_n, W_p, e["reflector_trasero"], 1.0,
                         np.linspace(max(union.x_n, 0.0), union.x_p, 12))
    tr = transporte(e["mu_p"], e["tau_p_us"] * 1e-6, e["mu_n"],
                    e["tau_n_us"] * 1e-6, e["S_f"], e["S_r"], t_k)

    j_l, j0, grid, _ = _celda_electrica()
    escalar = curva_iv(j0, j_l * (1.0 - grid.fraccion_sombra),
                       e["R_s"] + grid.r_serie, e["R_p"], e["n_idealidad"], t_k)

    sectores = generar_sectores(config.N_SECTORES, e["tau_n_us"] * 1e-6, e["S_f"], 0.0)
    celda = armar_celda(campo, union, W, tr, sectores, Defectos(), e["n_dedos"],
                        e["ancho_dedo_um"] * 1e-4, e["R_s"], e["NA"], e["ND"], t_k)
    v, j, v_oc = curva_global(celda, e["R_p"], e["n_idealidad"], t_k)
    por_sectores = parametros_de_curva(v, j, C.IRRADIANCE_1SUN, v_oc)

    return Verificacion(
        codigo="C-T6",
        nombre="Pestanas 3 y 4 coherentes con celda homogenea",
        calculado=1e3 * por_sectores["v_oc"],
        referencia=1e3 * escalar.v_oc,
        unidad="mV",
        tolerancia_rel=1e-4,
        nota="Dos implementaciones de la misma ecuacion: discrepar es un error.",
    )


# V2 del enunciado combina dos criterios de naturaleza distinta -una banda de
# tolerancia en el azul y un umbral en el infrarrojo-, asi que se reporta como
# dos entradas: V2a y V2b, implementadas arriba.
VERIFICACIONES_ENUNCIADO = (
    v1_balance_de_fotones,
    chequeo_coleccion_acotada,
    chequeo_coleccion_unitaria_en_deplexion,
    v5_cota_eficiencia_cuantica,
    c_t3_consistencia_corriente,
    v3_consistencia_optica_electrica,
    v4_factor_de_forma_ideal,
    v6_coeficiente_de_temperatura,
    v7_efecto_del_sombreado,
    c_t4_voltaje_bajo_el_bandgap,
    c_t5_trampa_de_la_forma_explicita,
    c_t6_pestanas_coherentes,
)


def ejecutar_todas():
    """Chequeos de datos mas las verificaciones del enunciado ya implementadas."""
    return [fn() for fn in CHEQUEOS_DE_DATOS + VERIFICACIONES_ENUNCIADO]


if __name__ == "__main__":
    print(f"{'cod':<6}{'verificacion':<42}{'calculado':>14}{'referencia':>14}"
          f"{'error':>10}{'criterio':>12}  veredicto")
    print("-" * 112)
    fallas = 0
    for v in ejecutar_todas():
        if v.veredicto == "FALLA":
            fallas += 1
        cal = f"{v.calculado:.4g}"
        ref = f"{v.referencia:.4g}"
        print(f"{v.codigo:<6}{v.nombre:<42}{cal:>14}{ref:>14}"
              f"{v.error_pct:>9.1f}%{v.criterio:>12}  {v.veredicto}")
    print("-" * 112)
    print(f"fallas reales: {fallas}")
