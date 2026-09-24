# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

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
