# CLAUDE_MD_RULES — reglas de `CLAUDE.md` probadas contra este repo

> Criterio de adopción (procedimiento): una regla se declara «no negociable» solo si (1) responde a un fallo observado, (2) se comprueba con una orden o un test,
> (3) esa comprobación **pasa** en el repo actual y **señala** el problema cuando se introduce (control negativo). Las que no cumplen (2) se etiquetan `[guía]`.
> Fecha de las pruebas: 2026-10-02, sobre la rama de trabajo (`e89f285` + infraestructura). Python 3.11 (y 3.9 / mínimos donde se indica).

## Resultado por regla

| Regla | Etiqueta | Origen (fallo observado) | Comprobación | Pasa en el repo | Control negativo (¿señala el problema?) |
|---|---|---|---|---|---|
| R-01 Cambios quirúrgicos | guía | — (criterio de revisión) | no mecánica | n/a | n/a |
| R-02 Validar contra referencia independiente | test | `mmc` desbordaba y nadie lo vio (W-09) | `tests/test_referencias_externas.py`, `tests/test_mmc_estable.py` | ✅ | ✅ MU-03 (recurrencia rota) muere; 11 tests fallan en v0.2.8 |
| R-03 Español en lo visible | test | 524 textos en inglés (W-25); 2 escaparon a la traducción manual | `tests/test_idioma.py` | ✅ 0 hallazgos | ✅ 524 hallazgos en v0.2.8; el test lleva su propio control negativo |
| R-04 Avances incrementales | comando | tag creado antes de subir la versión → artefactos viejos | `make release-check TAG=vX.Y.Z` | ✅ `v0.3.0` correcto | ✅ `TAG=v0.3.1` → código 2 y mensaje; sin `TAG` → código 2 |
| R-05 Fuente única de versión | test | `__version__` congelada (W-20/C-33) | `tests/test_version.py` | ✅ | ✅ MU-11 muere; 3 tests fallan en v0.2.8; reproducido: pyproject 0.3.1 → `__version__` 0.3.0 con metadatos |
| R-06 Dependencias opcionales | guía | — (hoy no hay extras: matplotlib y plotly son obligatorias) | no aplica | n/a | n/a |
| R-07 No contaminar estado global | test | regla inexacta (pedía `rc_context`, que no se usa) | `test_plot_no_modifica_rcparams` ×15 y `test_plot_directa_no_modifica_rcparams` ×4 | ✅ | ✅ MU-17 (una gráfica fija `font.size`): **sobrevivió** al principio (el test no cubría `plot_queue_metrics`), se amplió el test y ahora muere |
| R-08 Validación centralizada | test | W-01…W-05, W-18 | `tests/test_contrato_entradas.py` + `tests/test_regresion_validacion.py` | ✅ | ✅ MU-01, MU-02, MU-10 mueren; 57 + decenas de tests fallan en v0.2.8 |
| R-09 Checklist de renombre | comando | `cost_kpi_tree` (H-01) | `make obsoletas` | ✅ | ✅ inyectar `TU_USUARIO` en el README → código 2 |
| R-10 No repetir bugs del catálogo | guía | — | no mecánica | n/a | n/a |
| R-11 Tests de casos borde | test | W-06, W-07, W-11 | contrato + `tests/test_regresion_validacion.py` | ✅ (parcial: comprueba el barrido, no que cada función nueva tenga su test propio) | ✅ MU-09 muere |
| R-12 CI en versión mínima | CI | — | job «Tests con dependencias mínimas» y matriz 3.9–3.13; local: 3.9 | ✅ 3.9 y mínimos (numpy 1.22, pandas 1.4): 1 288 tests en cada uno | NO PROBADO (sin control negativo propio; la comprobación es la matriz del CI) |
| R-13 Símbolos en `__all__` documentados | test | K-11 (8 funciones sin documentar) | `tests/test_documentacion.py` | ✅ | ✅ quitar `wagner_whitin` de `inventory.rst` → falla `test_simbolo_publico_en_la_referencia_sphinx[wagner_whitin]` |
| R-14 Complejidad con benchmark | test | W-13 (O(n³) frente a O(n²) anunciado) | `tests/test_complejidad.py` (solo Wagner-Whitin y NEH) | ✅ | ✅ 2 tests fallan en v0.2.8. **Limitación:** la regla es general y solo dos algoritmos tienen test de tiempo |
| R-15 Ejemplos y doctests son tests | test | W-23 (13/61 README, 6/23 doctests rotos) | `tests/test_readme.py`, `tests/test_ejemplos.py`, `--doctest-modules` | ✅ 61 bloques, 5 ejemplos, 70 doctests | ✅ 6 doctests fallan en v0.2.8; `test_los_doctests_estan_activos` falla si se quita la opción |
| R-16 Bug corregido → 3 huellas | test | C-32 (tests que no fallaban sin el fix) | `tests/test_trazabilidad.py`, `make regresion`, `make mutaciones` | ✅ 24/24 selectores; 17/17 mutantes | ✅ un test independiente del bug en el manifiesto → código 1; quitar las 25 fichas `W-nn` del catálogo → 25 fallos de `test_trazabilidad` (con la versión anterior del test solo fallaban 6: ver D-07 en `BUG_CATALOG.md`) |
| R-17 Rama desde `origin/main` | comando | conflictos en 6 archivos; `origin/main` desactualizado | `git merge-base --is-ancestor origin/main HEAD` | ✅ código 0 | ✅ sobre `v0.2.8` (rama vieja) → código 1 |
| R-18 No cambiar versiones de acciones por intuición | guía | arreglo de v0.2.7 sin ver el log | no mecánica | n/a | n/a |

## Reglas con límites declarados
- **R-11** y **R-14** son más amplias que su comprobación (ver columnas). No se declaran «no negociables» sin esa salvedad.
- **R-06** queda vacía mientras no existan extras; si se crean, añadir el mensaje y el test con `monkeypatch.setitem(sys.modules, "<dep>", None)`.
- Cuatro reglas (`R-01`, `R-06`, `R-10`, `R-18`) son `[guía]`: nadie puede comprobarlas con una orden, y así figuran en `CLAUDE.md`.

## Reglas descartadas o aplazadas
- *Lint estático de parámetros de tamaño:* falsos positivos con `n`, `k`, `c`; el barrido de contrato ya los detecta (ver `docs/auditoria/REGLAS_PROPUESTAS.md`).
- *Fijar acciones por SHA / `attestations: true`:* aún sin probar (necesita TestPyPI); registrado como deuda en `CLAUDE.md`.
