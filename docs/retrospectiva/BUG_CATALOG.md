# BUG_CATALOG — walopy

> Fichas de los bugs corregidos y taxonomía de clases de error. Fuente: `git log` (30 commits hasta `e89f285`), las auditorías de `docs/auditoria/` y esta retrospectiva.
> HECHO = salida de un comando o contenido de un archivo; NO VERIFICADO = no se pudo comprobar. El detalle de las fichas `W-nn` está en
> `docs/referencia/BUG_CATALOG.md` (lo comprueba `tests/test_trazabilidad.py`) y su verificación contra la versión anterior en `tests/regresiones.json`.

## 1. Bugs del historial anterior a la auditoría (`H-nn`)

| ID | Commit | Síntoma | Causa raíz | Test de regresión | Clase |
|---|---|---|---|---|---|
| **H-01** | `f72967a` | El árbol de KPI se modeló como `cost_kpi_tree`; la intención era el árbol de ROI | Error de especificación (la persona usuaria lo corrigió: «Cometí un error era kpi tree ROI») | `tests/test_kpi.py` (existe). Mutación **MU-13** (`revenue - total_cost` → `+`): muerta | C-37 |
| **H-02** | `ea1c050` | `EOQResult.plot()` lanzaba `ImportError` (`plot_eoq` no existía) | Método que importaba una función no implementada; el commit no añadió ningún test | **Faltó hasta v0.3.0**; hoy `test_plot_de_resultado_devuelve_figura[eoq]`. Mutación **MU-12**: muerta | C-15 |
| **H-03** | `ea1c050` | `__version__` leída de `importlib.metadata` («fuente única»): queda congelada al instalar | El «arreglo» introdujo el defecto C-33 | Ver `W-20`; hoy `tests/test_version.py` (3 tests fallan en v0.2.8). Mutación **MU-11**: muerta | C-33 |
| **H-04** | `5dd87c1`, `e068086` | La publicación de v0.2.4 falló; se activó y se retiró `attestations` | Causa raíz no registrada: el mensaje de `e068086` la atribuye a una mala configuración del publicador de confianza (**inferencia del autor, NO VERIFICADO**) | Ninguno posible en pytest (infraestructura) | C-04 |
| **H-05** | `6cd60b4`, `4c6e371`, `0a4d376`/`e553700` | Versiones «ya ocupadas» en PyPI (0.2.2, 0.2.4): saltos de versión y commits de bump duplicados | Se eligió la versión siguiente sin comprobar el estado de PyPI; hoy `pip index versions walopy` no lista 0.2.4 | `make release-check` + guarda en `publish.yml` (comprueban tag == wheel; **no** la disponibilidad en PyPI: NO VERIFICABLE sin red a PyPI en CI) | C-36 |
| **H-06** | `35cc3e5` | El release de v0.2.7 falló (varios mensajes de la persona usuaria) | El diff del commit solo añade `attestations: false` a `pypa/gh-action-pypi-publish`; el log completo del fallo no se conserva (**causa exacta NO VERIFICADA**) | Ninguno posible en pytest | C-04 |
| **H-07** | `35cc3e5` | `exchange_curve` fallaba con lista vacía y con números escritos como texto | Validación ausente en una función nueva | **Faltaba** (solo el contrato cubría la lista vacía); añadidos `test_items_vacios_dan_value_error` y `test_acepta_numeros_escritos_como_texto`. Mutaciones **MU-15** y **MU-16**: muertas | C-01 |

## 2. Bugs corregidos en v0.3.0 (`W-nn`)

Índice (detalle: `docs/referencia/BUG_CATALOG.md`; la columna «Evidencia» es el resultado de `make regresion` contra `v0.2.8`; «Mutante» es `make mutaciones`).

| ID | Resumen | Clase | Evidencia en v0.2.8 | Mutante |
|---|---|---|---|---|
| W-01 | CPM/PERT aceptan duraciones NaN/inf | C-09 | 5 fallan + 2 guardas | MU-01 |
| W-02 | `t` y `mttr` sin validar en confiabilidad (R(t) > 1) | C-09 | 32 + 1 | MU-10 |
| W-03 | `mrp` con existencia inicial NaN/negativa | C-09 | 4 | MU-01 |
| W-04 | Weibull acepta tiempos NaN/inf (`OverflowError`) | C-09 | 2 | MU-01 |
| W-05 | `cv2_*`, `break_even_multi`, `queue_length_pmf`, `sojourn_cdf` sin validar | C-14 | 14 + 2 | — |
| W-06 | `items` mal formados en ABC/MRP: `KeyError`/`AttributeError` | C-01 | 3 | — |
| W-07 | ABC rechaza artículos con demanda 0 | C-02 | 1 + 1 | MU-09 |
| W-08 | Weibull con datos constantes: β = 100 sin aviso | C-16 | 3 | — |
| W-09 | `mmc` desborda con c ≳ 143 | C-12 | 11 | MU-03 |
| W-10 | `eoq_multi_constrained(budget ≤ 0)` se cuelga | C-18 | 7 + 1 | — |
| W-11 | Listas vacías → `ZeroDivisionError`/`IndexError` | C-01 | 5 + 2 | — |
| W-12 | `break_even_sales(...).plot()` → `KeyError` | C-15 | 3 | MU-07 |
| W-13 | `wagner_whitin` y `neh_flowshop` cúbicos | C-11 | 2 | — |
| W-14 | CPM fusiona actividades con el mismo nombre | C-13 | 3 | MU-04 |
| W-15 | `abc_xyz` empareja por nombre | C-13 | 1 | — |
| W-16 | MRP descarta liberaciones vencidas sin aviso | C-16 | 1 | MU-05 |
| W-17 | Tamaños sin cota bloquean el proceso | C-18 | 6 + 2 y 1 | MU-14 |
| W-18 | `bool` aceptado como número/entero | C-01 | 2 | MU-02 |
| W-19 | `-0.0` en holguras | C-26 | 1 | MU-06 |
| W-20 | `__version__` congelada en los metadatos | C-33 | 3 | MU-11 |
| W-21 | `batch_model` oculta errores sin opción | C-29 | 2 + 1 | MU-08 |
| W-22 | Funciones públicas sin contrato de entradas | C-14 | 57 + 10 | — |
| W-23 | README y doctests con API inexistente | C-10, C-19 | sin selector (gate) | — |
| W-24 | CI sin gates | C-15 | sin selector (gate de CI) | — |
| W-25 | 524 textos en inglés visibles | C-30 | 15 + 1 | — |

Totales verificados: 25 bugs; 23 con selectores de pytest que fallan en `v0.2.8` (24 selectores, 0 problemas); 17 mutantes de una línea, 17 muertos (MU-17 tras ampliar un test).

## 3. Defectos hallados en esta retrospectiva (`D-nn`; en `src/` solo se tocó la fuente de la versión, C-33)

| ID | Hallazgo | Evidencia | Estado |
|---|---|---|---|
| D-01 | Cuatro variantes del comando de `ruff` (PR template, `publish.yml` y la «definición de terminado» usaban `src/ tests/`; el CI, `CLAUDE.md` y `CONTRIBUTING` los cinco directorios) | `grep -rn "ruff check"` | Corregido: todo usa `make lint` |
| D-02 | La regla R-07 pedía `plt.rc_context` y `plotting.py` no lo usa (0 apariciones); el invariante real (no tocar `rcParams`) solo se probaba en 2 de 15 gráficas | `grep -c rc_context src/walopy/plotting.py` → 0 | Corregido: regla reescrita y test ampliado a las 15 |
| D-03 | La nota del CHANGELOG `[0.3.0]` afirmaba que `0.2.4` se había publicado | `pip index versions walopy` no lista 0.2.4 | Corregido en `[Sin publicar]` |
| D-04 | Entornos con metadatos obsoletos: `walopy.__version__` = 0.3.0 y `importlib.metadata.version` = 0.2.8 en dos venv de prueba; `test_version_coincide_con_metadatos` lo detectó | salida de pytest en `v39` y `vlow` | Reinstalados; ejemplo vivo de C-33 |
| D-05 | El CI ejecuta cada commit dos veces (evento `push` a `claude/**` y evento `pull_request`) | 28 checks en el PR #15 (dos ejecuciones) | **Sin corregir** (cambia `ci.yml`); propuesta: `concurrency` o limitar `push` a `main` |
| D-06 | El mutante MU-17 (una gráfica fija `rcParams["font.size"]`) **sobrevivió**: `test_plot_no_modifica_rcparams` solo recorría los resultados con `.plot()` y no `plot_queue_metrics` ni otras tres gráficas de llamada directa | `python scripts/verificar_mutaciones.py MU-17` → SOBREVIVE | Corregido: `test_plot_directa_no_modifica_rcparams` ×4; MU-17 muere |
| D-07 | `test_cada_bug_tiene_ficha_en_el_catalogo` aceptaba el identificador `W-nn` en cualquier parte del documento: al borrar las 25 fichas solo fallaban 6 tests (los demás IDs aparecían en la taxonomía) | prueba en una copia: 6 fallos → 25 tras corregir | Corregido: exige la fila `\| **W-nn** \|` de la ficha |

## 4. Taxonomía de clases de error

| Clase | Descripción | Cómo prevenirla | Cómo detectarla | Bugs |
|---|---|---|---|---|
| **C-01 Validación de entrada faltante** | La función acepta datos inválidos y falla aguas abajo con un error opaco | Capa de validación central; tests de entradas malformadas | Barrido de contrato | W-06, W-11, W-18, H-07 |
| **C-02 Caso degenerado no considerado** | La API no contempló valores extremos válidos (demanda 0, datos constantes) | Listar los casos degenerados al diseñar | Tests parametrizados con límites | W-07 |
| **C-04 CI/publicación que falla por diferencias de entorno** | Local pasa; la publicación o el CI fallan por configuración externa | Ensayo de publicación en TestPyPI; guarda de versión | Logs de CI | H-04, H-06 |
| **C-09 NaN pasa las comparaciones** | `x <= 0` es `False` para NaN | `isfinite` antes de comparar | Barrido con `nan`, `inf` | W-01…W-04 |
| **C-10 Documentación con API inventada** | Ejemplos que nunca se ejecutaron | Ejemplos como tests | Ejecutar los bloques | W-23 |
| **C-11 Complejidad documentada ≠ real** | O(n²) anunciado, O(n³) real | Medir con n creciente | Test de tiempo | W-13 |
| **C-12 Desbordamiento por fórmula directa** | `a**n / n!` | Recurrencias estables | Prueba a escala 10× | W-09 |
| **C-13 Duplicados fusionados en silencio** | Lista de dicts volcada a `dict` | Rechazar duplicados | Test con nombres repetidos | W-14, W-15 |
| **C-14 Validación solo en parte de las rutas** | Hay capa central pero rutas que no la usan | Barrido sobre `__all__` | Test de contrato | W-05, W-22 |
| **C-15 Código sin test / CI que no verifica** | Funciones o gates sin comprobación automática | Cobertura por módulo; gates en CI | `make cov`, `make check` | H-02, W-12, W-24 |
| **C-16 Recorte o descarte silencioso** | Cota fija o datos fuera de horizonte descartados sin aviso | `UserWarning` o error | Datos degenerados | W-08, W-16 |
| **C-18 Parámetros sin cota → bloqueo** | Tamaños o presupuestos sin límite | Cotas `MAX_*` y límites de iteración | Barrido con 1e7, 1e9 | W-10, W-17 |
| **C-19 Doctests que nunca se ejecutan** | `--doctest-modules` desactivado | Activarlo desde el primer ejemplo | `test_los_doctests_estan_activos` | W-23 |
| **C-26 `-0.0` en resultados** | `round(-1e-16, 10)` → `-0.0` | `+ 0.0` tras redondear | `copysign` | W-19 |
| **C-28 Rama creada desde una base antigua / ref desactualizada** | Conflictos en el PR; `git fetch origin main` deja `origin/main` viejo | `git fetch origin +refs/heads/main:refs/remotes/origin/main` y `merge-base --is-ancestor` | R-17 | (ver LESSONS L-08) |
| **C-29 Captura amplia que oculta errores** | `except Exception` sin opción de propagar | Parámetro `errors=` | Test con función que lanza | W-21 |
| **C-30 Política de texto sin comprobación** | «Español en lo que ve el usuario» sin test | `tests/test_idioma.py` | El propio test | W-25 |
| **C-31 Reemplazo global sin contexto** | Un glosario cambió una clave de datos y un valor de ejemplo | Separar claves de datos de cabeceras mostradas; revisar el diff | La suite | — |
| **C-32 Test de regresión que no falla en el código anterior** | Tests que pasan también sin el fix | `make regresion` y `make mutaciones` | Los propios scripts | W-19, W-20 |
| **C-33 Versión congelada en los metadatos de instalación** | `importlib.metadata.version()` en `__init__.py`: tras subir la versión, `__version__` muestra la anterior hasta reinstalar | Literal en `__init__.py` + `[tool.setuptools.dynamic]` | `tests/test_version.py`; reproducido: pyproject 0.3.1 → `__version__` 0.3.0 | H-03, W-20 |
| **C-34 Un comando de verificación, cuatro variantes** | El mismo gate escrito distinto en CI, publish, PR template y CLAUDE.md | Un único `Makefile`; los demás lo invocan | `grep` de cada comando | D-01 |
| **C-35 Regla documentada que el código no cumple** | R-07 exigía `rc_context`; el código usa otro mecanismo | Probar cada regla contra el repo antes de adoptarla | `grep` + test del invariante | D-02 |
| **C-36 Versión de release elegida sin comprobar el estado de PyPI / tag antes de subir la versión** | `400 File exists`, versiones «ocupadas», saltos de versión | `make release-check`; ensayo en TestPyPI | `pip index versions`, `release-check` | H-05 |
| **C-37 Error de especificación** | Se implementa lo que se pidió, no lo que se quería | Confirmar la intención con un ejemplo antes de implementar | Revisión de la persona usuaria | H-01 |
| *C-03, C-05…C-08, C-17, C-20…C-25, C-27* | Ver `docs/referencia/BUG_CATALOG.md` (importación opcional, documentación desactualizada, efectos de refactor, estado global, fuente múltiple de versión, funcionalidad sin documentar, bordes numéricos en ejemplos, empates, referencias externas imprecisas, nombres que colisionan, metadatos obsoletos, comprobaciones que se autodetectan, `!` en shell) | | | |
