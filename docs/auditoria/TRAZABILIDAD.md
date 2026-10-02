# TRAZABILIDAD — bug → test de regresión → catálogo → Playbook → CLAUDE.md

> Revisión de los cambios desde el último tag (`v0.2.8`, `2cc17c1`) hasta `HEAD` (v0.3.0 en preparación). Fecha: 2026-10-02.
> Evidencia reproducible: `python scripts/verificar_regresion.py --manifiesto tests/regresiones.json` (ejecuta los tests **actuales** contra el código de `v0.2.8` y exige que fallen; también corre en el CI).

## Resultado de la revisión

| Comprobación | Resultado |
|---|---|
| Bugs corregidos desde `v0.2.8` | **25** (`W-01`…`W-25`) |
| Con test de regresión que **falla en `v0.2.8`** | **23** (24 selectores de pytest; todos verificados con el script, 0 problemas) |
| Sin selector de pytest (evidencia de otro tipo) | **2**: W-23 (README/doctests: se ejecutan en cada `pytest`) y W-24 (gates del CI) |
| Con ficha en `BUG_CATALOG.md` | **25 de 25** (lo comprueba `tests/test_trazabilidad.py`) |
| Lección transferible en `PLAYBOOK.md` | **25 de 25** (ver columna) |
| Con regla en `CLAUDE.md` | **22 de 25**; W-08, W-16 y W-21 quedan solo en Playbook por decisión razonada (`REGLAS_PROPUESTAS.md`, candidatas 11–12) |

### Defectos de trazabilidad encontrados y corregidos en esta revisión

1. **Dos tests de regresión no protegían nada** (W-19 `-0.0` y W-20 `__version__` sin instalar): pasaban también con el código antiguo. Se reforzaron antes (la comprobación manual contra `v0.2.8` los delató) y ahora los cubre el script.
2. **Tests que «pasan» en `v0.2.8` a propósito** (guardas): 23 en total, por ejemplo W-01 (`pert` ya rechazaba NaN/inf), W-07 (todo cero ya daba `ValueError`), W-22 (10 funciones ya cumplían el contrato). Cada guarda está declarada en el manifiesto; si un test nuevo pasa en el tag anterior sin estar declarado, el script falla.
3. **Fichas ausentes:** el catálogo (heredado de otro proyecto) no tenía ninguna ficha de walopy; se añadieron `W-01`…`W-25` y las clases `C-09`…`C-32`.
4. **Texto en inglés que escapó a la traducción manual** (`queuing.py:124`, `network.py:146`): lo detectó el test nuevo `tests/test_idioma.py` (W-25).
5. **Palabra muerta en un selector** (`mmc_rechaza`): la detectó `test_trazabilidad.py`.

## Tabla de trazabilidad

| ID | Hallazgo | Bug | Módulo del fix | Test de regresión | Evidencia en `v0.2.8` | Catálogo | Playbook | `CLAUDE.md` |
|---|---|---|---|---|---|---|---|---|
| **W-01** | K-01 | CPM/PERT aceptan duraciones NaN/inf | project.py | `tests/regresiones.json` (1 selector) | **5** fallan en `v0.2.8` + 2 guardas | `BUG_CATALOG` W-01 | Validación → NaN antes de comparar | R-08 |
| **W-02** | K-01 | reliability: t y mttr sin validar (NaN, negativos) | reliability.py | `tests/regresiones.json` (1 selector) | **32** fallan en `v0.2.8` + 1 guardas | `BUG_CATALOG` W-02 | Validación → NaN antes de comparar | R-08 |
| **W-03** | K-01 | mrp: existencia inicial NaN/negativa | inventory.py (MRP) | `tests/regresiones.json` (1 selector) | **4** fallan en `v0.2.8` | `BUG_CATALOG` W-03 | Validación → NaN antes de comparar | R-08 |
| **W-04** | K-01 | Weibull acepta tiempos NaN/inf | reliability.py (Weibull) | `tests/regresiones.json` (1 selector) | **2** fallan en `v0.2.8` | `BUG_CATALOG` W-04 | Validación → NaN antes de comparar | R-08 |
| **W-05** | K-02 | cv2_*, break_even_multi, pmf y sojourn sin validar | queuing.py, advanced.py | `tests/regresiones.json` (1 selector) | **14** fallan en `v0.2.8` + 2 guardas | `BUG_CATALOG` W-05 | Validación → barrido de contrato | R-08, R-13 |
| **W-06** | K-03 | ABC/MRP: entradas mal formadas dan errores crípticos | inventory.py | `tests/regresiones.json` (1 selector) | **3** fallan en `v0.2.8` | `BUG_CATALOG` W-06 | Validación → listas de registros | R-08, R-11 |
| **W-07** | K-04 | ABC: demanda 0 rechazada o clase C inconsistente | inventory.py (ABC) | `tests/regresiones.json` (1 selector) | **1** fallan en `v0.2.8` + 1 guardas | `BUG_CATALOG` W-07 | Casos borde (caso degenerado válido) | R-11 |
| **W-08** | K-05 | Weibull: datos constantes / cota de β sin aviso | reliability.py | `tests/regresiones.json` (1 selector) | **3** fallan en `v0.2.8` | `BUG_CATALOG` W-08 | Validación → nada se recorta en silencio | — (solo Playbook; R-11 cubre el test) |
| **W-09** | K-06 | mmc: OverflowError con muchos servidores | queuing.py (`mmc`) | `tests/regresiones.json` (1 selector) | **11** fallan en `v0.2.8` | `BUG_CATALOG` W-09 | Casos borde → caso a escala | R-11, R-14 |
| **W-10** | K-07 | eoq_multi_constrained: presupuesto inválido cuelga la bisección | inventory.py | `tests/regresiones.json` (1 selector) | **7** fallan en `v0.2.8` + 1 guardas | `BUG_CATALOG` W-10 | Validación → cotas de tamaño | R-08 |
| **W-11** | K-08 / N-09 | listas vacías: IndexError/ZeroDivisionError en lugar de ValueError | reliability.py, inventory.py | `tests/regresiones.json` (1 selector) | **5** fallan en `v0.2.8` + 2 guardas | `BUG_CATALOG` W-11 | Validación → barrido de contrato | R-11 |
| **W-12** | N-01 | plot_break_even ignora break_even_sales | plotting.py | `tests/regresiones.json` (1 selector) | **3** fallan en `v0.2.8` | `BUG_CATALOG` W-12 | Cobertura por módulo | Definición de «terminado» (5) |
| **W-13** | N-03 | Complejidad: Wagner-Whitin O(n³), NEH O(n³m) | inventory.py, scheduling.py | `tests/regresiones.json` (1 selector) | **2** fallan en `v0.2.8` | `BUG_CATALOG` W-13 | Rendimiento → complejidad verificada | R-14 |
| **W-14** | N-04 | CPM acepta actividades duplicadas/incompletas | project.py | `tests/regresiones.json` (1 selector) | **3** fallan en `v0.2.8` | `BUG_CATALOG` W-14 | Validación → duplicados | R-08 |
| **W-15** | N-04 | abc_xyz empareja por nombre con nombres repetidos | inventory.py (`abc_xyz`) | `tests/regresiones.json` (1 selector) | **1** fallan en `v0.2.8` | `BUG_CATALOG` W-15 | Validación → duplicados | R-08 |
| **W-16** | N-05 | MRP: liberaciones vencidas sin aviso | inventory.py (MRP) | `tests/regresiones.json` (1 selector) | **1** fallan en `v0.2.8` | `BUG_CATALOG` W-16 | Validación → nada se recorta en silencio | — (solo Playbook) |
| **W-17** | N-06 | Tamaños absurdos (c, n_max, t_max) agotan memoria/tiempo | `_utils.py`, queuing.py, advanced.py | `tests/regresiones.json` (2 selectores) | **7** fallan en `v0.2.8` + 2 guardas | `BUG_CATALOG` W-17 | Validación → cotas de tamaño | R-08 |
| **W-18** | N-07 | bool aceptado como número/entero | `_utils.py` | `tests/regresiones.json` (1 selector) | **2** fallan en `v0.2.8` | `BUG_CATALOG` W-18 | Validación → NaN antes de comparar (`bool`) | R-08 |
| **W-19** | — (hallado al reforzar tests) | -0.0 en holguras de CPM/PERT | project.py | `tests/regresiones.json` (1 selector) | **1** fallan en `v0.2.8` | `BUG_CATALOG` W-19 | Casos borde → sin `-0.0` | R-16 |
| **W-20** | K-13 | __version__ sin fallback si el paquete no está instalado | `__init__.py` | `tests/regresiones.json` (1 selector) | **1** fallan en `v0.2.8` | `BUG_CATALOG` W-20 | Versionado → fallback de versión | R-05, R-16 |
| **W-21** | N-14 | batch_model oculta errores sin opción de propagarlos | solver.py | `tests/regresiones.json` (1 selector) | **2** fallan en `v0.2.8` + 1 guardas | `BUG_CATALOG` W-21 | Consistencia de API → capturas amplias | — (solo Playbook) |
| **W-22** | K-01…K-03 | Funciones públicas sin contrato de entradas homogéneo | toda la API | `tests/regresiones.json` (1 selector) | **57** fallan en `v0.2.8` + 10 guardas | `BUG_CATALOG` W-22 | Validación → barrido de contrato | R-13 |
| **W-23** | K-10 | README y doctests con API inexistente o valores inventados | README, docstrings | — (gate de CI/documentación) | n/a: 13 de 61 bloques del README y 6 de 23 doctests fallaban al ejecutarlos; los tests tests/test_readme.py y --doctest-modules los ejecutan desde entonces | `BUG_CATALOG` W-23 | Documentación → ejemplos son tests | R-15 |
| **W-24** | K-11, K-12, N-02 | CI sin gates (ruff, mypy, build, docs, cobertura) y publicación sin tests | `.github/workflows/`, typing | — (gate de CI/documentación) | n/a: gates del CI (.github/workflows/ci.yml y publish.yml); no son tests de pytest | `BUG_CATALOG` W-24 | CI básico → gates en el CI | Definición de «terminado» |
| **W-25** | N-12 | Texto visible en inglés (524 hallazgos en v0.2.8) | todos los módulos | `tests/regresiones.json` (1 selector) | **15** fallan en `v0.2.8` + 1 guardas | `BUG_CATALOG` W-25 | Consistencia de API → idioma comprobado | R-03 |

## Bugs pendientes o no abordados (sin test de regresión a propósito)

| Hallazgo | Motivo |
|---|---|
| K-08 (magnitudes extremas 1e308 / 1e-320) | Se aceptan sin `ValueError`; impacto bajo y fuera del contrato (decisión registrada en `SCORECARD.md`). |
| N-08, N-10, N-11, N-13, N-15, N-16 | No son bugs de comportamiento (código muerto, metadatos, higiene de tests, dependencias, comunidad, docstrings); los cubren gates de CI (ruff, mypy, `twine check`, test de `Raises`/`Examples`). |
| K-09 (`CLAUDE.md` desactualizado) | Lo cubre el paso «referencias obsoletas» del CI. |

## Cómo mantenerlo (R-16)

1. Al corregir un bug: añadir una entrada `W-nn` (siguiente número) a `tests/regresiones.json` con `ref` = último tag.
2. Añadir la ficha `W-nn` a `docs/referencia/BUG_CATALOG.md` (y la clase `C-nn` si es nueva).
3. Ejecutar `python scripts/verificar_regresion.py --manifiesto tests/regresiones.json`; si un test pasa en `ref`, reforzarlo o declararlo guarda.
4. Si la lección es transferible: una línea en `docs/referencia/PLAYBOOK.md`; si cambia cómo se trabaja: una regla en `CLAUDE.md`.
