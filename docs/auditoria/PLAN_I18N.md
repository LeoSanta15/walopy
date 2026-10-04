# PLAN I18N — walopy en español (por defecto) e inglés

> Estado: **Fases 0, 1, 2 y 3 terminadas** (2026-10-04); versión **0.4.0 preparada** (falta la revisión nativa del inglés y crear el tag/release, que lo hace una persona). **El catálogo inglés, `README.en.md` y las traducciones de Sphinx los redactó Claude y están pendientes de revisión por una persona nativa antes de publicar.** Decisiones tomadas: idiomas `es` e `en`; **el español sigue por defecto**; D1 a, D2 a, D3 sí, D4 español con enlace al inglés.
> Evidencia: `docs/auditoria/inventario_i18n_base.json` (línea base **congelada** de v0.3.0, generada con `scripts/inventario_i18n.py --src <código de v0.3.0>`) y `INVENTARIO_I18N.md`. Todo número de este plan sale de ese inventario.

> **Corrección sobre la Fase 0 (hecha en la Fase 1).** El primer inventario contó **667** textos y afirmó cobertura del 100 %. Era incompleto: no veía los textos escondidos en
> expresiones (`x or 'ninguna'`, `'ventas' if … else 'unidades'`), las claves de columna leídas dentro de f-strings (`row['Artículo']`) ni f-strings con solo marcadores, y
> clasificaba como «nombre de argumento» siete mensajes completos que empezaban por `items[{idx}]…`/`activities[{i}]…` y no veía el `metavar="MODELO"` de la ayuda del CLI (lo encontró la Fase 2). El extractor se rehízo (AST con posiciones exactas) y el inventario
> definitivo tiene **646 textos únicos** (763 usos), con un tipo nuevo `texto_en_expresion`. La cobertura ya no se afirma por el recuento sino por tres controles independientes
> (ver «Verificación» abajo). Lección: un inventario se valida migrando de verdad, no solo contando.

## 1. Resultado de la Fase 0

| Medida | Valor |
|---|---|
| Textos únicos en `src/walopy` | ~~667~~ → **646** tras la corrección (763 usos; los repetidos comparten clave) |
| Sin clasificar / mensajes construidos fuera del `raise` | **0 / 0** (lo comprueba un test) |
| Cobertura medida con un método **independiente** del extractor | (fase 0: 261 cadenas, 0 ausentes — insuficiente, ver la corrección). Fase 1: ver «Verificación» |
| Plantillas con variables (grupos A+B, 536 textos) | 175 (361 son fijas); solo 19 con expresiones complejas (hay que precalcular el valor) |

### Los 667 textos, por grupo de riesgo
| Grupo | Tipos | Textos | Qué implica |
|---|---|---|---|
| **A. Presentación pura** | `error` 106 · `etiqueta` 182 · `grafica` 66 · `kpi` 32 · `cli` 17 · `modelo` 8 · `aviso` 3 | **414** | Se traducen sin riesgo: no son datos |
| **B. Cabeceras de `to_frame()`** | `cabecera` 122 | **122** | Ya están aisladas por `.rename(columns=…)`: las claves de datos no cambian |
| **C. Forma de la API que depende del texto** | `clave_params` 38 · `columna_df` 36 · `valor_por_defecto` 6 | **80** (+16 accesos por texto) | **Decisión necesaria** (ver §3) |
| **D. No se traduce** | `nombre_arg` 35 (`capacity[{i}]`…) | 35 | Son nombres de argumentos dentro de mensajes |

Complejidad de A+B (536): 361 fijas · 48 con variables simples · 108 con formato (`!r`, `:.6g`) · 19 con expresiones. Módulos con más texto: `inventory` 155, `plotting` 66, `advanced` 65, `kpi` 38.

## 2. Hallazgo principal: el grupo C

`result.params` usa como **claves** textos legibles («P0 (prob. de sistema vacío)», 38 claves, 74 usos) y varias funciones devuelven `DataFrame` cuyas **columnas** son texto en español
que otras partes del código leen por su texto (`plotting.py` hace `df["Tiempo_ciclo"]`, `df["P(N=n)"]`; `eoq_quantity_discount` lee sus propias columnas: 16 accesos).
Si esos textos cambian con el idioma sin más, `result.params[...]` y `df["Estación"]` dejan de funcionar al cambiar de idioma, y las gráficas se romperían.

## 3. Decisiones pendientes (tuyas)

**D1 · Claves de `params` (38).**
- **(a) Recomendada para 0.4.0:** las claves quedan **fijas** (las de hoy, en español); `summary()` muestra la etiqueta traducida. Cero cambios para quien ya la usa.
- (b) Traducir las claves: `params[...]` depende del idioma activo.
- (c) Claves estables en inglés (`params["P0"]`) y etiqueta traducida solo en `summary()`: limpio, pero rompe compatibilidad respecto a 0.3.0 (candidato a 1.0).

**D2 · Columnas de `DataFrame` devueltas directamente (36 + 16 accesos).**
- **(a) Recomendada:** se traducen **al crear** la columna según el idioma activo, y el código interno las lee con la misma función `t()` (consistente dentro de un idioma). Quien cambie de idioma entre crear y leer la tabla verá nombres distintos; se documenta.
- (b) Dejarlas fijas en español: seguro, pero un usuario en inglés vería columnas en español.

**D3 · Nombres por defecto (6: `Artículo{i}`, `J{i}`, `I{i}`, `item_name="Artículo"`…).** Recomendado: **se traducen** según el idioma activo (`Item1`, `J1`); son valores por defecto, no claves.

**D4 · README en PyPI** (pendiente de antes): ¿español con enlace al inglés, o bilingüe en la misma página?

## 4. Diseño (comprobado con una prueba de concepto en Python 3.9 y 3.11)
- `walopy/_i18n.py`: catálogos `CATALOGOS = {"es": {...}, "en": {...}}` con las claves del inventario; `t("clave", **datos)` con respaldo en español (nunca un `KeyError` para la persona usuaria).
- Idioma activo en una `ContextVar` (seguro con hilos y `asyncio`): `walopy.set_language("en")`, `with walopy.language("en"):`, `walopy.get_language()` y la variable de entorno `WALOPY_LANG`. Un valor desconocido vuelve a `es`.
- Las cabeceras (`_COL_*`) pasan de constantes a funciones que se resuelven al llamar.
- Los 175 textos con variables usan marcadores **nombrados** (`{name}`, `{value!r}`); los 19 con expresiones complejas precalculan el valor antes de llamar a `t()`.
- Las 3 funciones nuevas entran en `__all__`, en la documentación y en el test de contrato (R-13).

## 5. Fases (estimaciones mías, no medidas)
| Fase | Qué | Criterio de aceptación | Esfuerzo |
|---|---|---|---|
| **0** ✅ | Inventario, claves, tests de paridad e inventario al día | hecho: 667 textos, 0 sin clasificar, cobertura independiente 100 % | 1 día |
| **1** ✅ | `_i18n.py` + migración de A, B y C (según D1–D3) **solo en español**; fixture que fija `es` | hecho: los tests existentes pasan (solo se adaptó `test_idioma.py`, cuyo objeto —mensajes literales— ya no existe); salida en español **idéntica** a la de v0.3.0 (`tests/test_salida_identica.py`); `make check` verde; suites en Python 3.9 (mínimos y recientes), 3.10, 3.11 y 3.13 | 1 día |
| **2** ✅ | Catálogo `en` (597 claves) + tests por idioma; `test_idioma.py` generalizado por catálogo | hecho: paridad total de claves y marcadores; con `language("en")` todo el recorrido de funciones, errores, escenarios y CLI no contiene vocabulario español; los números no cambian con el idioma; `make check` verde | 1 día |
| **3** ✅ | Documentación en inglés (README, Sphinx con `sphinx-intl`), CHANGELOG, versión 0.4.0 | hecho: `README.en.md` (mismos 25 apartados y bloques de código ejecutados por `test_readme`), 924 mensajes de Sphinx traducidos (excepto el registro de cambios) (`docs/source/locale/en`), `make docs` construye ambos idiomas con `-W`, enlaces cruzados entre los README, `make check` y `make release-check TAG=v0.4.0` en verde | 1 día |

## 5b. Verificación de la Fase 1 (lo que demuestra que no se rompió nada)
1. **Instantánea de salida** (`tests/golden/salida_es.json`, generada con el código de v0.3.0): resultado, `str`, `summary()`, `to_frame()`, gráficas, errores del contrato de entradas, escenarios, bloques del README y CLI. Control negativo: cambiar una letra de un mensaje la rompe.
2. **Extractor** (`python scripts/inventario_i18n.py`): no quedan textos visibles literales en `src/` (salvo claves fijas de `params`, decisión D1).
3. **Controles independientes** (`tests/test_inventario_i18n.py`): ningún `raise`/`warnings.warn` contiene prosa literal; todo literal con rasgos del español es una clave fija de `params`; cada `_t("clave", …)` pasa exactamente los marcadores de su plantilla; cada clave usada existe y ninguna clave del catálogo queda huérfana; el texto español del catálogo es idéntico al de v0.3.0.
4. **Hallazgos durante la verificación** (ambos con la salida en español idéntica, es decir, invisibles para el control 1): (a) la migración había sustituido por error la clave de datos `o["covers_periods"]` por una etiqueta (`_t("…covers_periods")`, cuyo texto español es el mismo): habría roto el inglés; lo detectó la comparación entre el catálogo y la base regenerada y ahora lo vigila `test_el_catalogo_no_tiene_claves_que_no_estaban_en_v030`; (b) siete mensajes que empezaban por `items[{idx}]…`/`activities[{i}]…` seguían en español porque el extractor los tomaba por nombres de argumento; los encontró el control 3 (literales con rasgos del español). Lección: la identidad de la salida en español **no** basta para validar una migración; hacen falta los controles 2 y 3 y comparar el catálogo con la base.

## 5c. Hallazgos de la Fase 2
- **Robustez:** un resultado creado dentro de `with language("en")` y mostrado fuera (p. ej. `print(r)` de `break_even_multi`) lanzaba `KeyError`, porque `summary()` buscaba claves traducidas en el idioma de ese momento. Ahora esos accesos usan `columna()`, que busca en cualquier idioma (`tests/test_salida_por_idioma.py::test_el_idioma_no_cambia_ningun_numero` lo cubre).
- **Bug de v0.3.0 (R-03):** el mensaje de `eoq_quantity_discount` «No feasible price break found.» estaba en inglés; ahora es «No se encontró ningún tramo de precio factible.» en español (`CORREGIDAS_TRAS_V030`).
- **Claves de datos:** las clases `A/B/C/X/Y/Z` de ABC-XYZ pasan por el catálogo pero son idénticas en todos los idiomas (un test lo exige: `DATOS_INVARIABLES`).
- **Cuidado al traducir:** `.method` de `lot_for_lot` («Lote por lote» → «Lot-for-lot») y los nombres por defecto son datos visibles que cambian con el idioma; está documentado en el README.

## 5d. Hallazgos de la Fase 3
- El extractor no veía acrónimos españoles sueltos (`HT`/`HL`, holgura total/libre, columnas de `ProjectResult.to_frame()`): ahora son `project.cabecera.to_frame.ht/hl` (en inglés `TF`/`FF`).
- Las columnas de varias tablas imprimían desalineados algunos rótulos del español (`z`, `R(t=…)`): es el comportamiento de v0.3.0 (se conserva en español); en inglés se alinearon salvo `R(t=…)`, cuyo ancho depende de `t`.
- El registro de cambios (`CHANGELOG.md`) **no** se traduce (convención del repositorio: español) y queda fuera de la comprobación de traducciones de Sphinx.
- Los ejemplos `>>>` de los docstrings muestran la salida en español también en la documentación en inglés (son doctests y se ejecutan en español).
- Mantenimiento: tras cambiar un docstring, `make docs-i18n` y traducir lo nuevo (`test_las_traducciones_de_sphinx_estan_al_dia` falla si se olvida).

Riesgo conocido: al añadir un texto visible hay que ponerlo en ambos catálogos (`CLAUDE.md`, sección «Internacionalización»); los tests lo exigen.

## 6. Cómo reproducir las fases 0 y 1
```bash
S=$(mktemp -d); git archive v0.3.0 src | tar -x -C $S    # código anterior a la migración
python scripts/inventario_i18n.py --src $S/src/walopy --escribir docs/auditoria/inventario_i18n_base.json --informe docs/auditoria/INVENTARIO_I18N.md
python scripts/inventario_i18n.py             # falla si quedan textos literales en src/ (make inventario-i18n)
python scripts/instantanea_salida.py --comprobar tests/golden/salida_es.json
python -m pytest tests/test_inventario_i18n.py tests/test_i18n_paridad.py tests/test_i18n.py tests/test_salida_identica.py
```
