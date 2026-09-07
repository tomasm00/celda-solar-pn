"""
Constantes físicas del proyecto. Fuente única de verdad.

Regla del enunciado (seccion 1.4): toda constante fisica se declara aqui, con su
unidad y su fuente. No se aceptan numeros arbitrarios dispersos en el codigo.

Sistema de unidades interno (ver DECISIONES.md):
  longitud de onda -> nm     |  profundidades y longitudes -> cm
  absorcion        -> 1/cm   |  concentraciones            -> 1/cm3
  tiempo de vida   -> s      |  velocidad superficial      -> cm/s
  corriente        -> A/cm2  |  temperatura                -> K
"""

# ---------------------------------------------------------------------------
# Constantes universales
# ---------------------------------------------------------------------------

Q = 1.602176634e-19          # C           carga elemental (CODATA 2018, valor exacto SI)
H_PLANCK = 6.62607015e-34    # J*s         constante de Planck (CODATA 2018, valor exacto SI)
C_LIGHT = 2.99792458e8       # m/s         velocidad de la luz en vacio (valor exacto SI)
KB_EV = 8.6173e-5            # eV/K        constante de Boltzmann (Anexo B del enunciado, U2)
KB_J = 1.380649e-23          # J/K         constante de Boltzmann (CODATA 2018, valor exacto SI)
EPS0 = 8.8541878128e-14      # F/cm        permitividad del vacio (CODATA 2018, convertida de F/m)

# ---------------------------------------------------------------------------
# Propiedades del silicio
# ---------------------------------------------------------------------------

NI_300K = 1.0e10             # 1/cm3       concentracion intrinseca a 300 K (Anexo B, U2)
EG_300K = 1.12               # eV          banda prohibida a 300 K, valor canonico (Anexo B, U4)

# Dependencia del bandgap con la temperatura. El Anexo B indica usarla solo para
# el barrido termico; a 300 K entrega 1.124 eV, consistente con EG_300K.
EG_T_A = 1.206               # eV          termino constante (Anexo B, U4)
EG_T_B = 0.000273            # eV/K        pendiente (Anexo B, U4)

# Permitividad relativa del silicio. DECISION D-01: las laminas 20-21 de la U2
# escriben la ecuacion de Poisson con EPS0, pero dentro del cristal corresponde
# la permitividad del material. Ver DECISIONES.md.
EPS_R_SI = 11.7              # adimensional  permitividad relativa del Si [EXTERNO]
EPS_SI = EPS_R_SI * EPS0     # F/cm          permitividad absoluta del silicio

# Movilidades de portadores minoritarios. DECISION D-09: valores fijos del Anexo B,
# sin modelo de dependencia con el dopaje, por fidelidad al curso.
MU_N = 1200.0                # cm2/(V*s)   electrones en base tipo p, NA ~ 1e16 (Anexo B, U3)
MU_P = 60.0                  # cm2/(V*s)   huecos en emisor tipo n+, ND ~ 1e19-1e20 (Anexo B, U3)

# ---------------------------------------------------------------------------
# Condiciones de referencia
# ---------------------------------------------------------------------------

IRRADIANCE_1SUN = 0.100      # W/cm2       AM1.5G de referencia, 100 mW/cm2 (Anexo B, U3)

# Reflectancia interna del contacto trasero de aluminio. El enunciado exige
# modelar el reflector pero no da un valor. [EXTERNO] Valor tipico de un contacto
# de Al sobre Si en el infrarrojo cercano; se declara como supuesto en DECISIONES.md.
R_CONTACTO_AL = 0.90         # adimensional
T_STC = 298.15               # K           25 C, condicion estandar de medicion (Anexo B, U3)
T_REF_300K = 300.0           # K           temperatura de los valores de referencia del Anexo B

# ---------------------------------------------------------------------------
# Valores de referencia para la pestaña de Validacion (Anexo B del enunciado).
# Se almacenan como REFERENCIA, nunca como resultado: el valor que la aplicacion
# reporta debe salir siempre del modelo (regla R4 / rubrica 1.6a).
# ---------------------------------------------------------------------------

REF_AM15G_IRRADIANCE = 1000.0    # W/m2         integral del espectro AM1.5G
REF_PHOTON_FLUX_1_12EV = 2.72e17  # 1/(cm2*s)   flujo con E > 1.12 eV bajo AM1.5G (U4)
REF_JSC_MAX_SI = 43.5            # mA/cm2       densidad de corriente maxima para silicio (U4)
REF_R_BARE_SI = 0.30             # adimensional reflectancia media del Si desnudo bajo AM1.5G (U2)
REF_FF0 = 0.86                   # adimensional factor de forma ideal (U4)
REF_DVOC_DT = -2.3               # mV/C         coeficiente de temperatura del Voc del silicio (U4)
REF_ABS_DEPTH_450NM = 1.0        # um           profundidad de absorcion a 450 nm (V2 del enunciado)
REF_ABS_DEPTH_1000NM = 100.0     # um           cota inferior de profundidad a 1000 nm (V2)

# ---------------------------------------------------------------------------
# Malla frontal de contactos de plata.
#
# [EXTERNO] El enunciado exige modelar la malla explicitamente pero no entrega el
# modelo, y no aparece en las Unidades 2 ni 3 del curso. Se usa la formulacion
# estandar de la ingenieria fotovoltaica (M. A. Green, "Solar Cells", cap. 6),
# declarada como decision propia en DECISIONES.md.
# ---------------------------------------------------------------------------

LADO_CELDA = 15.6              # cm        oblea cuadrada estandar de la industria
N_BARRAS_COLECTORAS = 3        # -         barras que recogen a los dedos
ESPESOR_DEDO = 15e-4           # cm        15 um, tipico de serigrafia
RHO_PLATA_SERIGRAFIA = 3.0e-6  # ohm*cm    plata serigrafiada, ~2x la plata masiva
RHO_CUADRO_EMISOR = 60.0       # ohm/cuadro  resistencia de capa del emisor difundido

# ---------------------------------------------------------------------------
# Procedencia de los archivos de datos, declarada en la aplicacion
# (exigido por el enunciado, Pestaña 1 del Problema 2.2).
# ---------------------------------------------------------------------------

FUENTE_ESPECTRO = (
    "ASTM G173-03 Reference Spectra Derived from SMARTS v2.9.2, columna "
    "'Global tilt' (AM1.5G). Rango 280-4000 nm. Planilla astmg173.xls "
    "provista por el curso via Webcursos."
)

FUENTE_NK_SILICIO = (
    "M. A. Green, 'Self-consistent optical parameters of intrinsic silicon at "
    "300 K including temperature coefficients', Solar Energy Materials and "
    "Solar Cells 92 (2008) 1305-1310. Tablas de indice de refraccion n y "
    "coeficiente de extincion k. Rango 250-1450 nm, cubre 300-1200 nm sin "
    "extrapolacion."
)
