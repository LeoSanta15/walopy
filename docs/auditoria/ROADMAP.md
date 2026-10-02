# ROADMAP — walopy (de nivel 2 parcial a nivel 3 sólido, con base para nivel 4)

> Plan priorizado a partir de `DIAGNOSTICO.md` y `HALLAZGOS.md`. **Aprobado y ejecutado el 2026-10-02** (ver «Estado de ejecución» al final).
> Esfuerzo: S ≤ 2 h · M ≤ 1 día · L > 1 día. Regla de ejecución: ningún fix sin test de regresión; tras cada fase se ejecuta la batería completa y se actualiza `SCORECARD.md`.

## Batería de verificación (se ejecuta al cerrar cada fase)

```bash
python -m pytest tests/ -q -W error
python -m pytest --cov=walopy --cov-report=term-missing --cov-fail-under=85 -q
python -m ruff check src/ tests/
python -m mypy src/walopy
python -m build && python -m twine check dist/*
python -m sphinx -b html -W docs/source docs/build
python -m pip_audit
grep -rn "PLACEHOLDER\|TU_USUARIO\|cost_kpi_tree" . --include="*.py" --include="*.md" --include="*.toml" --include="*.yml" || echo OK
# Python mínimo y dependencias mínimas (uv):
uv venv --python 3.9 v39 && uv pip install --python v39/bin/python -e ".[dev]" && v39/bin/python -m pytest -q
```

## Orden recomendado y dependencias

`Fase 0` → `Fase 1` → `Fase 2` → `Fase 3` → `Fase 4`. Dentro de la Fase 2, los gates de CI (2.6) se activan **al final**, cuando ruff y mypy ya pasan; si se activaran antes, el CI quedaría en rojo.

---

## Fase 0 — Quick wins (≤ 1 día)

| ID | Tarea | Esfuerzo | Impacto | Hallazgo | Criterio de aceptación | Verificación | Riesgo de regresión |
|---|---|---|---|---|---|---|---|
| 0.1 | Reescribir `CLAUDE.md` (mapa de los 16 módulos, comandos estándar, definición de terminado, reglas R-01…R-12 adaptadas, checklist de release corregido) | S | Alto | K-09 | Sin referencias a `cost_kpi_tree`; lista los 15 módulos de `src/walopy` | `grep -n cost_kpi_tree CLAUDE.md` vacío; revisión manual | Ninguno (solo texto) |
| 0.2 | `pyproject.toml`: descripción y keywords, `Typing :: Typed`, `py.typed` + `package-data`, `select = ["F","E9","B","I","S"]` en ruff, `[tool.coverage.report] fail_under = 85`, fijar `ruff` y `mypy`, añadir `build`, `twine`, `pip-audit` a `dev` | S | Medio | N-10, N-02 | `unzip -l dist/*.whl` contiene `py.typed`; `pip install -e ".[dev]"` instala las herramientas | `python -m build && unzip -l dist/*.whl \| grep py.typed` | Bajo |
| 0.3 | `__version__`: fallback `"0+unknown"` y test `__version__ == importlib.metadata.version("walopy")` | S | Bajo | K-13 | Test nuevo en verde | `pytest tests/test_version.py` | Bajo |
| 0.4 | `ruff check --fix` (imports, F401, UP037) y eliminar variables sin uso | S | Medio | N-08 | `ruff check src/` sin F401/F841/I001 | `ruff check src/ --select F401,F841,I001` | Bajo (autofix + suite completa) |
| 0.5 | Añadir `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/{bug,feature}.md`, `PULL_REQUEST_TEMPLATE.md`; ampliar `CONTRIBUTING.md` con la batería de verificación | S | Bajo | N-15 | Archivos presentes y enlazados desde README | `ls` | Ninguno |

## Fase 1 — Bugs críticos y red de seguridad de tests (≈ 2–3 días)

| ID | Tarea | Esfuerzo | Impacto | Hallazgo | Criterio de aceptación | Verificación | Riesgo de regresión |
|---|---|---|---|---|---|---|---|
| 1.1 | Añadir `tests/conftest.py` (fixture `rng`) y convertir el barrido exploratorio en un test permanente: para cada función pública, entradas `[nan, inf, -inf, -1, 0, None, "x"]` solo pueden producir `ValueError`/`TypeError` o un resultado finito | M | Alto | K-01, K-02, K-08, N-11 | El test falla hoy con 30 excepciones y se pone en verde al terminar 1.2–1.8 | `pytest tests/test_input_contract.py -q` | Medio: puede exigir decidir qué entradas extremas son válidas |
| 1.2 | Validar con `_utils` en `cpm`, `pert`, `mtbf_analysis`, `series_system`, `parallel_system`, `koon_system`, `mrp` (`initial_on_hand`), `weibull_analysis` (isfinite), `break_even_multi`, `cv2_*`, `queue_length_pmf`, `roi_kpi_tree`; `_utils.as_positive_list` reutilizable | M | Alto | K-01, K-02 | Parametrizados `[nan, inf, -inf, -1]` → `ValueError` | `pytest tests/test_validation_regressions.py` | Medio: entradas antes aceptadas ahora fallan (cambio documentado en CHANGELOG, versión 0.3.0) |
| 1.3 | Reimplementar `mmc` con recurrencia estable (Erlang-B → Erlang-C) | S | Alto | K-06 | `mmc` coincide con el balance de nacimiento-muerte para c ∈ {2,10,100,150,300,1000}; los valores previos no cambian (≤ 1e-9) | `pytest tests/test_queuing.py -k stable` | Bajo (comparación con la implementación actual en el rango que ya funcionaba) |
| 1.4 | `eoq_multi_constrained`: validar `budget`/`space`/costes y limitar iteraciones del multiplicador | S | Alto | K-07 | `budget ∈ {0,-1,nan,inf}` → `ValueError` en < 1 s | `pytest -k budget` | Bajo |
| 1.5 | `cpm`/`pert`: rechazar nombres duplicados | S | Alto | N-04 | `ValueError` con el nombre repetido | `pytest tests/test_cpm_pert.py -k duplicate` | Bajo |
| 1.6 | `abc_analysis`/`xyz_analysis`/`abc_xyz`: `demand ≥ 0`, helper de claves obligatorias, errores accionables | S | Medio | K-03, K-04 | SKU de demanda 0 → clase C; `items` mal formado → `ValueError` que nombra la clave | `pytest tests/test_abc_xyz.py` | Bajo |
| 1.7 | Weibull: dispersión nula → `ValueError`; aviso si la cota de β se alcanza; RRY con denominador 0 → `ValueError` | S | Medio | K-05 | Casos constante, casi constante y n=2 cubiertos | `pytest tests/test_weibull.py -k degenerate` | Bajo |
| 1.8 | MRP: `UserWarning` y campo `past_due_releases` cuando una liberación cae antes del periodo 1 | S | Medio | N-05 | `pytest.warns` y campo poblado | `pytest tests/test_mrp.py -k past_due` | Bajo (campo nuevo, no rompe el contrato) |
| 1.9 | `series_system([])`, `parallel_system([])` y cotas de tamaño (`n_customers`, `K`, `c`) con `ValueError` explicativo | S | Medio | K-08, N-06 | Sin excepciones crudas ni bloqueos en el test de contrato | `pytest tests/test_input_contract.py` | Medio: fija límites máximos que habrá que documentar |
| 1.10 | Tests de humo de gráficas con backend `Agg` (12 `plot_*` y cada `.plot()`); arreglar `break_even_sales().plot()` | M | Alto | N-01 | `plotting.py` ≥ 70 % de cobertura; el `plot()` roto funciona | `pytest tests/test_plotting.py --cov=walopy.plotting` | Bajo |
| 1.11 | Tests del CLI (`__main__`) incluyendo la salida de error por entrada inestable | S | Medio | N-11 | `__main__.py` ≥ 85 % | `pytest tests/test_cli.py --cov=walopy.__main__` | Bajo |

**Cierre de fase:** batería completa; ningún módulo público < 70 %, cobertura global ≥ 85 %.

## Fase 2 — Estructura, API, tipado y CI (≈ 2–3 días)

| ID | Tarea | Esfuerzo | Impacto | Hallazgo | Criterio de aceptación | Verificación | Riesgo de regresión |
|---|---|---|---|---|---|---|---|
| 2.1 | Imports bajo `if TYPE_CHECKING:` para `pd`, `plt`, `go` en los 13 módulos afectados | S | Alto | N-02 | 0 × F821 y 0 × `name-defined` | `ruff check src/ --select F821`; `mypy src/walopy` | Bajo (solo anotaciones) |
| 2.2 | Tipar los registros `list[dict]` internos (TypedDict o dataclasses) en `scheduling.py`, `inventory.py`, `solver.py` | M | Medio | N-02 | `mypy src/walopy` → `Success` | `mypy src/walopy` | Medio: tocar estructuras de retorno; cubrir con la suite existente |
| 2.3 | Complejidad real: sumas acumuladas en `wagner_whitin`; aceleración de Taillard en `neh_flowshop` | M | Medio | N-03 | `wagner_whitin` n=1000 < 1 s; `neh_flowshop` n=200,m=10 < 1 s; resultados idénticos a los actuales | Tests de equivalencia contra fuerza bruta y contra la versión anterior (semillas fijas) | Medio: es reescritura numérica; la suite de referencia independiente la protege |
| 2.4 | `batch_model`: columna `_error` siempre presente y `errors="collect"\|"raise"` | S | Bajo | N-14 | Esquema estable | `pytest tests/test_advanced.py -k batch` | Medio: cambio de comportamiento (documentar) |
| 2.5 | Reorganizar tests por tema (renombrar `test_v026.py`), parametrizar repeticiones, añadir referencias externas fijas (valores de scipy como constantes con su origen) | M | Medio | N-11 | Sin archivos de test nombrados por versión | `ls tests/` | Bajo |
| 2.6 | CI: jobs `lint`, `types`, `coverage` (`--cov-fail-under=85`), `build` + `twine check`, `docs` (`-W`), `audit`; matriz 3.9–3.13; `publish` depende de `test` | M | Alto | K-12 | CI en verde y falla si se introduce un error de lint, tipo o cobertura | Rama de prueba con error deliberado | Bajo (solo se activa cuando todo pasa) |
| 2.7 | Unificar política de entrada vacía (`ValueError` en `schedule_single`, `lot_for_lot`, …) | S | Bajo | N-09 | `[]` → `ValueError` en todas las funciones de listas | `pytest tests/test_input_contract.py` | Medio: cambio de comportamiento |
| 2.8 | Rechazar `bool` como entero y encadenar excepciones (`from None`) en `_utils` | S | Bajo | N-07 | `mmc(2,3,True)` → `TypeError`; 0 × B904 | `ruff check src/ --select B904` | Bajo |

**Cierre de fase:** ruff y mypy sin errores y activos en CI; batería completa.

## Fase 3 — Documentación, rendimiento y comunidad (≈ 2–3 días)

| ID | Tarea | Esfuerzo | Impacto | Hallazgo | Criterio de aceptación | Verificación | Riesgo de regresión |
|---|---|---|---|---|---|---|---|
| 3.1 | Corregir los 13 bloques fallidos del README y añadir `tests/test_readme.py` que ejecute todos los bloques ```python | M | Alto | K-10 | 0 bloques fallidos | `pytest tests/test_readme.py` | Bajo |
| 3.2 | Documentar en el README y en Sphinx: NEH, ABC/XYZ, MRP, CPM/PERT, Weibull, `wagner_whitin`, `rq/rs_policy`, `exchange_curve`, `safety_stock_curve`, scheduling, reliability; páginas `.rst` para los 15 módulos; `release` desde `importlib.metadata`; incluir `CHANGELOG.md` en Sphinx | L | Alto | K-11 | Cada símbolo de `__all__` aparece en la referencia; `sphinx-build -W` OK | Test que compare `__all__` con los símbolos documentados | Bajo |
| 3.3 | Completar secciones `Raises` y `Examples` en las 70 funciones públicas (doctests ejecutables) | L | Medio | N-16 | 0 funciones sin `Raises`; doctests en verde | `pytest --doctest-modules src/walopy` | Bajo |
| 3.4 | `benchmarks/` con línea base documentada (NEH, WW, `mmc`, Monte Carlo) y job de CI informativo (sin gate) | M | Medio | N-03, dimensión 10 | Tabla de tiempos de referencia en `docs/` | `python benchmarks/bench_core.py` | Ninguno |
| 3.5 | Revisar `attestations: true` en `publish.yml` (`permissions: attestations: write`) | S | Bajo | N-15 | Publicación con attestations o decisión documentada | Prueba con TestPyPI | Medio: es el fallo original de v0.2.7; probar antes en TestPyPI |
| 3.6 | Carpeta `examples/` ejecutable (3–5 scripts) verificada en CI | M | Bajo | Dimensión 14 | Los scripts corren sin error | `for f in examples/*.py; do python $f; done` | Ninguno |

## Fase 4 — Release y publicación

| ID | Tarea | Esfuerzo | Criterio de aceptación | Verificación |
|---|---|---|---|---|
| 4.1 | Subir versión a **0.3.0** (validación más estricta = cambio de comportamiento) en `pyproject.toml`; entrada de CHANGELOG con "Cambios que rompen compatibilidad" | S | Una sola fuente de versión | `python -c "import walopy; print(walopy.__version__)"` |
| 4.2 | Instalar el wheel en venv limpio con Python 3.9 y 3.13 y ejecutar los ejemplos | S | Sin errores | venv + `pip install dist/*.whl` |
| 4.3 | PR a `main`, CI en verde, merge y release `v0.3.0` (el release lo crea la persona propietaria; la sesión no tiene permisos para crear releases) | S | PyPI muestra 0.3.0; tag `v0.3.0` existe | `pip install walopy==0.3.0` |
| 4.4 | (Opcional, ver D-5) crear tags faltantes v0.2.4 y v0.2.6 | S | `git tag --list` completo | `git ls-remote --tags origin` |

---

## Decisiones pendientes (requieren su criterio)

| ID | Decisión | Recomendación del auditor |
|---|---|---|
| D-1 | Idioma de docstrings y mensajes de error | Mantener inglés en código y mensajes (documentación en español) y declararlo en `CLAUDE.md`; o español para todo lo que ve el usuario si el público es hispanohablante. Elegir uno |
| D-2 | ¿Se acepta que la validación más estricta rompa llamadas que hoy "funcionan" con basura (p. ej. `t = -1`)? | Sí, en 0.3.0 con nota explícita; son resultados incorrectos |
| D-3 | Cotas superiores de dependencias y extras para gráficas | No poner cotas superiores (las pruebas pasan con las últimas versiones; en librerías limita a los usuarios); añadir un job semanal contra las últimas versiones. Extras `[plot]`: posponer a 0.4.0 |
| D-4 | `abc_analysis` con demanda 0: ¿clase C? | Sí (inventario sin movimiento) |
| D-5 | ¿Crear tags históricos v0.2.4 y v0.2.6? | Solo si identifica los commits exactos de cada release; si no, documentar la laguna en CHANGELOG |

## Riesgos del plan

- **Cambios de comportamiento (1.2, 1.9, 2.4, 2.7):** rompen entradas antes aceptadas; mitigados con CHANGELOG y versión 0.3.0.
- **Reescrituras numéricas (1.3, 2.3):** se protegen con las referencias independientes ya construidas en esta auditoría (birth-death, fuerza bruta, scipy) convertidas en tests permanentes.
- **Activar el CI antes de tiempo (2.6):** dejaría el repositorio en rojo; por eso va al final de la Fase 2.
- **Alcance:** las tareas 3.2 y 3.3 son las más largas; pueden ir en una versión 0.3.1 sin bloquear el release.

## Estado de ejecución (2026-10-02)

Decisiones aplicadas: D-1 → todo en español (mensajes, avisos, CLI, README, docs); D-2 → sí (0.3.0); D-3 → sin cotas superiores, prueba semanal con las últimas versiones, extras de gráficas pospuestos; D-4 → demanda 0 es clase C; D-5 → sin tags históricos. Decisión **D-6** (resuelta el 2026-10-02): se tradujo también todo lo que ve la persona usuaria (columnas de DataFrame, etiquetas de `summary()`, nodos KPI, textos de gráficas, docstrings), registrado como cambio que rompe compatibilidad en 0.3.0; los identificadores y las claves de datos siguen en inglés.

| Tarea | Estado | Nota |
|---|---|---|
| 0.1–0.5 | Hechas | `CLAUDE.md`, `pyproject.toml`, `py.typed`, versión, autofix de ruff, SECURITY/CoC/plantillas |
| 1.1 | Hecha | `tests/test_contrato_entradas.py` (0 incumplimientos en 67 funciones) |
| 1.2 | Hecha | Validación central en CPM/PERT, MTBF, sistemas, MRP, Weibull, `cv2_*`, break-even, PMF/CDF |
| 1.3 | Hecha | `mmc` estable (Erlang-B), contraste con nacimiento-muerte hasta c = 1000 |
| 1.4–1.8 | Hechas | `eoq_multi_constrained`, duplicados CPM, ABC/XYZ, Weibull degenerado, MRP vencidas |
| 1.9 | Parcial | Listas vacías y cotas de tamaño hechas; **magnitudes extremas (K-08) no se rechazan** (impacto bajo) |
| 1.10–1.11 | Hechas | `tests/test_plotting.py`, `tests/test_cli.py`; `break_even_sales().plot()` corregido |
| 2.1–2.2 | Hechas | `TYPE_CHECKING`, `TypedDict` y `dict[str, Any]`; ruff y mypy en 0 |
| 2.3 | Hecha | `wagner_whitin` O(n²) real, NEH con Taillard; `tests/test_complejidad.py` |
| 2.4 | Hecha | `batch_model(errors=…)`; la columna `_error` condicional se mantiene (documentada) |
| 2.5 | Hecha | `test_v026.py` dividido por tema; constantes externas en `tests/test_referencias_externas.py` |
| 2.6 | Hecha | Jobs del CI verificados en GitHub; publicación con verificación previa |
| 2.7–2.8 | Hechas | Listas vacías → `ValueError`; `bool` rechazado; `from None` |
| 2.9 (nueva) | Parcial | Mensajes, avisos y CLI en español; cuerpo de docstrings pendiente |
| 3.1–3.2 | Hechas | README corregido y ampliado con test; Sphinx de 13 módulos; `tests/test_documentacion.py` |
| 3.3 | Hecha | `Raises` y `Examples` en las 70 funciones; doctests en `pytest` |
| 3.4 | Hecha | `benchmarks/bench_core.py`, `docs/source/rendimiento.md`, job informativo |
| 3.5 | **No hecha** | Requiere TestPyPI; `attestations: false` se mantiene |
| 3.6 | Hecha | `examples/` + `tests/test_ejemplos.py` |
| 4.1–4.2 | Hechas | Versión 0.3.0; rueda instalada en entornos limpios 3.9 y 3.13 con ejemplos ejecutados |
| 4.3 | Pendiente | PR abierto; merge y release a cargo de la persona propietaria |
| 4.4 | No se hace | D-5 |
