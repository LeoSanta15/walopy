# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [0.1.0] - primera versión

### Añadido
- Modelos de colas: M/M/1, M/M/c, M/D/1, G/G/1 (Kingman).
- Ley de Little (`littles_law`).
- OEE con derivación desde inputs crudos.
- Utilización y eficiencia (`utilization_efficiency`).
- Costo unitario (`unit_cost`).
- Análisis de cuello de botella (`bottleneck_analysis`) con fracciones de routing.
- Árboles de KPI: `KPINode`, `oee_kpi_tree`, `throughput_kpi_tree`, `cost_kpi_tree`.
- Gráficas para cada módulo vía `.plot()`.
