# INVENTARIO I18N — texto visible de walopy (generado)

> Generado por `python scripts/inventario_i18n.py`; **no editar a mano**. Fuente de verdad: `docs/auditoria/inventario_i18n.json`.
> 667 textos únicos, 820 usos en el código. Idioma base: `es`.
> Un texto repetido en un módulo cuenta una vez (clave única) y aparece con su número de usos.

## Por tipo y módulo (textos únicos)

| módulo | acceso_columna | aviso | cabecera | clave_params | cli | columna_df | error | etiqueta | grafica | kpi | modelo | nombre_arg | valor_por_defecto | total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `__main__` |  |  |  |  | 17 |  |  |  |  |  |  |  |  | 17 |
| `_utils` |  |  |  |  |  |  | 12 |  |  |  |  |  |  | 12 |
| `advanced` |  |  | 14 | 11 |  | 15 | 14 | 34 |  |  | 3 | 2 | 1 | 94 |
| `bottleneck` |  |  | 6 |  |  |  | 2 | 10 |  |  |  | 2 |  | 20 |
| `fitting` |  |  | 2 |  |  |  | 6 | 9 |  |  |  |  |  | 17 |
| `inventory` | 8 | 1 | 52 | 15 |  | 18 | 29 | 70 |  |  | 3 | 16 | 4 | 216 |
| `kpi` |  |  | 5 |  |  |  |  | 1 |  | 32 |  |  |  | 38 |
| `network` |  |  | 3 | 2 |  |  | 7 | 14 |  |  |  | 3 |  | 29 |
| `operations` |  |  | 12 |  |  |  |  | 6 |  |  |  |  |  | 18 |
| `plotting` | 8 |  |  |  |  |  |  |  | 66 |  |  |  |  | 74 |
| `project` |  |  | 4 |  |  |  | 9 | 5 |  |  |  | 7 |  | 25 |
| `queuing` |  |  | 8 | 4 |  |  | 7 | 11 |  |  | 2 |  |  | 32 |
| `reliability` |  | 2 | 7 | 1 |  |  | 5 | 7 |  |  |  |  |  | 22 |
| `scheduling` |  |  | 9 |  |  |  | 8 | 10 |  |  |  | 5 | 1 | 33 |
| `solver` |  |  |  | 5 |  | 3 | 7 | 5 |  |  |  |  |  | 20 |
| **total** | 16 | 3 | 122 | 38 | 17 | 36 | 106 | 182 | 66 | 32 | 8 | 35 | 6 | **667** |

## Complejidad de la plantilla

`fija` sin variables · `simple` solo nombres · `formato` con `!r` o formato numérico (`:.6g`) · `compleja` con expresiones (llamadas, índices…).

| tipo | fija | simple | formato | compleja |
|---|---|---|---|---|
| acceso_columna | 16 |  |  |  |
| aviso |  |  | 3 |  |
| cabecera | 119 | 1 |  | 2 |
| clave_params | 38 |  |  |  |
| cli | 15 | 2 |  |  |
| columna_df | 36 |  |  |  |
| error | 60 | 19 | 22 | 5 |
| etiqueta | 81 | 13 | 77 | 11 |
| grafica | 52 | 8 | 5 | 1 |
| kpi | 30 | 2 |  |  |
| modelo | 4 | 3 | 1 |  |
| nombre_arg |  | 34 | 1 |  |
| valor_por_defecto | 1 |  |  | 5 |

## Riesgos que detecta el inventario

- **Columnas/claves de `DataFrame` devueltas directamente por funciones públicas: 36**, y **16 accesos por texto** (`df["Estación"]`). Traducir una columna sin cambiar sus accesos rompe el código (p. ej. `plotting.py` lee `df["Tiempo_ciclo"]`).
- **Nombres de argumento dentro de mensajes: 35** (`capacity[{i}]`…): no se traducen; el inventario los separa para no contarlos.
- **Claves de `params` legibles: 38.** Si cambian con el idioma, `result.params[«clave»]` deja de funcionar al cambiar de idioma (ver `PLAN_I18N.md`).
- **Nombres generados por defecto: 6** (`Artículo{i}`, `escenario_{n}`): si dependen del idioma cambian los datos, no solo la presentación.
- **Textos sin clasificar: 0** (revisión manual obligatoria antes de la fase 1).
- **Plantillas con expresiones complejas: 24** (hay que precalcular el valor antes de llamar a `t()`).
- **Mensajes construidos fuera de la excepción (`raise <variable>`): 0** (no se pueden extraer sin leer el código).

## Textos sin clasificar

_(ninguno)_

## Mensajes indirectos

_(ninguno)_

## Accesos a columnas por su texto (acoplamiento)

- `inventory.eoq_quantity_discount`: 'Costo de compra'
- `inventory.eoq_quantity_discount`: 'Costo de mantener'
- `inventory.eoq_quantity_discount`: 'Costo de ordenar'
- `inventory.eoq_quantity_discount`: 'Costo total'
- `inventory.eoq_quantity_discount`: 'Precio unitario'
- `inventory.eoq_quantity_discount`: 'Q ajustada'
- `inventory.eoq_quantity_discount`: 'Índice de tramo'
- `inventory.exchange_curve`: 'Q_eoq'
- `plotting.plot_line_balance`: 'Estación'
- `plotting.plot_line_balance`: 'Sobrecargada'
- `plotting.plot_line_balance`: 'Tiempo_ciclo'
- `plotting.plot_line_balance`: 'Tiempo_ocioso'
- `plotting.plot_queue_distribution`: 'F(t)'
- `plotting.plot_queue_distribution`: 'P(N<=n)'
- `plotting.plot_queue_distribution`: 'P(N=n)'
- `plotting.plot_queue_distribution`: 'f(t)'

## Columnas de DataFrame devueltas por funciones públicas

- `advanced.break_even_multi`: 'Costo variable'
- `advanced.break_even_multi`: 'Mezcla'
- `advanced.break_even_multi`: 'PE ingresos'
- `advanced.break_even_multi`: 'PE unidades'
- `advanced.break_even_multi`: 'Precio'
- `advanced.break_even_multi`: 'Producto'
- `advanced.line_balance`: 'Estación'
- `advanced.line_balance`: 'Sobrecargada'
- `advanced.line_balance`: 'Tiempo_ciclo'
- `advanced.line_balance`: 'Tiempo_ocioso'
- `advanced.line_balance`: 'Utilización'
- `advanced.queue_length_pmf`: 'P(N<=n)'
- `advanced.queue_length_pmf`: 'P(N=n)'
- `advanced.sojourn_cdf`: 'F(t)'
- `advanced.sojourn_cdf`: 'f(t)'
- `inventory.<módulo>`: 'Q_eoq'
- `inventory.<módulo>`: 'Q_optimal'
- `inventory.ebq_multi`: 'Costo de preparación'
- `inventory.ebq_multi`: 'Frecuencia de lotes'
- `inventory.ebq_multi`: 'Inventario máximo'
- `inventory.ebq_multi`: 'Inventario promedio'
- `inventory.eoq_multi`: 'Artículo'
- `inventory.eoq_multi`: 'Costo de mantener'
- `inventory.eoq_multi`: 'Costo de ordenar'
- `inventory.eoq_multi`: 'Costo total'
- `inventory.eoq_multi`: 'Frecuencia de pedidos'
- `inventory.eoq_multi`: 'Tiempo de ciclo'
- `inventory.eoq_quantity_discount`: 'Cantidad mín.'
- `inventory.eoq_quantity_discount`: 'Costo de compra'
- `inventory.eoq_quantity_discount`: 'Factible'
- `inventory.eoq_quantity_discount`: 'Precio unitario'
- `inventory.eoq_quantity_discount`: 'Q ajustada'
- `inventory.eoq_quantity_discount`: 'Índice de tramo'
- `solver.solve_lam`: 'lam'
- `solver.solve_mu`: 'mu'
- `solver.solve_servers`: 'c (servidores)'

## Nombres generados por defecto

- `advanced.break_even_multi`: 'Producto-{expr}'
- `inventory.abc_analysis`: 'Artículo{expr}'
- `inventory.eoq_multi`: 'Artículo-{expr}'
- `inventory.exchange_curve`: 'I{expr}'
- `inventory.mrp`: 'Artículo'
- `scheduling.schedule_single`: 'J{expr}'

## Claves de `params`

- `advanced.break_even_multi`: 'fixed_cost'
- `advanced.break_even_multi`: 'n_products'
- `advanced.mm1_priority`: 'N_clases'
- `advanced.mm1_priority`: 'R (residual)'
- `advanced.mm1k`: 'K (capacidad)'
- `advanced.mm1k`: 'P0 (vacío)'
- `advanced.mm1k`: 'PK (prob. de bloqueo)'
- `advanced.mm1k`: 'λ_eff (tasa efectiva)'
- `advanced.monte_carlo_gg1`: 'ca2'
- `advanced.monte_carlo_gg1`: 'cs2'
- `advanced.monte_carlo_gg1`: 'seed'
- `inventory.ebq`: 'production_rate'
- `inventory.ebq`: 'setup_cost'
- `inventory.eoq`: 'demand_rate'
- `inventory.eoq`: 'holding_cost'
- `inventory.eoq`: 'ordering_cost'
- `inventory.eoq_multi`: 'n_items'
- `inventory.eoq_quantity_discount`: 'holding_cost_rate'
- `inventory.newsvendor`: 'cost'
- `inventory.newsvendor`: 'demand_mean'
- `inventory.newsvendor`: 'price'
- `inventory.newsvendor`: 'salvage'
- `inventory.reorder_point`: 'demand_std'
- `inventory.reorder_point`: 'lead_time'
- `inventory.reorder_point`: 'lead_time_std'
- `inventory.rs_policy`: 'review_period'
- `network.jackson_network`: 'J'
- `network.jackson_network`: 'total_gamma'
- `queuing.kingman`: 'ca² (CV² de llegadas)'
- `queuing.kingman`: 'cs² (CV² de servicio)'
- `queuing.mm1`: 'P0 (prob. de sistema vacío)'
- `queuing.mmc`: 'C(c,a) Erlang-C'
- `reliability.koon_system`: 'k'
- `solver.optimize_servers`: 'cost_per_server'
- `solver.optimize_servers`: 'cost_per_wait'
- `solver.solve_lam`: 'model'
- `solver.solve_lam`: 'mu'
- `solver.solve_mu`: 'lam'

## Plantillas complejas

- `utils.error.as_float_list.debe_contener_menos_elementos_recibieron`: "'{name}' debe contener al menos {min_len} elementos, se recibieron {expr}." — `expr` = `len(out)`
- `advanced.valor_por_defecto.break_even_multi.producto`: 'Producto-{expr}' — `expr` = `i + 1`
- `inventory.error.eoq_multi_constrained.restriccion_weights_tiene_longitud_distinta`: "La restricción '{expr}': 'weights' tiene una longitud distinta a demand_rates." — `expr` = `c['name']`
- `inventory.etiqueta.summary.ct`: '  {expr:<16} Q*={expr2:.4g}  CT={expr3:.4g}' — `expr` = `row['Artículo']`, `expr2` = `row['Q*']`, `expr3` = `row['Costo total']`
- `inventory.etiqueta.summary.restricciones_activas`: 'Restricciones activas: {expr}' — `expr` = `', '.join(self.binding_constraints) or 'ninguna'`
- `inventory.etiqueta.summary.cv`: 'CV > {expr:.2g}' — `expr` = `t['y']`
- `inventory.etiqueta.summary.cv_2`: 'CV ≤ {expr:.2g}' — `expr` = `t['x']`
- `inventory.etiqueta.summary.cv_3`: '{expr:.2g} < CV ≤ {expr2:.2g}' — `expr` = `t['x']`, `expr2` = `t['y']`
- `inventory.valor_por_defecto.abc_analysis.articulo`: 'Artículo{expr}' — `expr` = `i + 1`
- `inventory.valor_por_defecto.eoq_multi.articulo`: 'Artículo-{expr}' — `expr` = `i + 1`
- `inventory.valor_por_defecto.exchange_curve.texto`: 'I{expr}' — `expr` = `idx + 1`
- `network.error.jackson_network.estacion_inestable_aumente_capacidad_reduzca`: "La estación '{expr}' es inestable: ρ = {rho_j:.4g} ≥ 1. Aumente la capacidad o reduzca las tasas de llegada." — `expr` = `names[j]`
- `plotting.grafica.plot_break_even.pe`: 'PE ({bep:.0f} {expr})' — `expr` = `'ventas' if en_ventas else 'unidades'`
- `project.etiqueta.summary.ruta_critica`: 'Ruta crítica       : {expr}' — `expr` = `' → '.join(self.critical_path)`
- `reliability.etiqueta.summary.tasas_falla`: 'Tasas de falla λ: {expr}' — `expr` = `[f'{l:.4g}' for l in self.failure_rates]`
- `scheduling.cabecera.to_frame.fin`: 'M{expr}_fin' — `expr` = `mi + 1`
- `scheduling.cabecera.to_frame.inicio`: 'M{expr}_inicio' — `expr` = `mi + 1`
- `scheduling.error.neh_flowshop.todas_filas_deben_tener_misma`: 'Todas las filas deben tener la misma longitud; la fila {i} tiene {expr} ≠ {m_cnt}.' — `expr` = `len(row)`
- `scheduling.etiqueta.summary.secuencia_makespan`: 'Secuencia : {expr}\nMakespan  : {makespan:.4g}' — `expr` = `' → '.join(self.sequence)`
- `scheduling.etiqueta.summary.algoritmo_heuristica_neh_maquinas_secuencia`: 'Algoritmo : heurística NEH\nMáquinas  : {n_machines}\nSecuencia : {expr}\nMakespan  : {makespan:.4g}' — `expr` = `' → '.join((str(s) for s in self.sequence))`
- `scheduling.etiqueta.summary.secuencia`: 'Secuencia               : {expr}' — `expr` = `' → '.join(self.sequence)`
- `scheduling.valor_por_defecto.schedule_single.texto`: 'J{expr}' — `expr` = `i + 1`
- `solver.error.solve_lam.modelo_desconocido_elija_entre`: "Modelo desconocido '{model}'. Elija entre {expr}." — `expr` = `list(_models)`
- `solver.etiqueta.compare.escenario`: 'escenario_{expr}' — `expr` = `i + 1`
