# Guía de contribución

¡Gracias por querer mejorar walopy! Las reglas completas de trabajo están en [`CLAUDE.md`](CLAUDE.md).

## Flujo

1. Haz un fork y crea una rama a partir de `main` actualizado.
2. Instala en modo editable: `pip install -e ".[dev,release,docs]"`
3. Escribe el cambio **con su test de regresión** (toda función pública nueva necesita al menos un test de caso borde).
4. Ejecuta la batería de verificación:

```bash
python -m pytest tests/ -q
python -m pytest --cov=walopy --cov-report=term-missing -q   # global ≥ 85 %, ningún módulo público < 70 %
python -m ruff check src/ tests/
python -m mypy src/walopy --ignore-missing-imports
python -m build && python -m twine check dist/*
python -m sphinx -b html -W docs/source docs/build
```

5. Actualiza `CHANGELOG.md`, el README y la referencia Sphinx si cambias o añades funcionalidad.
6. Abre un pull request contra `main` y completa la plantilla.

## Convenciones

- Docstrings, mensajes de error y documentación en **español**; identificadores en inglés.
- Validación de entradas siempre a través de `src/walopy/_utils.py`.
- Resultados numéricos validados contra una referencia independiente (nunca contra el propio código).
- Python ≥ 3.9 (`from __future__ import annotations` en cada archivo).

## Seguridad

Para reportar vulnerabilidades consulta [`SECURITY.md`](SECURITY.md); no abras un issue público.
