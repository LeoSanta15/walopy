# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [Sin publicar]

Sin cambios todavía.

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
