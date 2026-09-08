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
