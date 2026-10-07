# Guía de contribución

¡Gracias por querer mejorar walopy! Las reglas completas de trabajo están en [`CLAUDE.md`](CLAUDE.md).

## Flujo

1. Haz un fork y crea una rama a partir de `main` actualizado (`git fetch origin +refs/heads/main:refs/remotes/origin/main`; comprueba con `git merge-base --is-ancestor origin/main HEAD`).
2. Instala en modo editable: `make install` (equivale a `pip install -e ".[dev,release,docs]"`)
3. Escribe el cambio **con su test de regresión** (toda función pública nueva necesita al menos un test de caso borde).
4. Ejecuta la batería de verificación (`make` ejecuta lo mismo que el CI):

```bash
make check-fast   # lint + tipos + tests: para iterar
make check        # todo: lint, tipos, tests, cobertura (global ≥ 85 %, ningún módulo < 70 %), build, docs, ejemplos, regresiones
```

Si corriges un bug (regla R-16): añade su entrada `W-nn` a `tests/regresiones.json`, su ficha a
`docs/referencia/BUG_CATALOG.md` y comprueba con `make regresion` (los tests deben fallar en el tag anterior; necesita
`git fetch --tags`) y `make mutaciones`.

Si subes la versión: edítala **solo** en `src/walopy/__init__.py`, ejecuta `make install` y comprueba con
`make release-check TAG=vX.Y.Z`.

5. Actualiza `CHANGELOG.md`, el README y la referencia Sphinx si cambias o añades funcionalidad.
6. Abre un pull request contra `main` y completa la plantilla.

## Cómo añadir una función pública

Una función nueva (en `src/walopy/<módulo>.py` y en `__all__` de `src/walopy/__init__.py`) no está terminada hasta cumplir estos pasos; `make check` falla si falta alguno de los pasos 1 a 6 (el 7 es convención):

1. **Código y validación:** entradas a través de `src/walopy/_utils.py`; docstring en español con `Parameters`, `Returns`, `Raises` y `Examples` (los ejemplos se ejecutan como doctest).
2. **Textos visibles** (mensajes de error, avisos, columnas, rótulos de gráficas): no se escriben en el código. Añade la clave `modulo.tipo.funcion.resumen` a `src/walopy/_catalogo_es.py` y la misma clave, con los mismos marcadores `{nombre}`, a `src/walopy/_catalogo_en.py`; úsala con `_t("clave", dato=valor)`. Declara la clave nueva en `AÑADIDAS_TRAS_V030` de `tests/test_inventario_i18n.py` y comprueba con `make inventario-i18n`. Si un texto debe ser igual en ambos idiomas, va en `EXENTAS_DE_TRADUCCION`.
3. **Test de contrato:** una llamada válida de referencia en `BASE` de `tests/test_contrato_entradas.py` (el barrido comprueba entradas inválidas) y un test de caso borde propio (vacío, NaN/inf, n mínimo, degenerado). Si la función devuelve una figura de Plotly, añádela a `FIGURAS` de `tests/test_dibujo_plotly.py` y ejecuta `make dibujo` (renderiza en Chromium; necesita Chrome/Chromium o `WALOPY_CHROME`).
4. **Referencia Sphinx:** el símbolo en `docs/source/referencia/<módulo>.rst`.
5. **README en español y en inglés:** una mención (y, si procede, un bloque de código ejecutable) en `README.md` y en `README.en.md`.
6. **Traducción de la referencia:** `make docs-i18n` (necesita el extra `docs`) actualiza `docs/source/locale/en/LC_MESSAGES/*.po`; traduce al inglés lo nuevo, sin dejar entradas vacías ni difusas.
7. **Cierre:** entrada en `CHANGELOG.md` (`[Sin publicar]`), el módulo en `CLAUDE.md` si es nuevo y `make check`.

El inglés no pasa por una revisión nativa (decisión del 2026-10-07, ver `docs/auditoria/PLAN_I18N.md` §7): escríbelo lo mejor que puedas y deja que las pruebas comprueben la estructura; los errores de redacción se corrigen cuando se reportan.

## Convenciones

- Docstrings, mensajes de error y documentación en **español**; identificadores en inglés. El inglés (catálogo, `README.en.md`, `.po`) se mantiene en paridad con el español.
- Validación de entradas siempre a través de `src/walopy/_utils.py`.
- Resultados numéricos validados contra una referencia independiente (nunca contra el propio código).
- Python ≥ 3.9 (`from __future__ import annotations` en cada archivo).

## Seguridad

Para reportar vulnerabilidades consulta [`SECURITY.md`](SECURITY.md); no abras un issue público.
