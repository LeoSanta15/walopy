# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

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
