# PLAYBOOK — madurez de una librería Python (niveles 0→5) con los comandos de walopy

> Checklist portable. Cada punto lleva el comando que lo comprueba en este repo (`make …`) y el criterio «hecho». Los puntos marcados ★ salieron de los incidentes de walopy
> (ver `LESSONS_LEARNED.md`) o de criterios ya contrastados en otro proyecto (los de Sphinx, ejemplos y release; en walopy `sphinx -W` pasa sin duplicados); los demás vienen del Playbook de partida (`docs/referencia/PLAYBOOK.md`). Estado de walopy por nivel al final.

## Nivel 0 → 1: estructura básica
- [ ] Layout `src/`, `pyproject.toml` completo, LICENSE, `.gitignore` con `build/`, `dist/`, `docs/_build/`, `.coverage`, cachés y `.venv/` — `git check-ignore -v dist/x docs/_build/x .coverage .venv/x`
- [ ] ★ **Versión con fuente única y literal:** `__version__ = "X.Y.Z"` en `__init__.py` y `[tool.setuptools.dynamic] version = {attr = "<paquete>.__version__"}`. **Nunca `importlib.metadata.version()` en `__init__.py`** (queda congelada al instalar) — `pytest tests/test_version.py`
- [ ] `py.typed` en el paquete y en `[tool.setuptools.package-data]` — `unzip -l dist/*.whl | grep py.typed`
- [ ] Tests pasan en un venv limpio — `python -m venv v && v/bin/pip install -e ".[dev]" && v/bin/pytest`
- [ ] ★ **Un `Makefile` (o nox) es la única definición de cada gate**; CI, docs y hooks lo invocan — `grep -rn "ruff check" . | sort -u` debe dar un solo comando

## Nivel 1 → 2: calidad verificable
- [ ] Linter con la configuración del CI (no inventar un `--select` más estricto sin probarlo) — `make lint` → «All checks passed!»
- [ ] Tipos — `make types` → «Success»
- [ ] **Cobertura por módulo**: global ≥ 85 % y ningún módulo público < 70 % (un 90 % global puede esconder un 19 %) — `make cov`
- [ ] CI con todos los gates (lint, tipos, tests, cobertura, build, docs) y matriz de **todas** las versiones de `classifiers`, `fail-fast: false`
- [ ] ★ Todo bug corregido tiene un test que **falla en el tag anterior** — `make regresion`
- [ ] ★ Mutación de una línea: el test falla si el bug vuelve — `make mutaciones` (si un mutante sobrevive, el test no cubría esa línea)
- [ ] ★ Cada test de un detector (lint, idioma, barrido) lleva un control negativo (una entrada mala que debe ser señalada)

## Nivel 2 → 3: lista para producción
- [ ] Capa de validación central y barrido de contrato sobre todo `__all__` (`[nan, inf, -inf, -1, 0, None, "x", []]`) — `pytest tests/test_contrato_entradas.py`
- [ ] ★ **NaN antes de comparar** (`isfinite` primero); `bool` no es número; cotas `MAX_*` en todo parámetro que dimensiona un cálculo
- [ ] Nada se recorta, fusiona ni descarta en silencio (duplicados → error; cota alcanzada → aviso)
- [ ] Caso a escala (≥ 10× el típico) con tiempo medido; fórmulas con potencias/factoriales → recurrencias estables — `pytest tests/test_mmc_estable.py tests/test_complejidad.py`
- [ ] Documentación: README con ejemplos **ejecutados como tests**, doctests activos (`--doctest-modules`), cada símbolo de `__all__` en las docs — `make docs && pytest tests/test_readme.py tests/test_documentacion.py`
- [ ] ★ **Un símbolo = una directiva autodoc canónica**; si dos páginas lo documentan, la procesada primero lleva `:no-index:`; en docstrings numpy evitar `shape (n,)` si existe un atributo `n` — `sphinx-build -W`
- [ ] Dependencias opcionales: `ImportError` con mensaje `pip install paquete[extra]` y test con `monkeypatch.setitem(sys.modules, "<dep>", None)` (en walopy no hay extras hoy)
- [ ] Gráficas: no modifican `rcParams` (test que compare `dict(rcParams)` antes y después, **para todas las gráficas**, también las de llamada directa) o usan `plt.rc_context({})`
- [ ] ★ Los ejemplos de `examples/` se **ejecutan** (un renombre los rompe en silencio) — `make examples`; buscar el nombre antiguo con `make obsoletas` (incluye ejemplos, CI y LICENSE)
- [ ] ★ La política de idioma tiene un test — `pytest tests/test_idioma.py`

## Nivel 3 → 4: publicada y mantenida
- [ ] SemVer, CHANGELOG por versión, tag `vX.Y.Z` **por cada versión publicada**
- [ ] ★ **«Listo para release» solo tras construir el wheel y ver su versión** — `make release-check TAG=vX.Y.Z` (un tag creado antes de subir la versión produjo artefactos viejos y `400 File exists`)
- [ ] ★ La publicación comprueba tag == versión del wheel y repite tests/lint — `scripts/comprobar_version_release.py` en `publish.yml`
- [ ] ★ Comprobar el estado de PyPI antes de elegir versión — `pip index versions <paquete>`
- [ ] Build aislado + `twine check` + instalación de la rueda en un entorno limpio — `make build`
- [ ] Soporte multi-versión verificado: mínimos de dependencias + últimas (semanal) — jobs del CI
- [ ] ★ **Preparado para agentes:** `CLAUDE.md` (estado verificado, comandos, definición de terminado, reglas etiquetadas), `AGENTS.md`, `Makefile`, `.claude/settings.json` (permisos), hook `SessionStart` (solo remoto, idempotente) y hook `Stop` (corre `make check-fast`; `stop_hook_active=true` → exit 0), plantilla de PR y CODEOWNERS
- [ ] ★ Cada regla de `CLAUDE.md` se prueba contra el repo antes de adoptarla y se etiqueta (`[test]`, `[CI]`, `[comando]`, `[guía]`) — `CLAUDE_MD_RULES.md`
- [ ] ★ Ramas desde `origin/main` recién traído — `git fetch origin +refs/heads/main:refs/remotes/origin/main && git merge-base --is-ancestor origin/main HEAD`

## Nivel 4 → 5: excelencia sostenida
- [ ] Benchmarks reproducibles **con línea base guardada y comparación automática** — `python benchmarks/bench_core.py` mide, pero no compara (pendiente en walopy)
- [ ] Seguridad: `pip-audit` en el CI, `SECURITY.md`, **attestations/procedencia**, actualización automática de dependencias, acciones fijadas por SHA — (pendiente en walopy)
- [ ] ★ Ensayo de publicación en TestPyPI antes de tocar PyPI real — (pendiente en walopy)
- [ ] Comunidad: CONTRIBUTING, plantillas, código de conducta, protección de ramas (configuración de GitHub: **no verificable desde el repo**)
- [ ] ★ Nunca cambiar la versión de una acción de GitHub «por intuición»: verificar en los logs qué versión usa y si funciona

## Checklist de «terminado» para un PR
```bash
make check                       # lint, tipos, tests, cobertura (global y por módulo), build, docs, ejemplos, obsoletas, regresión
make mutaciones                  # si se corrigió un bug
git merge-base --is-ancestor origin/main HEAD
make release-check TAG=vX.Y.Z    # solo si sube la versión
```

## Estado de walopy por nivel (2026-10-02)
| Nivel | Estado | Pendiente |
|---|---|---|
| 0 → 1 | cumplido | — |
| 1 → 2 | cumplido | — |
| 2 → 3 | cumplido | `ImportError` de opcionales: no aplica (sin extras) |
| 3 → 4 | cumplido salvo tag de `0.2.6` | ensayo en TestPyPI (para tener evidencia de la configuración de publicación) |
| 4 → 5 | parcial | línea base de benchmarks, attestations, Dependabot, SHA de acciones, protección de ramas (no verificable) |
