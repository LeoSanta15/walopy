# DIAGNÓSTICO — walopy v0.2.8

> Auditoría contra `docs/referencia/PLAYBOOK.md` y `docs/referencia/BUG_CATALOG.md`.
> Fecha: 2026-10-02 · Commit auditado: `2cc17c1` (main, v0.2.8) · Fase de solo lectura: no se modificó código fuente.
> Convención: **HECHO** = observado con un comando; **INFERENCIA** = deducción razonada; **NO VERIFICADO** = sin evidencia.

## 0. Contexto del proyecto (rellenado por el auditor)

- **Qué es:** librería Python de investigación de operaciones: colas (M/M/1, M/M/c, M/G/1, G/G/1, prioridades, Jackson, Monte Carlo), inventarios (EOQ/EBQ, (r,Q), (R,S), Wagner-Whitin, curvas de intercambio, ABC/XYZ, MRP), scheduling (Johnson, NEH), CPM/PERT, confiabilidad (MTBF, sistemas k-de-n, Weibull), OEE, balance de línea, break-even, árboles de KPI y CLI.
- **Usuarios:** ingenieros industriales y analistas de operaciones que usan DataFrames/gráficas; público hispanohablante (README y CHANGELOG en español).
- **Restricciones propias:** sin `scipy` (solo numpy/pandas/matplotlib/plotly); Python ≥ 3.9; publicación vía PyPI Trusted Publishing.
- **Partes más débiles según la evidencia:** documentación frente a código (README con API inexistente, 8 funciones de v0.2.8 sin documentar), validación de entradas fuera de la capa central, CI sin gates de calidad, tipado.
- **Historial:** 34 commits, 2 autores. La versión 0.2.8 se escribió y publicó en la misma sesión que esta auditoría; sus defectos se reportan igual que los demás.

## 1. Línea base (Paso 1)

| Verificación | Comando | Resultado (HECHO) |
|---|---|---|
| Inventario | `wc -l` | 16 módulos, 8 176 líneas en `src/`, 2 685 en `tests/`, 111 símbolos en `__all__` (70 funciones, 41 clases) |
| Python | `python --version` | 3.11.15 (venv limpio). También 3.9.23 vía `uv` |
| Instalación limpia | `pip install -e ".[dev,docs]"` en venv nuevo | OK; resuelve numpy 2.4.6, pandas 3.0.6, matplotlib 3.11.2, plotly 7.1.0 |
| Tests (3.11) | `pytest -q` | **357 passed**, 0 fallos |
| Tests (3.9) | `pytest -q` en venv 3.9 | **357 passed** |
| Tests con dependencias mínimas | 3.9 + numpy 1.22.0, pandas 1.4.0, matplotlib 3.5.0, plotly 5.0.0 | **357 passed** (nota: los `plot()` no están cubiertos por tests, ver §2) |
| Tests con `-W error` | `pytest -W error` | 357 passed (sin warnings) |
| Cobertura | `pytest --cov=walopy` | **80 % global** (< 85 % del Playbook). `plotting.py` **0 %** (220 sentencias), `__main__.py` 62 %; el resto 77–95 % |
| Linter (reglas del repo) | `ruff check src/` (ruff 0.16.10) | **215 errores** (116 autocorregibles). `ruff` no está fijado en `dev`, el recuento depende de la versión |
| Linter (reglas del Playbook) | `ruff check src/ --select F,E9,B,I,S` | **82 errores**: 43 F821 (nombre indefinido en anotaciones), 16 I001, 13 F401, 6 F841, 4 B904 |
| Tipos | `mypy src/walopy --ignore-missing-imports` | **78 errores** en 13 de 16 archivos (43 name-defined, 24 operator, 5 arg-type, 3 return-value, 2 call-overload, 1 misc) |
| Build | `python -m build` + `twine check` | wheel y sdist construidos; `twine check` PASSED. No incluye `py.typed` |
| Docs | `sphinx-build -b html -W docs/source` | build OK, pero documenta solo 4 de 15 módulos |
| Seguridad deps | `pip-audit` | Sin avisos para numpy/pandas/matplotlib/plotly. Solo `pip` y `setuptools` del venv |
| CI remoto | `gh api .../actions/runs` | Últimos runs de CI en `main` y del PR: `success`; publicación de `v0.2.8`: `success` |
| Referencias obsoletas | `grep PLACEHOLDER/TU_USUARIO/TODO` | Ninguna |
| Versión | `walopy.__version__` vs `importlib.metadata` | 0.2.8 = 0.2.8 (fuente única en `pyproject.toml`) |
| Tags remotos | `git ls-remote --tags` | v0.2.1, .2, .3, .5, .7, .8. **Faltan v0.2.4 y v0.2.6** |

**Nivel de madurez estimado: 2 — parcial (media 2,4 / 5).**
HECHO: cumple el Nivel 1 (instalable, tests) y partes del Nivel 4 (publicada en PyPI, SemVer, changelog).
No cumple los gates del Nivel 2 del Playbook: ruff y mypy no pasan, cobertura < 85 %, `plotting.py` < 70 %, y el CI no ejecuta linter ni tipos. Es el patrón "CI verde que no verifica lo que el Playbook exige".

## 2. Auditoría por dimensión (Paso 2)

Escala 0–5 como en el SCORECARD de referencia. Riesgo: B/M/A/C = Bajo/Medio/Alto/Crítico.

| # | Dimensión | Nota | Riesgo | Evidencia (HECHO) | Brecha frente al Playbook |
|---|---|---|---|---|---|
| 1 | Estructura del repositorio | 3 | B | `src/` layout, `pyproject.toml`, LICENSE, `.gitignore` correcto, `__all__` completo y sin duplicados, 55 archivos rastreados sin basura | Sin `py.typed`; `description` y `keywords` de `pyproject.toml` solo mencionan colas/OEE/KPI; sin `conftest.py`; sin SECURITY/CoC/templates; sdist sin CHANGELOG |
| 2 | Diseño de API pública | 3 | M | Nombres consistentes; resultados con `summary()`/`to_frame()` en casi todo; 7 de 41 clases sin `to_frame` y 4 sin `summary`; 47 resultados sin `.plot()`; `items: list[dict]` en varias funciones | Contrato de ingesta no uniforme; la documentación describe firmas que no existen (HALLAZGOS K-10) |
| 3 | Validación de entradas | 2 | A | `_utils.py` con 7 validadores. Barrido automático de entradas malformadas sobre 67 funciones (valores NaN/inf/negativos/cero/None/str/1e308/1e-320, listas vacías o con un elemento inválido): 1 248 rechazadas con `ValueError`/`TypeError`; 30 excepciones de otro tipo; 2 bloqueos (hang > 10 s); 68 aceptadas devolviendo NaN/inf (en su mayoría con magnitudes extremas); 26 aceptadas en silencio con NaN/inf/negativos/None/str y resultado finito | Funciones que no pasan por la capa central dejan pasar NaN/inf/negativos (K-01, K-02, N-04); `OverflowError`/`ZeroDivisionError` crudos (K-06, K-07, K-08) |
| 4 | Corrección numérica | 3 | M | 30 comprobaciones contra referencias independientes (scipy, networkx, fuerza bruta, balance de nacimiento-muerte, Cobham, binomial): **todas pasan** (Weibull MLE vs `scipy` error relativo < 2e-6; CPM = camino más largo en 200 DAG aleatorios; Wagner-Whitin y Johnson = óptimo por fuerza bruta) | `mmc` desborda para carga ofrecida ≥ ~140 (K-06); Weibull trunca β a 100 sin avisar (K-05); complejidades documentadas falsas (N-03) |
| 5 | Suite de pruebas | 3 | M | 357 tests, 0 sin aserciones, 69 con nombre de caso borde, estable en 3.9/3.11/mínimos/`-W error` | Cobertura 80 %; `plotting.py` 0 % (un `plot()` roto sin detectar, N-01); CLI 62 %; sin `conftest.py`/fixture de semilla; 0 tests parametrizados; `test_v026.py` nombrado por versión; ningún test ejecuta los ejemplos del README |
| 6 | Tipado estático | 2 | M | 78 errores mypy; 43 F821 por falta de `if TYPE_CHECKING: import pandas/plt/go` en 13 módulos; 24 errores `operator` por `list[dict]` con valores heterogéneos | Sin `py.typed` → los usuarios no reciben los tipos; mypy sin gate en CI |
| 7 | Gestión de dependencias | 3 | B | 4 dependencias, sin scipy; funciona con numpy 2.4/pandas 3.0 (últimas) y con los mínimos declarados; `pip-audit` limpio para dependencias de ejecución | Sin cotas superiores (el Playbook las pide; ver decisión D-3); matplotlib y plotly obligatorios aunque se importan de forma perezosa; `ruff`/`mypy` sin fijar en `dev`; sin `build`/`twine` en `dev` |
| 8 | CI/CD | 2 | A | `ci.yml` ejecuta solo `pytest` en 3.9/3.11/3.13; `publish.yml` con OIDC | Sin ruff, mypy, build, twine, sphinx, cobertura ni `pip-audit`; la matriz omite 3.10 y 3.12 que declara en `classifiers`; la publicación no ejecuta tests ni `twine check`; `attestations: false` como parche |
| 9 | Documentación | 2 | A | README de 1 622 líneas, Sphinx con `-W` OK, CHANGELOG completo. **13 de 61 bloques de código del README fallan** al ejecutarlos; 0 menciones en README/Sphinx de `neh_flowshop`, `abc_*`, `xyz_*`, `mrp`, `cpm`, `pert`, `weibull_analysis`; Sphinx cubre 4/15 módulos; `docs/source/changelog.md` se quedó en 0.1.0 y `conf.py` en `release = "0.1.0"`; 68/70 funciones sin sección `Raises`, 47/70 sin `Examples` | Documentación que contradice al código; sin tests que la protejan |
| 10 | Rendimiento | 1 | M | Sin `benchmarks/`, sin línea base documentada. Medido: `neh_flowshop` n=200,m=10 → 5,3 s; `wagner_whitin` n=1000 → 10,2 s; `monte_carlo_gg1` 1e6 → 0,7 s; `import walopy` 0,32 s | Las complejidades anunciadas (O(n²m), O(n²)) son en realidad O(n³m) y O(n³) (N-03); tamaños sin cota provocan bloqueos (N-06) |
| 11 | Seguridad | 2 | M | Sin `eval`/`exec`/`pickle`/`subprocess`; publicación con OIDC | Sin `SECURITY.md`; sin `pip-audit` en CI; parámetros sin cota que bloquean el proceso (N-06, K-07); `attestations: false` reduce la procedencia de la cadena de suministro |
| 12 | Versionado y releases | 3 | B | Fuente única vía `importlib.metadata`; SemVer; CHANGELOG; release `v0.2.8` publicado por CI | Fallback `__version__ = "0.2.0"` obsoleto (`__init__.py:171`); faltan tags v0.2.4/v0.2.6; sin `twine check` en CI; sin test de igualdad de versión |
| 13 | Comunidad y contribución | 2 | B | `CONTRIBUTING.md` (6 líneas con los comandos), LICENSE MIT | Sin issue/PR templates, código de conducta ni SECURITY |
| 14 | Developer Experience | 2 | M | `pip install -e ".[dev]"` funciona; CLI en `__main__` | `CLAUDE.md` lista 6 de 15 módulos, menciona `cost_kpi_tree` (no existe; es `roi_kpi_tree`) y un checklist de release que manda subir la versión en dos sitios; sin "definición de terminado" ni reglas del catálogo; sin `examples/`; el CLI solo cubre 6 de 70 funciones |
| | **GLOBAL** | **2,4** | | Suma 33 / 14 | |

## 3. Inferencias (no verificadas directamente)

- **INFERENCIA:** los 43 F821 y buena parte de los 24 errores de mypy se deben a que las anotaciones usan `"pd.DataFrame"` como cadena sin importar el nombre bajo `TYPE_CHECKING`; no son errores en tiempo de ejecución (las pruebas pasan). Se corrigen con imports condicionales.
- **INFERENCIA:** el README se generó describiendo una API prevista y no se contrastó con las firmas finales; por eso aparecen parámetros como `max_output`, `target` o `names`.
- **INFERENCIA:** las funciones que fallan en validación son las añadidas en bloques recientes (reliability, project, mrp) y las que reciben listas de diccionarios; las más antiguas usan `_utils`.
- **NO VERIFICADO:** corrección visual de las gráficas (no hay tests ni inspección); comportamiento en Windows/macOS; ejecución local en Python 3.10, 3.12 y 3.13; que el CI de GitHub use las mismas versiones de dependencias que mi entorno; el mismo barrido con matplotlib 3.5/plotly 5.0 sobre los `plot()`.

## 4. Lo que está bien (hechos a preservar)

- Resultados numéricos correctos frente a referencias independientes en los 30 casos probados, incluidas las funciones nuevas de v0.2.8.
- Cero warnings bajo `-W error`; ningún estado global contaminado: `rcParams` idéntico antes y después de ejecutar 19 `plot()` (clase C-07 del catálogo: no se reproduce).
- Compatibilidad real con el rango de versiones declarado (mínimos y máximos).
- `__all__` íntegro, sin duplicados ni símbolos públicos fuera de la lista.
- Fuente única de versión funcionando.
- Los errores explícitos de validación son accionables en las rutas que sí usan `_utils` (p. ej. `System unstable: ρ = 1.667 ≥ 1.  Need λ < μ.`).
