# BUG CATALOG — pccpy

> Fichas de todos los bugs verificados en el historial git + taxonomía de clases de error.
> Fuente: `git log --all --oneline` (102 commits), mensajes de commit, diffs.

---

## FICHAS DE BUGS

---

### BUG-01 · Zonas sigma no visibles en cartas asimétricas

| Campo | Detalle |
|---|---|
| **ID** | BUG-01 |
| **Síntoma** | Las cartas MR, R y S no mostraban las bandas ±1σ/±2σ aunque `zones=True` |
| **Causa raíz** | Condición `if zones and panel.symmetric` en `plotting.py` — las cartas asimétricas tienen `symmetric=False` y quedaban excluidas |
| **Cómo se detectó** | Revisión visual de salida de gráficos; commit de fix en v0.4.8 |
| **Solución aplicada** | Eliminada la condición `panel.symmetric`; matplotlib recorta naturalmente líneas por debajo del rango visible |
| **Archivo/línea** | `src/pccpy/plotting.py` (commit `314cb86`) |
| **Test de regresión** | NO VERIFICADO — no hay test que confirme que las zonas están presentes en cartas MR/R/S |
| **¿Puede ocurrir en otras libs?** | Sí — cualquier librería de visualización que añada condiciones de "simetría" para controlar trazado. |

---

### BUG-02 · `as_1d()` lanzaba `ValueError` opaco ante NaN/inf en datos

| Campo | Detalle |
|---|---|
| **ID** | BUG-02 |
| **Síntoma** | Usuarios con datos reales (ficheros CSV con celdas vacías) recibían `ValueError` sin contexto |
| **Causa raíz** | `as_1d()` llamaba `np.asarray(..., dtype=float)` que silenciosamente convierte NaN pero luego operaciones de scipy fallaban; no había filtrado previo |
| **Cómo se detectó** | Uso en producción / datos reales; commit `39bd66a` lo documenta como mejora de compatibilidad |
| **Solución aplicada** | Filtrado de valores no finitos con `UserWarning`; si no quedan valores válidos, `ValueError` con mensaje descriptivo |
| **Archivo/línea** | `src/pccpy/_data.py`, función `as_1d()` (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_charts.py` actualizado en `39bd66a` |
| **¿Puede ocurrir en otras libs?** | Sí — es el error más común en librerías científicas que reciben datos de usuarios finales. |

---

### BUG-03 · `to_subgroups()` fallaba con DataFrame con columnas de texto

| Campo | Detalle |
|---|---|
| **ID** | BUG-03 |
| **Síntoma** | Error `"could not convert string to float"` al pasar un DataFrame con columna de fecha o etiqueta |
| **Causa raíz** | `np.asarray(df)` sin filtrar columnas no numéricas |
| **Cómo se detectó** | Uso con datos industriales reales; commit `39bd66a` |
| **Solución aplicada** | Filtrado automático de columnas no numéricas con `UserWarning` que sugiere `subgroup='nombre_columna'` |
| **Archivo/línea** | `src/pccpy/_data.py`, función `to_subgroups()` (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_charts.py` actualizado |
| **¿Puede ocurrir en otras libs?** | Sí — cualquier librería que acepte DataFrames como entrada de subgrupos. |

---

### BUG-04 · `capability_analysis()` lanzaba `ValueError` sin límites de especificación

| Campo | Detalle |
|---|---|
| **ID** | BUG-04 |
| **Síntoma** | `capability_analysis(x)` sin `lsl`/`usl` lanzaba `ValueError("Se requiere al menos lsl o usl")` |
| **Causa raíz** | Diseño de API que asumía que los límites son siempre necesarios; no consideró el caso exploratorio |
| **Cómo se detectó** | Uso real; commit `39bd66a` |
| **Solución aplicada** | `lsl` y `usl` son ahora opcionales; sin ellos los índices Cp/Cpk/Pp/Ppk se devuelven como `NaN` |
| **Archivo/línea** | `src/pccpy/capability.py` (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_capability.py` actualizado |
| **¿Puede ocurrir en otras libs?** | Sí — patrón frecuente en APIs estadísticas con parámetros que "siempre" se necesitan en producción. |

---

### BUG-05 · `ZeroDivisionError` en `capability_analysis()` con datos constantes

| Campo | Detalle |
|---|---|
| **ID** | BUG-05 |
| **Síntoma** | `capability_analysis(np.ones(30))` lanzaba `ZeroDivisionError` o `ValueError` |
| **Causa raíz** | `_indices()`, `_expected_ppm()` y `_z_bench()` no manejaban `sigma=0` |
| **Cómo se detectó** | Commit `39bd66a`; caso límite de datos de proceso en calibración |
| **Solución aplicada** | Retorno de `NaN` con `UserWarning` al detectar desviación estándar = 0 |
| **Archivo/línea** | `src/pccpy/capability.py` funciones privadas (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_capability.py` actualizado |
| **¿Puede ocurrir en otras libs?** | Sí — división por cero con sigma en cualquier análisis estadístico. |

---

### BUG-06 · `zone_chart` fallaba con nuevo error de `subgroup_size=1`

| Campo | Detalle |
|---|---|
| **ID** | BUG-06 |
| **Síntoma** | `zone_chart(data)` con datos individuales fallaba internamente con el nuevo error de validación de `to_subgroups()` |
| **Causa raíz** | `to_subgroups(arr, 1)` fue modificado para rechazar `subgroup_size=1` con mensaje que apunta a `imr_chart()`. `zone_chart` usa internamente `to_subgroups` con tamaño 1. |
| **Cómo se detectó** | Commit `39bd66a` — detectado al aplicar la validación general de `subgroup_size=1` |
| **Solución aplicada** | Añadido parámetro `_allow_size_1=True` para llamadas internas legítimas |
| **Archivo/línea** | `src/pccpy/_data.py`, `src/pccpy/charts/advanced.py` (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_advanced_charts.py` existente cubre `zone_chart` |
| **¿Puede ocurrir en otras libs?** | Sí — añadir validación de entrada puede romper llamadas internas que usan el mismo camino. |

---

### BUG-07 · Import de openpyxl daba error opaco sin orientación al usuario

| Campo | Detalle |
|---|---|
| **ID** | BUG-07 |
| **Síntoma** | `result.to_excel("salida.xlsx")` lanzaba `ImportError: No module named 'openpyxl'` sin mensaje de qué instalar |
| **Causa raíz** | El `ImportError` de `pd.ExcelWriter(engine="openpyxl")` se propagaba sin capturar |
| **Cómo se detectó** | Commit `39bd66a` / v0.10.7; openpyxl es dependencia opcional |
| **Solución aplicada** | Helper `_excel_writer()` en `_data.py` que captura `ImportError` y da instrucción explícita `pip install pccpy[excel]` |
| **Archivo/línea** | `src/pccpy/_data.py`, función `_excel_writer()` (commit `39bd66a`) |
| **Test de regresión** | NO VERIFICADO — no hay test que simule ausencia de openpyxl |
| **¿Puede ocurrir en otras libs?** | Sí — patrón universal para dependencias opcionales. |

---

### BUG-08 · CI tests.yml tenía referencias a `spyc` tras el renombre

| Campo | Detalle |
|---|---|
| **ID** | BUG-08 |
| **Síntoma** | CI corría `pytest --cov=spyc` y `mypy src/spyc` — el módulo ya no existía |
| **Causa raíz** | El renombre de módulo no actualizó los workflows de GitHub Actions |
| **Cómo se detectó** | Primer run de CI tras el renombre; commit `3de6dc5` |
| **Solución aplicada** | Sed en los workflows: `--cov=spyc → --cov=pccpy`, `src/spyc → src/pccpy` |
| **Archivo/línea** | `.github/workflows/tests.yml`, `.github/workflows/publish.yml` (commit `3de6dc5`) |
| **Test de regresión** | N/A — es un bug de infraestructura CI |
| **¿Puede ocurrir en otras libs?** | Sí — renombres de paquete deben incluir todos los artefactos de CI. |

---

### BUG-09 · PEP 639: `license` SPDX + classifier duplicado con setuptools>=77

| Campo | Detalle |
|---|---|
| **ID** | BUG-09 |
| **Síntoma** | `python -m build` fallaba con error de setuptools sobre license classifier duplicado |
| **Causa raíz** | PEP 639 adoptado en setuptools>=77: `license = "MIT"` y `License :: OSI Approved :: MIT License` son mutuamente excluyentes |
| **Cómo se detectó** | Al intentar publicar en PyPI; commit `e894a25` |
| **Solución aplicada** | Eliminar el classifier `License :: ...` del `pyproject.toml` |
| **Archivo/línea** | `pyproject.toml` (commit `e894a25`) |
| **Test de regresión** | N/A — build funciona. Se podría añadir `twine check dist/*` al CI |
| **¿Puede ocurrir en otras libs?** | Sí — cualquier paquete que migre a setuptools>=77 sin revisar PEP 639. |

---

### BUG-10 · Python 3.9: `stats.normaltest` lanza `ValueError` para n < 8

| Campo | Detalle |
|---|---|
| **ID** | BUG-10 |
| **Síntoma** | `diagnose(x)` con menos de 8 puntos fallaba en Python 3.9 (`ValueError` de scipy) |
| **Causa raíz** | En Python 3.11+, `scipy.stats.normaltest` emite `SmallSampleWarning` para n<8. En Python 3.9 con scipy más antiguo lanza `ValueError`. No se manejaba la excepción. |
| **Cómo se detectó** | CI multi-versión; commit `44f7f69` |
| **Solución aplicada** | Guardar n antes del `try`; capturar la excepción y devolver resultado parcial |
| **Archivo/línea** | `src/pccpy/_diagnose.py` (commit `44f7f69`) |
| **Test de regresión** | SÍ — `test_diagnose.py` cubre casos con n < 8 |
| **¿Puede ocurrir en otras libs?** | Sí — scipy cambia comportamiento de warnings/errores entre versiones menores. |

---

### BUG-11 · Sphinx: `autoclass WidgetSession` generaba advertencia duplicada

| Campo | Detalle |
|---|---|
| **ID** | BUG-11 |
| **Síntoma** | `sphinx-build -W` fallaba con 18 warnings (duplicados y referencias cruzadas ambiguas) |
| **Causa raíz** | `wizard.md` usaba `.. autoclass:: pccpy.WidgetSession` cuando ya estaba documentado en otro lugar; referencias cruzadas sin namespace explícito |
| **Cómo se detectó** | CI job `documentacion`; commit `819ca11` |
| **Solución aplicada** | Reemplazar `autoclass` con tabla Markdown manual en `wizard.md`; corregir referencias cruzadas |
| **Archivo/línea** | `docs/source/referencia/wizard.rst`, `docs/source/wizard.md` (commit `819ca11`) |
| **Test de regresión** | SÍ — CI corre `sphinx-build -W` |
| **¿Puede ocurrir en otras libs?** | Sí — `autoclass` + documentación manual del mismo símbolo siempre genera duplicado. |

---

### BUG-12 · Plots contaminaban estilos globales de matplotlib (incompatibilidad con seaborn)

| Campo | Detalle |
|---|---|
| **ID** | BUG-12 |
| **Síntoma** | En entornos con seaborn importado antes de pccpy, los gráficos de control aparecían con estilos de seaborn; viceversa, pccpy alteraba los gráficos del usuario |
| **Causa raíz** | Las funciones `plot_*` modificaban `rcParams` globalmente sin restaurar el estado anterior |
| **Cómo se detectó** | Uso en Jupyter con seaborn; commit `786fccb` |
| **Solución aplicada** | Envolver todas las funciones `plot_*` en `plt.rc_context({})` |
| **Archivo/línea** | `src/pccpy/plotting.py`, `src/pccpy/quality_tools.py` (commit `786fccb`) |
| **Test de regresión** | NO VERIFICADO — no hay test que verifique aislamiento de estilos |
| **¿Puede ocurrir en otras libs?** | Sí — cualquier librería de visualización que no use `rc_context`. |

---

## TAXONOMÍA DE CLASES DE ERROR

| Clase | Descripción | Cómo prevenirla | Cómo detectarla | Bugs en este proyecto |
|---|---|---|---|---|
| **C-01 Validación de entrada faltante** | La función acepta datos inválidos (NaN, inf, tipo incorrecto, vacío) y falla con error opaco aguas abajo | Capa de validación explícita en cada función pública; tests con entradas malformadas | `pytest` con casos borde; `mypy` para tipos | BUG-02, BUG-03, BUG-05 |
| **C-02 Caso degenerado no considerado** | El diseño de API no contempló valores extremos válidos (sin límites, datos constantes, n<8) | Listar casos degenerados al diseñar la API; documentar en docstring | Tests parametrizados con valores límite | BUG-04, BUG-05, BUG-10 |
| **C-03 Import opcional sin mensaje orientativo** | Dependencia opcional ausente genera `ImportError` crudo sin guía al usuario | Capturar `ImportError` de opcionales; mensaje con `pip install ...` | Test que simula ausencia con `unittest.mock` | BUG-07 |
| **C-04 CI que no detecta el fallo** | El build/test local pasa pero CI falla por diferencia de entorno (versión Python, Node) | Correr la matrix localmente con tox antes del PR; CI fail-fast desactivado | Primera ejecución en CI; logs de CI | BUG-08, BUG-09, BUG-10, BUG-11 |
| **C-05 Documentación desactualizada** | Código o comandos en docs/CLAUDE.md apuntan al estado anterior | Incluir docs en el checklist de cada PR; grep de términos obsoletos en CI | Grep automatizado; revisión de CLAUDE.md en cada sesión | BUG-08, L-01, L-07 |
| **C-06 Efecto secundario de refactor** | Validación añadida en función base rompe llamada interna válida | Al añadir validación, buscar todas las llamadas internas con `grep`; añadir parámetro escape-hatch explícito | Tests de integración de módulos que se llaman entre sí | BUG-06 |
| **C-07 Estado global de entorno** | La librería modifica estado global (rcParams) contaminando el entorno del usuario | Usar context managers (`rc_context`, `warnings.catch_warnings`) | Test que verifica estado antes/después de la llamada | BUG-12 |
| **C-08 Versión múltiple fuente** | La versión se gestiona en N>1 lugares y se desincroniza | Única fuente de verdad: `importlib.metadata` o `setuptools-scm` | `assert pccpy.__version__ == importlib.metadata.version("pccpy")` en test | L-10 |

---

## FICHAS DE BUGS DE WALOPY (v0.2.8 → v0.3.0)

> Bugs hallados en la auditoría de `2cc17c1` (v0.2.8) y corregidos en v0.3.0. El identificador `W-nn` es el mismo que usa
> `tests/regresiones.json`, que enlaza cada bug con los tests que lo cubren y con la versión (`ref`) contra la que **deben fallar**
> (`scripts/verificar_regresion.py`, job `regresion` del CI). Detalle y evidencia en `docs/auditoria/HALLAZGOS.md` (K-nn/N-nn) y trazabilidad completa en `docs/auditoria/TRAZABILIDAD.md`.

| ID | Hallazgo | Síntoma | Causa raíz | Solución | Test de regresión | Clase |
|---|---|---|---|---|---|---|
| **W-01** | K-01 | `cpm` con duración NaN/inf devuelve `project_duration = nan/inf` | `dur < 0.0` es `False` para NaN; ruta sin pasar por `_utils` | `as_nonneg` en la ingesta de actividades | `test_cpm_rechaza_duracion_no_valida` | C-09 |
| **W-02** | K-01 | `mtbf_analysis(t=-1)` da fiabilidad 1,01; `series/parallel/koon` aceptan `t` NaN/inf | `t` y `mttr` sin validar | `_validar_t_mttr` + `as_float_list` | `test_mtbf_rechaza_t_y_mttr_no_validos`, `test_sistemas_…`, `test_koon_…` | C-09 |
| **W-03** | K-01 | `mrp(initial_on_hand=nan)` propaga NaN; negativo aceptado | `initial_on_hand` sin validar | `as_finite_scalar` | `test_mrp_rechaza_existencia_inicial_no_valida` | C-09 |
| **W-04** | K-01 | `weibull_analysis([nan, …])` → `OverflowError` crudo | tiempos sin validar | `as_float_list(kind="positive")` | `test_weibull_rechaza_tiempos_no_finitos` | C-09 |
| **W-05** | K-02 | `cv2_uniform(nan, 3)` → `nan`; `break_even_multi` con NaN; `queue_length_pmf(n_max=-1)` → vacío | validadores ausentes en funciones auxiliares | `_utils` en cada punto de ingesta | `test_cv2_*`, `test_break_even_multi_*`, `test_queue_length_pmf_*`, `test_sojourn_cdf_*` | C-14 |
| **W-06** | K-03 | `abc_analysis([{"name": "a"}])` → `KeyError`; `"abc"` → `AttributeError` | acceso directo a claves | `_leer_items` con errores `items[i]: falta la clave …` | `test_abc_items_mal_formados_dan_errores_claros`, `test_mrp_entradas_mal_formadas` | C-01 |
| **W-07** | K-04 | un artículo con demanda 0 hace fallar todo el análisis ABC | `as_positive` en un caso límite válido | `as_nonneg`; todo 0 → `ValueError` explícito | `test_abc_acepta_articulos_sin_demanda_como_clase_c` | C-02 |
| **W-08** | K-05 | Weibull con datos constantes: β = 100 sin aviso (MLE) o `ZeroDivisionError` (RRY) | cota fija del solucionador y división por 0 | `ValueError` en datos constantes; `UserWarning` si la cota recorta | `test_weibull_datos_constantes_…`, `test_weibull_casi_constante_…` | C-16 |
| **W-09** | K-06 | `mmc(145, 1, 150)` → `OverflowError` | `a**n / n!` desborda `float` | recurrencia de Erlang-B | `tests/test_mmc_estable.py` (11 tests) | C-12 |
| **W-10** | K-07 | `eoq_multi_constrained(budget=-1)` se cuelga; `budget=0` → `ZeroDivisionError` | presupuesto sin validar y búsqueda sin cota | validación + bisección acotada | `test_eoq_restringido_*` | C-18 |
| **W-11** | K-08 / N-09 | `series_system([])` → `ZeroDivisionError`; `mrp([])` → `IndexError` | política de entrada vacía inconsistente | `ValueError` uniforme | `test_sistemas_rechazan_lista_vacia`, `test_listas_vacias_son_value_error` | C-01 |
| **W-12** | N-01 | `break_even_sales(...).plot()` → `KeyError: 'price_per_unit'`; `plotting.py` con 0 % de cobertura | resultado sin los parámetros que usa la gráfica; ningún test ejecutaba las gráficas | `plot_break_even` admite `break_even_sales` + `tests/test_plotting.py` | `test_break_even_sales_usa_eje_de_ventas` | C-15 |
| **W-13** | N-03 | `wagner_whitin(n=1000)` 10,2 s y `neh_flowshop(n=200)` 5,3 s frente a O(n²) / O(n²m) anunciados | sumas recalculadas en el doble bucle; makespan completo por inserción | sumas acumuladas y aceleración de Taillard | `test_wagner_whitin_n1000_es_rapido`, `test_neh_n200_m10_es_rapido` | C-11 |
| **W-14** | N-04 | `cpm` con dos actividades `A` conserva la última sin aviso | volcado en `dict` | `ValueError` por nombre duplicado | `test_actividades_duplicadas_se_rechazan`, `test_actividad_sin_nombre_o_duracion_da_error_claro` | C-13 |
| **W-15** | N-04 | `abc_xyz` con nombres repetidos empareja el artículo equivocado | emparejamiento por nombre | emparejar por posición (clave `index`) | `test_abc_xyz_con_nombres_repetidos_empareja_por_posicion` | C-13 |
| **W-16** | N-05 | `mrp(lead_time=5)` descarta órdenes que caen antes del periodo 1 | recorte silencioso | `UserWarning` + campo `past_due_releases` | `test_mrp_avisa_de_liberaciones_vencidas` | C-16 |
| **W-17** | N-06 | `mmck(…, K=10**7)` y `monte_carlo_gg1(n=10**9)` no terminan | parámetros de tamaño sin cota | `MAX_SERVIDORES`, `MAX_ESTADOS`, `MAX_CLIENTES` en `_utils` | `test_tamanos_absurdos_se_rechazan_de_inmediato`, `test_mmc_rechaza_demasiados_servidores` | C-18 |
| **W-18** | N-07 | `mmc(2, 3, True)` se interpreta como `c=1` | `bool` es subclase de `int` | rechazar `bool` en los validadores | `test_bool_no_se_acepta_como_entero`, `test_bool_no_se_acepta_como_numero` | C-01 |
| **W-19** | — (hallado al reforzar tests) | holguras `-0.0` en tablas de CPM/PERT | `round(-1e-16, 10)` devuelve `-0.0` | `round(x, 10) + 0.0` | `test_holguras_sin_cero_negativo` | C-26 |
| **W-20** | K-13 | `__version__` sin fallback correcto cuando el paquete no está instalado | versión duplicada/obsoleta | `importlib.metadata` con fallback `0+unknown` (lo comprueba el test) | `test_sin_instalar_la_version_es_desconocida` | C-08 |
| **W-21** | N-14 | `batch_model` captura cualquier excepción y la oculta; columna `_error` condicional | `except Exception` sin opción | parámetro `errors="collect"\|"raise"` y columna `_error` solo si hay fallos | `test_batch_model_errors_raise_propaga_la_excepcion`, `…_invalido`, `…_sin_errores_…` | C-29 |
| **W-22** | K-01…K-03 | 30 excepciones inesperadas, 2 bloqueos y 26 entradas basura en el barrido de 67 funciones | validación solo en parte de las rutas | barrido permanente de la API (tabla `BASE` + candidatos + `ACEPTADOS`) | `test_contrato_de_entradas` (67 funciones) | C-14 |
| **W-23** | K-10 | 13 de 61 bloques del README y 6 de 23 doctests fallaban | documentación escrita sin ejecutarla; `--doctest-modules` desactivado | README y doctests son tests (`test_readme.py`, `--doctest-modules`) | gate: `tests/test_readme.py` y los doctests (sin selector antiguo reproducible) | C-10, C-19 |
| **W-24** | K-11 / K-12 / N-02 | CI en verde sin ruff, mypy, build, docs ni cobertura; 78 errores de mypy; publicación sin tests | el CI solo ejecutaba `pytest` | jobs de calidad en `ci.yml`; `publish.yml` verifica tag y tests | gate de CI (no es un test de pytest) | C-15, C-17 |
| **W-25** | N-12 | 524 textos en inglés visibles (mensajes, avisos, docstrings) | política de idioma sin comprobación automática | traducción + `tests/test_idioma.py` | `test_textos_visibles_en_espanol` (15 módulos) | C-30 |
| **W-26** | informe de usuario (v0.4.0) | `plot()` de todo árbol de KPI (`KPINode`, `oee_kpi_tree`, `throughput_kpi_tree`, `roi_kpi_tree`) sale **en blanco** en el navegador | con `branchvalues="total"` Plotly exige padre ≥ suma de hijos y un KPI casi nunca es la suma de sus hijos (EBITDA = Ingresos − Costos; OEE = A × P × Q); los tests solo miraban el objeto `Figure`, no su dibujo | tamaño del rectángulo = `max(valor, suma de los hijos)` y rótulo con el valor real del nodo | `tests/test_kpi_grafica.py` (12 fallan en v0.4.0) | C-33 |
| **W-27** | hallado con propiedades diferenciales (v0.4.1) | `wagner_whitin([0,0,100,0,0], 100, 1)` cuesta 200 (óptimo 100) y `[0,50,0,100]` 250 (óptimo 200); `[0,0,0]` devuelve un pedido de cantidad 0 | la recursión cobraba la preparación en bloques de demanda nula y forzaba un pedido en el periodo 1; el test de fuerza bruta tenía el mismo defecto (y fijaba `d[0] > 0`), así que nunca lo vio | solo se pide en periodos con demanda positiva; los de demanda nula arrastran el costo anterior | `tests/test_wagner_whitin_ceros.py` (costo óptimo exacto contra una fuerza bruta corregida; 160 fallan en v0.4.1) | C-34 |
| **W-28** | hallado con propiedades diferenciales (v0.4.2) | `solve_servers("Wq", 0.5, lam=4, mu=3)` devuelve 3 servidores cuando 2 ya cumplen (Wq = 0,267); `optimize_servers(lam=1, mu=5, …)` nunca evalúa M/M/1; el ejemplo del docstring (30,7232) y la salida del README ocultaban el defecto | la búsqueda empezaba en `ceil(λ/μ) + 1`, que solo es el menor `c` estable si λ/μ es entero; el test de «poca carga» comentaba `(=1)` pero solo comprobaba la métrica, no el valor | `_min_servidores_estables`: menor `c` con ρ < 1 con la misma condición que exige `mmc` | `tests/test_servidores_minimos.py` (comparación con enumeración; 21 fallan en v0.4.2 de 125) | C-35 |
| **W-29** | hallado al corregir W-28 (v0.4.2) | `optimize_servers(lam=4, mu=3, …, c_max=1)` → `min() arg is an empty sequence`; `c_max=True`, `2.5`, `nan`, `None` dan `TypeError` opacos o se aceptan | `c_max` sin validar y sin comprobar que quepa el mínimo estable | `as_int_positive(c_max, max=MAX_SERVIDORES)` y `ValueError` que dice cuántos servidores hacen falta | `tests/test_servidores_cmax.py` | C-14 |
| **W-30** | hallado con propiedades diferenciales (v0.4.2) | `batch_model(mmc, df)` con un DataFrame disperso y `c` entero falla en todas las filas («`c` debe ser un entero positivo, se recibió `float`») | pandas convierte la columna entera con NaN a `float64`; el código solo restauraba las columnas enteras sin NaN | en columnas flotantes con NaN, los valores enteros se pasan como `int` | `tests/test_solver_contratos.py -k batch_model` | C-37 |
| **W-31** | hallado con propiedades diferenciales (v0.4.2) | `compare()` sin argumentos devuelve una tabla vacía; `compare(wagner_whitin(...), silver_meal(...))` o `compare(cpm(...), …)` muestra solo la primera orden / actividad | `r.to_frame().iloc[0]` para todo resultado con `to_frame`; la documentación dice `ValueError` si no hay resultados | `ValueError` sin resultados; si `to_frame()` tiene varias filas se usan los campos escalares del resultado | `tests/test_solver_contratos.py -k compare` | C-16, C-36 |
| **W-32** | hallado con propiedades diferenciales (v0.4.2) | `sensitivity(mm1, "foo", [1, 2], mu=3)` → `TypeError`; `sensitivity(mm1, "lam", [], mu=3)` devuelve una tabla vacía | el código no implementaba los `ValueError` que documenta el docstring | `ValueError` si `values` está vacío o `param` no es parámetro del modelo (salvo `**kwargs`) | `tests/test_solver_contratos.py -k sensitivity` | C-36 |

---

## TAXONOMÍA DE CLASES DE ERROR — ampliación con walopy

| Clase | Descripción | Cómo prevenirla | Cómo detectarla | Bugs |
|---|---|---|---|---|
| **C-09 NaN pasa las comparaciones** | `x <= 0` es `False` para NaN; `inf` tampoco se rechaza; el valor llega al cálculo | `isfinite` **antes** de comparar; validador central | barrido `[nan, inf, -inf, -1, 0, None, "x"]` por argumento | W-01…W-04 |
| **C-10 Documentación con API inventada** | los ejemplos del README usan parámetros o atributos inexistentes | bloques de código del README convertidos en tests | ejecutar todos los bloques | W-23 |
| **C-11 Complejidad documentada ≠ real** | el docstring anuncia O(n²) y el código es O(n³) | medir con tamaños crecientes; benchmark | tabla de tiempos n = 100/400/1000 | W-13 |
| **C-12 Desbordamiento por fórmula directa** | `a**n / n!` desborda para tamaños realistas | recurrencias estables, `lgamma`, logaritmos | prueba a escala 10× el caso típico | W-09 |
| **C-13 Duplicados fusionados en silencio** | lista de dicts con clave de identidad volcada a un `dict` | rechazar duplicados al ingerir; emparejar por posición | test con nombres repetidos | W-14, W-15 |
| **C-14 Validación solo en parte de las rutas** | existe la capa central pero hay rutas que no la usan | barrido sobre `__all__` | test de contrato | W-05, W-22 |
| **C-15 CI verde que no verifica / módulo sin cobertura** | el CI no ejecuta los gates del Playbook; hay código sin ningún test | gates en el CI; cobertura por módulo | comparar `ci.yml` con la batería | W-12, W-24 |
| **C-16 Recorte o descarte silencioso** | cota fija del solucionador o datos fuera de horizonte descartados sin aviso | `UserWarning` o error cuando se toca la cota | datos degenerados y casi constantes | W-08, W-16 |
| **C-17 Funcionalidad publicada sin documentación** | símbolos nuevos de `__all__` ausentes de README/Sphinx | test que compare `__all__` con la documentación | `tests/test_documentacion.py` | W-24 |
| **C-18 Parámetros sin cota → bloqueo** | tamaños o presupuestos sin límite permiten cálculos que no terminan | cotas máximas con mensaje; límite de iteraciones | barrido con 1e7, 1e9, 0, negativos y `--timeout` | W-10, W-17 |
| **C-19 Doctests que nunca se ejecutan** | `--doctest-modules` desactivado: ejemplos rotos sin que nadie lo vea | `--doctest-modules` en `addopts` desde el primer ejemplo | `test_los_doctests_estan_activos` | W-23 |
| **C-20 Ejemplo con borde numérico** | `100 < x < 130` falla si `x == 100.0` | mostrar el valor redondeado | doctests | — |
| **C-21 Empates numéricos en heurísticas** | un empate exacto se resuelve distinto al cambiar el orden de las sumas | tolerancia relativa (1e-12) y datos enteros en los tests | comparar con la versión directa | — |
| **C-22 Referencia externa menos precisa que el código** | `scipy…fit` difería de la raíz exacta | constantes de referencia con `brentq` (1e-15) y su origen documentado | contraste cruzado de dos métodos | — |
| **C-23 Nombre que colisiona con una opción** | `from importlib.metadata import version` en `conf.py` | importar el módulo, no nombres genéricos | `sphinx -W` | — |
| **C-24 Metadatos de instalación obsoletos** | `egg-info` antiguo entra en `sys.path` | `--import-mode=importlib`; reinstalar al subir la versión | `test_version_coincide_con_metadatos` | W-20 |
| **C-25 Comprobación que coincide con su propio comando** | el `grep` de referencias obsoletas se encuentra a sí mismo | excluir `.github/` y el archivo con el patrón | ejecutar el paso localmente | — |
| **C-26 `-0.0` en resultados** | `round(-1e-16, 10)` → `-0.0` | sumar `0.0` tras redondear | comparar con `math.copysign` | W-19 |
| **C-27 `!` en scripts no detiene la ejecución** | `! grep` con `set -e` no falla | `if grep …; then exit 1; fi` | probar el paso con una coincidencia forzada | — |
| **C-28 Rama creada desde una base antigua** | la rama partía de v0.2.0 y el PR tuvo conflictos en 6 archivos | rama desde `origin/main` recién traído | `git merge-base --is-ancestor origin/main HEAD` | — |
| **C-29 Captura amplia que oculta errores** | `except Exception` sin opción de propagar | parámetro explícito (`errors=`) y columna estable | test con una función que lanza | W-21 |
| **C-30 Texto visible sin política comprobada** | la política «texto en español» existía pero nada la verificaba: 524 hallazgos en v0.2.8 y 2 más que escaparon a la traducción manual | `tests/test_idioma.py` recorre mensajes, avisos y docstrings con `ast` | el propio test (con control negativo) | W-25 |
| **C-31 Reemplazo global sin contexto** | un glosario aplicado a todo el árbol cambió una clave de datos (`"method"`) y un valor de ejemplo (`"Name"`) | separar *claves de datos* (se quedan) de *cabeceras de presentación* (`.rename(columns=…)`); revisar el diff y ejecutar los tests tras cada reemplazo | la suite completa | — |
| **C-32 Test de regresión que no falla en el código anterior** | tests de `-0.0` y de `__version__` pasaban también sin el fix: no protegían nada | ejecutar los tests contra el tag anterior | `scripts/verificar_regresion.py` | W-19, W-20 |
| **C-33 Test sobre el objeto, no sobre lo que ve la persona** | el test de la gráfica comprobaba que la `Figure` existiera y tuviera datos; la figura estaba en blanco en el navegador por una restricción de Plotly que solo se aplica al dibujar | probar la **invariante** que exige el renderizador (padre ≥ suma de hijos) y, ante un informe de usuario, renderizar de verdad (Chromium headless) antes y después | `tests/test_kpi_grafica.py`; captura con Chromium al diagnosticar | W-26 |
| **C-34 Oráculo que comparte el defecto del código** | el test «coincide con fuerza bruta» obligaba a pedir en el periodo 0 y cobraba `S` por bloque, igual que el código, y además evitaba el caso conflictivo (`d[0] = d[0] or 1`) | oráculo escrito de forma independiente (solo pedidos en periodos con demanda, ceros en cualquier posición) y propiedades diferenciales entre funciones relacionadas | `tests/test_wagner_whitin_ceros.py`, `tests/test_propiedades_diferenciales.py` | W-27 |
| **C-35 Cota de búsqueda desplazada (off-by-one) que oculta el óptimo** | una búsqueda «desde el menor valor válido» empezaba uno después; el resultado seguía siendo válido, solo no era el mínimo, y el ejemplo del docstring reproducía el valor erróneo | derivar la cota con la misma condición que usa la función evaluada y comparar con una enumeración independiente; no fijar en docstring/README un resultado sin verificarlo contra un oráculo | `tests/test_servidores_minimos.py` | W-28 |
| **C-36 Excepción documentada que el código no lanza** | el docstring promete `ValueError` y el código devuelve una tabla vacía o lanza otro tipo | para cada línea de `Raises`, un test que provoque esa excepción | `tests/test_solver_contratos.py` | W-31, W-32 |
| **C-37 Entero degradado a float por pandas** | una columna entera con NaN pasa a `float64` y el modelo, que exige `int`, la rechaza | restaurar el tipo entero de los valores enteros en columnas flotantes con NaN | `tests/test_solver_contratos.py` | W-30 |
