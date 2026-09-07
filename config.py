"""
Semilla, parametros asignados y estado inicial de la aplicacion.

La semilla S define la fila de la Tabla A.1 del Anexo A, cuyos valores son los
que deben aparecer como estado inicial de la app y los que usa la pestaña de
Validacion (enunciado, seccion 1.1).
"""

# ---------------------------------------------------------------------------
# Semilla
# ---------------------------------------------------------------------------

# S = (suma de los ultimos tres digitos del RUT, sin digito verificador, de todos
# los integrantes) mod 10, segun la seccion 1.1 del enunciado. Los digitos de
# origen no se publican; el valor resultante si, porque es lo que fija la fila de
# la Tabla A.1 y debe quedar visible en la aplicacion.
SEMILLA_S = 6

# ---------------------------------------------------------------------------
# Tabla A.1 completa (Anexo A del enunciado)
#   NA [1/cm3] | ND [1/cm3] | espesor [um] | tau_SRH [us] | S_frontal [cm/s] | T [C]
# ---------------------------------------------------------------------------

TABLA_A1 = {
    0: dict(NA=1e16,   ND=1e19,   espesor_um=180, tau_srh_us=100, s_frontal=1e3, t_operacion_c=25),
    1: dict(NA=3e15,   ND=5e19,   espesor_um=160, tau_srh_us=200, s_frontal=5e2, t_operacion_c=35),
    2: dict(NA=5e16,   ND=1e20,   espesor_um=200, tau_srh_us=50,  s_frontal=1e4, t_operacion_c=45),
    3: dict(NA=1e15,   ND=2e19,   espesor_um=150, tau_srh_us=500, s_frontal=1e2, t_operacion_c=25),
    4: dict(NA=2e16,   ND=8e19,   espesor_um=120, tau_srh_us=80,  s_frontal=5e3, t_operacion_c=55),
    5: dict(NA=8e15,   ND=3e19,   espesor_um=250, tau_srh_us=150, s_frontal=2e3, t_operacion_c=35),
    6: dict(NA=4e16,   ND=6e19,   espesor_um=100, tau_srh_us=30,  s_frontal=2e4, t_operacion_c=45),
    7: dict(NA=6e15,   ND=1.5e19, espesor_um=220, tau_srh_us=300, s_frontal=3e2, t_operacion_c=25),
    8: dict(NA=1.5e16, ND=4e19,   espesor_um=140, tau_srh_us=120, s_frontal=8e3, t_operacion_c=55),
    9: dict(NA=2.5e15, ND=7e19,   espesor_um=300, tau_srh_us=250, s_frontal=6e2, t_operacion_c=35),
}

PARAMETROS_SEMILLA = TABLA_A1[SEMILLA_S]

# El Problema 2.2 no usa el espesor de la Tabla A.1: el enunciado fija la
# geometria de la celda (emisor ~5 um sobre base ~100 um) y deja el espesor
# como control del usuario entre 20 y 300 um (Anexo A, nota final).
PARAMETROS_USADOS_2_2 = ("NA", "ND", "tau_srh_us", "s_frontal", "t_operacion_c")

# ---------------------------------------------------------------------------
# Estado inicial de la aplicacion
# ---------------------------------------------------------------------------

ESTADO_INICIAL = {
    # Dopajes y temperatura: asignados por la semilla
    "NA": PARAMETROS_SEMILLA["NA"],                       # 1/cm3   base tipo p
    "ND": PARAMETROS_SEMILLA["ND"],                       # 1/cm3   emisor tipo n
    "T_c": PARAMETROS_SEMILLA["t_operacion_c"],           # C       temperatura de operacion
    "tau_n_us": PARAMETROS_SEMILLA["tau_srh_us"],         # us      vida del minoritario en la base
    "S_f": PARAMETROS_SEMILLA["s_frontal"],               # cm/s    recombinacion superficial frontal

    # Geometria: fijada por el enunciado, ajustable por el usuario
    "d_n_um": 5.0,        # um    espesor del emisor        (rango 0.2 - 10)
    "W_p_um": 100.0,      # um    espesor de la base        (rango 20 - 300)

    # Recombinacion no asignada por la semilla
    "tau_p_us": 1.0,      # us    vida del minoritario en el emisor (rango 0.1 - 1000)
    "S_r": 1.0e3,         # cm/s  recombinacion superficial trasera (rango 10 - 1e6)

    # Optica
    "lambda_nm": 450.0,        # nm   color mostrado en la Pestaña 1
    "reflector_trasero": False,  # DECISION D-06: apagado por defecto, para que la
                                 # eficiencia cuantica sea la formula de un solo
                                 # paso del enunciado y las validaciones corran ahi.

    # Electrico
    "irradiancia_soles": 1.0,   # soles  (rango 0.1 - 1.5)
    "R_s": 0.5,                 # ohm*cm2  resistencia serie
    "R_p": 1000.0,              # ohm*cm2  resistencia paralelo
    "n_idealidad": 1.0,         # adimensional
    "n_dedos": 60,              # numero de dedos de plata
    "ancho_dedo_um": 80.0,      # um  ancho de cada dedo

    # Parametros del material que el Anexo B fija. Se exponen como controles
    # avanzados para poder explorar su efecto, pero su valor por defecto es el
    # del curso (decision D-09).
    "mu_n": 1200.0,             # cm2/(V*s)  movilidad de electrones en la base
    "mu_p": 60.0,               # cm2/(V*s)  movilidad de huecos en el emisor
}

# ---------------------------------------------------------------------------
# Rangos de los controles (enunciado, Problema 2.2)
# ---------------------------------------------------------------------------

RANGOS = {
    "lambda_nm": (300.0, 1200.0),
    "d_n_um": (0.2, 10.0),
    "W_p_um": (20.0, 300.0),
    "S_f": (10.0, 1e6),
    "S_r": (10.0, 1e6),
    "tau_n_us": (0.1, 1000.0),
    "tau_p_us": (0.1, 1000.0),
    "irradiancia_soles": (0.1, 1.5),
    "T_c": (-15.0, 75.0),
    "R_s": (0.0, 10.0),
    "R_p": (10.0, 1e5),
    "n_idealidad": (1.0, 2.0),
    "n_dedos": (10, 200),
    "ancho_dedo_um": (20.0, 300.0),
    "mu_n": (200.0, 1500.0),
    "mu_p": (20.0, 500.0),
}

# El enunciado fija 15-75 C para los controles de la Pestaña 3 y para la
# verificacion V6. El deslizador admite temperaturas mas bajas para poder
# explorar operacion en clima frio, pero V6 barre siempre este rango.
T_RANGO_V6_C = (15.0, 75.0)

# Grilla de sectores de las Pestañas 2 y 4 (enunciado: al menos 8x8)
N_SECTORES = 8
