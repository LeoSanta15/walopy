# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [Sin publicar]

### Cambiado
- **La versión tiene una sola fuente de verdad: el literal `__version__` de `src/walopy/__init__.py`**; `pyproject.toml` la lee con
  `[tool.setuptools.dynamic]`. Antes `__init__.py` la leía de `importlib.metadata`, que se congela al instalar: tras subir la versión,
  `walopy.__version__` mostraba la anterior hasta reinstalar.
- La publicación (`publish.yml`) comprueba que el wheel construido tiene la versión del tag (`scripts/comprobar_version_release.py`) y usa el mismo
  comando de `ruff` que el CI.

### Corregido
- La nota de `[0.3.0]` decía que las versiones `0.2.4` y `0.2.6` se publicaron sin tag. Comprobado en PyPI (2026-10-02): `0.2.6` sí está publicada y le falta el tag; `0.2.4` **no existe** en PyPI (su publicación falló y se saltó a `0.2.5`).

### Añadido
- **Fase 0 de la internacionalización (español por defecto e inglés):** `scripts/inventario_i18n.py` (`make inventario-i18n`) inventaría los 667 textos visibles de `src/` con sus marcadores, clasificados en 13 tipos; `docs/auditoria/inventario_i18n.json`, `INVENTARIO_I18N.md` y `PLAN_I18N.md` (plan por fases y decisiones D1–D4). `tests/test_inventario_i18n.py` mantiene el inventario al día y comprueba su cobertura con un método independiente; `tests/test_i18n_paridad.py` trae los verificadores de paridad entre idiomas (los tests sobre los catálogos reales se activan en la fase 1). No hay cambios de comportamiento.
- `Makefile` (`make check-fast`, `make check`, `make release-check TAG=vX.Y.Z`, …), `AGENTS.md`, `.claude/` (permisos y hooks `SessionStart` y `Stop` para agentes), `.github/CODEOWNERS`, `scripts/notas_release.py` (`make notas-release VERSION=X.Y.Z` imprime el cuerpo del release desde este archivo).
- `scripts/verificar_mutaciones.py`: mutación de una línea; cada test de regresión debe fallar si el bug vuelve (17 mutantes).
- `docs/retrospectiva/`: lecciones, catálogo de bugs, scorecard, playbook, reglas de `CLAUDE.md` y resumen ejecutivo.
- Los tests de `rcParams` cubren las 19 gráficas (15 con `.plot()` y 4 de llamada directa; antes solo 2).

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
