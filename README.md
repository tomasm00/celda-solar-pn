# Laboratorio virtual de caracterización de una celda p-n de silicio

Simulación interactiva de los procesos físicos de una celda solar de silicio cristalino,
desde la absorción de un fotón hasta la potencia entregada. Construida con Streamlit.

> **Aplicación en línea:** `[ pendiente: pegar aquí la URL de Streamlit Cloud ]`

**Proyecto 1 · Problema 2.2 · Celdas Solares Fotovoltaicas · Semestre 2026-2**
Semilla S = 6 · N_A = 4×10¹⁶ cm⁻³ · N_D = 6×10¹⁹ cm⁻³ · τ_SRH = 30 µs · S_frontal = 2×10⁴ cm/s · 45 °C

---

## La celda modelada

Un bloque de silicio tipo p de 100 µm que actúa como base, con una capa de silicio tipo n
de 5 µm encima que actúa como emisor. Contactos frontales de plata en forma de dedos y un
contacto trasero de aluminio. Sin recubrimiento antirreflejo ni estructura multicapa: la
óptica se resuelve con la ley de Beer-Lambert, con reflexión frontal en la interfaz
aire-silicio y un reflector metálico en la cara trasera.

## Arquitectura

Las pestañas no son cuatro programas pegados: son una sola cadena donde cada una consume lo
que la anterior produjo.

```
datos medidos ──► Pestaña 1 ──► Pestaña 2 ──► Pestaña 3 ──► Pestaña 4
                  generación    eficiencia    curva I-V     sectores
                  G(x,λ)        cuántica      Jsc Voc FF η  y defectos
                       │             │             │            │
                       └─────────────┴─────────────┴────────────┴──► Pestaña 5
                                                                     validación
```

La corriente fotogenerada de la Pestaña 3 **no es un parámetro libre**: sale de integrar la
eficiencia cuántica de la Pestaña 2, que a su vez pondera la generación de la Pestaña 1. Esa
es la condición que verifica el criterio V3 del enunciado.

### Organización del código

| Capa | Contenido |
|---|---|
| `app.py` | Solo interfaz y orquestación. **Cero física.** |
| `constants.py` | Toda constante con su unidad y su fuente. Sin números sueltos en el código. |
| `units.py` | Conversiones de unidades con nombre. Ninguna al paso dentro de un cálculo. |
| `config.py` | Semilla, Tabla A.1 del Anexo A, estado inicial y rangos de los controles. |
| `data/` | Archivos de datos medidos y sus cargadores con verificación de columnas. |
| `physics/` | El modelo. Un módulo por eslabón de la cadena. |
| `visualization/` | Construcción de figuras. No calcula física. |
| `validation/` | La certificación de 21 verificaciones sobre la celda de la semilla (`checks.py`) y el monitor físico en vivo sobre los valores actuales de los controles (`monitor.py`). |
| `ui/` | Una pestaña por módulo, más la barra lateral compartida. |

### Módulos de física

- **`optics.py`** — Beer-Lambert, reflectancia medida o fija, reflector trasero con rebotes sucesivos, generación de pares y grilla de profundidad.
- **`material.py`** — concentración intrínseca, difusividades, longitudes de difusión, potencial de contacto, zona de depleción y techo intrínseco de la vida media (radiativo y Auger).
- **`collection.py`** — probabilidad de que un par nacido a cada profundidad llegue a la juntura, muera en una superficie o se recombine en el volumen, y el reparto de los fotones incidentes entre sus diez destinos posibles.
- **`quantum_efficiency.py`** — eficiencia cuántica externa e interna, y la grilla de sectores.
- **`diode.py`** — corriente de saturación y la ecuación implícita del diodo, resuelta por búsqueda de raíz.
- **`front_grid.py`** — sombreado y resistencia serie de la malla de dedos de plata.
- **`balance.py`** — reparto de la potencia incidente entre lo que impone el silicio, las pérdidas ópticas, la recombinación y las pérdidas eléctricas.
- **`compromiso.py`** — lo que cuesta la malla en puntos de eficiencia, resolviendo la curva completa para cada número de dedos y repartiendo la pérdida entre sombra, emisor y dedos.
- **`defectos.py`** — grietas que se propagan, manchas de contaminación y el camino eléctrico de cada trozo de celda hasta la barra colectora, de donde salen la resistencia serie local y las zonas aisladas.
- **`sectors.py`** — la malla de 48 × 48 trozos en paralelo, todos al mismo voltaje de terminal, y la curva global que resulta.

## Datos externos

| Archivo | Contenido | Fuente |
|---|---|---|
| `data/astmg173.xls` | Espectro solar AM1.5G, columna *Global tilt* | ASTM G173-03, provisto por el curso |
| `data/Green-2008_silicon_nk.csv` | Índice de refracción y coeficiente de extinción del silicio, 250–1450 nm | M. A. Green, *Solar Energy Materials and Solar Cells* **92** (2008) 1305-1310 |

Ningún dato es inventado ni ajustado a mano. El coeficiente de absorción se deriva del
índice de extinción medido mediante α = 4πk/λ.

## Librerías

| Librería | Para qué | Qué supone |
|---|---|---|
| **NumPy** | Álgebra vectorial de todas las integrales espectrales y de profundidad | Aritmética de punto flotante de doble precisión |
| **SciPy** | `brentq` para la ecuación implícita del diodo | La raíz está encerrada en un intervalo con cambio de signo |
| **pandas** | Lectura de la planilla del espectro y tablas de la interfaz | — |
| **Plotly** | Todas las figuras, incluidas las tridimensionales y las animadas | — |
| **Streamlit** | Capa de despliegue web y manejo de estado compartido | — |
| **xlrd** | Lectura del formato `.xls` heredado del espectro | — |

Ninguna resuelve física del dispositivo: todo el modelo está implementado en `physics/`.
`solcore` no se usa, como exige el enunciado.

## Validación

La validación tiene dos partes con trabajos distintos.

**Certificación.** Veintiuna verificaciones que corren siempre sobre la celda asignada por la semilla,
sin importar lo que se haya movido en los controles. Incluyen las siete que exige el enunciado. El
valor calculado sale siempre del modelo; solo el de referencia está almacenado. Una de ellas, V2a,
queda marcada como informativa y no como falla: el dato medido de Green da 0,415 µm de profundidad de
absorción a 450 nm donde el enunciado pone «del orden de 1 µm». Se decidió mantener el dato medido y
reportar la discrepancia con su explicación. Descontada esa, la certificación pasa sin fallas.

**Monitor en vivo.** Veintiuna vigilancias que corren en cada movimiento de un control, sobre los valores
actuales, y avisan cuando lo que se está mostrando deja de ser físicamente posible o numéricamente
correcto. Su resumen está siempre visible arriba de la barra lateral. Por ahora cubre las Pestañas 1 y 2,
la coherencia de la Pestaña 1 con la 2 y con la 3, y la Pestaña 4 con su malla fina (ver D-38, D-42, D-43 y D-48).

Los valores que entrega la celda de la semilla, con la variación de fabricación entre sectores
del estado inicial (D-41), a 45 °C y un sol:

| Magnitud | Valor |
|---|---|
| Corriente de cortocircuito | 14,5742 mA/cm² |
| Voltaje de circuito abierto | 0,587142 V |
| Factor de forma | 0,769291 |
| Eficiencia | 6,5829 % |
| Coeficiente térmico del voltaje | −2,208 mV/°C |

Y el destino de los fotones que llegan a la parte iluminada de esa misma celda, que es lo que la
Pestaña 1 reporta como reparto. Suma exactamente 100 %; las tres últimas filas son la corriente
fotogenerada, 15,05 mA/cm², que con la sombra de la malla (3,08 %) queda en los 14,59 mA/cm² de la
Pestaña 3:

| Destino de un fotón incidente | Fracción |
|---|---|
| Se refleja en la superficie | 34,98 % |
| Llega al fondo y lo absorbe el aluminio | 12,32 % |
| Nace en el emisor y muere en la superficie frontal | 18,55 % |
| Nace en el emisor y se recombina en su volumen | 0,53 % |
| Nace en la base y se recombina en su volumen | 0,27 % |
| Nace en la base y muere en la cara trasera | 0,94 % |
| Nace en el emisor y llega a la juntura | 12,26 % |
| Nace en la zona de depleción y se separa de inmediato | 0,37 % |
| Nace en la base y llega a la juntura | 19,77 % |

## Limitaciones declaradas

Las más importantes, con su detalle en `DECISIONES.md`:

- **Sin recombinación radiativa ni de Auger explícitas** (D-33). Los tiempos de vida de los controles
  son vidas efectivas. Con el dopaje asignado al emisor, Auger limitaría su vida a 0,69 ns, pero el
  modelo usa el valor elegido; la colección en el emisor queda sobreestimada. Incorporarla anularía la
  respuesta en el azul del emisor de 5 µm que fija el enunciado. El monitor en vivo lo avisa.
- **Sin acoplamiento lateral entre sectores** (D-10).
- **Óptica plana**: incidencia normal, sin antirreflejo ni texturizado, reflector trasero especular.
- **Estadística de Boltzmann en un emisor degenerado** (D-05).

## Correr en local

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Las verificaciones sin abrir la aplicación:

```bash
.venv\Scripts\python.exe -m validation.checks
```

Requiere Python 3.10 o superior.

## Decisiones de modelamiento

Las treinta decisiones de modelamiento, con su motivo y su clasificación —requisito del
enunciado, decisión de diseño propia, o conocimiento externo declarado— están en
[`DECISIONES.md`](DECISIONES.md).

D-18 a D-27 documentan las correcciones hechas tras una auditoría externa independiente
del código, D-28 a D-30 las hechas tras la revisión del profesor, y D-31 la reconstrucción
de las figuras de la Pestaña 1 en torno al reparto de los fotones por destino, y D-32 a D-39
la revisión física completa de esa pestaña y el monitor en vivo.
