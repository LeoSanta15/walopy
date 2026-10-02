# PLAYBOOK — Madurez de librería Python (niveles 0→5)

> Checklist portable e independiente del dominio.
> Para cada nivel: criterios medibles y comandos de verificación.

---

## Niveles de madurez

| Nivel | Nombre | Descripción |
|---|---|---|
| **0** | Prototipo | Código que funciona localmente, sin estructura |
| **1** | Librería básica** | Empaquetable, instalable, con tests mínimos |
| **2** | Calidad verificable | CI activo, linter, tipos, cobertura razonada |
| **3** | Lista para producción | API estable, docs completas, casos borde cubiertos |
| **4** | Publicada y mantenida | PyPI, versiones semánticas, changelog, comunidad |
| **5** | Excelencia sostenida | Benchmarks, seguridad, soporte multi-versión verificado |

---

## NIVEL 0 → 1: Estructura básica

### Dimensión: Estructura del repositorio

- [ ] `src/` layout (no flat)
- [ ] `pyproject.toml` con `name`, `version`, `requires-python`, `dependencies`
- [ ] `LICENSE` presente
- [ ] `.gitignore` configurado (excluye `__pycache__`, `dist/`, `.egg-info/`)
- [ ] `src/<paquete>/__init__.py` con `__version__` y `__all__`

**Verificación:**
```bash
python -c "import <paquete>; print(<paquete>.__version__)"
pip install -e . && python -c "import <paquete>"
```

**Criterio "hecho":** la instalación en venv limpio no da error.

---

### Dimensión: Tests mínimos

- [ ] `tests/` con al menos un archivo por módulo público
- [ ] `pytest` configurado en `pyproject.toml` (`testpaths`, `addopts`)
- [ ] Fixture de semilla aleatoria (`rng = np.random.default_rng(seed)`) en `conftest.py`
- [ ] Tests pasan en venv limpio

**Verificación:**
```bash
python -m pytest tests/ -q
```

**Criterio "hecho":** 0 fallos, 0 errores.

---

## NIVEL 1 → 2: Calidad verificable

### Dimensión: Linter

- [ ] `ruff` configurado en `pyproject.toml` con `line-length` y `target-version`
- [ ] `ruff check src/` pasa sin errores
- [ ] Reglas mínimas activadas: `F` (pyflakes), `E9` (errores de sintaxis), `B` (bugbear), `I` (isort)

**Verificación:**
```bash
python -m ruff check src/
```

**Criterio "hecho":** `All checks passed!`

---

### Dimensión: Tipado estático

- [ ] Anotaciones de tipo en todas las funciones públicas (parámetros y retorno)
- [ ] `mypy src/<paquete> --ignore-missing-imports` sin errores
- [ ] `from __future__ import annotations` en archivos con tipos forward-reference

**Verificación:**
```bash
python -m mypy src/<paquete> --ignore-missing-imports
```

**Criterio "hecho":** `Success: no issues found in N source files`

---

### Dimensión: Cobertura

- [ ] `pytest-cov` en dependencias de dev
- [ ] Cobertura global >= 85%
- [ ] Sin módulos públicos con cobertura < 70%
- [ ] `--cov-report=term-missing` en CI para identificar líneas no cubiertas

**Verificación:**
```bash
python -m pytest --cov=<paquete> --cov-report=term-missing -q
```

**Criterio "hecho":** columna `Cover` >= 85% en `TOTAL`; ningún módulo público < 70%.

---

### Dimensión: CI básico

- [ ] GitHub Actions (o equivalente) activo en `push` y `pull_request`
- [ ] Jobs: tests, linter, tipos
- [ ] Matrix multi-versión Python (mínimo versión mínima declarada + versión actual)
- [ ] `fail-fast: false` en la matrix para ver todos los fallos

**Verificación:**
```bash
cat .github/workflows/tests.yml | grep "python-version"
```

**Criterio "hecho":** CI pasa en verde en la versión mínima declarada en `requires-python`.

---

## NIVEL 2 → 3: Lista para producción

### Dimensión: Validación de entradas

- [ ] Capa de ingesta centralizada (ej. función `_validate()` o `as_1d()`)
- [ ] Manejo explícito de: NaN/inf, arrays vacíos, tipos incorrectos, casos degenerados (n=0, sigma=0)
- [ ] Dependencias opcionales: `ImportError` capturado con mensaje `pip install X`
- [ ] Estado global (matplotlib rcParams, warnings): usar context managers

**Verificación:**
```bash
python -c "import <paquete>; <paquete>.funcion_publica([])"  # debe dar ValueError claro
python -c "import numpy as np; import <paquete>; <paquete>.funcion_publica(np.array([np.nan]))"
```

**Criterio "hecho":** errores con mensajes accionables; no `ValueError` ni `TypeError` de numpy.

---

### Dimensión: Casos borde documentados

- [ ] Docstring de cada función pública incluye sección `Raises` con condiciones
- [ ] Tests parametrizados que cubren: vacío, NaN, n=1, n=2, valores extremos
- [ ] Comportamiento con datos constantes (std=0) definido y testeado

**Verificación:**
```bash
python -m pytest tests/ -k "nan or edge or empty or zero" -v
```

**Criterio "hecho":** al menos 1 test de caso borde por función pública.

---

### Dimensión: Documentación

- [ ] README con: descripción, instalación, ejemplo mínimo funcional, referencia a docs completas
- [ ] Docstrings completos en todas las funciones públicas (parámetros, retorno, raises, ejemplo)
- [ ] CHANGELOG.md con entradas por versión
- [ ] Sphinx (o equivalente) construye sin warnings con `-W`

**Verificación:**
```bash
sphinx-build -b html -W docs/source docs/build
grep -r "TU_USUARIO\|PLACEHOLDER\|TODO" README.md docs/
```

**Criterio "hecho":** build de docs sin errores; README sin placeholders.

---

### Dimensión: Consistencia de API

- [ ] Un único archivo de ingesta de datos (no lógica duplicada)
- [ ] Todos los errores de usuario son `ValueError` o `TypeError` con mensaje en español (o el idioma del proyecto)
- [ ] Nombres consistentes: snake_case para funciones, PascalCase para clases
- [ ] `__all__` completo en `__init__.py`

---

## NIVEL 3 → 4: Publicada y mantenida

### Dimensión: Versioning y releases

- [ ] Versionado semántico (MAJOR.MINOR.PATCH)
- [ ] Una sola fuente de verdad para la versión (recomendado: `importlib.metadata` o `setuptools-scm`)
- [ ] Tags git para cada release (`vX.Y.Z`)
- [ ] CI de publicación a PyPI en push de tag
- [ ] `twine check dist/*` en CI antes de publicar

**Verificación:**
```bash
python -c "from importlib.metadata import version; print(version('<paquete>'))"
git tag --list | grep "^v"
```

**Criterio "hecho":** versión en metadata == versión en `__version__`; existe tag por cada versión publicada.

---

### Dimensión: Soporte multi-versión Python verificado

- [ ] CI matrix cubre todas las versiones en `classifiers` de `pyproject.toml`
- [ ] Sin uso de sintaxis/stdlib no disponible en la versión mínima
- [ ] Tests pasan en la versión más antigua soportada

**Verificación:**
```bash
python -m pytest tests/ -q  # en Python==versión_mínima
```

**Criterio "hecho":** 0 fallos en Python mínimo.

---

### Dimensión: Developer Experience

- [ ] `pip install -e ".[dev]"` instala todo lo necesario en un paso
- [ ] CLAUDE.md (o CONTRIBUTING.md) con comandos exactos para test/lint/tipos/build
- [ ] Sin placeholders activos en documentación de contribución
- [ ] Ejemplos ejecutables (`examples/`) que corren sin error

**Verificación:**
```bash
python examples/*.py
grep -r "TU_USUARIO\|spyc\|nombre_viejo" CLAUDE.md CONTRIBUTING.md
```

**Criterio "hecho":** ejemplos corren; sin referencias al nombre antiguo en documentación.

---

## NIVEL 4 → 5: Excelencia sostenida

### Dimensión: Rendimiento

- [ ] Benchmarks documentados para las operaciones críticas
- [ ] `benchmarks/` con scripts reproducibles
- [ ] Sin regresiones de rendimiento entre versiones mayores

**Verificación:**
```bash
python benchmarks/bench_charts.py  # o equivalente
```

---

### Dimensión: Seguridad

- [ ] Sin dependencias con CVEs conocidas (`pip audit`)
- [ ] Dependencias fijadas en rangos (no `>=0.1`, sino `>=1.22,<3`)
- [ ] Sin datos sensibles en el repositorio

**Verificación:**
```bash
pip audit
```

---

### Dimensión: Comunidad

- [ ] CONTRIBUTING.md con guía de contribución
- [ ] Issue templates en `.github/`
- [ ] Código de conducta
- [ ] Tiempo de respuesta a issues < 7 días (mantenimiento activo)

---

## Checklist de "terminado" para un PR

Antes de mergear cualquier PR:
```bash
# 1. Tests completos
python -m pytest tests/ -q

# 2. Sin fallos de linter
python -m ruff check src/

# 3. Sin fallos de tipos
python -m mypy src/<paquete> --ignore-missing-imports

# 4. Build limpio
python -m build --wheel

# 5. Sin referencias obsoletas
grep -r "nombre_antiguo\|TU_USUARIO\|PLACEHOLDER" . --include="*.py" --include="*.md" --include="*.toml" --include="*.yml"

# 6. Cobertura no cayó
python -m pytest --cov=<paquete> --cov-fail-under=85 -q
```
