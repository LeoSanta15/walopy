# REGLAS PARA CLAUDE.md — Bloque listo para pegar

> Copia este bloque en el CLAUDE.md de cualquier repo Python.
> Sustituye `<paquete>` por el nombre real del módulo Python (ej. `pccpy`).
> Sustituye `<nombre_pypi>` por el nombre en PyPI (puede ser distinto del módulo).

---

```markdown
## Comandos estándar

```bash
# Tests
python -m pytest tests/ -q

# Linter (bugs reales, no solo estilo)
python -m ruff check src/ --select F,E9,B,I,S

# Tipos
python -m mypy src/<paquete> --ignore-missing-imports

# Build
python -m build --wheel

# Tests con cobertura
python -m pytest --cov=<paquete> --cov-report=term-missing -q

# Verificar sin referencias obsoletas
grep -r "PLACEHOLDER\|TU_USUARIO" . --include="*.py" --include="*.md" --include="*.toml" --include="*.yml" || echo "OK"
```

## Definición de "terminado"

Una tarea está **terminada** solo cuando:
1. `pytest -q` → 0 fallos, 0 errores.
2. `ruff check src/` → `All checks passed!`
3. `mypy src/<paquete> --ignore-missing-imports` → `Success: no issues found`
4. `python -m build --wheel` → `Successfully built`
5. Cobertura global >= 85%; ningún módulo público < 70%.
6. Sin referencias al nombre antiguo del paquete en ningún archivo.
7. CHANGELOG.md actualizado con la versión nueva.
8. CLAUDE.md actualizado si se añadió funcionalidad o se cambió un comando.

## Reglas de trabajo (no negociables)

### R-01: Cambios quirúrgicos
No reescribas módulos enteros para añadir una función. Sigue el patrón que usan
los módulos vecinos. Haz el cambio mínimo que resuelve el problema.

### R-02: Validar contra referencia independiente
Todo resultado numérico se valida contra una fuente externa a este código
(publicación, cálculo manual, otra librería, simulación Monte Carlo con ≥20 semillas).
Nunca validar la salida del código contra sí mismo.

### R-03: Español en lo que ve el usuario
Docstrings, mensajes de `ValueError`/`UserWarning`, columnas de DataFrame,
texto de gráficos → en español. Nombres de funciones y variables → snake_case inglés está bien.

### R-04: Avances incrementales con checkpoint
Cada versión: construir, probar (suite + wheel en venv limpio), commit, tag `vX.Y.Z`.
No dejar trabajo a medio hacer entre commits.

### R-05: Una sola fuente de verdad para la versión
La versión vive en `pyproject.toml`. `__init__.py` la lee:
```python
from importlib.metadata import version
__version__ = version("<nombre_pypi>")
```
No actualices la versión en dos lugares distintos.

### R-06: Dependencias opcionales con mensaje orientativo
Cualquier `import` de dependencia opcional va dentro de `try/except ImportError`:
```python
try:
    import openpyxl  # noqa: F401
except ImportError:
    raise ImportError(
        "X es necesario. Instálalo con:\n    pip install <nombre_pypi>[extra]"
    ) from None
```

### R-07: No contaminar estado global
Las funciones de visualización van dentro de `plt.rc_context({})`.
Los warnings temporales van dentro de `warnings.catch_warnings()`.

### R-08: Validación de entrada centralizada
La conversión de datos de usuario a arrays internos pasa siempre por la misma
función de ingesta. Esa función maneja: NaN/inf (warning + filtrado), arrays vacíos
(ValueError), tipos incorrectos (TypeError), casos degenerados (std=0 → NaN + warning).

### R-09: Checklist de renombre
Si se cambia el nombre del módulo Python o del paquete PyPI, ejecutar ANTES:
```bash
grep -r "nombre_viejo" . --include="*.py" --include="*.toml" --include="*.yml" \
  --include="*.md" --include="*.rst" --include="*.yaml"
```
El resultado es la lista exacta de archivos a actualizar. Incluir este CLAUDE.md.

### R-10: No repetir bugs del catálogo
Los bugs documentados en `docs/retrospectiva/BUG_CATALOG.md` tienen solución conocida.
Antes de implementar validación de entrada, casos borde o importaciones opcionales,
leer ese catálogo y aplicar el patrón correcto directamente.

### R-11: Tests de casos borde obligatorios
Cada función pública nueva necesita al menos un test de caso borde:
- Entrada vacía
- NaN/inf en los datos
- n mínimo (1 o 2 según la función)
- Parámetros opcionales ausentes
- Caso degenerado (std=0, todos iguales, etc.)

### R-12: CI en versión mínima
Antes de abrir un PR, confirmar que los tests pasan en la versión mínima de Python
declarada en `pyproject.toml`. Si no se puede verificar localmente, el CI debe correr
esa versión y el PR no se mergea hasta que pase.

## Política de no repetición

Si un bug del catálogo (`BUG_CATALOG.md`) reaparece:
1. Identificar por qué la solución anterior no fue suficiente.
2. Añadir un test de regresión si no existe.
3. Actualizar el catálogo con la nueva ocurrencia.
4. Reforzar la regla correspondiente en este archivo.
```
