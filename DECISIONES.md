# Registro de decisiones y simplificaciones

Bitácora viva del Proyecto 1 — Problema 2.2 (Laboratorio virtual de caracterización de una celda p-n de silicio).
Todo lo que se anote aquí alimenta el reporte final y la defensa oral.

**Semilla S = 6** — N_A = 4×10¹⁶ cm⁻³ · N_D = 6×10¹⁹ cm⁻³ · τ_SRH = 30 µs · S_frontal = 2×10⁴ cm/s · T = 45 °C

Clasificación de cada entrada, según la regla R10 del set de instrucciones:
- **[PDF]** requisito textual del enunciado o de las Unidades del curso
- **[DISEÑO]** decisión de modelamiento propia
- **[EXTERNO]** conocimiento físico externo al curso

---

## D-01 · Permitividad en la zona de deplexión — [DISEÑO + EXTERNO]

**Decisión.** Se usa la permitividad del silicio, ε_Si = ε_r·ε₀ con ε_r ≈ 11,7, y no la del vacío.

**Contexto.** Las diapositivas 20 y 21 de la Unidad 2 escriben la ecuación de Poisson con ε₀. Físicamente, dentro del cristal de silicio corresponde ε_Si, porque el material apantalla el campo eléctrico.

**Impacto cuantificado.** W_dep = 0,183 µm con ε_Si, frente a 0,053 µm tomando la diapositiva al pie de la letra (factor 3,4). En ambos casos la zona de deplexión es minúscula frente al emisor de 5 µm, así que el efecto sobre EQE y sobre la corriente final es marginal.

**Refinamiento posterior.** Esa cifra de 0,183 µm usaba n_i = 10¹⁰ cm⁻³, el valor de referencia a 300 K. Al implementar la dependencia térmica de la concentración intrínseca (decisión D-08), a la temperatura de operación de 45 °C se obtiene n_i = 4,13×10¹⁰ cm⁻³, con lo que Ψ₀ baja de 1,034 a **0,956 V** y el ancho a **0,176 µm**. La conclusión no cambia: sigue siendo despreciable frente al emisor.

**Para el reporte.** Mencionar como discrepancia consciente con la notación de la diapositiva, no como error de lectura.

---

## D-02 · Reparto de la zona de deplexión — [PDF]

**Decisión.** Se sigue el enunciado: la zona de deplexión se reparte simétricamente a ambos lados de la juntura (x_n = x_j − W_dep/2, x_p = x_j + W_dep/2).

**Contexto.** Físicamente, en una juntura abrupta la zona se extiende hacia el lado menos dopado en razón inversa a los dopajes. Con nuestra razón de 1500:1, al lado n le corresponderían 0,00012 µm y al lado p prácticamente todo el ancho.

**Justificación.** El enunciado es la fuente de verdad (regla R1). Ambas cifras son despreciables frente al emisor de 5 µm, de modo que el efecto sobre la colección es nulo en la práctica.

**Para el reporte.** Simplificación del enunciado, identificada y acotada. Buen material de defensa: demuestra comprensión del modelo, no copia.

---

## D-03 · Grilla de profundidad no uniforme — [DISEÑO]

**Decisión.** La discretización en profundidad es no uniforme: densa cerca de la superficie frontal, progresivamente más gruesa hacia el fondo.

**Motivo.** A 300 nm el silicio absorbe la luz en los primeros 5,6 nm, mientras que la celda mide 100 µm. Son cinco órdenes de magnitud. Una grilla uniforme de 500 puntos deja 200 nm entre nodos y no resuelve la absorción del ultravioleta, haciendo fallar V1 sin ninguna señal visible de error.

**Uso adicional.** V1 sirve como test de calidad de la grilla: analíticamente el balance de fotones da exactamente 1, así que cualquier desviación numérica que reporte mide directamente la resolución de la discretización.

---

## D-04 · Coeficiente de absorción: dato medido sobre referencia del enunciado — [PDF + DISEÑO]

**Decisión.** Se usa α(λ) derivado de los datos medidos de Green (2008), sin ajustar ni truncar hacia la referencia del enunciado.

**Consecuencia conocida.** La verificación V2 compara la profundidad de absorción a 450 nm contra una referencia de "del orden de 1 µm ± 30 %". El dato real de Green entrega 0,415 µm, o sea −58 %, fuera de tolerancia.

**Justificación.** 0,415 µm es el valor físicamente correcto para silicio a 450 nm. La tolerancia de ±30 % del enunciado indica que la referencia es aproximada. El punto físico que V2 quiere comprobar —que el azul se absorbe íntegramente dentro del emisor de 5 µm— se cumple con holgura.

**Implementación.** V2 se reporta con doble veredicto: el chequeo físico real (azul dentro del emisor, infrarrojo más allá de 100 µm) como aprobado, y la comparación literal contra 1 µm mostrada con su error y su nota explicativa. El enunciado acepta explícitamente que una verificación falle si se explica físicamente por qué.

**Para el reporte.** Revisar si aparece algún problema derivado. Anotado como discrepancia dato-medido contra referencia-de-curso.

---

## D-05 · Estadística de Boltzmann en un emisor degenerado — [EXTERNO]

**Decisión.** Se usa la expresión clásica de la corriente de saturación de la Unidad 3, declarando que el supuesto de no degeneración no se cumple en el emisor.

**Contexto.** Con N_D = 6×10¹⁹ cm⁻³ el emisor está degenerado y además hay estrechamiento de banda prohibida por dopaje alto, que no modelamos. Adicionalmente, L_p = 12,8 µm supera el espesor del emisor de 5 µm, de modo que tampoco corresponde formalmente la expresión de "base larga".

**Cota del error.** El término del emisor vale 2,14×10⁻¹⁷ frente a 2,62×10⁻¹⁴ del término de la base: la base domina en razón 1225:1. Los supuestos violados viven íntegramente en la parte del cálculo que aporta menos de una milésima del resultado.

---

## D-06 · Reflector trasero y eficiencia cuántica — [PDF + DISEÑO]

**Decisión.** Dos regímenes explícitos:

- **Reflector apagado (estado inicial).** La eficiencia cuántica es exactamente la fórmula de un solo paso del enunciado. Las siete validaciones corren en este estado, donde el balance de tres partes de V1 (reflejado / absorbido en el silicio / transmitido al contacto trasero) está bien definido.
- **Reflector encendido.** Se suma el segundo paso: la luz que alcanza el fondo se refleja, vuelve a recorrer la base y genera pares adicionales. El efecto se concentra en el rojo e infrarrojo cercano.

**Motivo.** La fórmula de EQE del enunciado describe un solo paso y no tiene término para la luz de retorno, pero el enunciado sí exige el control de reflector activable en la Pestaña 1. Esta separación respeta la fórmula entregada como modelo canónico y le da consecuencias físicas correctas al control cuando se activa.

---

## D-07 · Consistencia del sombreado en la validación cruzada — [DISEÑO]

**Decisión.** La eficiencia cuántica se define siempre para la celda **sin sombrear**, y el factor de sombreado de la malla frontal se aplica de forma idéntica en ambos lados de la comparación de V3.

**Motivo.** V3 exige que la corriente de cortocircuito por vía óptica y por vía eléctrica coincidan dentro de 5 %. Si la eficiencia cuántica se define desnuda pero la corriente fotogenerada se multiplica por la fracción no sombreada, ambas vías difieren exactamente en la fracción de sombra (~5 %), justo en el borde de la tolerancia. Es el error que V3 está diseñada para detectar.

**Nota.** Con los parámetros de la semilla, la corriente de cortocircuito difiere de la fotogenerada en menos de 0,1 % por efecto de las resistencias. Si el usuario baja mucho R_p, la igualdad se degrada y la aplicación debe advertirlo en vez de fallar en silencio.

---

## D-08 · Dependencia térmica completa de la corriente de saturación — [EXTERNO]

**Decisión.** Al barrer temperatura se recalcula íntegra la corriente de saturación, incluyendo la dependencia térmica de la concentración intrínseca y del ancho de banda prohibida.

**Motivo.** El voltaje de circuito abierto crece con la energía térmica. Si solo se actualiza ese factor y se congela la corriente de saturación, el coeficiente de temperatura sale **positivo**, cuando la física y V6 exigen negativo. El signo correcto proviene enteramente del crecimiento exponencial de la concentración intrínseca con la temperatura.

**Verificación previa.** Estimación analítica con nuestros parámetros: −1,88 mV/°C, dentro del rango de V6 (−1,8 a −2,6 mV/°C).

---

## D-09 · Movilidades fijas del Anexo B — [PDF]

**Decisión.** Se usan µ_n ≈ 1200 cm²/V·s y µ_p ≈ 60 cm²/V·s del Anexo B, sin modelo de dependencia con el dopaje.

**Motivo.** Fidelidad al curso. Un modelo tipo Caughey-Thomas sería más realista pero es conocimiento externo, y nuestros dopajes caen cerca de los valores de referencia del Anexo B.

---

## D-10 · Sectores en paralelo a voltaje común, sin acoplamiento lateral — [DISEÑO]

**Decisión.** Los 64 sectores se resuelven en paralelo compartiendo el mismo voltaje de terminal. Para cada voltaje del barrido, cada sector aporta la corriente que le corresponde con su colección y su resistencia local, y la curva global es la suma ponderada por área.

**Consecuencia buscada.** La asimetría que el enunciado pide explicar emerge sola del modelo: un defecto de colección reduce la corriente en proporción al área, mientras que un defecto de resistencia serie casi no toca la corriente de cortocircuito pero deteriora el factor de forma.

**Límite declarado.** No se modela el acoplamiento lateral entre sectores vecinos. En una celda real, un sector muerto puede ser empujado a polarización inversa por sus vecinos, origen de los puntos calientes que revela la termografía. Modelarlo exigiría resolver una red eléctrica bidimensional completa, fuera del alcance del enunciado.

---

## D-11 · Reflectancia del contacto trasero de aluminio — [EXTERNO]

**Decisión.** Se usa R_Al = 0,90 para la reflexión interna en el contacto trasero.

**Motivo.** El enunciado exige un control de reflector trasero activable pero no entrega un valor. 0,90 es el orden típico de un contacto de aluminio sobre silicio en el infrarrojo cercano, que es la región donde el reflector importa (el resto del espectro ya se absorbió antes de llegar al fondo).

**Declarado en.** `constants.py`, marcado como [EXTERNO]. Solo interviene cuando el reflector está encendido; con el reflector apagado, que es el estado por defecto, no participa en ningún cálculo (ver D-06).

---

## D-12 · Rango de temperatura extendido hacia el frío — [DISEÑO]

**Decisión.** El deslizador de temperatura admite de −15 a 75 °C, en vez de los 15 a 75 °C que fija el enunciado.

**Motivo.** Permite explorar operación en clima frío, donde la celda es más eficiente. No introduce ningún problema físico: no hay transiciones de fase ni cambios de régimen en ese rango para el silicio.

**Restricción mantenida.** La verificación V6 sigue barriendo exactamente 15–75 °C, que es el rango que el enunciado fija para ese criterio. Declarado en `config.T_RANGO_V6_C`.

---

## D-13 · Nodos forzados en los bordes de la zona de deplexión — [DISEÑO]

**Decisión.** La grilla de profundidad incluye nodos exactamente en x_n y x_p, más doce nodos repartidos dentro de la zona de deplexión.

**Motivo.** La probabilidad de colección está definida por tramos y cambia de rama justo en esos bordes, donde debe valer exactamente 1. Sin un nodo en el borde, el punto más cercano de la grilla cae antes, y la prueba de valor unitario falla por un 0,2 % que parece un error de fórmula pero es de discretización. Detectado al correr las pruebas físicas del Hito 3: el chequeo devolvía 0,9979 en vez de 1.

**Efecto secundario buscado.** Los nodos interiores de la zona de deplexión también hacen falta para el Hito 4: la eficiencia cuántica integra el producto de la generación por la colección, y en esa franja la colección vale 1 mientras la generación sigue decayendo exponencialmente.

**Costo.** La grilla pasa de 799 a 811 nodos. V1 sigue dando 0,0040 % de error.

---

## D-14 · Variación entre sectores generada, no medida — [DISEÑO]

**Decisión.** La variación de calidad entre los 64 sectores se genera con una distribución log-normal en torno a los valores nominales, con desviación logarítmica controlable por el usuario (0 a 0,6, por defecto 0,20) y semilla fija para que el mapa sea reproducible.

**Motivo.** El enunciado exige que cada sector tenga su propio tiempo de vida local y su propia velocidad de recombinación superficial local, pero no entrega datos de una celda real. La log-normal es la forma habitual de describir dispersiones multiplicativas y no puede producir valores negativos.

**Honestidad del dato.** No son datos medidos: son variación simulada, y así queda etiquetado en la interfaz ("dispersión de fabricación"). Poniendo el control en cero la celda queda perfectamente homogénea, que es el caso de referencia contra el que se comparan los defectos del Hito 6.

**Correlación.** El tiempo de vida y la pasivación superficial se sortean de forma independiente, porque son defectos de naturaleza distinta: uno es de volumen y el otro de superficie.

---

## D-15 · Modelo de la malla frontal de plata — [EXTERNO]

**Decisión.** Se usa la formulación estándar de la ingeniería fotovoltaica, con dos contribuciones a la resistencia serie:

- **Resistencia del emisor**: la corriente entra repartida entre dos dedos y viaja lateralmente hasta el más cercano. El promedio de esa resistencia distribuida da ρ_cuadro·S²/12, con S la separación entre dedos.
- **Resistencia de los dedos**: cada dedo va recogiendo corriente a lo largo de su recorrido, así que la que transporta crece hacia la barra colectora. El promedio da ρ·L²·S/(3·ancho·espesor).

**Motivo.** El enunciado exige modelar la malla explícitamente, pero el modelo no aparece en las Unidades 2 ni 3, y no dispongo de la Unidad 4. Autorizado por el usuario a aportarlo desde conocimiento externo.

**Constantes declaradas** (todas en `constants.py`, marcadas [EXTERNO]): oblea cuadrada de 15,6 cm de lado, 3 barras colectoras, dedos de 15 µm de espesor, plata serigrafiada de 3,0×10⁻⁶ Ω·cm, resistencia de capa del emisor 60 Ω/cuadro.

**Simplificación declarada.** El sombreado cuenta solo los dedos, no las barras colectoras. Así, duplicar el ancho de los dedos duplica exactamente la sombra, y la verificación V7 mide lo que dice medir.

**Comportamiento.** Con 60 dedos de 80 µm: sombreado 3,08 %, resistencia del emisor 0,338 Ω·cm², de los dedos 0,146 Ω·cm², total 0,484 Ω·cm². Valores realistas para una celda serigrafiada.

---

## D-16 · Modelo del dedo de plata interrumpido — [DISEÑO]

**Decisión.** Al interrumpirse los dedos que sirven a una columna de sectores, esos sectores ven una separación efectiva multiplicada por (dedos_por_columna + 1), y sus resistencias del emisor y de los dedos se recalculan con esa separación. El sombreado **no** cambia.

**Motivo físico.** El metal roto sigue estando ahí y sigue tapando la luz; lo que pierde es la conducción. La corriente del centro de esa franja tiene que recorrer varias separaciones hasta el primer dedo sano, y como la resistencia del emisor crece con el cuadrado de la distancia recorrida, el efecto es severo. Con 60 dedos sobre 8 columnas son unos 7-8 dedos consecutivos, lo que lleva la resistencia local de 0,98 a **26,2 Ω·cm²**.

**Iteración.** El primer modelo suponía que romper el dedo solo duplicaba la separación, y producía una caída de factor de forma de apenas 0,46 %, demasiado tenue para demostrar la asimetría que el enunciado pide explicar. Se corrigió al notar que romper una columna entera de dedos no equivale a romper uno.

**Resultado.** Con áreas dañadas comparables (14,06 % contra 12,50 %):

| | Contaminación | Dedos rotos |
|---|---|---|
| Caída de Jsc | 4,96 % | 0,31 % |
| Caída del factor de forma | 0,35 % | 9,06 % |
| Caída de eficiencia | 5,29 % | 9,34 % |

La colección hunde la corriente 16 veces más; la resistencia hunde el factor de forma 26 veces más. Es exactamente la asimetría que el enunciado pide demostrar, y emerge sola de la condición de que los sectores estén en paralelo al mismo voltaje (D-10), sin haberla programado a mano.

---

## D-17 · Fotocorriente por sector desde la generación integrada — [DISEÑO]

**Decisión.** La fotocorriente de cada sector se calcula como q·∫G_tot(x)·f_c(x)dx, integrando primero la generación sobre todo el espectro y ponderando después por la colección local.

**Motivo.** Es la forma que el enunciado prescribe literalmente para J_L, y es **exacta, no aproximada**: la probabilidad de colección no depende del color, así que el orden de integración es indiferente. Verificado contra la vía de la eficiencia cuántica: coinciden con diferencia relativa de 2×10⁻¹⁶.

**Beneficio.** Reduce el trabajo de los 64 sectores de cincuenta millones de operaciones a cincuenta mil, que es lo que hace viable resolver el mapa en tiempo real.

---

## Nota numérica · Grilla de profundidad verificada

La grilla no uniforme de la decisión D-03 quedó implementada con 799 nodos: un tramo exponencial en el emisor y otro en la base, ambos refinados en su borde inicial. El primer paso mide **0,034 nm** y el último **1,50 µm**.

Resultado de V1 (balance de fotones) sobre todo el rango 300–1200 nm: **error máximo 0,004 %**, contra una tolerancia de 1 %. Como el balance es exacto analíticamente, esa cifra es una medida directa de la calidad de la discretización.

---

## Supuestos globales del modelo

Lista para la sección de límites del reporte y de la presentación.

| Supuesto | Estado | Nota |
|---|---|---|
| Juntura abrupta y deplexión total | Modelo del curso | Adecuado para dopaje uniforme |
| Dopaje uniforme en cada región | Simplificación | Un emisor difundido real tiene perfil decreciente |
| Baja inyección | **Verificado** | Δn/N_A = 0,020 bajo un sol |
| Sin acoplamiento lateral entre sectores | Declarado | Ver D-10 |
| Incidencia normal, sin antirreflejo ni texturizado | Impuesto por el enunciado | Una celda comercial refleja mucho menos que el 30 % del silicio desnudo |
| Sin atrapamiento de luz difuso | Simplificación | Solo reflector trasero especular, ver D-06 y D-11 |
| Sin absorción por portadores libres | Simplificación | — |
| Sin recombinación dentro de la zona de deplexión | Simplificación | — |
| Movilidades fijas | Ver D-09 | — |
| Estadística de Boltzmann | Violado en el emisor | Acotado en D-05 |
| Constantes ópticas medidas a 300 K usadas a la temperatura de operación | Simplificación | Green (2008) entrega coeficientes de temperatura que no se aplican; cerca de la banda prohibida la absorción real crece con la temperatura, así que a 45 °C el modelo subestima levemente la absorción del infrarrojo |
| Sin recombinación radiativa ni de Auger explícitas | **Limitación declarada** | τ_n y τ_p son vidas efectivas; con N_D = 6×10¹⁹ el τ_p elegido supera el techo que impone Auger y la colección en el emisor queda sobreestimada. Ver D-33 |

---

## Pendientes

- Modelo de resistencia serie de la malla frontal de plata: no aparece en las Unidades 2 ni 3. Se usará el modelo estándar de ingeniería fotovoltaica, declarado como **[EXTERNO]** con su fuente en el módulo de constantes.

---

# Correcciones tras auditoría externa · 7 de septiembre de 2026

Una auditoría independiente revisó el commit `38ade8f` y encontró errores reproducibles. **Se verificó cada afirmación contra el código antes de actuar; todas las comprobadas resultaron correctas**, con cifras que coinciden con las nuestras hasta la cuarta cifra significativa.

## D-18 · El solver por sectores no permitía corriente negativa — [BUG CORREGIDO]

**Qué pasaba.** `_corriente_vectorizada` buscaba el voltaje de juntura en un intervalo que arrancaba en el voltaje de terminal, de modo que la corriente resultante nunca podía ser negativa. Un sector con poca fotocorriente tiene un circuito abierto local más bajo que el del conjunto, y por encima de él **consume** corriente: su diodo conduce en directa alimentado por los sectores sanos. Eso no requiere polarización inversa ni acoplamiento lateral, solo estar en paralelo.

**Además**, la Pestaña 4 fijaba el voltaje máximo del barrido en 0,62 V y, si la curva no cruzaba cero, `parametros_de_curva` devolvía el último punto como circuito abierto.

**Evidencia.** A 0,600 V el solver daba +0,0000 donde el escalar da −5,1003 mA/cm². A −15 °C reportaba Voc = 0,620000 V y FF = 0,936280, cuando lo real es 0,718812 y 0,810169.

**Corrección.** El intervalo se expande hacia ambos lados hasta encerrar la raíz con cambio de signo. El circuito abierto se busca resolviendo la raíz de la corriente total, no recorriendo un rango fijo.

**Resultado.** Las Pestañas 3 y 4 coinciden ahora a **0,0000 mV** a −15, 45 y 75 °C. Se añadió la verificación **C-T6** para que no vuelvan a divergir sin avisar.

---

## D-19 · La contaminación no actualizaba la corriente de saturación — [INCONSISTENCIA CORREGIDA]

**Qué pasaba.** El defecto de contaminación bajaba el tiempo de vida local, acortaba la longitud de difusión y reducía la fotocorriente, pero los sectores conservaban la corriente de saturación de la celda nominal. Eso contradice la propia expresión del modelo: J₀ de la base va como el inverso de la longitud de difusión, así que **reducir el tiempo de vida también aumenta la recombinación en oscuridad**.

**Magnitud.** Dividir el tiempo de vida por mil multiplica J₀ local por **31,6**. Verificado: 32,34 con el término de emisor incluido.

**Corrección.** `armar_celda` calcula J₀ por sector con el mismo tiempo de vida, geometría y condiciones de borde que usa la colección.

**Consecuencia sobre nuestras conclusiones publicadas.** La asimetría entre defectos cambia de forma material:

| Contaminación, 14,06 % del área | Antes | Después |
|---|---|---|
| Caída de Jsc | 4,96 % | 4,96 % |
| Caída de Voc | 0,00 % | **3,92 %** |
| Caída del factor de forma | 0,35 % | **4,39 %** |
| Caída de eficiencia | 5,29 % | **12,69 %** |

La asimetría en **corriente** sobrevive intacta, 16 a 1. La de **factor de forma** cae de 26:1 a 2,1:1: era en buena parte un artefacto del error. Aparece en cambio una asimetría más limpia que la anterior: los dedos rotos dejan el voltaje **exactamente** intacto (−0,00 %) mientras la contaminación lo baja un 3,92 %.

---

## D-20 · J₀ y colección usaban condiciones de borde distintas — [INCONSISTENCIA CORREGIDA]

**Qué pasaba.** La corriente de saturación usaba la forma de «base larga», que supone regiones mucho más largas que la longitud de difusión. Ese supuesto **no se cumple aquí**: la longitud en la base es de 314 µm sobre una base de 100 µm. Mientras tanto la colección sí usaba la forma finita con recombinación superficial. Son la misma ecuación con las mismas condiciones de borde; usar dos formas distintas es incoherente.

**Corrección.** Se añadió el factor de región finita

    F = [tanh(w/L) + S·L/D] / [1 + (S·L/D)·tanh(w/L)]

cuyos tres límites son los esperados: F → 1 para región mucho más larga que L, F → tanh(w/L) con superficie perfectamente pasivada, F → coth(w/L) con superficie infinitamente ávida.

**Magnitud, verificada contra la auditoría:**

| S trasera | F | Voc antes | Voc después |
|---|---|---|---|
| 10 cm/s | 0,318 | 0,587233 V | 0,618581 V (**+31,35 mV**) |
| 10³ cm/s | 0,977 | 0,586464 V | 0,587100 V (+0,64 mV) |
| 10⁶ cm/s | 3,239 | 0,583651 V | 0,551500 V (**−32,15 mV**) |

Con los valores de la semilla el efecto es pequeño porque el cociente S·L/D está cerca de uno, **no porque la base sea larga**. En otros regímenes llega a ±32 mV.

---

## D-21 · Geometría inválida aceptada en silencio — [BUG CORREGIDO]

**Qué pasaba.** Con dopajes bajos, la zona de deplexión llega a medir más que el emisor, y el reparto simétrico del enunciado dejaba su borde **fuera de la celda**. Con dₙ = 0,2 µm y N_A = 10¹⁴ cm⁻³ resultaba x_n = −1,40013 µm. El código no lo detectaba: la rama del emisor se saltaba y la colección quedaba valiendo **1,000000 en la superficie frontal**, ocultando por completo el efecto de la recombinación superficial.

**Corrección.** Se detecta y se cae al reparto por neutralidad de carga, `N_D·w_n = N_A·w_p`, que es el físicamente correcto, avisando en pantalla. La colección en la superficie pasa de 1,000000 a 0,804316.

---

## D-22 · Las claves de caché excluían parámetros físicos — [BUG CORREGIDO]

**Qué pasaba.** Streamlit excluye del hash de caché los argumentos que empiezan con guion bajo. Como pasábamos el campo óptico, la juntura y el transporte con ese prefijo, cambios en el tiempo de vida del emisor, la recombinación trasera, la temperatura o el reflector **no invalidaban la entrada**, y la aplicación podía devolver un resultado viejo mientras otra parte de la pantalla ya se había actualizado.

**Corrección.** Se añadió una huella explícita con todos los parámetros físicos que solo entraban por esos objetos.

---

## D-23 · El reflector no llegaba a la animación ni a la tabla — [BUG CORREGIDO]

Las cifras de la Pestaña 1 incluían el segundo paso de la luz, pero la animación tridimensional y la tabla de destinos del color seguían mostrando un solo paso: las dos vistas se contradecían. Ahora ambas reciben el estado del reflector, y la tabla separa lo que absorbe el aluminio de lo que escapa por el frente, en vez de agruparlo todo bajo «transmitido».

---

## D-24 · La interpretación de la eficiencia cuántica estaba al revés — [TEXTO CORREGIDO]

La interfaz atribuía a reflexión la distancia entre la curva externa y la cota `1−R`. **Esa reflexión ya está descontada en la cota**: esa distancia es la suma de la luz que atraviesa sin absorberse más los pares que se recombinan.

Se mantiene la definición del enunciado, `IQE = EQE/(1−R)`, y se añade junto a ella la eficiencia por fotón **absorbido**, que sí aísla la calidad de colección. A 1000 nm la diferencia entre ambas es de 43,7 puntos porcentuales, y esa diferencia es absorción incompleta, no recombinación.

---

## D-25 · El mapa no calculaba electroluminiscencia — [TEXTO CORREGIDO]

Llamábamos «mapa de emisión» a lo que dibuja fotocorriente local. De ahí salía una conclusión falsa: que un sector sin dedo «brilla igual», presentado como resultado físico cuando era una consecuencia de lo que el mapa grafica. **La electroluminiscencia real sí detecta defectos de resistencia serie** — es una técnica estándar precisamente para eso. Renombrado a «Fotocorriente local por sector», con la aclaración en pantalla.

---

## D-26 · La verificación C-T1 era vacía — [VALIDACIÓN CORREGIDA]

Comprobaba que la probabilidad de colección estuviera en [0,1] **después** de recortarla con `np.clip`. No podía fallar nunca. Ahora se evalúa antes del recorte, que pasa a ser red de seguridad y no parte del modelo.

---

## D-27 · V4 no detectaba la trampa que decía detectar — [VALIDACIÓN AMPLIADA]

El enunciado define V4 con resistencia serie nula, y **sin resistencia serie el término Rs·J desaparece**: las dos formas de la ecuación coinciden exactamente. Verificado: difieren en 8×10⁻⁷. Un solver que ignorara el término aprobaría V4 igual.

Se mantiene V4 como la exige el enunciado y se añade **C-T5**, que evalúa con resistencia serie real y exige que el factor de forma correcto quede por debajo del que da el atajo. Con nuestra resistencia, el atajo sobrestima un 2,6 %.

---

## Lo que la auditoría señaló y decidimos no cambiar

- **Definición de IQE.** El enunciado y la Unidad 3 la definen como `EQE/(1−R)`. Se mantiene, y se añade la otra al lado en lugar de sustituirla.
- **Reparto simétrico de la deplexión.** Sigue siendo el del enunciado por defecto, ahora con el reparto por neutralidad disponible y activado automáticamente cuando el simétrico produciría una geometría imposible.
- **Resistencia de capa del emisor fija.** La auditoría señala que 60 Ω/cuadro implicaría una movilidad de mayoritarios de 3,47 cm²/V·s, inconsistente con nuestro dopaje uniforme. Es correcto, y queda declarado como limitación: el valor corresponde a un perfil difundido real, no al emisor uniforme del modelo óptico.
- **Emisor degenerado.** La auditoría objeta que acotar el error con la razón 1225:1 es circular, porque esa razón sale del mismo modelo inválido. Es una crítica justa al *argumento*. La conclusión se mantiene pero se enuncia con más cuidado: incluso si el estrechamiento de banda multiplicara por cincuenta el término del emisor, seguiría siendo veinticinco veces menor que el de la base.

## Estado tras las correcciones

**18 verificaciones, 0 fallas reales.** Las siete del enunciado aprueban.

Valores actualizados de la celda de la semilla: Jsc **14,5526 mA/cm²**, Voc **0,587100 V**, factor de forma **0,769274**, eficiencia **6,5726 %**, coeficiente térmico **−2,209 mV/°C**.

---

# Correcciones tras la revisión del profesor · 8 de septiembre de 2026

## D-28 · La celda es una sola, no sesenta y cuatro celdas separadas — [BUG CORREGIDO]

**Qué señaló el profesor.** La eficiencia cuántica no se puede calcular como si la celda
fuera muchas celdas independientes. Es un solo dispositivo con respuesta distinta en
distintos sectores.

**Qué pasaba.** Tres pestañas montaban su propia celda:

- La Pestaña 2 mostraba arriba la curva de una celda **homogénea nominal** y abajo un mapa
  de 64 sectores. Cuando la dispersión no era cero, la curva y el mapa describían
  dispositivos distintos.
- La Pestaña 3 tomaba su fotocorriente de esa misma celda homogénea, ignorando la dispersión.
- Las Pestañas 2 y 4 tenían **cada una su propio deslizador de dispersión**, con valores por
  defecto distintos (0,20 y 0,00). Podían quedar en valores distintos y nadie lo notaba.

La verificación C-T6 comprobaba la coherencia solo con la celda homogénea, que es justo el
único caso donde las tres coinciden por construcción. El agujero era invisible.

**La física.** Bajo iluminación uniforme todos los sectores reciben el mismo flujo por unidad
de área, y la eficiencia cuántica es **lineal** en la probabilidad de colección. Por lo tanto

    promedio por área de las EQE locales  ≡  EQE calculada con la colección promedio

No es una aproximación: es una identidad exacta. Verificada a **8,9×10⁻¹⁶**.

**Corrección.** Un único control de dispersión, en la barra lateral, compartido por toda la
aplicación. La respuesta de la celda se calcula con la colección promediada por área sobre
sus sectores (`coleccion_de_celda`), y las Pestañas 2, 3 y 4 la usan sin excepción. El mapa
se calcula desde las mismas colecciones locales que produjeron esa curva, de modo que no
pueden desincronizarse.

**Valor por defecto de la dispersión: cero.** La Tabla A.1 del Anexo A define una celda
homogénea; ésa es la celda que el enunciado asigna y la que describen las cifras reportadas.
La dispersión es una adición propia y vive detrás de un control explícito. Con esto ninguna
cifra publicada cambia.

**Verificaciones nuevas.** **C-T7** comprueba la identidad con dispersión 0,30, donde sí mide
algo. **C-T8** comprueba que las Pestañas 2, 3 y 4 siguen coincidiendo con dispersión
distinta de cero, que es exactamente lo que C-T6 no podía ver.

---

## D-29 · El mapa de generación medía la cosa equivocada — [BUG CORREGIDO]

**Qué señaló el profesor.** El mapa de calor de la Pestaña 1 no parecía representar un caso
real.

**Qué pasaba.** Dibujaba la generación absoluta en escala logarítmica con un piso fijo seis
décadas por debajo del máximo global. Pero la generación abarca **más de trescientas
décadas**: el azul cae a cero a pocas micras mientras el infrarrojo se mantiene casi plano.

Medido sobre el modelo: **el 26,4 % del mapa quedaba contra el piso**, y **46 de 1001 colores
salían enteros planos**, pintados de un color uniforme que se lee como «aquí no se genera
nada». Es falso: a 1100 nm sí se generan pares, de forma casi constante en toda la
profundidad. El mapa no estaba mal dibujado, estaba midiendo la cantidad equivocada.

**Corrección.** Se dibuja la **fracción de los pares de cada color ya creados por encima de
cada profundidad**, normalizada color a color. Es una cantidad acotada entre cero y uno, así
que no necesita escala logarítmica ni piso arbitrario, y cada color usa todo el rango de la
paleta. Se añade el contorno del 50 %, que es el frente de absorción. Resultado: **0 colores
planos**, y el frente aparece como una curva limpia que barre de 0,07 µm a 400 nm hasta
43 µm a 1000 nm.

---

## D-30 · Relieve tridimensional del origen de la corriente — [FIGURA NUEVA]

Superficie que dibuja la generación **multiplicada por la probabilidad de colección**: no
dónde nacen los pares, sino de dónde sale la corriente que la celda entrega. Su integral
sobre toda la superficie es la corriente fotogenerada.

Dos detalles de construcción, ambos por la misma razón que D-29:

- El eje de profundidad es logarítmico, así que se dibuja la densidad **ponderada por la
  profundidad**. Sin esa ponderación la superficie es un pico en el ultravioleta y una
  llanura en todo lo demás. La ponderación baja la superficie plana del 92,6 % al 54,7 %.
- Se usan **dos canales**, porque son dos preguntas distintas: la altura, normalizada color a
  color, dice *dónde* nace la corriente de ese color; el color de la superficie dice *cuánto*
  aporta ese color al total.

---

## D-31 · El reparto de los fotones por destino sustituye a los dos mapas de calor — [FIGURA NUEVA, DOS RETIRADAS]

**Qué se observó.** Los dos mapas de la Pestaña 1 —el plano de D-29 y el relieve de D-30—
seguían sin comunicar nada utilizable. El diagnóstico de D-29 era correcto y la corrección
funcionó, pero resolvió el problema equivocado: normalizar cada color contra su propio máximo
elimina el piso de la escala **y de paso elimina la magnitud**. Los dos mapas solo podían
responder «hasta qué profundidad llega cada color», y esa pregunta ya la respondían la
penetración por color y el acumulado espectral. Tres figuras de ocho compitiendo por lo mismo.

Además, las dos necesitaban un párrafo debajo para entenderse, que es el criterio que este
proyecto adoptó para declarar una figura fallida.

**Qué se pone en su lugar.** El reparto de los fotones incidentes entre sus **siete destinos
posibles**, en dos figuras que son la misma información a dos niveles de detalle:

- Una **cascada**, integrada sobre todo el espectro: parte de la corriente que habría si cada
  fotón del rango 300-1200 nm diera un par colectado —46,46 mA/cm² para esta celda— y va
  restando pérdida por pérdida hasta la corriente fotogenerada. Reflexión −16,25, atraviesan
  −5,72, se recombinan en el emisor −8,89, se recombinan en la base −0,56, quedan
  **15,03 mA/cm²**.
- El mismo reparto **color por color**, en franjas apiladas que llenan el 100 % en cada
  longitud de onda. Las pérdidas van abajo y lo que produce corriente arriba, de modo que el
  espesor del bloque superior es la eficiencia cuántica externa. Se comprobó: la frontera vale
  exactamente 1 − EQE en todo el rango.

**Por qué esto sí responde la pregunta del usuario.** Las magnitudes vuelven a ser legibles y
cada franja tiene un culpable identificable. La reflexión la fija la ausencia de recubrimiento
antirreflejo; lo que se recombina en el emisor, la recombinación superficial frontal; lo que
atraviesa la celda, el espesor. Mover un deslizador y ver qué franja crece es la lectura que
las figuras anteriores hacían imposible por construcción.

**Dónde vive el cálculo.** En `physics/collection.py`, no en la capa de gráficos: es física, y
la Pestaña 3 y las verificaciones tienen que poder consumirla. Devuelve las fracciones
espectrales, las integradas, la corriente fotogenerada y el techo absoluto.

**Detalle de implementación que importa.** Los tres tramos de integración —emisor, deplexión,
base— **comparten sus extremos**, así que las tres integrales parciales suman exactamente la
integral sobre toda la celda. Eso exige que la grilla traiga nodos forzados en los bordes de
la deplexión, que es lo que ya hace `grilla_profundidad`.

**Verificación asociada.** Ver C-T9.

**Figuras de la Pestaña 1: de ocho a seis.** Salen el mapa plano, el relieve, el balance
espectral —cuyo trabajo absorbe la figura nueva, mejor contado— y el acumulado espectral.
Entran la cascada y el reparto por destino. Se conservan la celda tridimensional, el perfil de
generación con colección, el perfil de probabilidad de colección y la penetración por color.

---

## C-T9 · Los siete destinos del fotón suman uno — [VALIDACIÓN NUEVA]

Es la verificación V1 llevada hasta el final. V1 comprueba que lo reflejado, lo absorbido y lo
transmitido cierren. C-T9 comprueba además que el reparto de lo absorbido entre emisor,
deplexión y base, y dentro de cada región entre lo que se colecta y lo que se recombina, sea
consistente con la probabilidad de colección.

Tiene más fuerza de la que parece. Los pares que nacen en la zona de deplexión aparecen en un
**solo** destino, el de colectados, porque ahí la probabilidad de colección vale uno. Si alguna
vez dejara de valer uno haría falta un octavo destino y la suma no cerraría, así que C-T9
vigila de paso el empalme de las tres ramas del modelo de colección.

La tolerancia es diez veces más estrecha que la de V1 —0,1 % contra 1 %— porque aquí no hay
cancelación posible entre términos: el único error admisible es el de la grilla resolviendo la
absorción. Medido: **0,0040 %** sobre las 1001 longitudes de onda, y se mantiene por debajo de
0,0045 % con el reflector encendido, con el emisor entre 0,2 y 10 µm, con la base entre 20 y
300 µm y con la recombinación superficial frontal entre 10 y 10⁶ cm/s.

Comprobado además, aunque no se reporta como verificación separada por ser exacto por
construcción: la corriente que sale de sumar los tres destinos que producen carga coincide con
la que sale de integrar la eficiencia cuántica **hasta la última cifra de la máquina**.

Con C-T9 el proyecto pasa de veinte verificaciones a **veintiuna**.

---

## Revisión física completa de la Pestaña 1 (15 de septiembre de 2026)

Antes de rehacer la pestaña se contrastó cada supuesto con el enunciado y con las Unidades 2 y 3, y
se midió sobre el modelo. Las decisiones D-32 a D-39 salen de esa revisión.

**Hallazgos que no requirieron cambiar el modelo**

- *Grilla.* En los extremos de los controles (emisor de 0,2 a 10 µm, base hasta 300 µm) el primer
  paso de la grilla mide entre 0,001 y 0,07 nm, frente a los 5,6 nm a los que muere el ultravioleta
  de 300 nm. El paso más grueso de la base es 4,5 µm, frente a longitudes de difusión de decenas o
  cientos de micras. Resuelve bien en todo el rango.
- *Potencial de contacto y zona de depleción.* Contrastados a 45 °C: concentración intrínseca
  4,13×10¹⁰ cm⁻³, potencial 0,956 V, ancho 0,176 µm, coherentes con las expresiones de la Unidad 2.
- *La tabla del color «no cambiaba» con el reflector.* No era un error de cálculo: a 450 nm, el color
  por defecto, el 90 % de la luz se absorbe antes de 0,95 µm y nada llega al fondo, así que el
  reflector no tiene qué devolver. A 1000 nm la tabla sí cambiaba (lo que escapa pasaba de 34,9 % a
  16,0 %). El defecto era de comunicación: la tabla no lo explicaba. Ahora lo dice.

**Hallazgos que sí requirieron cambios:** D-32 a D-39. **Hallazgo que quedó como limitación
declarada:** D-33.

---

## D-32 · El reflector trasero sumaba solo dos pasadas de la luz — [MODELO CORREGIDO]

**Qué pasaba.** Con el reflector encendido, el modelo sumaba la luz que baja y la que vuelve del
aluminio, y ahí se detenía. Pero la luz que vuelve llega a la cara frontal, y la misma interfaz
aire-silicio que refleja el 30 % de la luz que entra desde afuera refleja lo mismo de la que llega
desde adentro, a incidencia normal. Ese haz hace otro viaje, y otro.

**Corrección.** Cada ciclo completo multiplica la intensidad por la reflectancia frontal, la trasera y
la atenuación de ida y vuelta. La suma de todos los ciclos es una serie geométrica con suma exacta, así
que la generación se multiplica por un factor cerrado, y el balance separa lo que absorbe el aluminio
de lo que escapa por el frente. Sin reflector el factor vale exactamente uno: **las cifras
certificadas de la semilla no cambian**.

**Efecto medido con el reflector encendido.** La eficiencia cuántica a 1100 nm pasa de 3,92 % a
5,31 %; a 1000 nm, de 41,5 % a 44,8 %. La corriente sube de 15,82 a 16,07 mA/cm² (+1,6 %).

---

## D-33 · Techo intrínseco de la vida media, y un tiempo de vida del emisor que no es físico — [VIGILANCIA NUEVA · LIMITACIÓN DECLARADA]

**Base teórica.** La Unidad 2 (lámina 25) escribe la vida media en el volumen como la combinación de
tres mecanismos que se suman como tasas: radiativo, Auger y SRH. Los dos primeros ocurren incluso en
un cristal perfecto y dependen solo del dopaje, así que imponen un techo que ningún material con ese
dopaje puede superar. Se calculan con los coeficientes del Anexo B: radiativo 4,73×10⁻¹⁵ cm³/s y
Auger 4×10⁻³¹ cm⁶/s.

El Anexo B entrega solo la suma de los dos coeficientes de Auger. Para un minoritario en material
dopado interviene uno solo, así que usar la suma da un techo algo más bajo que el real. Con el
coeficiente de electrones solo (2,8×10⁻³¹, valor de la literatura) el techo del emisor sería 1,0 ns
en lugar de 0,69 ns: la conclusión no cambia.

**Lo que se encontró.**

| Región | Dopaje | Techo radiativo | Techo Auger | Techo total | Valor del control |
|---|---|---|---|---|---|
| Base | 4×10¹⁶ cm⁻³ | 5,3 ms | 1,6 ms | 1,2 ms | 30 µs · posible |
| Emisor | 6×10¹⁹ cm⁻³ | 3,5 µs | 0,69 ns | 0,69 ns | 1 µs · **1440 veces por encima** |

En la base el tiempo de vida de la semilla es perfectamente posible: leído como vida efectiva, el
97,5 % de la recombinación en el volumen es SRH, el 1,9 % Auger y el 0,6 % radiativa. En el emisor no:
con 6×10¹⁹ donantes por cm³, ni un cristal perfecto supera 0,69 ns, y el valor por defecto de 1 µs
—que no viene de la semilla sino de una elección nuestra— es imposible. Más aún: **el mínimo del rango
que fija el enunciado para τ_p, 0,1 µs, sigue estando 144 veces por encima del techo**. Ningún valor
permitido del control es físico para el dopaje asignado.

**Qué se hizo.** El modelo no se modificó. Se agregaron dos vigilancias al monitor en vivo (M-10 para
el emisor, M-11 para la base) que avisan cuando la vida elegida supera el techo, y el reparto de la
recombinación en el volumen entre los tres mecanismos solo se muestra cuando es físicamente posible.

**Qué se evaluó.** Incorporar la recombinación radiativa y la de Auger al modelo, de modo que el
control fuera la vida SRH y la vida efectiva se combinara con las dos intrínsecas como indica la
lámina 25. Se calculó el efecto completo sobre la celda de la semilla:

| Magnitud | Modelo actual | Con radiativa y Auger |
|---|---|---|
| Longitud de difusión del emisor | 12,8 µm | 0,34 µm |
| Corriente de cortocircuito | 14,55 mA/cm² | 9,42 mA/cm² |
| Voltaje de circuito abierto | 587,1 mV | 573,6 mV |
| Eficiencia | 6,57 % | 4,10 % |
| Eficiencia cuántica interna a 450 nm | 20,9 % | 0,0 % |
| Coeficiente térmico del voltaje (V6) | −2,21 mV/°C | −2,25 mV/°C |

Con el coeficiente de Auger propio de cada portador (literatura) en vez de la suma del Anexo B, las
cifras cambian menos de 1 %.

**Decisión: no se incorpora.** Queda como limitación declarada del modelo. Dos razones:

- Con el emisor de 5 µm que fija el enunciado, Auger anula por completo la respuesta en el azul
  para cualquier velocidad de recombinación frontal: la eficiencia cuántica interna a 450 nm vale
  0 % con S_f de 10, de 2×10⁴ o de 10⁶ cm/s. Eso borra el comportamiento que el enunciado pide
  reproducir (la respuesta en el azul dominada por la superficie frontal, lámina 30 de la Unidad 3)
  y que anuncia como pregunta de la presentación. Con un emisor de 0,3 µm el comportamiento vuelve,
  lo que explica por qué los emisores industriales son delgados.
- Cambiaría todas las cifras reportadas y se apartaría del modelo simplificado que entrega el
  enunciado, en el que τ_n y τ_p son vidas medias efectivas del portador minoritario.

**Consecuencia que hay que declarar.** Con el dopaje asignado, la colección en el emisor está
sobreestimada: el modelo le permite al hueco recorrer 12,8 µm cuando físicamente no alcanzaría a
recorrer 0,4 µm. El monitor en vivo lo señala con la vigilancia M-10, que por eso aparece como aviso
en el estado inicial de la aplicación, y la pestaña lo explica.

---

## D-34 · Destino de un par: juntura, superficie o volumen — [FÍSICA NUEVA]

**Por qué.** La probabilidad de colección del enunciado dice cuántos pares llegan a la juntura, pero
no qué les pasa a los demás. Para mostrar las pérdidas separadas por causa, que es lo que permite
entender qué parámetro controla cada una, hacía falta repartir el resto.

**Cómo.** La probabilidad de que un par muera en la superficie sale de la misma ecuación de difusión
que el enunciado resuelve para la colección, con las condiciones de borde intercambiadas: vale cero en
el borde de la zona de depleción, y la superficie pasa a ser el destino que se cuenta. Tiene solución
cerrada con la misma estructura hiperbólica y se escribe en la misma forma estable. La probabilidad de
recombinarse en el volumen es lo que falta para completar uno.

**Verificación.** La solución cerrada se contrastó con una resolución independiente de la ecuación de
difusión por diferencias finitas, con 4001 nodos: coincide hasta 10⁻⁹ en el emisor y en la base, tanto
para la colección como para la captura superficial. La probabilidad de volumen nunca sale negativa, y
las tres suman uno hasta la precisión de la máquina. El monitor lo vigila en vivo (M-05).

**Consecuencia.** El reparto de fotones pasa de siete destinos a diez: tres pérdidas ópticas
(reflexión, absorción en el aluminio, escape tras rebotar), cuatro de recombinación (superficie y
volumen en cada región) y tres que producen corriente. C-T9 se actualizó a los diez destinos.

---

## D-35 · Un control de iluminación para toda la aplicación — [DISEÑO]

Hasta ahora el modo de un solo color o espectro completo existía solo dentro de la animación 3D, y el
resto de la Pestaña 1 mezclaba figuras de un color con cifras de todo el espectro. Se reemplaza por un
único control en la barra lateral, que gobierna todas las vistas que lo admiten: el diagrama de
recorrido, la animación, la tabla de destinos, el perfil de generación, el balance y el viaje del
fotón. En modo espectro las cifras se expresan en mA/cm²; en modo de un color, como fracción de los
fotones de ese color, que es su eficiencia cuántica externa.

Por ahora lo usa la Pestaña 1. En las Pestañas 3 y 4 el modo de un color significa un ensayo I-V con
luz monocromática, que cambia la definición de la corriente y de la eficiencia y toca V3 y V7; se
incorpora al revisar esas pestañas. La Pestaña 2 es espectral por definición.

---

## D-36 · Reflexión frontal de valor fijo, como pide el enunciado — [REQUISITO FALTANTE]

El enunciado lista entre los controles de la Pestaña 1 la reflexión frontal «de silicio desnudo o
valor fijo». Solo existía la primera. Se agrega el modo de valor fijo, con un deslizador entre 0 y
0,95 y valor inicial 0,30, el promedio del Anexo B. La interfaz frontal usa el mismo valor para la luz
que intenta salir desde adentro, coherente con D-32.

Es una propiedad de la celda, no de la vista, así que llega a las cuatro pestañas de contenido y a las
verificaciones, incluidas sus claves de caché (D-22).

---

## D-37 · La Pestaña 1 describe la misma celda que las Pestañas 2, 3 y 4 — [INCONSISTENCIA CORREGIDA]

Dos diferencias hacían que la corriente de la Pestaña 1 no fuera la de la Pestaña 3:

- La Pestaña 1 no descontaba la sombra de la malla de plata: reportaba 15,03 mA/cm² donde la
  Pestaña 3 usa 14,57. Ahora la malla es el primer paso del recorrido, porque físicamente la luz
  choca primero con los dedos.
- La Pestaña 1 usaba la colección de la celda homogénea nominal, mientras las otras usan la
  promediada por área sobre los sectores (D-28). Con dispersión cero coinciden; con dispersión no.
  Ahora usa la promediada, extendida a los tres destinos.

El monitor lo vigila en vivo (M-20): las dos pestañas deben entregar la misma corriente fotogenerada
con una diferencia menor a una parte por millón.

---

## D-38 · Monitor físico en vivo — [VALIDACIÓN NUEVA]

Las 21 verificaciones de `checks.py` son una certificación: corren siempre sobre la celda de la
semilla. Ninguna miraba los controles, así que un parámetro sin sentido no producía ningún aviso.

Se agrega un segundo sistema que corre en cada ejecución sobre los valores actuales. No recalcula:
cada pestaña publica en un registro común lo que ya resolvió, y el monitor evalúa sobre eso. Distingue
tres estados: EN ORDEN; AVISO, cuando el cálculo es correcto pero lo pedido no es físicamente posible o
se sale de un supuesto del curso; y FALLA, cuando se rompe algo que el modelo debe cumplir para
cualquier parámetro.

| Código | Vigilancia | Si no se cumple |
|---|---|---|
| M-01 | Balance de fotones (V1 en vivo) | FALLA |
| M-02 | Todos los destinos del fotón suman uno (C-T9 en vivo) | FALLA |
| M-03 | Colección entre 0 y 1 antes del recorte (C-T1 en vivo) | FALLA |
| M-04 | Colección unitaria en los bordes de la zona de depleción (C-T2 en vivo) | FALLA |
| M-05 | Juntura, superficie y volumen suman uno | FALLA |
| M-06 | Eficiencia cuántica bajo 1 − R (V5 en vivo) | FALLA |
| M-07 | La grilla resuelve la absorción más superficial | FALLA |
| M-08 | La zona de depleción cabe en el emisor (el aviso de D-21, que nunca se mostraba) | AVISO |
| M-09 | Zona de depleción angosta frente a la difusión (U3, lámina 15) | AVISO |
| M-10 | Vida media del emisor bajo el techo intrínseco (D-33) | AVISO |
| M-11 | Vida media de la base bajo el techo intrínseco (D-33) | AVISO |
| M-20 | Las Pestañas 1 y 3 entregan la misma corriente fotogenerada (D-37) | FALLA |

El resumen queda arriba de la barra lateral, visible desde cualquier pestaña; los avisos de la
Pestaña 1 aparecen además dentro de ella, y la tabla completa en la Pestaña 5. Las demás pestañas se
incorporan al revisarlas.

---

## D-39 · Figuras de la Pestaña 1 rehechas — [FIGURAS]

**El mapa λ-x vuelve.** D-31 lo había retirado, y eso dejó sin cumplir una salida obligatoria del
enunciado: «el mapa bidimensional de generación en el plano λ–x, que es la gráfica que muestra a qué
profundidad se absorbe cada color». Se reconstruye con otra cantidad: la probabilidad de que un fotón
que entró se absorba en cada capa, con capas de igual ancho en escala logarítmica. Así cada color es
comparable con los demás sin normalizarlo contra sí mismo, que era el defecto de fondo de D-29. Lleva
las líneas del 50 % y el 90 % absorbido, porque el enunciado anuncia la pregunta de predecir el 90 % a
450 y 950 nm y verificarlo en este mapa.

**La cascada pasa a ser un diagrama de flujo proporcional** (Sankey), con las diez rutas y la malla.

**La penetración por color pasa a ser un corte de la celda con un rayo por color**, conservando la
curva continua 1/α(λ) superpuesta al espesor que exige el enunciado.

**La probabilidad de colección se muestra completa:** para cada profundidad, cuántos pares llegan a
la juntura, cuántos mueren en una superficie y cuántos en el volumen. El borde de la banda verde sigue
siendo la curva f_c(x) del enunciado.

**La generación se reparte en los mismos tres destinos**, y sigue mostrando G(x) con la juntura
marcada.

**Terminología.** «Zona de deplexión» no es un término del español. El enunciado y la Unidad 3
(lámina 15) usan «zona» o «región de depleción». Se adopta «zona de depleción (juntura p-n)».

**Figuras nuevas.** Un diagrama de recorrido al comienzo que integra las cifras principales, y el
viaje de un fotón: una animación en corte transversal con narración, cuyas bifurcaciones se sortean
con las probabilidades del modelo. Su escala vertical es esquemática y la forma del camino de difusión
es ilustrativa; las dos cosas se declaran en la propia figura.

---

## D-40 · Ajustes de la Pestaña 1 tras la revisión del usuario — [FIGURAS]

**La animación 3D marca cada par donde nació.** En la versión de D-39 los pares que llegaban a la
juntura se desplazaban hasta el plano de la juntura y los que morían en una superficie hasta esa
superficie, así que al terminar la base quedaba casi vacía. No era un error de física, pero se perdía
la información de dónde se absorbe cada color y parecía que casi ningún par nacía en el medio. Ahora
cada par queda marcado en el lugar donde nació, con el color de su destino, y una línea recta lo une
con el lugar donde terminó. La línea indica el destino, no el camino: el recorrido real del portador
es una difusión al azar.

Las cruces rosadas, recombinación en el volumen, son escasas con la semilla por una razón física: la
longitud de difusión de la base, 314 µm, triplica su espesor, y en el emisor la superficie frontal
captura los pares antes que el volumen. Solo el 1,5 % de los pares se recombina en el volumen, aunque
el 27 % nace a más de 10 µm de profundidad. Con τ_n = 0,1 µs la fracción sube al 20 %. La pestaña lo
explica con cifras calculadas en vivo.

**El mapa λ-x se transpone.** La profundidad pasa al eje horizontal y la longitud de onda al vertical,
de modo que al avanzar hacia adentro de la celda se lee cómo la absorción se corre a colores más largos.

**Colores reservados por Streamlit.** El tema de Streamlit usa ciertos colores, entre ellos #000004,
como marcadores internos y los reemplaza por colores de su paleta. El negro de la escala «inferno» es
exactamente ese, y el cero del mapa salía rojo. Se escribe la escala punto por punto con un negro
equivalente que no coincide con los marcadores. Conviene evitar colores de la forma #0000XX en
cualquier figura.

---

## D-41 · Los sectores varían desde el estado inicial, con correlación espacial — [MODELO CORREGIDO]

**Qué pasaba.** El estado inicial traía la variación de fabricación en cero, por la razón de D-28: la
Tabla A.1 describe una celda homogénea. Con eso los 64 sectores eran idénticos y el mapa de eficiencia
cuántica de la Pestaña 2 salía plano. Pero el enunciado pide explícitamente que la celda se divida en
una grilla de al menos 8 × 8 sectores, **cada uno con su propio τ local y su propia S_frontal local**,
y que se muestre el mapa de la IQE local. Un estado inicial homogéneo no cumple eso.

Además, cuando la variación se subía, cada sector se sorteaba independiente de sus vecinos: un ruido
blanco, con correlación de 0,23 entre sectores contiguos, que se ve como un tablero al azar y no como
una oblea.

**Corrección.**

- La variación se genera con un campo aleatorio suave: se sortea un valor por sector y se promedia con
  sus vecinos con peso gaussiano de ancho 1,2 sectores, unos 2,3 cm sobre la oblea de 15,6 cm. Sectores
  vecinos se parecen, porque las causas reales —la historia térmica del lingote, la uniformidad del
  horno de difusión— actúan sobre regiones extensas. Parámetro de diseño declarado.
- El campo se normaliza a media cero y desviación uno, así que los valores de la barra lateral son
  exactamente la media geométrica de los sectores: la semilla sigue describiendo la celda.
- τ_n y S_f se sortean de forma independiente, porque uno es un defecto del volumen y la otra de la
  superficie.
- El estado inicial trae una variación de **0,25** en el logaritmo: sectores entre unas 0,6 y 1,6 veces
  el valor nominal.

**Efecto sobre las cifras.** La corriente de la celda sube de 14,5526 a 14,5742 mA/cm² (+0,15 %), porque
la colección no es lineal en τ y S_f. La eficiencia pasa de 6,5726 % a 6,5829 %. La certificación se
actualizó para usar la misma celda que muestra la aplicación: V3, V5, V6, V7, C-T3 y C-T9 promedian la
colección sobre los sectores del estado inicial. C-T6 sigue comparando la celda homogénea, que es lo que
dice verificar. Las 21 verificaciones pasan.

**En el mapa.** A 450 nm la IQE local varía entre 14,7 % y 24,9 %; a 900 nm, entre 82,0 % y 83,8 %. El
promedio del mapa coincide con la IQE de la celda hasta 10⁻¹⁶.

---

## D-42 · Pestaña 2 rehecha — [FIGURAS · VALIDACIÓN]

**Portada.** Un diagrama del recorrido de los fotones de un color hasta la eficiencia cuántica, con las
cifras del color del ensayo, y cuatro cifras de diagnóstico: EQE media, IQE en el azul y en el rojo, y el
rango entre sectores. La corriente se informa con y sin la sombra de la malla, para que coincida con la
de las Pestañas 1 y 3.

**Qué parte de la curva informa sobre qué parte de la celda.** Reemplaza la familia de curvas por vida
media, que respondía una sola pregunta. Tres paneles cambian un parámetro cada uno —recombinación frontal,
vida media de la base, espesor de la base— y sombrean los colores donde las curvas se separan más de 3
puntos. Responde directamente la pregunta de la presentación. El panel de vida media usa ahora los valores
de la lámina 30 de la Unidad 3 (10, 50 y 200 µs). En esta celda su efecto en el rojo es moderado, porque
incluso con 10 µs la longitud de difusión, 181 µm, supera la base de 100 µm; con una base de 300 µm las
mismas vidas medias separan el rojo de 950 nm en 12,7 puntos, y la pestaña lo informa.

**Relieve de los sectores.** Se conserva la superficie tridimensional original, que pasa por el centro de
cada sector, con altura y color iguales a su IQE local. Se probó una versión con una columna por sector y
se descartó: la superficie resultó más legible, y con la variación suave de D-41 unir los sectores es una
representación razonable. Se le agregó un plano translúcido en la IQE de la celda y los valores locales de
vida media y recombinación frontal al pasar el cursor. El eje vertical se ajusta al rango de los sectores y
lo declara en el subtítulo; un control lo lleva a la escala completa. El relieve antiguo se veía plano
porque la celda era homogénea, no por el tipo de gráfico. Se agregan los mapas de las causas —vida media y
recombinación frontal locales— y la correlación del relieve con cada una, calculada en vivo: en el azul
sigue a la superficie; en el rojo, a la vida media.

**Cómo se calcula.** Una sección explica de qué trata, los cuatro pasos del cálculo y qué observar en el azul, el rojo y el infrarrojo, con cifras en vivo. Una animación recorre el espectro. Para cada color muestra dónde se absorben los
fotones y cuáles de los pares llegan a la juntura, dibujados por década de profundidad para que las áreas
sean proporcionales, y construye la curva punto por punto. Informa también la respuesta espectral, que es
lo que mide el instrumento (Unidad 3, lámina 27).

**Monitor en vivo.** Vigilancias nuevas:

| Código | Vigilancia | Si no se cumple |
|---|---|---|
| M-21 | El promedio del mapa es la IQE de la celda (C-T7 en vivo) | FALLA |
| M-22 | Ningún sector supera el 100 % de IQE (V5 local) | FALLA |
| M-23 | Las vidas medias locales de la base bajo su techo intrínseco | AVISO |
| M-24 | El azul no depende de la vida media de la base (lámina 30) | AVISO |
| M-25 | La corriente de la curva de la Pestaña 2 es la del balance de la Pestaña 1 | FALLA |
| M-26 | La eficiencia por fotón absorbido no supera el 100 % (D-43) | FALLA |

---

## D-43 · La eficiencia por fotón absorbido contaba una sola pasada — [ERROR CORREGIDO]

**Qué pasaba.** La curva de eficiencia por fotón absorbido de la Pestaña 2 (D-24) dividía la EQE por
la absorción de una sola pasada, (1 − R)·(1 − e^(−αW)). Sin reflector trasero es la absorción correcta.
Con el reflector activo, en cambio, la EQE ya incluye los pares que genera la luz devuelta por el
aluminio, pero el divisor no la contaba: a 1100 nm la curva marcaba 214 % y a 1190 nm, 223 %. Se
encontró al preparar el manual de la Pestaña 2.

**Corrección.** El divisor es ahora lo que el silicio absorbe de verdad: la integral del perfil de
generación dividida por el flujo que llega. Cuenta exactamente lo mismo que la EQE —todos los rebotes
del reflector, con la reflectancia elegida— y sin reflector coincide con la fórmula anterior. Con el
reflector, el máximo de la curva queda en 86,4 %, casi igual al de la celda sin reflector, 86,7 %, como
debe ser: el reflector agrega luz, no cambia la calidad de la colección.

**Vigilancia nueva.** M-26 comprueba en cada ejecución que esa curva no supere el 100 %, con nivel de
falla. Habría detectado el error. El monitor pasa a 18 vigilancias; con la semilla, 17 en orden y el
aviso de M-10 (D-33).

---

## D-44 · La malla frontal, contada como proceso — [FIGURAS]

**Qué pasaba.** La Pestaña 3 cerraba con un gráfico que superponía tres curvas con tres unidades
distintas: el área sombreada en por ciento, la resistencia serie en ohm por centímetro cuadrado y la
eficiencia en un tercer eje sin marcas. Mostraba que existe un óptimo, pero no dejaba ver por qué, y no
permitía comparar las dos pérdidas, que es justamente lo que el enunciado pide mostrar.

**Qué se hizo.** La sección pasa a contar el compromiso en tres pasos.

1. **El viaje de una carga.** Un relieve en tres dimensiones con el voltaje que pierde una carga según
   dónde se recogió: cero sobre un dedo, máximo a medio camino entre dos —una parábola, porque la
   corriente se va acumulando— y creciendo hacia la barra colectora a lo largo del propio dedo. Las dos
   expresiones que dibuja el relieve son las mismas cuyo promedio da la resistencia de la malla, así que
   la figura muestra de dónde salen esas fórmulas. Con la semilla: 6,77 mV en el emisor y 2,93 mV en el
   dedo, sobre un voltaje de trabajo de 0,493 V.
2. **Cuánto cuesta cada cosa.** Las dos pérdidas se llevan a una sola unidad, puntos de eficiencia,
   resolviendo la curva I-V completa en cada caso (`physics/compromiso.py`). La resta es secuencial y el
   orden está declarado: a la celda sin malla se le agrega primero la sombra, después la resistencia del
   emisor y al final la de los dedos. Las tres suman exactamente la distancia entre la celda sin malla y
   la celda real. Se apilan contra el número de dedos, y el mínimo de la pila es el óptimo, sin comparar
   ejes distintos. Con la semilla: 60 dedos cuestan 0,315 puntos y el óptimo son 50 dedos, con 0,309.
3. **El recorrido.** Una animación agrega dedos de a poco, con la curva I-V a la izquierda y las tres
   pérdidas a la derecha. Cada cuadro es una celda resuelta de verdad: 39 mallas, tres curvas completas
   cada una.

**Costo.** El barrido resuelve 118 curvas. Con 70 voltajes por curva —el punto de máxima potencia se
afina aparte, así que la eficiencia coincide en la sexta cifra con la de 420 puntos— toma 1,9 s, y queda
en caché aparte, porque no depende del número de dedos elegido: al moverlo solo se mueve la marca.

---

## D-45 · Cómo se resuelve la curva, y dónde está la trampa — [FIGURAS]

**Qué faltaba.** La pestaña advertía que la ecuación es implícita y comparaba dos factores de forma, pero
no mostraba el cálculo. Tampoco quedaba a la vista qué hace cada parte del circuito equivalente en cada
punto de la curva.

**Qué se hizo.** Una sección final, con la misma forma que la de la Pestaña 2.

- **Un circuito equivalente con las cifras del punto elegido**, dibujado en SVG: la corriente que genera
  la luz repartida entre el diodo, la resistencia paralela y el circuito, y la caída sobre la resistencia
  serie. Un control elige el punto como fracción del voltaje de circuito abierto —no en volts— para que
  el control siga siendo válido cuando el voltaje de circuito abierto cambia con la temperatura o la
  irradiancia. En el punto de máxima potencia de la semilla: de 14,59 mA/cm², el diodo se lleva 0,73 y la
  fuga 0,506; salen 13,35, y la resistencia serie consume 13,1 mV.
- **Una animación del barrido** que, para cada voltaje, dibuja la función que el programa anula y marca
  su raíz, junto a la curva que se va armando. La cruz gris es lo que daría la forma explícita: coincide
  con la raíz a voltaje bajo y se separa cerca del punto de máxima potencia, que es donde el error
  importa. En la semilla, el atajo da 13,64 en lugar de 13,35 mA/cm², un 2,2 % de más.

**Corrección de texto.** La pestaña decía que la verificación V4 detecta el error de la forma explícita.
No puede: V4 se evalúa con resistencia serie nula, y sin ella las dos formas coinciden. La verificación
que lo detecta es C-T5, que evalúa con resistencia no nula (D-27). El enunciado tiene la misma
imprecisión —menciona V5, que en su propia tabla es la cota de la eficiencia cuántica—, y así queda
declarado.

---

## D-46 · Portada de la Pestaña 3, y dos figuras que salieron — [FIGURAS]

**La portada.** La pestaña abría con cuatro cifras sueltas. Ahora abre como las Pestañas 1 y 2: un
recorrido de seis tarjetas que va de la corriente a la potencia —corriente fotogenerada, cortocircuito,
voltaje de circuito abierto, punto de trabajo, factor de forma y potencia— cada una con la pérdida que
explica el paso siguiente, y seis cifras debajo, con la potencia máxima y la resistencia serie desglosada
entre la malla y el resto del circuito. La primera tarjeta declara que la corriente viene de las Pestañas
1 y 2, que es lo que exige V3 y vigila M-25.

Dos cifras que la portada deja a la vista y antes no estaban: el **déficit de voltaje**, 0,532 V bajo la
banda prohibida —la celda sostiene el 52,5 % del techo—, y la **distancia al factor de forma ideal**,
0,0479. Las dos son las que necesita el balance de potencia.

**Dos figuras que salieron.** El relieve en tres dimensiones de la caída de voltaje y la animación del
número de dedos se sacaron a pedido del usuario: eran vistosas, pero el lector no distinguía qué pregunta
respondían que no respondiera ya el gráfico del compromiso. Lo que el relieve explicaba —de dónde salen
las dos expresiones de la resistencia de la malla y cuánto cuesta el viaje de una carga, 6,77 mV en el
emisor y 2,93 en el dedo— quedó como texto con las mismas cifras, calculadas igual. El reparto de la
pérdida en puntos de eficiencia se queda: es la figura que responde el «debe verse el compromiso» del
enunciado, y sin ella la pestaña no lo cumple.

**Regla que queda.** Una figura se justifica por la pregunta que responde, no por cómo se ve. Si su
pregunta ya está respondida en otra parte, sale.

---

## D-47 · Balance de potencia de la Pestaña 3 — [FIGURAS]

**Qué faltaba.** La pestaña informaba que la celda entrega 6,58 % y no decía dónde quedaba el 93,4 %
restante. El enunciado pide comparar el factor de forma con el ideal y mostrar el compromiso de la
malla, pero la lectura de conjunto —qué pérdida pesa más y cuál se puede corregir— no estaba en ninguna
parte.

**La convención, declarada en pantalla.** Cada par que llega a la juntura vale la energía de la banda
prohibida; todo lo que el fotón traía de más ya se contó como termalización. Con eso, cada fotón perdido
cuesta lo mismo —la banda prohibida por su carga— y las pérdidas eléctricas se miden sobre lo que
sobrevive. Es la contabilidad del límite de eficiencia de la Unidad 4, aplicada a esta celda.

**El reparto con la semilla**, en mW/cm² sobre los 100,04 que trae el espectro:

| Etapa | mW/cm² | Familia |
|---|---|---|
| Bajo la banda prohibida, más de 1108 nm | 19,23 | lo impone el silicio |
| Termalización | 31,75 | lo impone el silicio |
| Malla de plata | 1,51 | óptica |
| Reflexión en la superficie | 16,74 | óptica |
| Luz que no se absorbe | 4,26 | óptica |
| Recombinación en la superficie frontal | 9,35 | recombinación |
| Recombinación en el volumen y atrás | 0,88 | recombinación |
| Déficit de voltaje | 7,76 | eléctrica |
| Pérdida de forma y fuga | 1,98 | eléctrica |
| **Entregada** | **6,58** | |

**Coherencia.** El reparto óptico y de recombinación sale de los mismos diez destinos de la Pestaña 1,
restringidos a los fotones sobre la banda prohibida: los diez más la malla suman 49,055 mW/cm², que es
exactamente la energía que sobrevive a la termalización, calculada por separado desde el espectro. El
balance completo cierra con un error de 8×10⁻⁴ mW/cm². La última pérdida se calcula como resto, así que
el cierre es exacto por construcción y lo que mide el error es la corriente que aportan los fotones de
más de 1108 nm, que el coeficiente de absorción medido todavía absorbe un poco.

**Lo que se aprende.** Las dos pérdidas mayores, 51 mW/cm², no dependen del diseño. De las que sí, la
reflexión sola se lleva 16,7 mW/cm², más del doble de lo que la celda entrega, porque el enunciado pide
la superficie pulida y sin recubrimiento antirreflejo. La pestaña lo cuantifica en vivo: con una
reflectancia del 5 %, la misma celda daría 9,66 % en lugar de 6,58 %.

**Precisiones declaradas.** El espectro se integra completo, incluidos los fotones de más de 1200 nm que
el modelo óptico no recorre, porque su energía llega igual; los de menos de 300 nm aportan menos de
0,001 mW/cm² y quedan dentro de la termalización. La potencia incidente del balance es la del archivo,
100,04 mW/cm², mientras que la eficiencia usa los 100,00 de referencia: 0,04 % de diferencia.

---

## D-48 · La Pestaña 4, rehecha: fallas con forma de falla y zonas que se apagan solas — [MODELO · FIGURAS]

**Qué estaba mal.** La física eléctrica estaba bien —sectores en paralelo a voltaje de terminal común, con
su propia fotocorriente, su corriente de saturación y su resistencia— pero las fallas no. La contaminación
era un rango de filas por un rango de columnas, un rectángulo perfecto; el defecto resistivo, una columna
entera sin dedo. Ninguna falla de laboratorio tiene esa forma. Peor: las zonas apagadas había que
dibujarlas, cuando en una celda real aparecen porque un trozo se quedó sin camino hacia la barra
colectora.

**Malla fina y malla de reporte.** La física se resuelve ahora sobre 48 × 48 celdas de 3,25 mm, seis por
cada sector de los 8 × 8 que exige el enunciado, que se mantienen como grilla de reporte y se dibujan
encima de los mapas. Cada celda fina sigue siendo un problema unidimensional: su lado es diez veces la
longitud de difusión de la base. El campo de fabricación fino se construye como el de 8 × 8 más un detalle
de promedio cero dentro de cada sector, así que **la media geométrica de cada bloque es exactamente el
sector que usa la Pestaña 2**: las dos pestañas describen la misma celda y ninguna cifra de referencia se
movió. Lo vigila M-40.

**Las dos fallas.**

- **La grieta se propaga.** Avanza con dirección persistente, gira un poco al azar en cada paso y se
  ramifica con cierta probabilidad. Por debajo de severidad 0,5 nace en un borde; por encima, de un punto
  de impacto, del que salen tres brazos. Corta los dedos que cruza: no se eligen, se calculan.
- **La contaminación es una mancha.** El mismo generador de campo correlacionado de la celda, recortado
  por encima de un umbral: bordes irregulares, como una mancha real. La severidad mueve a la vez el área
  y la caída del tiempo de vida, hasta mil veces menos en el núcleo.

**El camino eléctrico, que es lo que cambia todo.** Para cada celda fina se calcula el recorrido de la
corriente hasta la barra colectora: cruzando el emisor hasta el dedo útil más cercano —esquivando la
grieta, que también corta el silicio— y después por el propio dedo. Las dos resistencias usan las mismas
expresiones cuyo promedio da la resistencia de la malla sana, así que **sin grieta el cálculo reproduce el
valor analítico dentro del 0,2 %**: ésa es su calibración, y M-41 la comprueba en vivo. Una celda sin
ningún camino queda aislada y se apaga sola. La fragmentación dejó de dibujarse y pasó a ser un resultado.

**Electroluminiscencia.** El brillo de cada trozo va con la exponencial del voltaje que ve su juntura, que
el solver ya calcula. Un trozo lejos del metal brilla varias veces menos que uno bien conectado aunque
genere la misma corriente, y uno aislado sale negro: es exactamente lo que detecta el ensayo real, y lo que
el mapa de corriente no puede ver.

**Propagación a la Pestaña 3.** El enunciado la pide con esas palabras. La celda con fallas se resuelve en
un módulo compartido, `ui/danos.py`, y la Pestaña 3 dibuja la curva dañada junto a la sana con la caída de
eficiencia escrita en la leyenda. Como ambas pestañas piden el mismo cálculo por caché, la segunda no paga
nada.

**Lo que costó hacerlo posible.** Con la malla fina, el código anterior habría tardado más de veinte
segundos por ejecución. Se vectorizaron dos cosas:

| | Antes | Ahora |
|---|---|---|
| Colección de los sectores | bucle, 64 llamadas | una operación; 48 × 48 en 115 ms |
| Curva global | bisección, 80 pasos por voltaje | Newton con red de seguridad, arrancando en la solución del voltaje anterior |
| Curva de 64 sectores | 633 ms | 69 ms |
| Curva de 2304 sectores | ~23 s estimados | 0,1 a 0,8 s |

Dos detalles del solver que importan: el intervalo de búsqueda se acota entre el voltaje de terminal y el
circuito abierto local del sector —no con la caída sobre la resistencia serie, que para un sector aislado
daría miles de volts— y cada voltaje arranca donde terminó el anterior, que es lo que baja las iteraciones
de cuarenta a tres o cuatro.

**Verificaciones.** Las 21 de la certificación siguen pasando, y C-T6 y C-T8 ahora coinciden **exactamente**
—587,1002 mV y 14,58327 mA/cm²— porque las dos vías parten de la misma resistencia serie. El monitor sube a
21 vigilancias con M-40 (identidad por bloques), M-41 (calibración del camino) y M-42 (las Pestañas 3 y 4
dan la misma celda sin fallas).

**Límites declarados.** El camino eléctrico es el de menor distancia hasta el dedo útil más cercano, no la
solución de la red completa de resistencias. No hay acoplamiento lateral entre celdas vecinas ni balance
térmico: el modelo no calcula temperatura, así que no predice puntos calientes.

---

## D-49 · Siete vigilancias para la Pestaña 3 — [VALIDACIÓN]

**Qué faltaba.** El monitor vigilaba las Pestañas 1, 2 y 4, pero de la Pestaña 3 solo miraba la coherencia
de su corriente con las otras. Lo que la pestaña calcula por dentro —el solver implícito, el punto de
máxima potencia, el régimen de validez— no tenía ninguna vigilancia. El aviso de voltaje mayor que la banda
prohibida era un mensaje suelto dentro de la pestaña, invisible desde la de Validación.

| Código | Vigilancia | Qué comprueba | Nivel |
|---|---|---|---|
| M-30 | Cada punto de la curva cumple la ecuación del diodo | Evalúa el residuo en los 420 puntos con la corriente publicada: si el solver hubiera resuelto la forma explícita, el residuo sería del orden de la caída sobre la resistencia serie | FALLA |
| M-31 | La resistencia serie no toca el voltaje de circuito abierto | En circuito abierto no circula corriente, así que la ecuación en ese punto no contiene la resistencia serie: se comprueba que se anula sin ella | FALLA |
| M-32 | Voltaje de circuito abierto frente a la banda prohibida | Reemplaza el mensaje suelto. Salta con factor de idealidad 2, donde el modelo da 1,172 V contra un techo de 1,119 | FALLA |
| M-33 | Factor de forma frente al ideal de la Unidad 4 | El ideal sin resistencias parásitas es su techo | AVISO |
| M-34 | El punto de máxima potencia es el máximo de la curva | El refinamiento entre los dos vecinos del máximo grueso tiene que mejorarlo, nunca empeorarlo | FALLA |
| M-35 | Baja inyección en circuito abierto | El exceso de portadores frente al dopaje de la base. Salta junto con M-32, porque es la misma causa | AVISO |
| M-36 | El balance de potencia cierra | Todas las etapas suman la potencia incidente, dentro de 0,05 mW/cm² | FALLA |

**Un error que encontró M-34.** El refinamiento del punto de máxima potencia buscaba entre los dos vecinos
del máximo con una grilla de 60 puntos —número par—, que no contiene al máximo grueso. A 15 °C eso devolvía
una potencia una fracción por debajo de la de partida. Con 61 puntos el máximo grueso queda dentro y el
refinamiento solo puede mejorar.

**Probado en diez regímenes**: la semilla, factor de idealidad 2, 1,5 soles, 15 y 75 °C, resistencia serie
de 5 Ω·cm², resistencia paralela de 10, vida media de 1000 µs con superficie pasivada, emisor de 0,2 µm con
reflector y reflectancia fija en cero. Solo saltan M-32 y M-35, y saltan donde deben: con el factor de
idealidad en 2, que es el régimen que el modelo no puede describir. El monitor queda en 28 vigilancias.

