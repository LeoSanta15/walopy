# PLAN I18N — walopy en español (por defecto) e inglés

> Estado: **Fase 0 terminada** (2026-10-04). Decisiones tomadas: idiomas `es` e `en`; **el español sigue por defecto**.
> Evidencia: `docs/auditoria/inventario_i18n.json` (generado por `scripts/inventario_i18n.py`) y `INVENTARIO_I18N.md`. Todo número de este plan sale de ese inventario.

## 1. Resultado de la Fase 0

| Medida | Valor |
|---|---|
| Textos únicos en `src/walopy` | **667** (820 usos; los repetidos comparten clave) |
| Sin clasificar / mensajes construidos fuera del `raise` | **0 / 0** (lo comprueba un test) |
| Cobertura medida con un método **independiente** del extractor | 261 cadenas con rasgos del español fuera de docstrings, **0 ausentes** del inventario |
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
| **1** | `_i18n.py` + migración de A, B y C (según D1–D3) **solo en español**; fixture que fija `es` | los **1 288+ tests pasan sin cambiar uno**; la salida en español es **idéntica** a la de v0.3.0 (comparación contra el tag); `test_i18n_paridad` activo | 1–1,5 semanas |
| **2** | Catálogo `en` + tests por idioma; `test_idioma.py` generalizado por catálogo | paridad total de claves y marcadores; cada mensaje comprobado en `en` | ~1 semana |
| **3** | Documentación en inglés (README, Sphinx con `sphinx-intl`), CHANGELOG, release **0.4.0** | `sphinx -W` en ambos idiomas; `make check` en verde | ~1 semana |

Riesgo conocido: durante las fases 1–3 el inventario se mantiene al día con `python scripts/inventario_i18n.py` (un test falla si se añade un texto sin regenerarlo).

## 6. Cómo reproducir la Fase 0
```bash
python scripts/inventario_i18n.py             # regenera inventario_i18n.json e INVENTARIO_I18N.md
python scripts/inventario_i18n.py --comprobar # falla si están desactualizados
python -m pytest tests/test_inventario_i18n.py tests/test_i18n_paridad.py
```
