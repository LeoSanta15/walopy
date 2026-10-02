# REGLAS_PROPUESTAS — candidatas a `CLAUDE.md`, evaluadas y probadas

> Criterio: una regla solo entra en `CLAUDE.md` si (1) responde a un fallo **observado** en este proyecto, (2) se puede **comprobar con una orden o un test**,
> (3) esa comprobación **señala el problema** en el código anterior (control negativo) y **pasa** en el actual, y (4) no duplica otra regla.
> Fecha: 2026-10-02. Referencia de «código anterior»: tag `v0.2.8` (`2cc17c1`).

## Resumen

| # | Candidata | Origen | Decisión | Dónde queda |
|---|---|---|---|---|
| 1 | Todo bug corregido deja tres huellas (test que falla en el tag anterior + ficha + lección transferible) | C-32 (dos tests no protegían nada) | **Aplicada: R-16** | `CLAUDE.md`, `tests/regresiones.json`, `scripts/verificar_regresion.py`, `tests/test_trazabilidad.py`, job `regresion` |
| 2 | El texto visible está en español, **comprobado** por un test | C-30 (524 hallazgos; 2 escaparon a la traducción manual) | **Aplicada: refuerzo de R-03** | `tests/test_idioma.py` |
| 3 | Cabeceras mostradas ≠ claves de datos | C-31 | **Aplicada dentro de R-03** | `CLAUDE.md` (R-03) |
| 4 | Los doctests de `src/` están activos | C-19 (6 de 23 rotos) | **Aplicada: refuerzo de R-15** | `tests/test_trazabilidad.py::test_los_doctests_estan_activos` |
| 5 | Cada rama parte de `origin/main` actualizado | C-28 (conflictos en 6 archivos) | **Aplicada: R-17** | `CLAUDE.md`, plantilla de PR |
| 6 | Cotas de tamaño y validación de registros (duplicados, claves) como parte de R-08 | C-13, C-18 | **Aplicada dentro de R-08** | `CLAUDE.md` (R-08), contrato + manifiesto |
| 7 | Plantilla de PR con la lista de huellas del bug | R-16 | **Aplicada** (plantilla, no regla) | `.github/PULL_REQUEST_TEMPLATE.md` |
| 8 | Lint estático «todo parámetro de tamaño pasa por `as_int_positive(max=…)`» | C-18 | **Rechazada** | — |
| 9 | «Caso a escala 10× en cada función» como regla | C-12 | **Rechazada como regla** (queda en el Playbook) | `PLAYBOOK.md` |
| 10 | Resolver empates de heurísticas con tolerancia relativa | C-21 | **Rechazada** (lección, no regla) | `BUG_CATALOG.md` C-21 |
| 11 | Reemplazos masivos solo con revisión del diff | C-31 | **Rechazada como regla** (queda en el Playbook) | `PLAYBOOK.md` |
| 12 | «Avisar en vez de recortar/descartar en silencio» | C-16 | **Rechazada como regla** (queda en el Playbook) | `PLAYBOOK.md` |

## Análisis y pruebas por candidata

### 1 · R-16 — Todo bug corregido deja tres huellas — APLICADA
- **Problema real:** al revisar los tests de regresión descubrí que dos de ellos (`-0.0` en holguras y el fallback de `__version__`) **también pasaban con el código antiguo**: daban sensación de cobertura sin proteger nada (C-32).
- **Diseño:** `tests/regresiones.json` registra por bug: `W-nn`, `ref` (tag que aún lo tenía), selectores de pytest y *guardas* (tests que pasan a propósito en `ref`). `scripts/verificar_regresion.py` crea un `git worktree` de `ref`, ejecuta los tests **actuales** contra el código **antiguo** (con `match=` eliminado, porque los mensajes cambiaron de idioma) y exige que fallen. `tests/test_trazabilidad.py` comprueba que cada `W-nn` tiene ficha en el catálogo y que cada selector apunta a tests que existen.
- **Pruebas:**
  - Contra `v0.2.8`: **25 entradas, 0 problemas** (23 con selectores de pytest + 2 de evidencia: W-23 y W-24); p. ej. W-09 → 11 de 11 tests fallan, W-22 → 57 fallan y 10 son guardas declaradas.
  - Control negativo: un manifiesto con un test que no depende del bug (`test_version_tiene_formato_semver`) → el script sale con **código 1** y señala el test.
  - `test_trazabilidad.py` falló 25 veces mientras el catálogo no tenía las fichas `W-nn` (control negativo natural) y pasa ahora; además detectó una palabra muerta en mi propio manifiesto (`mmc_rechaza`, que no coincidía con ningún test del archivo).
  - Refinamientos que salieron de la prueba: ejecutar **sin `-x`** para ver cada test; `pytest-timeout` para los bloqueos (`budget=-1`); quitar `match=` (con él, un test «fallaba» solo por el idioma del mensaje); `ref` por entrada (si no, al publicar `v0.3.0` el «último tag» ya tendría el fix y todo pasaría).
- **Coste:** ~2 min en el CI (job independiente). **Falsos positivos:** ninguno tras declarar las guardas (cada una está justificada: el código antiguo ya rechazaba esa entrada).

### 2 · Refuerzo de R-03 — `tests/test_idioma.py` — APLICADA
- **Problema real:** la política «español en lo que ve el usuario» existía (R-03) pero nada la comprobaba; tras traducir a mano quedaron **dos docstrings en inglés** (`queuing.py:124` «If zero or more than one variable is None», `network.py:146`) que solo vio el test nuevo.
- **Diseño:** recorre con `ast` los mensajes de `raise`, los `warnings.warn` y los docstrings; marca palabras inequívocamente inglesas (`the, of, and, with, must, should…`). Excluye bloques `>>>`, encabezados numpydoc, líneas de tipo (`x : sequence of float`), código en línea y términos con guion (*Head-of-Line*).
- **Pruebas:** `v0.2.8` → **524 hallazgos**; `HEAD` → **0**; dos controles dentro del propio test (uno malo que debe señalar los 3 tipos de texto y uno bueno que no debe señalar nada).
- **Falsos positivos descartados al probar:** tipos numpydoc, `k-of-n`, *Head-of-Line* (ya contemplados). **Limitación:** no detecta inglés sin palabras de la lista; es una red de seguridad, no una garantía.

### 3 · Cabeceras mostradas ≠ claves de datos (dentro de R-03) — APLICADA
- Un glosario global cambió la clave `"method"` y un valor `"Name"` (C-31). La regla no es comprobable por sí sola, pero la distinción se escribió en R-03 y la protege la suite (`tests/test_contrato_entradas.py`, `test_readme.py`): reproduje el error original y la suite lo señala.

### 4 · Refuerzo de R-15 — doctests activos — APLICADA
- Con `--doctest-modules` desactivado, 6 de 23 doctests de `v0.2.8` estaban rotos y nadie lo vio. Prueba: `pytest --doctest-modules src/walopy` sobre `v0.2.8` → **6 fallos, 17 aciertos**; sobre `HEAD`, 70 doctests pasan. `test_los_doctests_estan_activos` falla si se quita la opción de `pyproject.toml`.

### 5 · R-17 — rama desde `origin/main` — APLICADA
- **Problema real:** la rama partía de v0.2.0 y el PR de v0.2.8 tuvo conflictos en 6 archivos resueltos en dos rondas (L-16).
- **Prueba:** `git merge-base --is-ancestor origin/main HEAD` → código **0** en la rama actual; sobre `v0.2.8` (simula una rama vieja) → código **1**. Se añadió a la plantilla de PR.
- **Límite:** tras un merge *squash* el commit de `main` no está en el historial de la rama, así que la comprobación obliga a reiniciarla desde `main` (es el comportamiento buscado).

### 6 · R-08 ampliada (cotas y registros) — APLICADA
- Respaldada por tests que ya fallan en `v0.2.8` (W-10, W-14, W-15, W-17 en el manifiesto) y por el contrato de entradas (67 funciones). No se creó una regla aparte para no duplicar R-08/R-11.

### 7 · Plantilla de PR — APLICADA
- Se añadió la verificación de R-16 y R-17 a la lista «terminado». No es regla de `CLAUDE.md`; es el recordatorio en el momento en que se abre el PR.

### 8 · Lint estático de parámetros de tamaño — RECHAZADA
- Identificar «un parámetro que dimensiona un cálculo» por AST es heurístico (falsos positivos con `n`, `k`, `c`), y el barrido dinámico del contrato (valores 1e7/1e9 con límite de tiempo) ya detecta los casos reales. Coste alto, beneficio duplicado.

### 9 · «Caso a escala 10×» como regla — RECHAZADA COMO REGLA
- Es una buena práctica (C-12), pero no hay forma mecánica de decir qué es «10× el caso típico» en cada función; R-14 (complejidad con benchmark) y R-11 (casos borde) cubren lo comprobable. Queda en el Playbook (casos borde).

### 10 · Tolerancia en empates — RECHAZADA
- Es una lección específica de NEH y de heurísticas con desempates; una regla general («siempre tolerancia 1e-12») sería incorrecta para otros algoritmos. Queda como clase C-21.

### 11 · Reemplazos masivos con revisión — RECHAZADA COMO REGLA
- No es comprobable; el control real es la suite completa tras cada paso (ya en la definición de «terminado»). Queda en el Playbook y como clase C-31.

### 12 · «Avisar en vez de recortar» — RECHAZADA COMO REGLA
- Decisión de diseño que depende de cada algoritmo; no hay comprobación mecánica general. Cada caso concreto (W-08, W-16) tiene su test; la guía general queda en el Playbook.

## Resultado

`CLAUDE.md` pasa de **15 a 17 reglas** (R-16, R-17) y refuerza R-03, R-08, R-10 y R-15. Las cuatro que no se aplicaron como regla quedan documentadas en el catálogo y el Playbook con su motivo.
