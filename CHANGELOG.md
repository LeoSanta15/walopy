# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [Sin publicar]

Sin cambios todavía.

---

## [0.5.0] — 2026-10-23

Versión que sale del mundo exponencial: la simulación de centros de contacto admite llegadas, servicio y paciencia con otras distribuciones, para medir cuánto se equivoca Erlang A. Solo añade capacidades: sin indicarlas todo es igual que en 0.4.15, bit a bit con la misma semilla.

### Añadido
- **`monte_carlo_erlang_a(..., arrivals, service, patience)`**: la forma de los tiempos entre llegadas de cada clase (proceso de renovación), del servicio y de la paciencia, siempre con media 1/λ, 1/μ y 1/θ. Cada uno acepta `'exponential'` (por defecto), `'deterministic'`,
  `('gamma', cv2)` (`cv2` = 1/k es Erlang-k), `('lognormal', cv2)` y `('hyperexponential', cv2)` (dos fases con medias balanceadas, `cv2` ≥ 1), donde `cv2` es varianza / media² (hasta 10 000). Una especificación vale para todas las clases o se da una lista con una por clase.
  El resultado (`ErlangASimulationResult`) guarda las distribuciones (`arrivals`, `service`, `patience`) y su `summary()` pasa a titularse G/G/c+G y las muestra.
- **`erlang_a_classes_servers(..., arrivals, service, patience)`**: la dotación mínima con esas distribuciones. Con cualquiera de ellas siempre simula (`method='exact'` da un error claro). Con dos clases de λ = 4 y 12 y abandono máximo del 3 %: 19 agentes con todo exponencial, 18 con servicio determinista, 20 con servicio hiperexponencial (CV² = 6) y 17 con paciencia determinista.
- Ejemplo: `examples/06_centro_de_contacto_erlang_a.py` compara Erlang A con otras formas (9 llamadas/min, 10 agentes): abandono 4,4 % exponencial, 3,2 % con servicio determinista, 5,4 % con servicio de CV² = 4, 0,04 % con paciencia determinista y 8,5 % con llegadas en ráfagas (CV² = 4).

### Qué enseña
El abandono es poco sensible a la forma del servicio (±30 % entre determinista y CV² = 4), pero muy sensible a la de la paciencia (con la misma media, la paciencia determinista casi elimina el abandono) y a la de las llegadas (casi el doble con ráfagas). Antes de fiarse de Erlang A conviene medir el CV² de cada tiempo y simular.

### Pruebas
- `tests/test_monte_carlo_distribuciones.py`: los momentos de cada familia; el caso exponencial idéntico a lo anterior bit a bit; las familias con CV² = 1 contra `erlang_a`; **M/G/1** (Pollaczek-Khinchine, `mg1`) para el servicio general; **G/M/1** (la raíz σ = A\*(μ(1 − σ))) para las llegadas
  generales; la **insensibilidad de Erlang B** (con paciencia casi nula el bloqueo no depende de la forma del servicio); una simulación de eventos escrita aparte (abandonos como eventos, generador de `random`) con distribuciones mixtas en dos clases; la ampliación del horizonte de las llegadas; la validación y la dotación.
  Nueve mutantes nuevos (`MU-72` a `MU-80`).

---

## [0.4.15] — 2026-10-23

Versión de dimensionamiento con K clases: la pregunta «¿cuántos agentes?» para los modelos de 0.4.11 a 0.4.14. Solo añade capacidades.

### Añadido
- **`erlang_a_classes_servers(lam, mu, theta, *, max_abandon, max_wait_prob, min_service_level, t, method, conservative, c_max, n_customers, n_replications, seed)`** y **`ErlangAStaffingResult`**: el menor número de servidores de M/M/c+M con 2 a 6 clases, prioridad y
  tiempo de servicio por clase que cumple **todos** los objetivos a la vez: abandono máximo por clase, nivel de servicio mínimo por clase (con un *t* común), y probabilidad máxima de esperar. Cada objetivo por clase es un número (para todas) o una secuencia con `None`
  donde no se pide. Es el equivalente de `erlang_a_servers` para varias clases.
- **Búsqueda**: parte de una **cota inferior rigurosa** (los servidores ocupados en promedio, Σ λₖ(1 − abandono máximoₖ)/μₖ, no superan a *c*), crece con pasos duplicados y bisecta; `evaluations` registra los tamaños probados y si cumplían.
- **`method`**: `'exact'` evalúa con `erlang_a_classes`; `'simulation'` con `monte_carlo_erlang_a` (cualquier *c*, K y μ), con la misma semilla en todos los tamaños (números aleatorios comunes, que hacen casi monótona la respuesta en *c*);
  `'auto'` (por defecto) usa el exacto donde llega (2 clases, o 3 con μ común, y *c* moderado si los μ difieren) y simula si no, o si el exacto supera su cota de cálculo. `conservative=True` exige el extremo adverso del intervalo del 95 %.
- Ejemplo: `examples/06_centro_de_contacto_erlang_a.py` calcula la dotación mínima con la carga base (10 agentes, exacto) y con diez veces más llamadas (82, simulación).

### Pruebas
- `tests/test_erlang_a_dotacion_clases.py`: el mínimo contra un barrido lineal c = 1, 2, … con el modelo exacto (abandono, nivel de servicio, P(esperar); 2 clases con μ distintos y 3 con μ común); la cota inferior; que con un servidor menos algún objetivo incumpla (la traza);
  la simulación contra lo exacto y el modo conservador; los respaldos de `'auto'` (K = 4, 3 clases con μ distintos, cota de cálculo superada) y la validación de entradas. Seis mutantes nuevos (`MU-66` a `MU-71`).

---

## [0.4.14] — 2026-10-22

Versión de simulación para centros de contacto grandes o con más clases: lo que los modelos exactos de 0.4.11 a 0.4.13 no alcanzan. Solo añade una función.

### Añadido
- **`monte_carlo_erlang_a(lam, mu, theta, c, *, n_customers, n_replications, warmup, t, seed)`** y **`ErlangASimulationResult`**: simulación de eventos de M/M/c+M con 1 a 6 clases, prioridad no expropiativa, abandono en cola y tasa de servicio por clase,
  con cualquier *c*. Es el mismo sistema que modela `erlang_a_classes`, sin sesgo de modelo: solo error estadístico, que se mide con réplicas independientes (un flujo por réplica derivado de `seed`) y se informa como semiancho
  del intervalo de confianza del 95 % (t de Student) de cada estimación: P(abandono) y Wq por clase, nivel de servicio por clase (con `t`) y P(esperar). El abandono no es un evento: al liberarse un servidor se descarta, en orden de llegada, a quien ya se había
  ido, lo que la hace rápida (≈ 1 s por millón de llegadas, casi independiente de *c*: 200 agentes y 2 millones de llegadas en 1,7 s).
- Ejemplo: `examples/06_centro_de_contacto_erlang_a.py` simula 80 agentes con VIP y estándar a tiempos de servicio distintos (abandono estándar ≈ 5,5 % ± 0,4 puntos).

### Explorado y descartado
Para «dos clases con μ distintos y muchos agentes» se probaron aproximaciones deterministas, y **ninguna** alcanzó una exactitud que justificara publicarla. Con el modelo exacto como referencia (c = 10 a 30, carga 0,85 a 1,15):
- *Jerarquía simple* (la clase alta como Erlang A aislado, la baja con la capacidad que le deja): error relativo ≈ 100 % en la clase alta (ignora que en sobrecarga todos los servidores los ocupa la baja y la alta espera una liberación).
- *Campo medio* (modelo exacto de μ común con una tasa efectiva calibrada por la ley de conservación E[ocupados] = Σ λ_eff,k/μ_k): ≤ 3 % en sobrecarga con la clase alta más rápida, pero −14 a −17 % con carga 0,85 y la clase alta más lenta, y ese sesgo no baja con c.
- *Promediar la cola de la clase alta* (fases n₁ en vez de (n₁, q₁)), incluso conservándola exacta en los primeros 8 niveles de la cola baja: −8 a −28 % en la clase baja con carga 0,85. Con muchos agentes q₁ y q₂ saltan a la misma velocidad (≈ c·μ), y el promedio
  distorsiona la varianza de q₂, que gobierna el abandono cerca del equilibrio.
La simulación (sin sesgo de modelo, con error estadístico medido) es la herramienta fiable para esos casos; las aproximaciones asintóticas (QED/difusión) quedan como trabajo futuro con su propia validación.

### Pruebas
- `tests/test_monte_carlo_erlang_a.py`: contra los modelos exactos (2 clases con μ distintos, 3 clases, 1 clase = `erlang_a`, y c = 100 contra `erlang_a_priority`), con sus propios intervalos de confianza; reproducibilidad con semilla; el semiancho recalculado a mano con
  las mismas réplicas; que más llegadas lo estrechen ≈ √n; la prioridad ordena las esperas; y validación de entradas. Seis mutantes nuevos (`MU-60` a `MU-65`).

---

## [0.4.13] — 2026-10-22

Versión de centros de contacto con servicio heterogéneo: tiempos de servicio distintos por clase en Erlang A con dos clases y prioridad. Solo añade capacidades: con `mu` numérico todo es igual que en 0.4.12.

### Añadido
- **`erlang_a_classes(lam, mu, theta, c)` y `erlang_a_classes_service_level(...)` aceptan `mu` como secuencia** con la tasa de servicio de cada clase (p. ej. agentes senior que atienden más rápido a los VIP). Exacto, no una aproximación. Con
  tiempos distintos hay que seguir cuántos servidores ocupa cada clase (n₁ de alta y c − n₁ de baja), y la región sin cola, que ya no tiene forma cerrada, es una malla triangular de c(c+1)/2 estados. Se resuelve por niveles de la cola de la clase
  baja con fases (n₁, q₁); la bajada de nivel deja de ser diagonal pero tiene a lo más dos entradas por fila, así que N·D se calcula sin matrices intermedias. **Solo con 2 clases**: con más y μ distintos lanza `ValueError`.
- `ErlangAClassesResult.mu` es un número si es común, o una tupla con el de cada clase; `rho` es la proporción de servidores ocupados, Σ λ_eff,k /(μ_k·c); el resumen muestra una columna μ cuando difieren.
- Niveles de servicio con μ distintos, exactos por uniformización: la clase alta con estado (n₁, posición) y la baja con (n₁, a, posición), donde n₁ cambia cuando termina un servicio de baja y entra uno de alta.
- Con μ₁ = μ₂ el motor reproduce `erlang_a_priority` (cola, P(esperar), abandono y niveles de servicio, a 1e-8); la ocupación de cada clase cumple E[nₖ] = λ_eff,k/μₖ (a 1e-8); con una clase casi sin llegadas, la otra es `erlang_a` con su propio μ; y todo
  coincide con una simulación de eventos con μ distintos (10 réplicas de 25 000 llegadas, a menos de 4 errores estándar).
- Ejemplo: `examples/06_centro_de_contacto_erlang_a.py` compara 10 agentes con el mismo tiempo de servicio (1,3 % de abandono VIP y 7,1 % estándar) y con los VIP atendidos en 2,5 min (0,8 % y 4,3 %).

### Cambia
- Interno: el tamaño del truncamiento se amplía extrapolando el decaimiento geométrico de la masa en la frontera, en vez de multiplicar por un factor fijo cuando hay dos soluciones previas (nunca más que el factor); evita resolver una malla mucho mayor por pasarse por poco de la tolerancia.
  Acelera también `erlang_a_classes` con μ común (p. ej. 3 clases con c = 6: de 5 s a 3 s).

### Límites
- **Tamaño con μ distintos.** El costo crece con c (fases (c + 1)(q₁ + 1) y región libre c(c+1)/2). Con carga cercana a la capacidad (ρ ≈ 1): ≈ 0,5 s con 10 servidores, ≈ 4 s con 20 y ≈ 15 s con 30; con 40 o más se supera la cota de
  cálculo (≈ 20 s hasta rendirse) y lanza `ValueError`. Con carga menor, o `mu` común, el límite es mucho más holgado.
- Solo 2 clases con μ distintos: con más, el estado necesitaría la composición de servidores por clase y no es abordable de forma exacta.

### Pruebas
- `tests/test_erlang_a_mu_distintos.py`: la cadena completa con álgebra lineal (c = 1 a 5), el caso μ₁ = μ₂ contra `erlang_a_priority`, la identidad de ocupación por clase, los límites con una clase casi sin llegadas, la exponencial de la matriz
  de las dos cadenas de espera (transiciones escritas una a una), simulación de eventos con μ distintos y validación de entradas. Siete mutantes nuevos (`MU-53` a `MU-59`).

---

## [0.4.12] — 2026-10-22

Versión de centros de contacto con más de dos clases: Erlang A con K clases y prioridad. Solo añade funciones: no cambia ningún resultado existente.

### Añadido
- **`erlang_a_classes(lam, mu, theta, c)`** y **`ErlangAClassesResult`**: cola M/M/c+M con 2 a 6 clases que abandonan con paciencias distintas y se atienden por prioridad no expropiativa (la clase 0 es la de
  mayor prioridad), con λ y θ propias y μ común. Generaliza `erlang_a_priority`: con dos clases da lo mismo, y con θ iguales la cola total coincide con `erlang_a`. Es exacto (cadena de Markov resuelta
  por niveles de la cola de la clase de menor prioridad; no una aproximación) y estable aunque Σλ ≥ c·μ. Devuelve por clase la probabilidad de abandono, la tasa atendida, Lq y Wq, y la utilización y P(esperar).
- **`erlang_a_classes_service_level(lam, mu, theta, c, t)`**: nivel de servicio exacto de cada clase. El de la clase 0 es la fórmula cerrada de `erlang_a_service_level`; el de cada una de las demás se calcula con la cadena de
  su espera (colas de las clases altas por delante y posición propia) por uniformización.
- Los indicadores de las tres clases (P(abandono), Wq y nivel de servicio de cada una, y P(esperar)) coinciden con una simulación de eventos con prioridad (10 réplicas de 25 000 llegadas, a menos de 4 errores estándar);
  con 3 y 4 clases, el motor coincide con la cadena completa resuelta con álgebra lineal a 1e-12.
- Ejemplo: `examples/06_centro_de_contacto_erlang_a.py` suma el caso de tres niveles (platino, oro y estándar). Con 10 agentes abandonan 0,6 %, 1,5 % y 7,8 %.

### Cambia
- Interno: el motor de dos clases de 0.4.11 es ahora el caso K = 2 del motor general. La truncación es un símplex (suma de las colas de las clases altas ≤ S, cola de la clase baja ≤ Q) en vez de una caja por clase,
  que desperdiciaba casi todas las fases con tres o más clases; se amplía mientras la masa en la frontera supere 1e-10 (error relativo de los indicadores ≲ 1e-8; antes 1e-13). Para guardar menos
  matrices en el recorrido por niveles se usan puntos de control (≈ 2√Q matrices en vez de Q, a cambio de ≈ el doble de tiempo). Los resultados de `erlang_a_priority` no cambian más allá de ese error.
- Herramientas: `scripts/instantanea_salida.py` y la suite se ajustan a la nueva API.

### Límites
- **Tamaño.** El costo crece con el producto de las colas de las clases altas (matrices de C(S + K − 1, K − 1) filas). Con 2 o 3 clases y carga moderada tarda décimas de segundo; con 4 clases, unos segundos y solo con
  colas cortas (0,7 s con Σλ = 1,8 y c = 4; 8 s con Σλ = 3,3); con más clases o colas largas (λ/θ muy grande) se supera la cota de cálculo (≈ 15 s) y lanza `ValueError`. No se ofrece una aproximación para esos casos.
- Todas las clases comparten μ (los tiempos de servicio distintos por clase llegan en la versión siguiente).

### Pruebas
- `tests/test_erlang_a_clases.py`: la cadena completa con álgebra lineal (K = 2, 3 y 4, con la misma restricción de símplex), el caso de dos clases (`erlang_a_priority`), paciencias iguales (Erlang A), límites con una clase
  casi sin llegadas, identidad de flujo, sobrecarga, la exponencial de la matriz de la cadena de espera (clases 1 a 3, aplicada a un vector), simulación de eventos con 3 clases y validación de entradas. Seis mutantes nuevos
  (`MU-47` a `MU-52`).

---

## [0.4.11] — 2026-10-22

Versión de centros de contacto con dos tipos de cliente: Erlang A con dos clases y prioridad. Solo añade funciones: no cambia ningún resultado existente.

### Añadido
- **`erlang_a_priority(lam_high, lam_low, mu, theta_high, theta_low, c)`** y **`ErlangAPriorityResult`**: cola M/M/c+M con dos clases (p. ej. VIP y estándar) que comparten los mismos
  agentes. La clase alta pasa delante en la fila sin desplazar a nadie en servicio (prioridad no expropiativa); cada clase tiene su λ y su paciencia θ y el servicio tiene la misma tasa μ. Es
  exacto, no una aproximación: la cadena de Markov (b < c servidores ocupados, o c ocupados con q₁ y q₂ en cola) se resuelve por niveles de q₂, de modo que solo se invierten matrices del
  tamaño de la cola de la clase alta (≈ 20 × 20), y los estados con servidores libres salen de un corte de flujo y de un nacimiento y muerte. Devuelve por clase la probabilidad de abandono, la tasa
  atendida, Lq y Wq (que cuentan a todos los que llegan de la clase), y la utilización y P(esperar) del sistema. Tarda menos de 1 s con 250 agentes y es estable aunque λ ≥ c·μ.
- **`erlang_a_priority_service_level(..., t)`**: nivel de servicio exacto de cada clase (fracción atendida esperando como máximo *t*). El de la clase alta es la fórmula cerrada de
  `erlang_a_service_level` sobre su propia cola; el de la baja se calcula con la cadena de su espera (clientes de alta por delante, posición propia) por uniformización.
- Con paciencias iguales la cola total coincide con `erlang_a` (a 1e-9 relativo); con una clase casi sin llegadas, la otra coincide con `erlang_a`; y los indicadores de las dos clases coinciden
  con una simulación de eventos con prioridad (10 réplicas de 30 000 llegadas: P(abandono), Wq y nivel de servicio de ambas clases y P(esperar), a menos de 4 errores estándar).
- Ejemplo: `examples/06_centro_de_contacto_erlang_a.py` suma el caso VIP y estándar. Con 10 agentes, 1,3 % de los VIP y 7,1 % de los estándar abandonan.

### Cambia
- Interno: el nivel de servicio de una clase se calcula con un helper compartido (`_nivel_servicio_cola`) que usan `erlang_a_service_level` y la clase alta; sin cambio de resultados.
- Herramientas: la instantánea de salida (`scripts/instantanea_salida.py`) redondea a 9 cifras los números del `str()` de los resultados, como ya hacía con la salida del README; sin eso, el `str()` de
  una tupla de floats difería en la última cifra con numpy 1.22 (dependencias mínimas) y con numpy 2.

### Pruebas
- `tests/test_erlang_a_prioridad.py`: la cadena completa resuelta con álgebra lineal (sin la reducción por niveles), el límite de paciencias iguales (Erlang A), los límites de una sola clase, identidades de
  flujo, sobrecarga con λ = 2·c·μ, la exponencial de la matriz de la cadena de espera de la clase baja (aplicada a un vector), simulación de eventos con prioridad y validación de entradas. Cinco
  mutantes nuevos (`MU-42` a `MU-46`).

---

## [0.4.10] — 2026-10-22

Versión de rigor estadístico en `weibull_analysis`: con pocas fallas los intervalos de 0.4.8 quedaban cortos y el MLE de β sobrestima. Mismos β y η que en 0.4.9; cambian los
intervalos de confianza (más anchos con pocas fallas) y hay un aviso nuevo.

### Corregido
- **Intervalos de confianza de Weibull con pocas fallas.** Los de 0.4.8 usaban el cuantil normal y, con pocas fallas, cubrían mucho menos de lo nominal: en una simulación de 1 500 muestras completas
  (β = 2, η = 100) el «95 %» cubría 85 % con 5 fallas, 90 % con 10 y 93 % con 20. Ahora se usa el cuantil de una t de Student con r − 2 grados de libertad (r fallas, dos parámetros estimados): la
  cobertura queda en 94 a 96 % desde 5 fallas (94,7 % con 10, 94,5 % con 20); con datos censurados queda algo conservadora (≈ 95 a 98 %). Con menos de 3 fallas ya no hay grados de libertad y
  `shape_ci`, `scale_ci` y `confidence` son `None`. Con muchas fallas el cambio es mínimo (con 40 fallas, la t es 3 % mayor que la normal).

### Añadido
- **Aviso de sesgo del MLE.** Con `method="MLE"` y menos de 8 fallas, `weibull_analysis` emite un `UserWarning`: el MLE de β sobrestima con pocas fallas (medido: en promedio +45 % con 5, +22 % con 8,
  +15 % con 10, +7 % con 20 y +3,5 % con 40) y `method="RRY"` casi no tiene ese sesgo (de −4 a +5 % desde 5 fallas). Los intervalos de confianza ya lo tienen en cuenta; el aviso es sobre la estimación puntual.
- Cuantil general de la t de Student (`walopy._utils.t_cuantil(p, gl)`, interno), por inversión numérica de la función de distribución con la beta incompleta: coincide con `scipy.stats.t.ppf`
  hasta 1e-9 (relativo) y admite cualquier nivel de confianza y grados de libertad no enteros.

- Ejemplos ejecutables de las capacidades de 0.4.8 y 0.4.9: `examples/04_confiabilidad_weibull.py` suma un caso con suspensiones (descartarlas deja η en 653 h y R(500 h) en 61,3 %; con ellas,
  803 h y 70,0 %) y `examples/06_centro_de_contacto_erlang_a.py` dimensiona un centro de contacto con abandono (con 8 agentes λ = c·μ y `mmc` no es calculable; Erlang A sí). La referencia
  de Sphinx y los dos README ya cubrían todas las funciones exportadas: no hubo huecos que cerrar.

### Cambia
- Los intervalos de `weibull_analysis` (solo los de 0.4.8 en adelante; antes no existían) son más anchos con pocas fallas, y con menos de 8 fallas aparece el aviso descrito arriba (con
  `warnings` como error, esas llamadas ahora lanzan `UserWarning`: usa `method="RRY"` o filtra el aviso).

### Pruebas
- `tests/test_weibull_censurado.py`: constantes de scipy con la t de 6 grados de libertad, cobertura con 6 fallas, razón de anchos entre niveles de confianza igual a la de cuantiles t, sesgo del MLE
  y de RRY medido por simulación, aviso en español e inglés y caso sin grados de libertad. `tests/test_t_cuantil.py`: 11 cuantiles de scipy, caso de Cauchy (forma cerrada), simetría y
  límite normal. Cuatro mutantes nuevos (`MU-38` a `MU-41`).

---

## [0.4.9] — 2026-10-22

Versión de centros de contacto: Erlang A, la cola con abandono de clientes impacientes, el último punto de la hoja de ruta de la auditoría de dominio. Solo añade funciones: no cambia
ningún resultado existente.

### Añadido
- **`erlang_a(lam, mu, theta, c)`**: cola M/M/c+M, donde cada cliente en espera abandona a tasa θ (paciencia exponencial de media 1/θ). A diferencia de `mmc`, es estable aunque λ ≥ c·μ
  (los abandonos compensan el exceso de carga) y es exacta (proceso de nacimiento y muerte), no una aproximación. Devuelve un `QueueResult` (`rho` es la utilización λ_eff/(c·μ); `Lq` y `Wq`
  cuentan a todos los que llegan, y `L` y `W` cumplen la ley de Little con λ) con, en `params`, P(esperar), P(abandono), la tasa atendida λ_eff y la espera media de quienes se atienden
  y de quienes abandonan. Con θ → 0 coincide con `mmc` y con θ grande, con `erlang_b`; con θ = μ el número en el sistema es Poisson(λ/μ).
- **`erlang_a_service_level(lam, mu, theta, c, t)`**: nivel de servicio exacto, la fracción de las llegadas que se atienden esperando como máximo *t* (p. ej. «80 % atendidas en 20 segundos»).
  Los que abandonan antes no cuentan como atendidos. Es una fórmula cerrada: la espera de quien llega a la posición *j* de la fila cumple θ·T = −ln B con B ~ Beta(cμ/θ, j), y la
  beta incompleta es una suma finita de términos positivos (sin simulación y sin restas que cancelen).
- **`erlang_a_servers(lam, mu, theta, *, max_abandon, max_wait_prob, min_service_level, t, c_max)`**: mínimo número de servidores que cumple todos los objetivos pedidos (por duplicación y bisección,
  porque los tres indicadores mejoran al añadir servidores). Devuelve el `erlang_a` de ese *c*.
- Los cinco indicadores (P(abandono), P(esperar), espera de atendidos, espera de abandonos y nivel de servicio) coinciden con una simulación de eventos con colas FIFO y abandono: 30 réplicas de 100 000
  llegadas, con λ = 10, μ = 1, θ = 0,5 y 8 servidores (λ > c·μ), a menos de 0,5 errores estándar.

### Pruebas
- `tests/test_erlang_a.py`: solución directa de las ecuaciones de balance con álgebra lineal, identidades de flujo y de Little, reparto de la espera media entre atendidos y abandonos, el límite
  θ = μ (Poisson), los límites M/M/c y Erlang B, sobrecarga con λ = 2·c·μ, monotonía en *c* y θ, integración numérica (RK4) de las ecuaciones de la espera para el nivel de servicio,
  simulación con intervalo de confianza y validación de entradas. Cinco mutantes nuevos (`MU-33` a `MU-37`).

---

## [0.4.8] — 2026-10-21

Versión de fiabilidad con datos censurados: `weibull_analysis` admite unidades suspendidas e intervalos de confianza, de la auditoría de dominio. Sin suspensiones,
β y η son los de siempre.

### Añadido
- **`weibull_analysis(..., suspensions=[...])`**: censura por la derecha. Las unidades que seguían funcionando al terminar el estudio entran a la verosimilitud con R(t) en vez de f(t) (MLE)
  o con los rangos ajustados de Johnson (RRY). Descartarlas, o tratarlas como fallas, sesga la vida: en una simulación de 150 muestras de 40 unidades (β = 2, η = 100, censura en t = 90, cerca de la mitad suspendidas),
  ignorarlas deja η en promedio 38 % por debajo del valor verdadero y el MLE con censura, 0,5 %.
- **Intervalos de confianza de β y η** con `method="MLE"` (`shape_ci`, `scale_ci`, `confidence`, nivel con `confidence=`, 0,95 por defecto): aproximación normal sobre el logaritmo del
  parámetro con la información observada de Fisher. Coinciden con el Hessiano numérico y, sin censura, con las varianzas asintóticas 0,6079·β²/n y 1,1087·η²/(n·β²); en una simulación
  de 500 muestras de 60 unidades con 31 % de censura la cobertura del 95 % fue 96,4 % para β y 95,6 % para η. Son asintóticos: con menos de unas 10 fallas pueden ser optimistas. Con `method="RRY"` no se calculan.
- `WeibullResult` gana `n_suspended`, `confidence`, `shape_ci` y `scale_ci`; `summary()` y `to_frame()` los muestran (columnas nuevas al final de `to_frame()`).

### Corregido
- Textos de las notas de 0.4.7: el rango de utilización de la simulación de la línea serial era 0,64 a 0,78 (no 0,7 a 0,78), con CV² de servicio de 0,5, 2 y 1; las simulaciones de `ggc`
  cubrían de 2 a 4 servidores (no solo 3 y 4); y la fecha de la versión es 2026-10-21.

### Pruebas
- `tests/test_weibull_censurado.py`: valores de scipy (optimizador y Hessiano numérico), búsqueda por sección áurea de la verosimilitud perfilada, rangos de Johnson calculados a mano,
  invariancia a la escala de tiempo, varianzas asintóticas, cobertura por simulación y el sesgo de ignorar las suspensiones. Cuatro mutantes nuevos (`MU-29` a `MU-32`).

---

## [0.4.7] — 2026-10-21

Versión de flujo y servicio: colas de varios servidores con variabilidad cualquiera y líneas de estaciones en serie, de la auditoría de dominio. Solo añade funciones: no cambia
ningún resultado existente.

### Añadido
- **`ggc(lam, mu, c, ca2, cs2)`**: cola G/G/c con la aproximación de Allen-Cunneen, Wq ≈ Wq(M/M/c)·(ca² + cs²)/2. Con un servidor coincide con `kingman`, con ca² = cs² = 1 con `mmc`
  y con servicio determinista y llegadas de Poisson (un servidor) con `md1`. En `params` incluye cd², el CV² de las salidas. En las pruebas, Wq quedó a menos de 12 % de una simulación
  de eventos con ρ entre 0,70 y 0,85 (2 a 4 servidores; llegadas y servicio no exponenciales).
- **`departure_cv2(lam, mu, c, ca2, cs2)`**: ecuación de enlace de la variabilidad de las salidas, cd² = 1 + (1 − ρ²)(ca² − 1) + ρ²(cs² − 1)/√c (Whitt; con un servidor, la de Hopp y Spearman).
  Es una aproximación: con ρ = 0,8, ca² = 2 y cs² = 0,5 da 1,04 y una simulación de 400 000 clientes, 0,96.
- **`serial_line(station_names, mu, *, lam, ca2, cs2, servers)`**, **`SerialLineResult`** y **`LineStationResult`**: línea de estaciones en serie; cada estación es G/G/c y su cd² pasa a ser el
  ca² de la siguiente. Devuelve tiempo de ciclo, inventario en proceso (ley de Little), cuello de botella y los indicadores por estación. A diferencia de `jackson_network` (exacta, pero con
  llegadas de Poisson y servicio exponencial) admite cualquier variabilidad; con todo exponencial coincide con ella. Contra una simulación de tres colas en serie (ρ entre 0,64 y 0,78; CV² de
  servicio de 0,5, 2 y 1) el tiempo de ciclo quedó a menos de 10 %. Supone buffers infinitos, sin mermas ni reproceso.

### Pruebas
- `tests/test_ggc_linea_serial.py`: casos límite exactos, simulación multiservidor con `heapq`, simulación de colas en serie (recursión de Lindley), variabilidad de las salidas medida en una
  simulación de un servidor y coincidencia con `jackson_network` en una línea exponencial.

---

## [0.4.6] — 2026-10-21

Versión de simulación: réplicas con intervalo de confianza en `monte_carlo_gg1` y PERT con simulación Monte Carlo. Cierran los dos hallazgos de la auditoría de dominio
que en 0.4.4 solo tenían un aviso. Los resultados existentes no cambian: con los valores por defecto los números son los de siempre.

### Añadido
- **`monte_carlo_gg1(..., n_replications=N, warmup=K)`**: réplicas independientes (flujos derivados de `seed` con `SeedSequence`) y descarte de los `K` primeros clientes de
  cada una (el arranque en vacío sesga Wq a la baja). El resultado trae `Wq_halfwidth` y `Wq_ci` (intervalo de confianza al 95 %: t de Student sobre las medias de las
  réplicas o, con una sola, medias de 20 lotes), `n_replications` y `warmup`. Con ρ = 0,95 y 20 000 clientes, 20 corridas sueltas dieron Wq entre 11 y 27 (exacto: 19); con 200
  réplicas el intervalo fue [18,1; 19,6]. El aviso de precisión (semiancho > 10 % de Wq) usa ahora ese intervalo. Con `n_replications=1` y `warmup=0` el flujo aleatorio es
  el de siempre.
- **`pert(..., n_simulations=N, seed=...)`**: simula el proyecto con duraciones beta-PERT, a + (b − a)·Beta(1 + 4(m − a)/(b − a), 1 + 4(b − m)/(b − a)) (media (a + 4m + b)/6),
  y considera **todas** las rutas. Añade `mc_mean`, `mc_std`, `criticality_index` (fracción de simulaciones en que cada actividad está en la ruta crítica),
  `probability_mc(T)` y `percentile_mc(q)`; la tabla gana la columna de criticidad y el resumen una línea de simulación. Con 5 rutas paralelas idénticas, P(T ≤ 17,5) es 0,50
  con la normal de una ruta y 0,04 por simulación. Con `n_simulations` no se emite el aviso de rutas casi críticas de 0.4.4 (que ahora recomienda esa opción).

### Cambiado
- `SimulationResult` tiene los campos `n_replications`, `warmup` y `Wq_halfwidth` (y la propiedad `Wq_ci`); `summary()` muestra una línea más (`IC 95 % Wq`) y `to_frame()` tres
  columnas más al final. `ProjectResult` tiene `n_simulations`, `mc_mean`, `mc_std` y `criticality_index`, que solo se rellenan con `n_simulations`.
- El texto del aviso de precisión de `monte_carlo_gg1` menciona `n_replications` en lugar de «varias semillas».

### Descartado tras medirlo
- Calentamiento automático con MSER-5: con ρ = 0,95 y 200 réplicas de 20 000 clientes dio Wq = 17,8 (IC [17,1; 18,5]) frente a 19 exacto, peor que no descartar nada (18,9;
  [18,1; 19,6]), porque recorta justo las excursiones largas. Por eso `warmup` es un entero y la documentación orienta cuánto descartar (varias veces 1/(1 − ρ)² clientes).

### Pruebas
- `tests/test_simulacion_replicas.py`: M/M/1 como oráculo (Wq exacto = λ/(μ(μ − λ))): el intervalo cubre el valor exacto con frecuencia cercana al 95 % en 40 corridas, el semiancho
  baja con más réplicas, las réplicas son independientes y reproducibles y los cuantiles de la t coinciden con tablas.
- `tests/test_pert_simulacion.py`: casos deterministas exactos (duración e índice de criticidad), media y varianza exactas de la beta-PERT, dos rutas idénticas (criticidad 0,5 cada una y
  P(T ≤ t) = F(t)² con F integrada numéricamente) y reproducibilidad independiente del tamaño de bloque.

---

## [0.4.5] — 2026-10-21

Versión de inventarios: objetivos de **tasa de llenado** y punto de reorden exacto para **demanda discreta**, a raíz de la auditoría de dominio. Sin
cambios incompatibles en los cálculos existentes: con `service_level` el stock de seguridad es el de siempre.

### Añadido
- **Tasa de llenado (β, tipo 2) como objetivo** en `reorder_point` (con `order_qty`), `rq_policy` y `rs_policy`: `fill_rate=0.98` sustituye a `service_level` y se
  resuelve G(z) = (1 − β)·Q / σ con la función de pérdida de la normal (Q = EOQ en (r, Q); D·R en (R, S)). El nivel de servicio del resultado pasa a ser el nivel
  por ciclo implícito Φ(z). El punto de reorden no baja de 0: con un objetivo muy holgado frente a Q, la tasa alcanzada es mayor que la pedida. En `rq_policy` con
  λ = 50, σ = 10, L = 2: «95 % de nivel por ciclo» equivale a una tasa de llenado de 99,5 %; quien pide 95 % de tasa de llenado necesita bastante menos stock.
- **`reorder_point_discrete`** y **`DiscreteReorderResult`**: punto de reorden exacto cuando la demanda en el tiempo de entrega es de conteo (piezas de baja
  rotación, demanda intermitente). **Poisson** sin `demand_std` (o con varianza igual a la media) y **binomial negativa** con varianza mayor que la media; devuelve
  el menor entero con el nivel de servicio por ciclo o la tasa de llenado pedidos. Sin SciPy (recurrencias con `lgamma`). La normal, con medias pequeñas, asigna
  probabilidad a demanda negativa. No admite subdispersión ni medias mayores de 100 000 unidades en el tiempo de entrega (usar `reorder_point`).

### Cambiado
- `ReorderResult`, `RQPolicyResult` y `RSPolicyResult` tienen el campo `fill_rate` (en `ReorderResult` solo si se indicó `order_qty`). `rq_policy` y `rs_policy`
  muestran siempre la tasa de llenado alcanzada: una línea más en `summary()` y una columna más al final de `to_frame()`. No cambia ningún otro valor.

### Pruebas
- `tests/test_tasa_llenado_y_demanda_discreta.py`: la tasa alcanzada se comprueba con integración numérica de E[(X − r)⁺] (independiente de la función de pérdida
  cerrada) y la demanda discreta con tablas de la función de masa por recurrencia: el punto de reorden es el menor entero que cumple el servicio (Poisson y binomial
  negativa), coincide con la normal para medias grandes y la binomial negativa tiende a Poisson al acercarse la varianza a la media.

---

## [0.4.4] — 2026-10-20

Versión de corrección tras una auditoría de dominio: la disponibilidad de los sistemas redundantes y la varianza PERT con rutas críticas empatadas daban
resultados engañosos, y tres modelos avisan ahora cuando se usan fuera del rango en que su resultado es fiable.

### Corregido
- **Disponibilidad de `parallel_system` y `koon_system`.** Con `mttr` calculaban `MTTF_sistema / (MTTF_sistema + MTTR)`, que supone que nada se repara hasta que cae
  todo el sistema. Con dos componentes en paralelo (λ = 0,01, MTTR = 10) daba 0,9375; con reparación independiente de cada componente, el supuesto habitual,
  es 0,9917 (8 veces menos indisponibilidad). Ahora `parallel_system` usa `1 − ∏(1 − Aᵢ)` y `koon_system` la binomial de la disponibilidad de cada componente;
  el supuesto queda documentado. `series_system` no cambia (el sistema está detenido mientras se repara). El MTBF de los resultados sigue siendo el tiempo medio
  hasta la falla del sistema sin reparación. Bug `W-33`: `tests/test_disponibilidad_redundante.py` y mutante `MU-27`.
- **Varianza de `pert` con varias rutas críticas empatadas.** Sumaba las varianzas de todas las actividades críticas en lugar de las de una ruta: con 5 rutas
  idénticas de 3 actividades, σ salía 3,23 en lugar de 1,44. Ahora es la varianza de la ruta crítica de mayor varianza (la convención con empates); con una
  sola ruta crítica no cambia. `critical_path` sigue listando todas las actividades críticas. Bug `W-34`: `tests/test_pert_varianza.py` y mutante `MU-28`.

### Añadido
- **Avisos de validez (`UserWarning`)** cuando el resultado de un modelo no es fiable; el resultado no cambia:
  - `pert`: hay actividades fuera de la ruta crítica usada con holgura ≤ σ del proyecto. La probabilidad PERT considera una sola ruta y es optimista cuando
    convergen rutas casi críticas (con 5 rutas paralelas, P(T ≤ 17,5) = 0,50 según PERT y 0,04 por simulación).
  - `newsvendor`: demanda normal con CV > 0,5; el aviso indica P(D < 0) del modelo y sugiere una distribución no negativa.
  - `monte_carlo_gg1`: el semiancho al 95 % de Wq (medias de 20 lotes) supera el 10 %; con ρ = 0,95 y 20 000 clientes, 20 réplicas dieron Wq entre 11,3 y
    26,6 (exacto: 19).

### Documentación
- `reorder_point`, `rq_policy`, `rs_policy` y `safety_stock_curve`: si la demanda se pronostica, `demand_std` debe ser la desviación del error de pronóstico;
  `service_level` es el nivel de servicio por ciclo (tipo 1), no la tasa de llenado.
- Supuestos de disponibilidad de `series_system`, `parallel_system` y `koon_system`.

### Seguridad
- La publicación vuelve a generar **atestaciones de procedencia** (PEP 740, `attestations: true`). PyPI mostraba «pérdida de procedencia» porque se habían
  desactivado tras el fallo de publicación de v0.2.7; los archivos de 0.4.3 coinciden con el commit del tag `v0.4.3` (comprobado).

### Mantenimiento
- Los workflows de GitHub Actions usan versiones que ejecutan Node 24 (Node 20 está obsoleto y GitHub lo retira de los runners): `actions/checkout@v7`, `actions/setup-python@v7`,
  `actions/upload-artifact@v7` y `actions/download-artifact@v8` (primero a v6/v7 a mano y después con el primer PR de Dependabot). Sin cambios en el paquete.
- Los jobs de Python 3.9 del CI (la entrada 3.9 de la matriz y el de dependencias mínimas) se fijan a `ubuntu-24.04`: `ubuntu-latest` pasa a Ubuntu 26.04 de forma gradual hasta el
  19 de noviembre de 2026 y esa imagen puede no ofrecer Python 3.9. El resto de los jobs sigue en `ubuntu-latest`.
- Nuevo `.github/dependabot.yml`: Dependabot propone cada semana (lunes) las subidas de las acciones de GitHub de los workflows, agrupadas en un solo PR que pasa por el CI completo.

---

## [0.4.3] — 2026-10-07

Versión de corrección en `solver`: `solve_servers` y `optimize_servers` no consideraban el menor número de servidores estable, y `batch_model`, `compare` y `sensitivity`
no cumplían lo que documentan (0.4.2 y anteriores).

### Corregido
- **`solve_servers` y `optimize_servers` empezaban a buscar un servidor después del mínimo estable.** La búsqueda partía de `ceil(λ/μ) + 1`, que solo es el menor `c` con
  ρ < 1 cuando λ/μ es entero. En los demás casos, `solve_servers` podía devolver más servidores de los necesarios (`solve_servers("Wq", 0.5, lam=4, mu=3)` daba 3 y
  ahora da 2, con Wq = 0,267) y `optimize_servers` no evaluaba el plan más barato (`optimize_servers(lam=4, mu=3, cost_per_server=10, cost_per_wait=5)` costaba
  30,7232 con 3 servidores y ahora cuesta 25,3333 con 2; con λ=1, μ=5 nunca consideraba un solo servidor). Cuando λ/μ es entero el resultado no cambia. Los ejemplos de
  los docstrings se actualizaron. Bug `W-28`: `tests/test_servidores_minimos.py` (falla en v0.4.2) y mutante `MU-20`. Hallado con propiedades diferenciales (comparación con una enumeración).

- **`solve_servers` y `optimize_servers` no validaban `c_max`.** Con `c_max` menor que el mínimo estable, `optimize_servers` fallaba con `min() arg is an empty sequence`;
  un `c_max` no entero, `bool`, `nan` o `None` daba `TypeError` opacos o se aceptaba. Ahora `c_max` debe ser un entero positivo (máximo `MAX_SERVIDORES`) y, si no alcanza
  para el mínimo estable, el `ValueError` dice cuántos servidores hacen falta. Bug `W-29`: `tests/test_servidores_cmax.py` y mutante `MU-21`.
- **`batch_model` con un DataFrame disperso rechazaba los parámetros enteros** (`c`, `k`…): pandas convierte a `float64` una columna entera con NaN y el modelo exige `int`,
  así que todas las filas fallaban. Ahora los valores enteros de una columna flotante con NaN se pasan como `int`. Bug `W-30`: `tests/test_solver_contratos.py` y mutante `MU-22`.
- **`compare` sin resultados devolvía una tabla vacía** (la documentación dice `ValueError`) y, con un resultado de varias filas (`wagner_whitin`, `silver_meal`, `cpm`,
  `pert`, `schedule_single`…), conservaba solo la primera orden o actividad. Ahora lanza `ValueError` y, para esos resultados, compara sus campos escalares (`total_cost`,
  `n_orders`, `project_duration`…); los de una fila (colas, EOQ…) no cambian. Un resultado de una sola fila de elementos (un único pedido) sigue mostrando esa fila.
  Bug `W-31`: `tests/test_solver_contratos.py` y mutantes `MU-23` y `MU-24`.
- **`sensitivity` no lanzaba los `ValueError` que documenta**: con un parámetro que el modelo no tiene daba `TypeError` y con `values` vacío devolvía una tabla vacía. Ahora ambos
  casos lanzan `ValueError` (los modelos con `**kwargs` siguen admitidos). Bug `W-32`: `tests/test_solver_contratos.py` y mutantes `MU-25` y `MU-26`.

### Pruebas
- Nuevo `tests/test_propiedades_inventario_fiabilidad.py`: `weibull_analysis`, `mtbf_analysis`, `fit_from_data`, `reorder_point`, `rq_policy`, `rs_policy`, `eoq_multi`, `ebq`,
  `eoq_multi_constrained`, `eoq_quantity_discount`, `exchange_curve`, `safety_stock_curve`, `jackson_network`, `break_even_multi`, `abc_analysis`, `bottleneck_analysis`,
  `unit_cost` y `utilization_efficiency` contra fórmulas y enumeraciones independientes. Esta tanda de propiedades encontró `W-28`.
- Nuevo `tests/test_dibujo_plotly.py` (`make dibujo`, job «Dibujo» del CI): renderiza las figuras de Plotly en Chromium sin interfaz y comprueba que la zona del
  gráfico difiere de la misma figura con las trazas invisibles; reintroducir el defecto W-26 (árbol de KPI en blanco) lo hace fallar en las cuatro figuras de KPI.
  Sin navegador (o sin `WALOPY_DIBUJO=1`) solo se ejecuta la capa de datos finitos por traza.
- Nuevo `tests/test_propiedades_algoritmos.py`: `neh_flowshop`, `johnson_flowshop`, `schedule_single` (SPT, EDD, WSPT), `cpm`, `mmck`/`mm1k`, `mm1_priority`,
  `newsvendor`, `silver_meal`, `lot_for_lot` y `mrp` contra oráculos independientes (fuerza bruta, camino más largo, ecuaciones de balance, fórmula cerrada) sobre
  escenarios aleatorios con semilla fija. No hallaron defectos nuevos; protegen contra regresiones.

### Documentación
- `CONTRIBUTING.md` incluye «Cómo añadir una función pública», con los siete pasos que exige la batería (código, textos en los dos catálogos, test de contrato,
  referencia Sphinx, los dos README, traducción de la referencia y cierre).
- Política del inglés: no se exige revisión por una persona nativa; la paridad entre español e inglés sigue siendo obligatoria y comprobada por tests
  (`docs/auditoria/PLAN_I18N.md` §7).

---

## [0.4.2] — 2026-10-07

Versión de corrección: `wagner_whitin` no devolvía el costo óptimo cuando la demanda tenía periodos en cero (0.4.1 y anteriores).

### Corregido
- **`wagner_whitin` con periodos de demanda nula** devolvía un plan más caro que el óptimo: cobraba la preparación en bloques sin demanda y obligaba a pedir en el
  periodo 1. Ejemplos con `setup_cost=100`, `holding_cost=1`: `[0, 0, 100, 0, 0]` costaba 200 (ahora 100, un solo pedido en el periodo 3) y `[0, 50, 0, 100]`
  costaba 250 (ahora 200); `[0, 0, 0]` devolvía un pedido de cantidad 0 y costo 100 (ahora ningún pedido y costo 0). Con demanda positiva en todos los periodos el
  resultado no cambia. Bug `W-27`: `tests/test_wagner_whitin_ceros.py` (falla en v0.4.1) y mutante `MU-19`. Hallado con propiedades diferenciales entre funciones
  relacionadas.

### Pruebas
- El test de fuerza bruta de `wagner_whitin` compartía el defecto del código (obligaba a pedir en el periodo 1 y evitaba `d[0] = 0`); se reescribió con un oráculo
  independiente y ceros en cualquier posición.
- Nuevo `tests/test_propiedades_diferenciales.py`: relaciones que deben cumplir funciones distintas del mismo modelo (M/G/1 con cs²=1 = M/M/1, M/M/c con c=1 = M/M/1,
  Erlang-B decreciente, serie ≤ mínimo, paralelo ≥ máximo, EOQ mínimo, etc.) sobre escenarios aleatorios con semilla fija.

## [0.4.1] — 2026-10-05

Versión de corrección: los gráficos de árboles de KPI salían en blanco en 0.4.0 y en las anteriores (0.2.7, 0.2.8 y 0.3.0 tienen el mismo código).

### Corregido
- **Los gráficos de árboles de KPI salían en blanco** (`KPINode.plot()`, `oee_kpi_tree`, `throughput_kpi_tree` y `roi_kpi_tree`, en `treemap` y en `sunburst`). Plotly, con
  `branchvalues="total"`, no dibuja la figura si un padre vale menos que la suma de sus hijos, y un KPI casi nunca es esa suma (EBITDA = Ingresos − Costos; OEE = A × P × Q).
  Ahora el tamaño de cada rectángulo es el mayor entre su valor y la suma de sus hijos, y el rótulo muestra el valor real del nodo (con separador de miles). Los árboles que ya
  cumplían la condición conservan sus tamaños. Bug `W-26`: `tests/test_kpi_grafica.py` (falla en v0.4.0) y mutante `MU-18`. Reportado por una persona usuaria.

---

## [0.4.0] — 2026-10-04

**Versión multilenguaje:** los textos y la documentación están en **español (por defecto) e inglés**. La salida en español es idéntica a la de v0.3.0
(comprobada con una instantánea de toda la salida visible), salvo el mensaje corregido de `eoq_quantity_discount`. **La traducción al inglés la redactó
Claude y debe revisarla una persona nativa antes de publicar.**

### Añadido
- **Idioma de los textos:** `walopy.set_language("en")`, `with walopy.language("en"):` (seguro con hilos y `asyncio`), `walopy.get_language()` y la variable de
  entorno `WALOPY_LANG` (también para el CLI). Orden de prioridad: contexto → global → entorno → español. Un idioma no admitido lanza `ValueError`; un texto sin
  traducir se muestra en español. Se aplica a mensajes de error, avisos, etiquetas de `summary()`, cabeceras de `to_frame()`, títulos de gráficas y ayuda del CLI.
  Las claves de `result.params` no cambian con el idioma (`summary()` muestra su etiqueta traducida); los nombres de las columnas de los `DataFrame` y los nombres
  por defecto (`Artículo-1` → `Item-1`) se crean en el idioma activo.
- **Catálogos de textos:** los 646 textos visibles de `src/` pasaron del código a `_catalogo_es.py` y `_catalogo_en.py` (claves `modulo.tipo.funcion.resumen`,
  marcadores `str.format` nombrados) y se usan con `_t("clave", ...)`. Infraestructura de verificación: `scripts/inventario_i18n.py` (`make inventario-i18n`),
  `scripts/instantanea_salida.py` y los tests `test_inventario_i18n`, `test_i18n_paridad`, `test_i18n`, `test_salida_identica` y `test_salida_por_idioma`.
  Plan y decisiones en `docs/auditoria/PLAN_I18N.md`.
- **Documentación en inglés:** `README.en.md` (enlazado desde `README.md` y desde los metadatos de PyPI) y la documentación Sphinx en inglés
  (`sphinx-build -D language=en`, traducciones en `docs/source/locale/en`, `make docs` construye ambos idiomas; `make docs-i18n` actualiza las plantillas).
  El registro de cambios sigue en español. `tests/test_documentacion_ingles.py` comprueba que ambos README tienen la misma estructura, que todos los mensajes de
  Sphinx están traducidos y que no hay mensajes nuevos sin traducir.
- `Makefile` (`make check-fast`, `make check`, `make release-check TAG=vX.Y.Z`, …), `AGENTS.md`, `.claude/` (permisos y hooks `SessionStart` y `Stop` para agentes), `.github/CODEOWNERS`, `scripts/notas_release.py` (`make notas-release VERSION=X.Y.Z` imprime el cuerpo del release desde este archivo).
- `scripts/verificar_mutaciones.py`: mutación de una línea; cada test de regresión debe fallar si el bug vuelve (17 mutantes).
- `docs/retrospectiva/`: lecciones, catálogo de bugs, scorecard, playbook, reglas de `CLAUDE.md` y resumen ejecutivo.
- Los tests de `rcParams` cubren las 19 gráficas (15 con `.plot()` y 4 de llamada directa; antes solo 2).
- Clasificadores `Natural Language :: Spanish` y `Natural Language :: English` y la URL «README (English)» en los metadatos.

### Cambiado
- **La versión tiene una sola fuente de verdad: el literal `__version__` de `src/walopy/__init__.py`**; `pyproject.toml` la lee con
  `[tool.setuptools.dynamic]`. Antes `__init__.py` la leía de `importlib.metadata`, que se congela al instalar: tras subir la versión,
  `walopy.__version__` mostraba la anterior hasta reinstalar.
- La publicación (`publish.yml`) comprueba que el wheel construido tiene la versión del tag (`scripts/comprobar_version_release.py`) y usa el mismo
  comando de `ruff` que el CI.
- El CI construye la documentación en español y en inglés (`-W` en ambos).

### Corregido
- `eoq_quantity_discount`: el mensaje «No feasible price break found.» estaba en inglés en la versión en español; ahora dice «No se encontró ningún tramo de precio factible.».
- Un resultado creado con un idioma y mostrado con otro (`with language("en")` + `print(r)` fuera del bloque) ya no falla con `KeyError` en `break_even_multi` y `eoq_multi_constrained`.
- La nota de `[0.3.0]` decía que las versiones `0.2.4` y `0.2.6` se publicaron sin tag. Comprobado en PyPI (2026-10-02): `0.2.6` sí está publicada y le falta el tag; `0.2.4` **no existe** en PyPI (su publicación falló y se saltó a `0.2.5`).

---

## [0.3.0] — 2026-10-02

Versión de endurecimiento tras la auditoría de madurez (`docs/auditoria/`). Cierra los hallazgos K-01…K-07,
K-09…K-13 y N-01…N-16 (ver `docs/auditoria/ROADMAP.md`).

### Cambios que rompen compatibilidad
- **Validación estricta de entradas.** Ahora lanzan `ValueError`/`TypeError` valores que antes se aceptaban en silencio:
  NaN/inf en `cpm`, `pert`, `mtbf_analysis`, `series_system`, `parallel_system`, `koon_system`, `mrp`, `weibull_analysis`,
  `cv2_uniform`, `cv2_triangular`, `break_even_multi`, `eoq_multi_constrained`; `t`/`mttr` negativos en confiabilidad
  (antes devolvían R(t) > 1); `initial_on_hand` inválido en `mrp`; `budget ≤ 0` en `eoq_multi_constrained` (antes se colgaba).
- **`bool` ya no se acepta como número o entero** (`mmc(2, 3, True)` antes se interpretaba como `c=1`).
- **`cv2_erlang(k)`** exige un entero ≥ 1 (antes truncaba `2.5` a `2`).
- **Listas vacías** en `lot_for_lot`, `silver_meal`, `wagner_whitin`, `schedule_single` y `series_system`/`parallel_system` lanzan `ValueError`.
- **Nombres de actividad duplicados** en `cpm`/`pert` lanzan `ValueError` (antes se fusionaban en silencio).
- **Todo texto que ve la persona usuaria está en español** (los identificadores del código siguen en inglés): mensajes de error y avisos, ayuda del CLI, docstrings, etiquetas de `summary()`, títulos y ejes de las gráficas, nombres de nodos de los árboles de KPI y los **encabezados de columna de los `DataFrame`** (`to_frame()`, `compare()`, …) y las claves de `params` con etiqueta legible. Ejemplos: `"Total cost"` → `"Costo total"`, `"λ (arrival rate)"` → `"λ (tasa de llegada)"`, `M1_start` → `M1_inicio`, `TF`/`FF` → `HT`/`HL`, columnas ABC/XYZ → `clase`, `valor_anual`, `pct_acumulado`; `compare()` etiqueta por defecto `escenario_1`. Las claves de los diccionarios de datos (`items[i]["class"]`, `result.params["fixed_cost"]`) y los atributos de los resultados no cambian.
- **Cotas de tamaño:** `c` ≤ 10⁶, `K`/`n_max`/`n_points` ≤ 10⁶, `n_customers` ≤ 10⁷.
- `abc_analysis` acepta artículos con demanda 0 (clase C); si todas son 0 lanza `ValueError`.
- `weibull_analysis` lanza `ValueError` si todos los tiempos son iguales y `UserWarning` si β alcanza la cota 100.
- `mrp` emite `UserWarning` cuando una liberación cae antes del periodo 1; `MRPResult` incorpora `past_due_releases`.

### Corregido
- `mmc` desbordaba (`OverflowError`) con carga ofrecida ≳ 140; ahora usa la recurrencia de Erlang-B y es estable hasta 10⁶ servidores.
- `abc_xyz` mezclaba artículos con nombres repetidos al emparejar por nombre; ahora empareja por posición.
- `break_even_sales(...).plot()` lanzaba `KeyError`.
- Holguras de CPM/PERT mostraban `-0.0`.
- Seis doctests que nunca se habían ejecutado estaban rotos (ejemplos de `newsvendor`, `wagner_whitin`, `weibull_analysis`, `fit_from_data`, `batch_model`, `compare`).
- Ejemplos del README: 13 de 61 usaban parámetros o atributos inexistentes; ahora los 61 se ejecutan.
- `__version__` sin instalar devolvía `0.2.0`; ahora `0+unknown`.

### Rendimiento
- `wagner_whitin` pasa de O(n³) a O(n²) real (n=1000: 10,2 s → 0,06 s).
- `neh_flowshop` usa la aceleración de Taillard, O(n²·m) (n=200, m=10: 5,3 s → 0,12 s).

### Añadido
- `batch_model(..., errors="collect"|"raise")`.
- `py.typed`: los tipos de walopy se exportan a quienes lo usan.
- README: secciones de ABC/XYZ, MRP, NEH, Weibull y CPM/PERT; referencia Sphinx de los 13 módulos; página de rendimiento.
- Secciones `Raises` y `Examples` (con doctests ejecutables) en las 70 funciones públicas.
- `examples/` (5 scripts) y `benchmarks/bench_core.py`.
- `SECURITY.md`, `CODE_OF_CONDUCT.md`, plantillas de issues y de PR; `CLAUDE.md` y `CONTRIBUTING.md` reescritos.
- CI: ruff, mypy, cobertura (global ≥ 85 % y por módulo ≥ 70 %), build + `twine check`, Sphinx `-W`, `pip-audit`,
  matriz Python 3.9–3.13, dependencias mínimas y prueba semanal con las últimas versiones; la publicación verifica antes de publicar.
- Tests: 357 → 1 260 (contrato de entradas sobre las 67 funciones, regresiones, referencias externas fijas, gráficas, CLI,
  README, documentación, ejemplos, complejidad, doctests, política de idioma y trazabilidad). Cobertura 80 % → 94,7 %.
- Trazabilidad de bugs: `tests/regresiones.json` (25 bugs `W-nn`), `scripts/verificar_regresion.py` (los tests de regresión deben **fallar** en la versión anterior; job `regresion` del CI),
  `tests/test_trazabilidad.py` y `tests/test_idioma.py` (mensajes, avisos y docstrings en español). `CLAUDE.md` pasa a 17 reglas (R-16 y R-17).
  El catálogo de bugs y el Playbook de `docs/referencia/` incorporan las lecciones de walopy; ver `docs/auditoria/TRAZABILIDAD.md` y `REGLAS_PROPUESTAS.md`.
- Extra de desarrollo `pytest-timeout` (la verificación de regresiones detecta bloqueos del código anterior).

### Notas
- Los tags `v0.2.4` y `v0.2.6` nunca se crearon en GitHub (las versiones sí se publicaron); no se reconstruyen.
- Sigue sin existir dependencia de `scipy`.

---

## [0.2.8] — 2026-09-29

### Añadido
- **`scheduling`** — `neh_flowshop` / `NEHResult`: heurística NEH para flow-shop de m máquinas (permutation); Gantt como DataFrame con columnas M{i}_start/M{i}_end
- **`inventory`** — `abc_analysis` / `ABCResult`: clasificación ABC de Pareto por valor anual; umbrales configurables; resumen por clase; `.to_frame()`
- **`inventory`** — `xyz_analysis` / `XYZResult`: clasificación XYZ por variabilidad (CV); acepta cv directamente o demand_std + demand_mean/demand_rate; `.to_frame()`
- **`inventory`** — `abc_xyz` / `ABCXYZResult`: análisis combinado ABC-XYZ; matriz 3×3 de conteos; `.matrix_frame()`
- **`inventory`** — `mrp` / `MRPResult`: MRP de un nivel con política LFL o lote fijo, lead time, safety stock, recepciones programadas; `.to_frame()`
- **`project`** — `cpm` / `ProjectResult` / `ActivityResult`: CPM determinístico; paso adelante/atrás; holgura total/libre; ruta crítica
- **`project`** — `pert` / `ProjectResult`: PERT estocástico; te = (a+4m+b)/6, σ² = ((b−a)/6)²; `.probability(target)` vía aproximación normal
- **`reliability`** — `weibull_analysis` / `WeibullResult`: Weibull biparamétrico (β, η) por MLE (bisección normalizada) o RRY (rangos medianos de Benard); MTTF, B10, B50, R(t), F(t), h(t), `.b_life(pct)`
- 91 nuevos tests (357 en total); sin dependencia de `scipy`

---

## [0.2.7] — 2026-09-29

### Añadido
- **`inventory`** — `exchange_curve` / `ExchangeCurveResult`: curva de intercambio Tipo 1 (ciclo); hipérbola N × I = cte.; solver analítico por target pedidos/año o inversión; `.curve_to_frame()`
- **`inventory`** — `safety_stock_curve` / `SafetyStockCurveResult`: curva de intercambio Tipo 2 (seguridad); política z común; solver por nivel de servicio o inversión en SS; reorder point por artículo; soporte `lead_time_std`
- 38 nuevos tests (266 en total); sin dependencia de `scipy`

---

## [0.2.6] — 2026-09-29

### Añadido
- **`inventory`** — `wagner_whitin`: dimensionado óptimo de lotes por programación dinámica (O(n²))
- **`inventory`** — `rq_policy` / `RQPolicyResult`: política de revisión continua (r, Q) con EOQ + punto de reorden estocástico
- **`inventory`** — `rs_policy` / `RSPolicyResult`: política de revisión periódica (R, S) con nivel de reposición estocástico
- **`scheduling`** — `schedule_single`: programación de una máquina con reglas SPT, EDD, WSPT, CR y FIFO
- **`scheduling`** — `johnson_flowshop` / `FlowShopResult`: algoritmo de Johnson para flow-shop de 2 máquinas (makespan óptimo)
- **`reliability`** — `mtbf_analysis`, `series_system`, `parallel_system`, `koon_system` / `ReliabilityResult`: confiabilidad con modelo exponencial, sistemas serie/paralelo/k-de-n, disponibilidad
- 40 nuevos tests (228 en total); sin dependencia de `scipy`

---


## [0.2.5] — 2026-09-29

### Añadido
- **`inventory`** — `ebq` / `EBQResult`: Lote Económico de Producción (EBQ/EPQ)
- **`inventory`** — `eoq_multi` / `ebq_multi` / `MultiItemResult`: EOQ y EBQ para múltiples artículos
- **`inventory`** — `eoq_multi_constrained` / `ConstrainedMultiEOQResult`: EOQ multi-artículo con restricciones de presupuesto, espacio y genéricas (relajación lagrangiana)
- **`inventory`** — `lot_for_lot`, `silver_meal` / `LotSizingResult`: heurísticas de dimensionado dinámico de lotes
- **`inventory`** — `eoq_quantity_discount` / `QuantityDiscountResult`: EOQ con descuentos por cantidad (todos los modelos)
- **`advanced`** — `break_even_multi` / `BreakEvenMultiResult`: punto de equilibrio multi-producto con WACM
- **`advanced`** — `break_even_sales`: punto de equilibrio en ingresos por ratio de coste variable
- **`queuing`** — `mg1`: modelo M/G/1 con fórmula exacta de Pollaczek-Khinchine
- **`queuing`** — `cv2_triangular`, `cv2_uniform`, `cv2_normal`, `cv2_erlang`, `cv2_gamma`, `cv2_lognormal`, `cv2_weibull`: helpers para calcular el CV² de cualquier distribución y alimentar `mg1` o `kingman`
- 62 nuevos tests (188 en total); sin dependencia de `scipy`

---


## [0.2.3] — 2026-09-29

### Cambiado
- Versión corregida a 0.2.3 (0.2.2 ya estaba ocupada en PyPI)

---

## [0.2.2] — 2026-09-25

### Añadido
- README exhaustivo con documentación completa de todas las funciones (20 secciones, ~1100 líneas)

---

## [0.2.1] — 2026-09-24

### Corregido
- `EOQResult.plot()` — implementa `plot_eoq` en `plotting.py`; ya no lanza `ImportError`
- `__version__` — se lee desde los metadatos del paquete instalado (`importlib.metadata`); `pyproject.toml` es la única fuente de verdad

### Añadido
- Workflow CI (`.github/workflows/ci.yml`) — ejecuta `pytest` en Python 3.9, 3.11 y 3.13 en cada push y PR a `main`

---

## [0.2.0] — 2026-09-24

### Añadido
- **`fitting`** — `fit_from_data`: estima λ, μ, ca², cs² desde tiempos entre llegadas, tiempos de servicio o timestamps crudos
- **`inventory`** — `eoq`, `reorder_point`, `newsvendor`; usa `statistics.NormalDist` de stdlib, sin scipy
- **`network`** — `jackson_network`: redes de Jackson abiertas vía ecuaciones de tráfico
- **`advanced`** — `mmck` (M/M/c/K), `mm1_priority` (prioridad HOL no-preemptiva, fórmula de Kleinrock)
- **`solver`** — `compare()` para comparar resultados en un DataFrame; corrección del upcast int→float en `batch_model`
- **CLI** (`python -m walopy`) — subcomandos `mm1`, `mmc`, `md1`, `eoq`, `--version`
- 126 tests en todos los módulos

---

## [0.1.0] - primera versión

### Añadido
- Modelos de colas: M/M/1, M/M/c, M/D/1, G/G/1 (Kingman).
- Ley de Little (`littles_law`).
- OEE con derivación desde inputs crudos.
- Utilización y eficiencia (`utilization_efficiency`).
- Costo unitario (`unit_cost`).
- Análisis de cuello de botella (`bottleneck_analysis`) con fracciones de routing.
- Árboles de KPI: `KPINode`, `oee_kpi_tree`, `throughput_kpi_tree`, `roi_kpi_tree`.
- Gráficas para cada módulo vía `.plot()`.
