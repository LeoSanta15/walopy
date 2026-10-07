# CLAUDE.md — walopy

## Descripción
Librería Python de investigación de operaciones: colas, inventarios, scheduling, proyectos (CPM/PERT),
confiabilidad, OEE, cuellos de botella, break-even y árboles de KPI. Usuarios: ingenieros industriales y
analistas de operaciones. Sin `scipy`: solo numpy, pandas, matplotlib y plotly (las cuatro son dependencias obligatorias;
matplotlib y plotly se importan de forma perezosa dentro de las funciones de gráficas).

Python ≥ 3.9 · layout `src/` · versión actual: ver `src/walopy/__init__.py` (`__version__`).

## Estado verificado (2026-10-07, v0.4.2)
Cifras medidas con `make check`; si cambian, actualiza esta sección con la salida real (no de memoria).

| Medida | Valor |
|---|---|
| Tests (`make test`) | 2 206 pasan (incluye los doctests de `src/`, los bloques de código de `README.md` y `README.en.md` y los ejemplos); el CI los ejecuta en 3.9 a 3.13 y en 3.9 con dependencias mínimas |
| Cobertura | global 97,3 %; el módulo menor (`solver.py`) 89,1 % |
| Lint / tipos | `ruff` y `mypy` sin errores (19 archivos fuente) |
| Build | `python -m build` + `twine check` correctos; el wheel incluye `py.typed` |
| Docs | `sphinx -W` sin avisos en español y en inglés, 14 páginas de referencia |
| Regresiones | 27 bugs (`W-01`…`W-27`) en `tests/regresiones.json`; 25 con selectores que fallan en `v0.2.8` |

## Mapa del código (`src/walopy/`)
- `queuing.py`     — M/M/1, M/M/c, M/D/1, M/G/1, G/G/1 (Kingman), ley de Little, helpers `cv2_*`
- `advanced.py`    — M/M/1/K, M/M/c/K, Erlang-B, colas con prioridad, Monte Carlo G/G/1, takt, balance de línea, break-even, PMF/CDF
- `network.py`     — redes de Jackson
- `fitting.py`     — ajuste de parámetros de cola desde datos (`fit_from_data`)
- `solver.py`      — `solve_lam`, `solve_mu`, `solve_servers`, `optimize_servers`, `sensitivity`, `batch_model`, `compare`
- `inventory.py`   — EOQ/EBQ, multi-artículo, lotes, (r,Q), (R,S), Wagner-Whitin, newsvendor, curvas de intercambio, ABC/XYZ, MRP
- `scheduling.py`  — secuenciación de una máquina, Johnson y NEH (flow-shop)
- `project.py`     — CPM y PERT
- `reliability.py` — MTBF, sistemas serie/paralelo/k-de-n, Weibull
- `operations.py`  — OEE, utilización/eficiencia, costo unitario
- `bottleneck.py`  — análisis de cuello de botella
- `kpi.py`         — `KPINode`, `oee_kpi_tree`, `throughput_kpi_tree`, `roi_kpi_tree`
- `plotting.py`    — todas las gráficas (matplotlib y plotly, importación perezosa)
- `__main__.py`    — CLI (`python -m walopy`)
- `_utils.py`      — validadores compartidos (única capa de ingesta numérica) y cotas de tamaño
- `_i18n.py`       — idioma activo (`set_language`, `language`, `get_language`, `WALOPY_LANG`) y `t("clave", **datos)`; los textos viven en los catálogos
- `_catalogo_es.py` — catálogo de textos en español (idioma por defecto); claves `modulo.tipo.funcion.resumen`
- `_catalogo_en.py` — catálogo de textos en inglés (mismas claves y marcadores que el español) y `EXENTAS_DE_TRADUCCION` (textos iguales en ambos idiomas a propósito)
- `__init__.py`    — API pública (`__all__`) y **fuente única de la versión** (`__version__`, literal)

Otras carpetas: `tests/` (pytest; incluye doctests de `src/` y los ejemplos del README), `examples/` (scripts ejecutables),
`benchmarks/` (rendimiento), `scripts/` (utilidades de CI y verificación), `docs/` (Sphinx; `auditoria/`, `referencia/` y `retrospectiva/`),
`.claude/` (permisos y hooks para agentes), `Makefile` (todos los comandos de abajo).

## Comandos estándar (`make` ejecuta exactamente lo que ejecuta el CI)
```bash
make install       # pip install -e ".[dev,release,docs]"
make check-fast    # lint + tipos + tests   ← iterar con esto
make check         # lint + tipos + cobertura (global y por módulo) + build + docs + ejemplos + obsoletas + regresion
make release-check TAG=vX.Y.Z   # construye y comprueba que el wheel tiene la versión del tag

make test | cov | lint | types | build | docs | examples | obsoletas | regresion | mutaciones | inventario-i18n | clean
```
Equivalentes directos: `python -m pytest` · `python -m ruff check src/ tests/ benchmarks/ scripts/ examples/` ·
`python -m mypy src/walopy --ignore-missing-imports` · `python -m build && python -m twine check dist/*` ·
`python -m sphinx -b html -W docs/source docs/build/es` y `... -W -D language=en docs/source docs/build/en` (la documentación en inglés sale de `docs/source/locale/en`; tras cambiar un docstring ejecuta `make docs-i18n` y traduce lo nuevo).
**Internacionalización** (`docs/auditoria/PLAN_I18N.md`; el inglés no pasa por revisión nativa y la paridad es obligatoria, §7; pasos de una función nueva en `CONTRIBUTING.md`): los textos que ve la persona usuaria no se escriben en el código sino en `_catalogo_es.py` (y su traducción en `_catalogo_en.py`) y se usan con `_t("modulo.tipo.funcion.resumen", dato=valor)` (`from ._i18n import t as _t`). Para un texto nuevo: añade la clave al catálogo español (marcadores `str.format` nombrados, p. ej. `{name}`, `{value!r}`), la misma clave con los mismos marcadores en el inglés, y llámalo con `_t`. `make inventario-i18n` falla si queda un texto literal visible en `src/`; una clave nueva (que no estaba en v0.3.0) se declara además en `AÑADIDAS_TRAS_V030` de `tests/test_inventario_i18n.py`. Las claves de `result.params` se mantienen fijas; las columnas de DataFrame se leen con `columna(df, "clave")`.
`make regresion` y `make mutaciones` necesitan `pytest-timeout` (extra `dev`) y, la primera, los tags de git (`git fetch --tags`).

## Definición de «terminado»
Una tarea está terminada solo cuando `make check` termina con código 0, es decir:
1. `pytest` → 0 fallos, 0 errores (incluye doctests y ejemplos del README).
2. `ruff check src/ tests/ benchmarks/ scripts/ examples/` → `All checks passed!` (el mismo comando que el CI y que `make lint`).
3. `mypy src/walopy --ignore-missing-imports` → `Success: no issues found`.
4. Cobertura global ≥ 85 % y **ningún módulo público < 70 %** (se comprueba por módulo con `scripts/comprobar_cobertura_modulos.py`).
5. `python -m build` + `twine check` correctos; `sphinx -W` sin avisos; los 5 ejemplos de `examples/` se ejecutan.
6. Sin referencias obsoletas (`make obsoletas`).
7. Los tests de regresión fallan en el tag anterior (`make regresion`).
8. `CHANGELOG.md` actualizado; README, referencia Sphinx y este archivo actualizados si cambió la funcionalidad.

«Listo para release» solo después de `make release-check TAG=vX.Y.Z` (el wheel construido muestra la versión del tag).

## Reglas de trabajo
Etiqueta de cada regla: `[test]` la comprueba la suite · `[CI]` la comprueba un job · `[comando]` se comprueba con una orden manual · `[guía]` criterio de revisión, no verificable mecánicamente.
Estado de la prueba de cada regla contra este repo: `docs/retrospectiva/CLAUDE_MD_RULES.md`.
- **R-01 Cambios quirúrgicos.** `[guía]` No reescribas módulos para añadir una función; sigue el patrón de los módulos vecinos.
- **R-02 Validar contra referencia independiente.** `[test]` Todo resultado numérico se contrasta con una fuente externa (publicación, cálculo manual, otra librería, fuerza bruta, simulación con ≥ 20 semillas). Nunca contra el propio código. (`tests/test_referencias_externas.py`)
- **R-03 Español en lo que ve el usuario.** `[test]` Docstrings, mensajes de `ValueError`/`TypeError`/`UserWarning`, columnas de DataFrame, textos de gráficas, README, CHANGELOG y commits van en español. Identificadores y claves de datos en inglés (snake_case; clases en PascalCase); las cabeceras que se muestran (`to_frame()`, `summary()`) se traducen con `.rename(columns=…)` sin tocar las claves. Desde 0.4.0 esos textos viven en el catálogo (`_catalogo_es.py` es el idioma por defecto; ver «Internacionalización») y el español sigue siendo lo que se ve por defecto. Lo comprueban `tests/test_idioma.py` y `tests/test_inventario_i18n.py`.
- **R-04 Avances incrementales.** `[comando]` Cada versión: construir, probar (suite + wheel en venv limpio), commit, tag `vX.Y.Z` **después** de subir la versión (un tag creado antes produce artefactos viejos y PyPI responde `400 File exists`).
- **R-05 Una sola fuente de verdad para la versión: el literal `__version__` de `src/walopy/__init__.py`.** `[test]` `pyproject.toml` la lee con `[tool.setuptools.dynamic] version = {attr = "walopy.__version__"}`. **No uses `importlib.metadata.version()` en `__init__.py`:** los metadatos se congelan al instalar y tras subir la versión `__version__` seguiría mostrando la anterior (comprobado). Tras subirla, `make install` refresca los metadatos. Lo comprueba `tests/test_version.py`.
- **R-06 Dependencias opcionales con mensaje orientativo** `[guía]` (`try/except ImportError` con `pip install walopy[extra]`). Hoy no hay extras: matplotlib y plotly son obligatorias; si se declara un extra, añadir el mensaje y el test con `monkeypatch.setitem(sys.modules, "<dep>", None)`.
- **R-07 No contaminar estado global.** `[test]` Las gráficas no modifican `matplotlib.rcParams` (`tests/test_plotting.py::test_plot_no_modifica_rcparams`, una por cada gráfica); si una gráfica necesita estilos propios, usar `plt.rc_context({...})`. Warnings temporales con `warnings.catch_warnings()`.
- **R-08 Validación de entrada centralizada.** `[test]` Todo argumento numérico de usuario pasa por `_utils.py` (finito, positivo, entero, etc.). NaN/inf se rechazan **antes** de comparar: `x <= 0` es `False` para NaN. Los parámetros que dimensionan un cálculo llevan cota (`MAX_*`, `as_int_positive(max=…)`) y las listas de registros se validan (tipo, claves, duplicados). (`tests/test_contrato_entradas.py`)
- **R-09 Checklist de renombre.** `[comando]` Si se renombra un símbolo o módulo: `grep -rn "nombre_viejo" . --include="*.py" --include="*.md" --include="*.toml" --include="*.yml" --include="*.rst"` y actualizar todo, incluidos `examples/`, el CI, `LICENSE` y este archivo.
- **R-10 No repetir bugs del catálogo.** `[guía]` Antes de validar entradas, tratar casos borde o importar opcionales, leer `docs/referencia/BUG_CATALOG.md` (fichas `W-nn` y clases `C-nn`) y `docs/retrospectiva/BUG_CATALOG.md`.
- **R-11 Tests de casos borde obligatorios** `[test]` para toda función pública nueva: entrada vacía, NaN/inf, n mínimo, parámetros opcionales ausentes, caso degenerado (std = 0, todos iguales).
- **R-12 CI en versión mínima.** `[CI]` Antes de abrir un PR, los tests deben pasar en Python 3.9 (`uv venv --python 3.9`).
- **R-13 Todo símbolo nuevo de `__all__`** `[test]` se documenta (README y Sphinx) y entra en el test de contrato de entradas. (`tests/test_documentacion.py`)
- **R-14 Toda complejidad anunciada** `[test]` en un docstring o CHANGELOG tiene un benchmark o un test de tiempo que la respalda. (`tests/test_complejidad.py`)
- **R-15 Los ejemplos de README y docs son tests** `[test]` (`tests/test_readme.py`, `tests/test_ejemplos.py`) y los doctests de `src/` están activos (`--doctest-modules` en `pyproject.toml`).
- **R-16 Todo bug corregido deja tres huellas.** `[test]` (1) Un test de regresión que **falla en el tag anterior**, registrado con su `W-nn` y su `ref` en `tests/regresiones.json`; (2) una ficha `W-nn` en `docs/referencia/BUG_CATALOG.md` (con su clase `C-nn`); (3) si la lección es transferible, una línea en `docs/referencia/PLAYBOOK.md` y, si cambia cómo se trabaja, una regla aquí. Lo comprueban `tests/test_trazabilidad.py`, `make regresion` y `make mutaciones` (mutación de una línea: el test debe fallar si el bug vuelve).
- **R-17 Cada rama parte de `origin/main` actualizado.** `[comando]` Antes de abrir el PR: `git fetch origin +refs/heads/main:refs/remotes/origin/main && git merge-base --is-ancestor origin/main HEAD` debe terminar con código 0 (un `git fetch origin main` a secas puede dejar `origin/main` desactualizado). Tras un merge *squash*, reiniciar la rama desde `main`.
- **R-18 Acciones de GitHub: nunca cambiar una versión «por intuición».** `[guía]` Verifica en los logs del CI qué versión usa y si funciona antes de tocarla.

## Hooks para agentes (`.claude/`)
- `settings.json`: permisos para `make`, pytest, ruff, mypy, build, twine, sphinx y git de solo lectura (`status`, `diff`, `log`, `show`).
- `hooks/session-start.sh`: solo con `CLAUDE_CODE_REMOTE=true`; instala el proyecto con extras de desarrollo (síncrono, idempotente).
- `hooks/verify-before-stop.sh`: si hay cambios sin confirmar en `src/`, `tests/`, `scripts/`, `examples/`, `benchmarks/`, `pyproject.toml` o `Makefile`, corre `make check-fast`; si falla, devuelve el error (exit 2) para que el agente lo corrija. Con `stop_hook_active=true` no hace nada (evita bucles).

## Pendientes y deuda técnica (solo lo verificado)
| Deuda | Evidencia | Estado |
|---|---|---|
| `attestations: false` en la publicación | `.github/workflows/publish.yml` | Activarlo exige probar con TestPyPI (su activación sin probar rompió v0.2.7) |
| Acciones fijadas por tag, no por SHA; sin Dependabot | `uses: actions/...@v4` en los workflows | Pendiente |
| Aviso de Node.js 20 en `actions/checkout@v4` y `setup-python@v5` | logs del CI del PR #15 | Informativo; los jobs pasan |
| K-08: magnitudes extremas (1e308, 1e-320) no se rechazan explícitamente | `docs/auditoria/HALLAZGOS.md` | Fuera del contrato; impacto bajo |
| `plotting.py` no usa `rc_context` (no modifica `rcParams`; lo prueba el test) | `grep rc_context src/` → 0 | Invariante cumplido; R-07 corregida |
| Tag ausente para `0.2.6`, que sí está en PyPI; `0.2.4` no existe en PyPI (su publicación falló); `v0.1.0` y `v0.2.0` sin tag y fuera de `pip index versions walopy` | `git ls-remote --tags origin` y `pip index versions walopy` (2026-10-02) | Pendiente decidir si se etiquetan commits históricos; causa de la ausencia de 0.1.0/0.2.0 en PyPI: NO VERIFICADO |
| Protección de ramas y revisión de CODEOWNERS | configuración de GitHub, fuera del repo | NO VERIFICADO |

## Política de no repetición
Si reaparece un bug del catálogo: identificar por qué la solución anterior no bastó, añadir test de regresión, actualizar el catálogo y reforzar la regla correspondiente aquí.

## Checklist de release
- [ ] Subir la versión **solo** en `src/walopy/__init__.py` y ejecutar `make install`
- [ ] Entrada en `CHANGELOG.md` (con «Cambios que rompen compatibilidad» si aplica)
- [ ] `make check` con código 0
- [ ] `make release-check TAG=vX.Y.Z` correcto (el wheel construido tiene la versión del tag)
- [ ] PR a `main`, CI en verde, merge
- [ ] Crear el release de GitHub con tag `vX.Y.Z` (dispara `publish.yml`, que repite la comprobación de versión)
- [ ] Verificar `pip install walopy==X.Y.Z` en un venv limpio
