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

## Convenciones

- Docstrings, mensajes de error y documentación en **español**; identificadores en inglés.
- Validación de entradas siempre a través de `src/walopy/_utils.py`.
- Resultados numéricos validados contra una referencia independiente (nunca contra el propio código).
- Python ≥ 3.9 (`from __future__ import annotations` en cada archivo).

## Seguridad

Para reportar vulnerabilidades consulta [`SECURITY.md`](SECURITY.md); no abras un issue público.
