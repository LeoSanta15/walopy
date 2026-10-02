# HALLAZGOS — walopy v0.2.8

> Commit auditado `2cc17c1`. Cada ficha: ID · archivo:línea · clase · severidad · evidencia (HECHO) · causa raíz · corrección propuesta · test de regresión propuesto.
> Reproducciones: ejecutadas fuera del árbol de código (scratchpad de la sesión) con Python 3.11 y numpy 2.4.6 / pandas 3.0.6, salvo indicación.
> Severidad: Crítica / Alta / Media / Baja. **Ninguna es Crítica**: no hay pérdida de datos, fallo de seguridad explotable ni resultado erróneo en el camino feliz.
> Los IDs `K-xx` corresponden a clases del catálogo (`BUG_CATALOG.md`); `N-xx` son hallazgos nuevos. Marca ★ = candidato a añadir al catálogo.

## Estado tras la ejecución (2026-10-02)

**Cerrados con test de regresión:** K-01, K-02, K-03, K-04, K-05, K-06, K-07, K-09, K-10, K-11, K-12, K-13, N-01, N-02, N-03, N-04, N-05, N-06, N-07, N-08, N-09, N-10, N-11, N-12 (traducción completa, comprobada por `tests/test_idioma.py`), N-14, N-16.
**Parciales:** K-08 (listas vacías sí; magnitudes extremas 1e308/1e-320 no), N-15 (SECURITY, CoC y plantillas sí; `attestations` sigue desactivado).
**Trazabilidad:** cada bug corregido figura como `W-nn` en `tests/regresiones.json` y se verifica contra `v0.2.8` (ver `TRAZABILIDAD.md`).
**Sin cambios por decisión:** N-13 (matplotlib y plotly siguen siendo obligatorias; extras `[plot]` pospuestos a 0.4.0).

---

## Resumen

| ID | Clase | Sev. | Título |
|---|---|---|---|
| K-01 | C-01 | Alta | NaN/inf/negativos pasan la validación en CPM/PERT, MTBF/sistemas, MRP y Weibull |
| K-02 | C-01 | Media | Otras entradas aceptadas en silencio (`cv2_uniform`, `break_even_multi`, `queue_length_pmf`, `eoq_multi_constrained`, `roi_kpi_tree`) |
| K-03 | C-01 | Media | `items` malformado en ABC/XYZ → `KeyError`/`AttributeError` opacos |
| K-04 | C-02 | Media | `abc_analysis` rechaza artículos con demanda 0 |
| K-05 | C-02 | Media | Weibull con datos constantes: β recortado a 100 sin aviso (MLE) y `ZeroDivisionError` (RRY) |
| K-06 | C-02 | Alta | `mmc` desborda con carga ofrecida ≳ 140 servidores |
| K-07 | C-02 | Alta | `eoq_multi_constrained(budget ≤ 0)` se cuelga o lanza `ZeroDivisionError` |
| K-08 | C-02 | Media | `series_system([])` y magnitudes extremas → `ZeroDivisionError`/`OverflowError` crudos |
| K-09 | C-05 | Alta | `CLAUDE.md` desactualizado |
| K-10 | C-05 | Alta | README documenta API inexistente (13 de 61 bloques fallan) |
| K-11 | C-05 | Alta | Funciones de v0.2.6–v0.2.8 sin documentar; Sphinx y changelog de docs congelados |
| K-12 | C-04 | Alta | CI sin linter, tipos, build, docs ni cobertura; matriz incompleta; publicación sin tests |
| K-13 | C-08 | Baja | Fallback de versión obsoleto, sin test de igualdad, tags v0.2.4/v0.2.6 ausentes |
| N-01 | nuevo ★ | Media | `plotting.py` con 0 % de cobertura y un `plot()` roto |
| N-02 | nuevo | Media | 78 errores de mypy / 43 F821; sin `py.typed` |
| N-03 | nuevo ★ | Media | Complejidad documentada ≠ real (Wagner-Whitin, NEH) |
| N-04 | nuevo ★ | Alta | CPM/PERT fusionan en silencio actividades con el mismo nombre |
| N-05 | nuevo | Media | MRP descarta sin aviso liberaciones que caen antes del periodo 1 |
| N-06 | nuevo ★ | Media | Tamaños sin cota bloquean el proceso |
| N-07 | nuevo | Baja | `bool` aceptado como entero; excepciones sin `from` |
| N-08 | nuevo | Baja | Código muerto e imports sin usar |
| N-09 | nuevo | Baja | Política de entrada vacía inconsistente |
| N-10 | nuevo | Baja | Metadatos de `pyproject.toml` obsoletos y reglas de ruff sin definir |
| N-11 | nuevo | Media | Higiene de tests (sin `conftest`, sin parametrizar, nombre por versión) |
| N-12 | nuevo | Baja | Idioma inconsistente (documentación en español, mensajes en inglés) |
| N-13 | nuevo | Baja | matplotlib y plotly obligatorios aunque se importan de forma perezosa |
| N-14 | nuevo | Baja | `batch_model`: columna `_error` condicional y `except Exception` amplio |
| N-15 | nuevo | Baja | Sin SECURITY/CoC/templates; `attestations: false` |
| N-16 | nuevo | Media | 68/70 funciones sin sección `Raises`, 47/70 sin `Examples` |

Clases del catálogo **sin reproducción**: C-03 (no hay dependencias opcionales; matplotlib/plotly son obligatorias), C-06 (no se halló validación nueva que rompa llamadas internas), C-07 (`rcParams` idéntico tras 19 `plot()`).

---

## Fichas

### K-01 · NaN/inf/negativos pasan la validación en CPM/PERT, MTBF/sistemas, MRP y Weibull
- **Archivo:línea:** `project.py:249-252` (`dur < 0.0`), `reliability.py:144-145, 184-185, 229+` (`t` y `mttr` sin validar), `inventory.py:2489` (`initial_on_hand` sin validar), `reliability.py:472-477` (`t <= 0.0`).
- **Clase:** C-01 (validación faltante) — variante ★ "la comparación con NaN es siempre falsa".
- **Severidad:** Alta (resultado silenciosamente incorrecto).
- **Evidencia:**
  - `wl.cpm([{"name":"A","duration":float("nan"),"predecessors":[]}]).project_duration` → `nan`; con `inf` → `inf`.
  - `wl.mtbf_analysis(0.01, t=-1.0).R_t` → `1.0100` (una fiabilidad > 1); `mttr=-1` → disponibilidad `1.0101`. Igual en `series_system`, `parallel_system`, `koon_system` con `t=nan/inf/-inf`.
  - `wl.mrp([10,20,30], initial_on_hand=float("nan"))` → `Proj_On_Hand = nan`; `initial_on_hand=-1` aceptado.
  - `wl.weibull_analysis([nan,1.0,2.0])` y con `inf` → `OverflowError: math range error` (`reliability.py:490`).
- **Causa raíz (inferencia):** estas rutas convierten con `float()` y comparan con `<`/`<=`, que devuelven `False` para NaN; no pasan por `_utils.as_*`, que sí rechaza no finitos.
- **Corrección propuesta:** usar `as_nonneg`/`as_finite_scalar`/`as_positive` de `_utils` en todos los puntos de ingesta citados; añadir `_utils.as_positive_list` para secuencias y reutilizarlo.
- **Test de regresión:** parametrizado `[nan, inf, -inf, -1]` × {`cpm`, `pert`, `mtbf_analysis`, `series_system`, `parallel_system`, `koon_system`, `mrp`, `weibull_analysis`} esperando `ValueError`.

### K-02 · Otras entradas aceptadas en silencio
- **Archivo:línea:** `queuing.py` (`cv2_uniform`), `advanced.py` (`break_even_multi`), `queuing.py` (`queue_length_pmf`), `inventory.py:~925` (`eoq_multi_constrained`), `kpi.py` (`roi_kpi_tree`).
- **Clase:** C-01. **Severidad:** Media.
- **Evidencia:** `cv2_uniform(nan, 3.0)` → `nan`; `break_even_multi(1000,[10,20],[4,8],[nan,1.0]).bep_units_total` → `nan`; `queue_length_pmf(2.0, 3.0, n_max=-1.0)` → DataFrame vacío; `eoq_multi_constrained(..., budget=nan)` devuelve un coste; `roi_kpi_tree(revenue=-1.0)` e `investment=-1.0` aceptados.
- **Corrección propuesta:** validar con `_utils`; `n_max` entero ≥ 0. (Corrección de la auditoría: `sales_mix` son pesos relativos que se normalizan por diseño; no debe sumar 1.)
- **Test:** parametrizados análogos a K-01.

### K-03 · `items` malformado en ABC/XYZ → errores opacos
- **Archivo:línea:** `inventory.py:2184-2186` (`it.get(...)`, `it["unit_value"]`), y los equivalentes en `xyz_analysis`/`abc_xyz`.
- **Clase:** C-01. **Severidad:** Media.
- **Evidencia:** `abc_analysis([{"name":"a","demand":5}])` → `KeyError: 'unit_value'`; `abc_analysis("abc")` → `AttributeError: 'str' object has no attribute 'get'`.
- **Causa raíz:** acceso directo a claves sin comprobar que el elemento es un `dict` ni que las claves existen.
- **Corrección:** helper `_require_item_keys(it, i, keys)` que lance `ValueError("items[0]: falta la clave 'unit_value'")`.
- **Test:** `pytest.raises(ValueError, match="unit_value")` y `match="items"` para entrada no iterable de dicts.

### K-04 · `abc_analysis` rechaza artículos con demanda 0
- **Archivo:línea:** `inventory.py:2185` (`as_positive` para `demand`).
- **Clase:** C-02 (caso degenerado válido no considerado). **Severidad:** Media.
- **Evidencia:** `abc_analysis([{"name":"a","demand":0,"unit_value":1},{"name":"b","demand":0,"unit_value":1}])` → `ValueError: items[0]['demand'] must be a finite positive number`; con un inventario real con un solo SKU sin movimiento, toda la lista falla.
- **Corrección:** permitir `demand ≥ 0` (`as_nonneg`); si el valor total es 0, lanzar `ValueError` explícito; los artículos de valor 0 quedan en C.
- **Test:** lista con un artículo de demanda 0 → clase C; todos 0 → `ValueError` con mensaje claro.

### K-05 · Weibull con datos constantes o casi constantes
- **Archivo:línea:** `reliability.py:408` (`lo, hi = 1e-4, 100.0`), `reliability.py:435` (`slope = ... / (n*sxx - sx**2)`).
- **Clase:** C-02 (equivalente a BUG-05 del catálogo: sigma = 0). **Severidad:** Media.
- **Evidencia:** `weibull_analysis([5,5,5,5])` → `shape = 100.0`, sin aviso (β real tiende a ∞); `weibull_analysis([5,5,5,5.0000001])` → también `100.0`; `weibull_analysis([5,5,5,5], method="RRY")` → `ZeroDivisionError`.
- **Corrección:** detectar dispersión nula (todos iguales) → `ValueError` con mensaje; si la cota 100 limita la solución, emitir `UserWarning`; RRY con denominador 0 → `ValueError`.
- **Test:** datos constantes, casi constantes y n=2 en ambos métodos.

### K-06 · `mmc` desborda con carga ofrecida ≳ 140
- **Archivo:línea:** `queuing.py:204-205` (`(a**n)/math.factorial(n)` y `(a**c)/...`).
- **Clase:** C-02 (caso de escala no considerado). **Severidad:** Alta (modelo clave de la librería; afecta a `solve_servers`/`optimize_servers` con cargas grandes).
- **Evidencia:** `wl.mmc(95.0,1.0,100)` OK; `wl.mmc(145.0,1.0,150)`, `wl.mmc(195.0,1.0,200)`, `wl.mmc(295.0,1.0,300)` → `OverflowError: (34, 'Numerical result out of range')`. En cambio `erlang_b` y `mmck` con c=300 funcionan (usan recurrencias estables).
- **Causa raíz:** potencias y factoriales explícitos desbordan `float` (`145**143 ≈ 1e309`).
- **Corrección:** calcular Erlang-B por recurrencia y derivar Erlang-C (`C = B / (1 − ρ(1 − B))`), o trabajar con `lgamma`; mantener los mismos resultados.
- **Test:** `mmc` contra el balance de nacimiento-muerte truncado para c ∈ {2, 10, 100, 150, 300, 1000}; comprobar que los valores antiguos no cambian (tolerancia 1e-9).

### K-07 · `eoq_multi_constrained` con presupuesto ≤ 0
- **Archivo:línea:** `inventory.py:~936` (cálculo de `Q_opt` con multiplicador), bucle de búsqueda del multiplicador.
- **Clase:** C-02. **Severidad:** Alta (bloqueo del proceso).
- **Evidencia:** `eoq_multi_constrained([1000,500],[50,30],[2,1], budget=-1.0, budget_unit_costs=[10,5])` no termina en 5 s (hang); `budget=0.0` → `ZeroDivisionError` (`inventory.py:936`); `budget=nan` y `inf` aceptados sin aviso.
- **Corrección:** validar `budget`, `space` y costes con `as_positive`; poner una cota de iteraciones a la búsqueda del multiplicador y lanzar `ValueError` si no converge.
- **Test:** `budget ∈ {0, -1, nan, inf}` → `ValueError` en < 1 s.

### K-08 · Errores crudos con listas vacías y magnitudes extremas
- **Archivo:línea:** `reliability.py:183` (`series_system([])`), `inventory.py:118` (`eoq` con 1e308), `queuing.py` (`cv2_erlang(k=inf)`), `reliability.py`/`inventory.py` (`reorder_point(demand_rate=1e308)`).
- **Clase:** C-01/C-02. **Severidad:** Media (`series_system([])` es realista) / Baja (1e308).
- **Evidencia:** 30 excepciones que no son `ValueError`/`TypeError` en el barrido; las más relevantes: `series_system([])` → `ZeroDivisionError: float division by zero`.
- **Corrección:** validar listas no vacías con `as_nonempty`; capturar desbordes con un mensaje que indique que el valor está fuera de rango.
- **Test:** `series_system([])`, `parallel_system([])`, `cv2_erlang(inf)` → `ValueError`.

### K-09 · `CLAUDE.md` desactualizado
- **Archivo:línea:** `CLAUDE.md` (toda la sección "Structure" y "Release checklist").
- **Clase:** C-05 (L-07 del catálogo). **Severidad:** Alta (cada sesión nueva parte de información falsa).
- **Evidencia:** lista 6 de 15 módulos (faltan `solver`, `advanced`, `fitting`, `inventory`, `network`, `scheduling`, `reliability`, `project`); cita `cost_kpi_tree` (no existe; es `roi_kpi_tree`); el checklist manda subir la versión en `pyproject.toml` y en `__init__.py`, pero `__init__.py` ya la lee de `importlib.metadata`; falta el comando de build, cobertura con `--cov-report=term-missing`, "definición de terminado" y las reglas R-01…R-12 de `CLAUDE_MD_RULES.md`.
- **Corrección:** reescribir con el bloque de `CLAUDE_MD_RULES.md` (paquete `walopy`, PyPI `walopy`), mapa real del código y checklist de release corregido.
- **Test/verificación:** `grep -rn "cost_kpi_tree" CLAUDE.md` vacío; un test que compare los módulos listados en `CLAUDE.md` con `src/walopy/*.py`.

### K-10 · README documenta API inexistente
- **Archivo:línea:** `README.md:152, 235, 398, 886-896, 939, 958, 1064, 1084-1110, 1162`.
- **Clase:** C-05 (documentación falsa). **Severidad:** Alta.
- **Evidencia:** al ejecutar los 61 bloques ```python del README, **13 fallan**:
  - `utilization_efficiency(actual_output=…, max_output=…)` → no existe `max_output` (la firma es `capacity`).
  - `unit_cost(fixed_cost, variable_cost, units)` → la firma real es `variable_cost_per_unit`, `units_produced`; `r.var_cost_per_unit` no existe.
  - `line_balance(names=…, investment=…)` → la firma real es `station_names`; no hay `investment`.
  - `wl.KPINode(...).add_child(...)` → el método no existe.
  - `solve_lam/solve_mu/solve_servers(..., target=…)` → la firma real es `target_metric`, `target_value`.
  - `OptimizeResult.optimal_cost`, `BreakEvenResult.profit` → atributos inexistentes.
  - `mm1k(...).params["lam_eff"]` → la clave real es `"λ_eff (effective rate)"`.
  - `batch_model` documenta la columna `_error` siempre presente, pero el código la elimina si no hay errores.
  - Dos bloques usan `...` o `fit.to_model_kwargs()` con datos que no producen `mu`/`cs2`.
- **Causa raíz (inferencia):** el README se escribió sin ejecutar los ejemplos.
- **Corrección:** corregir cada bloque con la firma real y añadir `tests/test_readme.py` que ejecute los bloques ```python (con `MPLBACKEND=Agg`).
- **Test:** el propio `tests/test_readme.py` (0 bloques fallidos; los marcados `# no-run` se excluyen de forma explícita).

### K-11 · Documentación ausente para v0.2.6–v0.2.8 y docs congelados
- **Archivo:línea:** `README.md` (sin secciones), `docs/source/referencia/index.md` (4 módulos), `docs/source/changelog.md:5` (`## [0.1.0]`), `docs/source/conf.py:3` (`release = "0.1.0"`).
- **Clase:** C-05. **Severidad:** Alta.
- **Evidencia:** `grep -c` en README y `docs/source`: `neh_flowshop`, `weibull_analysis`, `wl.cpm`, `wl.pert`, `abc_analysis`, `xyz_analysis`, `abc_xyz`, `wl.mrp` → **0 menciones**. Sphinx referencia 4 de 15 módulos y construye "sin warnings" porque documenta poco.
- **Corrección:** añadir secciones al README y páginas `.rst` para los 15 módulos; incluir `CHANGELOG.md` en Sphinx y leer `release` de `importlib.metadata`.
- **Test:** `sphinx-build -W` en CI; test que verifique que cada símbolo de `__all__` aparece en el README o en la referencia Sphinx.

### K-12 · CI sin gates de calidad
- **Archivo:línea:** `.github/workflows/ci.yml` (único job `test`), `.github/workflows/publish.yml`.
- **Clase:** C-04. **Severidad:** Alta.
- **Evidencia:** solo `pytest tests/ -q --tb=short` en 3.9/3.11/3.13; los `classifiers` declaran también 3.10 y 3.12; ruff (215/82 errores) y mypy (78) no se ejecutan, por eso nunca fallan; `publish.yml` construye y publica sin ejecutar tests ni `twine check`.
- **Corrección:** jobs `lint`, `types`, `coverage` (`--cov-fail-under=85`), `build` (+`twine check`), `docs` (`-W`), `audit` (`pip-audit`); matriz 3.9–3.13; `publish` dependiente del job de tests.
- **Test/verificación:** introducir un error de lint deliberado en una rama de prueba y comprobar que el CI falla.

### K-13 · Versión: fallback y tags
- **Archivo:línea:** `src/walopy/__init__.py:171` (`__version__ = "0.2.0"`).
- **Clase:** C-08. **Severidad:** Baja (la fuente única ya funciona).
- **Evidencia:** el fallback devuelve `0.2.0` aunque el paquete sea 0.2.8; no hay test de igualdad; `git ls-remote --tags` no contiene v0.2.4 ni v0.2.6.
- **Corrección:** fallback `"0+unknown"`; test `walopy.__version__ == importlib.metadata.version("walopy")`; decidir si se crean los tags faltantes sobre los commits correspondientes.

### N-01 ★ · `plotting.py` con 0 % de cobertura y un `plot()` roto
- **Archivo:línea:** `plotting.py:500` (`p["price_per_unit"]`).
- **Clase:** nueva (relacionada con BUG-01: código de gráficos sin test de regresión). **Severidad:** Media.
- **Evidencia:** 220 de 220 sentencias sin cobertura. Al ejecutar `.plot()` de 20 resultados: 19 correctos; `break_even_sales(1000, 0.4).plot()` → `KeyError: 'price_per_unit'` (el resultado de `break_even_sales` no guarda ese parámetro).
- **Corrección:** hacer que `plot_break_even` soporte resultados de `break_even_sales` (o que éstos guarden los parámetros necesarios).
- **Test:** smoke test con backend `Agg` que llame a los 12 `plot_*` y a cada `.plot()` y compruebe el tipo devuelto.

### N-02 · Tipado: 78 errores de mypy, sin `py.typed`
- **Archivo:línea:** 43 × name-defined (13 módulos), `scheduling.py:190-201, 293-306`, `inventory.py:1755-1780, 2190-2202`, `solver.py:407-415`.
- **Severidad:** Media.
- **Evidencia:** los 43 `F821`/`name-defined` son `pd`, `plt` y `go` usados en anotaciones cadena sin `if TYPE_CHECKING:`; los 24 `operator` provienen de `list[dict]` cuyos valores se infieren como `object`/`str | float | None`; no existe `src/walopy/py.typed`.
- **Corrección:** imports bajo `TYPE_CHECKING`; `TypedDict` o dataclasses para los registros internos; añadir `py.typed` y `package-data`.
- **Test/verificación:** `mypy src/walopy` → `Success`; un test que verifique que `py.typed` está en el wheel.

### N-03 ★ · Complejidad documentada ≠ real
- **Archivo:línea:** `inventory.py:1297` ("Time complexity O(n²)") y `CHANGELOG.md:32`; `scheduling.py:395` ("Runs in O(n²m)").
- **Severidad:** Media (la promesa de rendimiento es falsa; los tiempos medidos crecen de forma cúbica).
- **Evidencia:** `wagner_whitin`: n=100 → 0,011 s; n=400 → 0,56 s; n=1000 → **10,2 s** (el cálculo `hold = h * sum(...)` dentro del doble bucle lo hace O(n³)). `neh_flowshop`: n=50,m=5 → 0,07 s; n=100,m=10 → 0,64 s; n=200,m=10 → **5,3 s** (recalcula el makespan completo en cada inserción: O(n³m)).
- **Corrección:** sumas acumuladas en Wagner-Whitin (O(n²) real); aceleración de Taillard en NEH (O(n²m) real). Alternativa mínima: corregir la documentación.
- **Test:** igualdad de resultados con la versión actual (referencia fuerza bruta ya validada) + prueba de tiempo no bloqueante (benchmark).

### N-04 ★ · CPM/PERT fusionan actividades con el mismo nombre
- **Archivo:línea:** `project.py:246-252` (`acts[nm] = {...}` sobrescribe).
- **Severidad:** Alta (resultado erróneo sin aviso).
- **Evidencia:** `cpm([{"name":"A","duration":1,...},{"name":"A","duration":9,...}])` → una sola actividad `A`, duración 9.
- **Corrección:** `ValueError(f"Nombre de actividad duplicado: 'A'")`.
- **Test:** nombres duplicados en `cpm` y `pert`.

### N-05 · MRP descarta liberaciones que caen antes del periodo 1
- **Archivo:línea:** `inventory.py:2506-2513`.
- **Severidad:** Media.
- **Evidencia:** `wl.mrp([10,20], lead_time=5)` → `planned_receipts = [10, 20]` pero `planned_releases = [0, 0]`: las órdenes planificadas "vencidas" desaparecen sin aviso.
- **Corrección:** emitir `UserWarning` y exponer un campo `past_due_releases`.
- **Test:** `pytest.warns(UserWarning)` y comprobar el campo.

### N-06 ★ · Tamaños sin cota bloquean el proceso
- **Archivo:línea:** `advanced.py` (`monte_carlo_gg1`), `queuing.py` (`mmck`, `mmc`), `queuing.py` (`queue_length_pmf`).
- **Severidad:** Media (relevante si la librería se usa en un servicio).
- **Evidencia:** `monte_carlo_gg1(..., n_customers=10**9)` y `mmck(2,3,2,10**7)` > 5 s sin terminar; `mmc(2,3,10**6)` → `OverflowError`.
- **Corrección:** cotas máximas documentadas (p. ej. `n_customers ≤ 10⁷`) con `ValueError` explicativo.
- **Test:** parámetros por encima de la cota → `ValueError` inmediato.

### N-07 · `bool` aceptado como entero y excepciones sin `from`
- **Archivo:línea:** `_utils.py:44` (`isinstance(value, (int, np.integer))` acepta `True`), `_utils.py:12, 23, 34, 64` (B904).
- **Severidad:** Baja.
- **Evidencia:** `wl.mmc(2.0, 3.0, True)` se interpreta como `c=1` y devuelve `M/M/1`; las excepciones se encadenan con "During handling of the above exception…".
- **Corrección:** rechazar `bool`; añadir `from None`.
- **Test:** `mmc(2,3,True)` → `TypeError`.

### N-08 · Código muerto e imports sin usar
- **Archivo:línea:** `inventory.py:381-383` (`z`, `phi_z`, `Phi_z`), `inventory.py:2084` (`n_total`), `inventory.py:2336` (`abc_map`), `advanced.py:841` (`rho`); 13 × F401; 16 × I001.
- **Severidad:** Baja.
- **Corrección:** `ruff check --fix` y eliminación manual de las variables. **Test:** `ruff check` limpio.

### N-09 · Política de entrada vacía inconsistente
- **Evidencia:** `mrp([])` → `ValueError`; `schedule_single([])` y `lot_for_lot([])` devuelven resultados vacíos.
- **Severidad:** Baja. **Corrección:** decidir una política (recomendada: `ValueError`) y documentarla.

### N-10 · Metadatos y configuración
- **Archivo:línea:** `pyproject.toml:8, 14-17, 51-53`.
- **Severidad:** Baja.
- **Evidencia:** la descripción ("Queuing theory, operations analysis, OEE, bottleneck analysis and KPI trees") ignora inventarios, scheduling, confiabilidad y proyecto; `[tool.ruff]` no define `select`; `ruff`/`mypy` sin fijar; sin `[tool.coverage]`.
- **Corrección:** actualizar descripción/keywords/classifiers (`Typing :: Typed`); fijar `ruff` y `mypy` en `dev`; definir `select` y `fail_under`.

### N-11 · Higiene de tests
- **Evidencia:** sin `tests/conftest.py` (el Playbook pide fixture de semilla); 0 tests parametrizados (357 funciones de test, muchas repetitivas); `tests/test_v026.py` se nombra por versión; los tests numéricos de v0.2.8 comparan con los parámetros teóricos de la distribución generadora con tolerancias amplias (5 % en Weibull) y no fijan valores de referencia externos (scipy) como constantes.
- **Severidad:** Media. **Corrección:** `conftest.py` con `rng`; parametrizar; renombrar por tema; añadir tests con referencias externas fijas (valores calculados con scipy y guardados como constantes con su origen).

### N-12 · Idioma
- **Evidencia:** README/CHANGELOG/CONTRIBUTING mezclan español e inglés; docstrings y mensajes de error en inglés. `CLAUDE.md` no define política.
- **Severidad:** Baja. **Decisión pendiente D-1.**

### N-13 · Dependencias pesadas obligatorias
- **Evidencia:** `dependencies = ["numpy","pandas","matplotlib","plotly"]`; `import walopy` tarda 0,32 s (por pandas); matplotlib y plotly no se importan hasta usar un `plot()`.
- **Severidad:** Baja. **Opción:** extras `walopy[plot]` en una versión minor con aviso de cambio. **Decisión pendiente D-3.**

### N-14 · `batch_model`
- **Archivo:línea:** `solver.py:552` (`except Exception`), `solver.py:~560` (elimina `_error` si no hay fallos).
- **Severidad:** Baja. **Evidencia:** el esquema de salida cambia según haya o no errores; la captura amplia oculta errores de programación.
- **Corrección:** columna `_error` siempre presente (o parámetro `errors="raise"|"collect"`).

### N-15 · Comunidad y cadena de suministro
- **Evidencia:** sin `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/`, `PULL_REQUEST_TEMPLATE.md`; `attestations: false` en `publish.yml` (parche del 2026-09-29).
- **Severidad:** Baja. **Corrección:** añadir los archivos; valorar habilitar `attestations: true` con `permissions: attestations: write`.

### N-16 · Docstrings
- **Evidencia:** de 70 funciones públicas, 68 sin sección `Raises` y 47 sin `Examples`.
- **Severidad:** Media (requisito del Playbook para el Nivel 3). **Corrección:** completar secciones al corregir cada validación (K-01…K-08).

---

## Verificaciones sin hallazgo (HECHO)

- **Correctitud numérica:** 30/30 comprobaciones contra referencias independientes pasan (scipy, networkx, fuerza bruta, nacimiento-muerte, Cobham, binomial, integración numérica del `newsvendor`).
- **Estado global (C-07):** `rcParams` idéntico antes y después de 19 `plot()`.
- **Versiones:** 357 tests OK en Python 3.9 y 3.11, con numpy 1.22…2.4, pandas 1.4…3.0, matplotlib 3.5…3.11, plotly 5.0…7.1.
- **Seguridad estática:** reglas `S` de ruff sin hallazgos; sin `eval`/`exec`/`pickle`/`subprocess`.
