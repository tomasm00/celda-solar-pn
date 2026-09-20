"""
Monitor en vivo: vigila que la configuración actual siga siendo física.

Las verificaciones de `checks.py` son una certificación: corren siempre sobre la
celda asignada por la semilla, y respaldan las cifras que se reportan. Este módulo
hace otro trabajo. Corre sobre lo que el usuario tiene en pantalla, con los
parámetros que acaba de mover, y responde a una pregunta distinta: ¿lo que se está
mostrando ahora sigue teniendo sentido?

No recalcula nada. Cada pestaña publica en un registro común los objetos que ya
resolvió, y el monitor evalúa sobre ellos. Por eso puede correr en cada movimiento
de un control sin costo apreciable.

Tres estados posibles:

  EN ORDEN  el invariante se cumple.
  AVISO     el modelo resuelve bien, pero lo que se pidió no es físicamente
            posible o se sale de un supuesto del curso. Los números siguen
            saliendo; lo que cambia es cuánto hay que creerles.
  FALLA     se rompió un invariante que el modelo tiene que cumplir para
            cualquier combinación de parámetros. Es un error de cálculo, no de
            física, y los resultados de la pestaña no son confiables.
"""

from dataclasses import dataclass

import numpy as np

from physics.collection import probabilidad_coleccion
from physics.material import vida_intrinseca
from physics.optics import balance_fotones
from units import cm_a_um

EN_ORDEN = "EN ORDEN"
AVISO = "AVISO"
FALLA = "FALLA"


@dataclass
class Vigilancia:
    codigo: str
    pestana: str
    nombre: str
    estado: str
    medido: str
    criterio: str
    mensaje: str


def _estado(cumple, si_no_cumple):
    return EN_ORDEN if cumple else si_no_cumple


def _coma(x, cifras=3):
    return f"{x:.{cifras}g}".replace(".", ",")


def _fmt_tiempo(t_s):
    if t_s >= 1e-3:
        return f"{_coma(t_s * 1e3)} ms"
    if t_s >= 1e-6:
        return f"{_coma(t_s * 1e6)} µs"
    return f"{_coma(t_s * 1e9)} ns"


_SUPERINDICE = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def _fmt_concentracion(n):
    exponente = int(np.floor(np.log10(n)))
    mantisa = n / 10 ** exponente
    base = f"10{str(exponente).translate(_SUPERINDICE)}"
    texto = base if abs(mantisa - 1) < 1e-9 else f"{_coma(mantisa, 2)}×{base}"
    return texto + " cm⁻³"


def _fmt_veces(x):
    return f"{x:,.0f}".replace(",", " ") if x >= 10 else _coma(x, 2)


# ---------------------------------------------------------------------------
# Pestaña 1 · absorción, generación y destino de los pares
# ---------------------------------------------------------------------------

def vigilar_absorcion(r):
    """
    Invariantes de la Pestaña 1 sobre el resultado que ella misma publicó.

    `r` trae: campo, union, tr, destinos, reparto, estado (parámetros).
    """
    campo, union, tr, destinos, reparto = r["campo"], r["union"], r["tr"], r["destinos"], r["reparto"]
    tau_n, tau_p = r["tau_n_s"], r["tau_p_s"]
    na, nd = r["NA"], r["ND"]
    salida = []

    # V1 en vivo
    balance = balance_fotones(campo)
    error = float(np.max(np.abs(balance["suma"] - 1.0)))
    salida.append(Vigilancia(
        "M-01", "1", "Balance de fotones de Beer-Lambert",
        _estado(error <= 0.01, FALLA), f"{100 * error:.4f} %", "error ≤ 1 %",
        "Lo reflejado, lo absorbido y lo que deja la celda suman el 100 % en cada color."
        if error <= 0.01 else
        "La luz no se conserva: la grilla no está resolviendo la absorción con estos parámetros.",
    ))

    # C-T9 en vivo
    error = float(np.max(np.abs(reparto.suma_espectral - 1.0)))
    salida.append(Vigilancia(
        "M-02", "1", "Suma de todos los destinos del fotón",
        _estado(error <= 1e-3, FALLA), f"{100 * error:.4f} %", "error ≤ 0,1 %",
        "Cada fotón termina en uno y solo uno de los diez destinos posibles."
        if error <= 1e-3 else
        "El reparto por destino no cierra: hay fotones contados dos veces o perdidos.",
    ))

    # Colección acotada antes del recorte (C-T1 en vivo)
    fc_crudo = probabilidad_coleccion(campo.x_cm, union, campo.W_cm, tr, recortar=False)
    exceso = max(float(np.max(fc_crudo)) - 1.0, -float(np.min(fc_crudo)), 0.0)
    salida.append(Vigilancia(
        "M-03", "1", "Rango de la probabilidad de colección",
        _estado(exceso <= 1e-9, FALLA), f"{exceso:.1e}", "fuera de rango ≤ 1e-9",
        "Las fórmulas del enunciado entregan una probabilidad válida en toda la celda."
        if exceso <= 1e-9 else
        "La colección se sale de [0, 1] antes del recorte: error de fórmula o de signo.",
    ))

    # Colección unitaria en los bordes (C-T2 en vivo)
    i_n = int(np.argmin(np.abs(campo.x_cm - union.x_n)))
    i_p = int(np.argmin(np.abs(campo.x_cm - union.x_p)))
    peor = max(abs(destinos.fc[i_n] - 1.0), abs(destinos.fc[i_p] - 1.0))
    salida.append(Vigilancia(
        "M-04", "1", "Colección en los bordes de la zona de depleción",
        _estado(peor <= 1e-9, FALLA), f"{peor:.1e}", "desvío ≤ 1e-9",
        "Las tres ramas del modelo de colección empalman en los bordes de la zona."
        if peor <= 1e-9 else
        "Las ramas del modelo no empalman: falta un nodo de grilla en el borde.",
    ))

    # Tres destinos del par suman uno
    suma = destinos.fc + destinos.p_superficie + destinos.p_volumen
    error = float(np.max(np.abs(suma - 1.0)))
    salida.append(Vigilancia(
        "M-05", "1", "Suma de los tres destinos de un par",
        _estado(error <= 1e-9, FALLA), f"{error:.1e}", "desvío ≤ 1e-9",
        "Cada par nacido llega a la juntura, muere en una superficie o se recombina "
        "en el volumen; no hay otra salida." if error <= 1e-9 else
        "Las probabilidades de destino no completan uno: alguna salió negativa.",
    ))

    # V5 en vivo
    eqe = sum(reparto.espectral[c] for c in ("emisor_colectados", "deplecion", "base_colectados"))
    holgura = float(np.min((1.0 - campo.R) - eqe))
    salida.append(Vigilancia(
        "M-06", "1", "Eficiencia cuántica frente a la reflexión",
        _estado(holgura >= -1e-9, FALLA), f"holgura mínima {_coma(holgura)}", "EQE ≤ 1 − R",
        "Ningún fotón reflejado produce corriente." if holgura >= -1e-9 else
        "Hay colores con más corriente que fotones que entraron: error de cálculo.",
    ))

    # Grilla
    paso = float(campo.x_cm[1] - campo.x_cm[0])
    minimo = float(1.0 / np.max(campo.alpha))
    salida.append(Vigilancia(
        "M-07", "1", "Resolución de la grilla cerca de la superficie",
        _estado(paso <= 0.1 * minimo, FALLA),
        f"{_coma(cm_a_um(paso) * 1e3)} nm contra {_coma(cm_a_um(minimo) * 1e3)} nm",
        "primer paso ≤ 1/10 del menor 1/α",
        "El primer paso de la grilla es mucho más fino que la profundidad a la que muere "
        "el ultravioleta." if paso <= 0.1 * minimo else
        "La grilla es demasiado gruesa cerca de la superficie para el ultravioleta.",
    ))

    # Geometría de la juntura
    salida.append(Vigilancia(
        "M-08", "1", "Zona de depleción dentro del emisor",
        EN_ORDEN if not union.aviso else AVISO,
        f"{_coma(cm_a_um(union.W_dep))} µm de zona en {_coma(cm_a_um(union.x_j))} µm de emisor",
        "reparto simétrico del enunciado representable",
        "El reparto simétrico del enunciado deja los dos bordes dentro de la celda."
        if not union.aviso else union.aviso,
    ))

    # Supuesto de U3, lámina 15: zona mucho más angosta que las longitudes de difusión
    menor_L = min(tr.L_p, tr.L_n)
    razon = union.W_dep / menor_L
    salida.append(Vigilancia(
        "M-09", "1", "Ancho de la zona de depleción frente a la difusión",
        _estado(razon <= 0.1, AVISO), f"{_coma(razon)} veces la menor longitud de difusión",
        "ancho ≤ 1/10 de L (U3, lámina 15)",
        "Se cumple el supuesto con que el curso da colección unitaria en la zona."
        if razon <= 0.1 else
        "La zona de depleción es comparable a la longitud de difusión: el supuesto de "
        "colección unitaria dentro de ella deja de estar justificado.",
    ))

    # Vidas medias físicamente posibles
    for codigo, region, tau, dopaje, simbolo in (("M-10", "emisor", tau_p, nd, "τ_p"),
                                                 ("M-11", "base", tau_n, na, "τ_n")):
        vida = vida_intrinseca(dopaje)
        posible = tau <= vida.limite
        salida.append(Vigilancia(
            codigo, "1", f"Vida media del {region} frente a su techo intrínseco",
            _estado(posible, AVISO),
            f"{simbolo} = {_fmt_tiempo(tau)} · techo {_fmt_tiempo(vida.limite)}",
            "τ ≤ techo radiativo + Auger",
            (f"Con {_fmt_concentracion(dopaje)}, la recombinación radiativa y la de Auger "
             f"permitirían hasta {_fmt_tiempo(vida.limite)}; el valor elegido es posible.")
            if posible else
            (f"Con {_fmt_concentracion(dopaje)} ni un cristal perfecto supera "
             f"{_fmt_tiempo(vida.limite)}, porque la recombinación de Auger lo impide. El valor "
             f"elegido es {_fmt_veces(tau / vida.limite)} veces mayor, así que la colección en el "
             f"{region} está sobreestimada. El modelo no incluye la recombinación radiativa ni la de "
             f"Auger: es una limitación declarada (D-33)."),
        ))

    return salida


# ---------------------------------------------------------------------------
# Pestaña 2 · eficiencia cuántica de la celda y de sus sectores
# ---------------------------------------------------------------------------

def vigilar_eqe(r):
    """
    Invariantes de la Pestaña 2 sobre lo que ella publicó.

    `r` trae: campo, eqe, iqe, mapa (IQE local al color del ensayo), i_lam,
    sectores, NA, iqe_por_tau (curvas de la familia de vidas medias).
    """
    campo, iqe, mapa, i = r["campo"], r["iqe"], r["mapa"], r["i_lam"]
    lam = float(campo.lambda_nm[i])
    salida = []

    # C-T7 en vivo: el mapa promediado es la curva de la celda
    error = abs(float(np.mean(mapa)) - float(iqe[i]))
    salida.append(Vigilancia(
        "M-21", "2", "Promedio del mapa frente a la eficiencia de la celda",
        _estado(error <= 1e-9, FALLA),
        f"{_coma(100 * float(np.mean(mapa)), 6)} % y {_coma(100 * float(iqe[i]), 6)} % a {lam:.0f} nm",
        "diferencia ≤ 1e-9",
        "El promedio por área de los sectores reproduce exactamente la curva de la celda: la "
        "celda es una sola, no 64 celdas separadas." if error <= 1e-9 else
        "El mapa y la curva no salen de los mismos sectores: se están tratando como celdas distintas.",
    ))

    # V5 local: ningún sector supera la cota
    peor = float(np.max(mapa))
    salida.append(Vigilancia(
        "M-22", "2", "Eficiencia interna local de cada sector",
        _estado(peor <= 1.0 + 1e-9, FALLA), f"máximo {_coma(100 * peor, 3)} %", "IQE local ≤ 100 %",
        "Ningún sector entrega más pares que fotones entraron." if peor <= 1.0 + 1e-9 else
        "Un sector entrega más pares que fotones entraron: error de cálculo.",
    ))

    # Vidas medias locales físicamente posibles
    vida = vida_intrinseca(r["NA"])
    tau_max = float(np.max(r["sectores"].tau_n_s))
    posible = tau_max <= vida.limite
    salida.append(Vigilancia(
        "M-23", "2", "Vidas medias locales de la base frente a su techo intrínseco",
        _estado(posible, AVISO),
        f"sector más largo {_fmt_tiempo(tau_max)} · techo {_fmt_tiempo(vida.limite)}",
        "τ local ≤ techo radiativo + Auger",
        "Todos los sectores tienen una vida media posible para el dopaje de la base." if posible else
        (f"Hay sectores con vidas medias que ningún silicio con {_fmt_concentracion(r['NA'])} puede "
         f"tener: la variación de fabricación los llevó por encima del techo que impone Auger."),
    ))

    # Lámina 30 de la Unidad 3: el azul no se entera del volumen
    i450 = int(np.argmin(np.abs(campo.lambda_nm - 450.0)))
    curvas = np.array(r["iqe_por_tau"])
    separacion = float(100 * (curvas[:, i450].max() - curvas[:, i450].min()))
    salida.append(Vigilancia(
        "M-24", "2", "La respuesta en el azul frente a la vida media de la base",
        _estado(separacion <= 1.0, AVISO),
        f"cambia {_coma(separacion, 2)} puntos a 450 nm", "≤ 1 punto (U3, lámina 30)",
        "El azul se absorbe en el emisor y no depende del volumen de la base, como muestra la "
        "lámina 30 de la Unidad 3." if separacion <= 1.0 else
        "Con esta geometría el azul alcanza la base y también depende de su vida media: la "
        "respuesta en el azul ya no informa solo sobre el emisor y la superficie frontal.",
    ))

    # La eficiencia por fotón absorbido nunca supera 1 (D-43)
    if "iqe_abs" in r:
        tope = float(np.max(r["iqe_abs"]))
        k = int(np.argmax(r["iqe_abs"]))
        salida.append(Vigilancia(
            "M-26", "2", "Eficiencia por fotón absorbido",
            _estado(tope <= 1.0 + 1e-6, FALLA),
            f"máximo {_coma(100 * tope, 4)} % a {float(campo.lambda_nm[k]):.0f} nm", "≤ 100 %",
            "Ningún color entrega más pares colectados que fotones absorbió el silicio." if tope <= 1.0 + 1e-6 else
            "La curva por fotón absorbido supera el 100 %: el divisor no cuenta toda la luz absorbida, "
            "por ejemplo la que devuelve el reflector.",
        ))
    return salida


def vigilar_fallas(r):
    """
    Invariantes de la Pestaña 4 sobre la malla fina y el camino eléctrico.

    `r` trae lo que publicó la pestaña: la curva con fallas y sin ellas, las áreas
    dañadas, el error de la identidad por bloques y la calibración de la
    resistencia de camino.
    """
    salida = []

    error = float(r["error_bloques"])
    salida.append(Vigilancia(
        "M-40", "4", "La malla fina describe la misma celda que la Pestaña 2",
        _estado(error <= 1e-9, FALLA),
        f"diferencia máxima {_coma(100 * error, 3)} % entre bloques",
        "media geométrica de cada bloque = sector de 8 × 8",
        "Cada bloque de la malla fina promedia exactamente el sector que usa la Pestaña 2: "
        "las dos pestañas describen la misma celda." if error <= 1e-9 else
        "La malla fina y la de 8 × 8 ya no describen la misma celda.",
    ))

    calculada, analitica = float(r["r_calculada"]), float(r["r_analitica"])
    desvio = abs(calculada / analitica - 1.0) if analitica > 0 else 0.0
    salida.append(Vigilancia(
        "M-41", "4", "El camino eléctrico reproduce la resistencia de la malla",
        _estado(desvio <= 0.02, AVISO),
        f"{_coma(calculada, 4)} frente a {_coma(analitica, 4)} Ω·cm²", "dentro de 2 %",
        "Sin grieta, seguir el camino de la corriente da la misma resistencia serie que la "
        "fórmula analítica de la malla: el modelo de caminos está calibrado." if desvio <= 0.02
        else "El camino eléctrico ya no reproduce la resistencia de la malla sana.",
    ))
    return salida


# ---------------------------------------------------------------------------
# Coherencia entre pestañas
# ---------------------------------------------------------------------------

def vigilar_coherencia(bus):
    salida = []
    if "absorcion" in bus and "curva_iv" in bus:
        j1 = bus["absorcion"]["j_fotogenerada"]
        j3 = bus["curva_iv"]["j_l"]
        error = abs(j1 - j3) / max(abs(j3), 1e-30)
        salida.append(Vigilancia(
            "M-20", "1 y 3", "Corriente fotogenerada de las Pestañas 1 y 3",
            _estado(error <= 1e-6, FALLA),
            f"{_coma(1e3 * j1, 6)} y {_coma(1e3 * j3, 6)} mA/cm²", "diferencia ≤ 1 ppm",
            "El balance de fotones de la Pestaña 1 y la corriente que alimenta la curva "
            "I-V son el mismo número por dos caminos." if error <= 1e-6 else
            "Las dos pestañas describen celdas distintas: algún parámetro no llega a una de ellas.",
        ))
    if "absorcion" in bus and "eqe" in bus:
        j1 = bus["absorcion"]["j_fotogenerada"]
        j2 = bus["eqe"]["j_con_malla"]
        error = abs(j1 - j2) / max(abs(j1), 1e-30)
        salida.append(Vigilancia(
            "M-25", "1 y 2", "Corriente de la curva de eficiencia cuántica y del balance de fotones",
            _estado(error <= 1e-6, FALLA),
            f"{_coma(1e3 * j2, 6)} y {_coma(1e3 * j1, 6)} mA/cm²", "diferencia ≤ 1 ppm",
            "Integrar la eficiencia cuántica con el espectro da la misma corriente que el balance "
            "de fotones de la Pestaña 1." if error <= 1e-6 else
            "La curva de la Pestaña 2 y el balance de la Pestaña 1 no describen la misma celda.",
        ))
    return salida


def vigilar_defectos_y_curva(bus):
    """Las Pestañas 3 y 4 tienen que dar la misma celda cuando no hay fallas."""
    if "defectos" not in bus or "curva_iv" not in bus:
        return []
    j3 = bus["curva_iv"]["j_l"]
    j4 = bus["defectos"]["p_sana"]["j_sc"]
    error = abs(j4 - j3) / max(abs(j3), 1e-30)
    return [Vigilancia(
        "M-42", "3 y 4", "La celda sin fallas, resuelta por las dos pestañas",
        _estado(error <= 5e-3, FALLA),
        f"{_coma(1e3 * j4, 6)} y {_coma(1e3 * j3, 6)} mA/cm²", "diferencia ≤ 0,5 %",
        "El motor de sectores en paralelo de la Pestaña 4 reproduce la celda de la Pestaña 3."
        if error <= 5e-3 else
        "Las dos pestañas dejaron de describir la misma celda sin fallas.",
    )]


def evaluar(bus):
    """Todas las vigilancias disponibles con lo que las pestañas publicaron."""
    resultados = []
    if "absorcion" in bus:
        resultados += vigilar_absorcion(bus["absorcion"])
    if "eqe" in bus:
        resultados += vigilar_eqe(bus["eqe"])
    if "defectos" in bus:
        resultados += vigilar_fallas(bus["defectos"])
    resultados += vigilar_coherencia(bus)
    resultados += vigilar_defectos_y_curva(bus)
    return resultados
