# CLAUDE.md — walopy

## Descripción
Librería Python de investigación de operaciones: colas, inventarios, scheduling, proyectos (CPM/PERT),
confiabilidad, OEE, cuellos de botella, break-even y árboles de KPI. Usuarios: ingenieros industriales y
analistas de operaciones. Sin `scipy`: solo numpy, pandas, matplotlib y plotly.

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

Otras carpetas: `tests/` (pytest; incluye doctests de `src/` y los ejemplos del README), `examples/` (scripts ejecutables), `benchmarks/` (rendimiento), `scripts/` (utilidades de CI y `verificar_regresion.py`), `docs/` (Sphinx, `auditoria/` y `referencia/`).

## Comandos estándar
```bash
# Tests
python -m pytest tests/ -q

# Linter (bugs reales, no solo estilo; reglas F, E9, B, I, S definidas en pyproject.toml)
python -m ruff check src/ tests/ benchmarks/ scripts/ examples/

# Tipos
python -m mypy src/walopy --ignore-missing-imports

# Build y verificación del paquete
python -m build && python -m twine check dist/*

# Cobertura
python -m pytest --cov=walopy --cov-report=term-missing -q

# Los tests de regresión fallan en la versión anterior (necesita pytest-timeout y los tags de git)
python scripts/verificar_regresion.py --manifiesto tests/regresiones.json

# Documentación (warnings como errores)
python -m sphinx -b html -W docs/source docs/build

# Referencias obsoletas
grep -rn "PLACEHOLDER\|TU_USUARIO\|cost_kpi_tree" . --include="*.py" --include="*.md" --include="*.toml" --include="*.yml" --exclude=CLAUDE.md --exclude-dir=.git --exclude-dir=.github --exclude-dir=auditoria --exclude-dir=referencia || echo OK
```
Instalación de desarrollo: `pip install -e ".[dev,release,docs]"`.

## Definición de "terminado"
Una tarea está terminada solo cuando:
1. `pytest -q` → 0 fallos, 0 errores.
2. `ruff check src/ tests/` → `All checks passed!`
3. `mypy src/walopy --ignore-missing-imports` → `Success: no issues found`
4. `python -m build` + `twine check` → correctos.
5. Cobertura global ≥ 85 %; ningún módulo público < 70 %.
6. Sin referencias obsoletas (comando de arriba).
7. `CHANGELOG.md` actualizado con la versión nueva.
   Si el cambio corrige un bug: entrada en `tests/regresiones.json` y ficha en `BUG_CATALOG.md` (R-16).
8. `CLAUDE.md`, README y la referencia Sphinx actualizados si se añadió o cambió funcionalidad.

## Reglas de trabajo (no negociables)
- **R-01 Cambios quirúrgicos.** No reescribas módulos para añadir una función; sigue el patrón de los módulos vecinos.
- **R-02 Validar contra referencia independiente.** Todo resultado numérico se contrasta con una fuente externa (publicación, cálculo manual, otra librería, fuerza bruta, simulación con ≥ 20 semillas). Nunca contra el propio código.
- **R-03 Español en lo que ve el usuario.** Docstrings, mensajes de `ValueError`/`TypeError`/`UserWarning`, columnas de DataFrame, textos de gráficas, README, CHANGELOG y commits van en español. Identificadores y claves de datos en inglés (snake_case; clases en PascalCase); las cabeceras que se muestran (`to_frame()`, `summary()`) se traducen con `.rename(columns=…)` sin tocar las claves. Lo comprueba `tests/test_idioma.py`.
- **R-04 Avances incrementales.** Cada versión: construir, probar (suite + wheel en venv limpio), commit, tag `vX.Y.Z`.
- **R-05 Una sola fuente de verdad para la versión:** `pyproject.toml`. `__init__.py` la lee con `importlib.metadata`. No hay que tocar `__init__.py` al subir versión.
- **R-06 Dependencias opcionales con mensaje orientativo** (`try/except ImportError` con `pip install walopy[extra]`).
- **R-07 No contaminar estado global.** Gráficas dentro de `plt.rc_context`; warnings temporales con `warnings.catch_warnings()`.
- **R-08 Validación de entrada centralizada.** Todo argumento numérico de usuario pasa por `_utils.py` (finito, positivo, entero, etc.). NaN/inf se rechazan **antes** de comparar: `x <= 0` es `False` para NaN. Los parámetros que dimensionan un cálculo llevan cota (`MAX_*`, `as_int_positive(max=…)`) y las listas de registros se validan (tipo, claves, duplicados).
- **R-09 Checklist de renombre.** Si se renombra un símbolo o módulo: `grep -rn "nombre_viejo" . --include="*.py" --include="*.md" --include="*.toml" --include="*.yml" --include="*.rst"` y actualizar todo, incluido este archivo.
- **R-10 No repetir bugs del catálogo.** Antes de validar entradas, tratar casos borde o importar opcionales, leer `docs/referencia/BUG_CATALOG.md` (fichas `W-nn` y clases `C-nn`) y `docs/auditoria/CATALOG_UPDATES.md`.
- **R-11 Tests de casos borde obligatorios** para toda función pública nueva: entrada vacía, NaN/inf, n mínimo, parámetros opcionales ausentes, caso degenerado (std = 0, todos iguales).
- **R-12 CI en versión mínima.** Antes de abrir un PR, los tests deben pasar en Python 3.9 (`uv venv --python 3.9`).
- **R-13 Todo símbolo nuevo de `__all__`** se documenta (README y Sphinx) y entra en el test de contrato de entradas.
- **R-14 Toda complejidad anunciada** en un docstring o CHANGELOG tiene un benchmark que la respalda.
- **R-15 Los ejemplos de README y docs son tests** (`tests/test_readme.py`) y los doctests de `src/` están activos (`--doctest-modules` en `pyproject.toml`).
- **R-16 Todo bug corregido deja tres huellas.** (1) Un test de regresión que **falla en el tag anterior**, registrado con su `W-nn` y su `ref` en `tests/regresiones.json`; (2) una ficha `W-nn` en `docs/referencia/BUG_CATALOG.md` (con su clase `C-nn`); (3) si la lección es transferible, una línea en `docs/referencia/PLAYBOOK.md` y, si cambia cómo se trabaja, una regla aquí. Lo comprueban `tests/test_trazabilidad.py` y `scripts/verificar_regresion.py` (job `regresion` del CI).
- **R-17 Cada rama parte de `origin/main` actualizado.** Antes de abrir el PR: `git fetch origin main && git merge-base --is-ancestor origin/main HEAD` debe terminar con código 0. Tras un merge *squash*, reiniciar la rama desde `main`.

## Política de no repetición
Si reaparece un bug del catálogo: identificar por qué la solución anterior no bastó, añadir test de regresión, actualizar el catálogo y reforzar la regla correspondiente aquí.

## Checklist de release
- [ ] Subir la versión **solo** en `pyproject.toml`
- [ ] Entrada en `CHANGELOG.md` (con "Cambios que rompen compatibilidad" si aplica)
- [ ] Batería completa de la "definición de terminado" en verde
- [ ] Wheel instalado en venv limpio (Python 3.9 y la más reciente) y ejemplos ejecutados
- [ ] PR a `main`, CI en verde, merge
- [ ] Crear el release de GitHub con tag `vX.Y.Z` (dispara la publicación a PyPI)
- [ ] Verificar `pip install walopy==X.Y.Z` en un venv limpio
