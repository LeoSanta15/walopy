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
- [ ] **Todo bug corregido tiene un test de regresión que FALLA en la versión anterior** (`scripts/verificar_regresion.py` + manifiesto `tests/regresiones.json`; un test que también pasa sin el fix no protege nada) *(C-32)*
- [ ] Un test que verifica un detector (lint, idioma, barrido) incluye un **control negativo**: una entrada mala que debe ser señalada

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
- [ ] Los gates del Playbook (linter, tipos, cobertura, build, docs, `pip-audit`) son **jobs del CI**, no solo comandos de la lista *(C-15)*
- [ ] Instalación de la rueda en un entorno limpio con comprobación de `py.typed` y de la versión
- [ ] Job de regresión: los tests de cada bug fallan en el tag anterior (`verificar_regresion.py`, `fetch-depth: 0`)
- [ ] Pasos de shell que buscan patrones: `if grep …; then exit 1; fi` (un `!` no detiene `set -e`) y excluyendo el propio archivo del patrón *(C-25, C-27)*

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
- [ ] **NaN antes de comparar**: `isfinite` primero, luego `<`/`<=` (con NaN toda comparación es `False`); `bool` no es un número ni un entero *(C-09)*
- [ ] **Barrido de contrato** sobre todo `__all__`: cada argumento × `[nan, inf, -inf, -1, 0, None, "x", []]` solo puede dar `ValueError`/`TypeError` o un resultado finito, y cada función nueva debe entrar en la tabla *(C-14)*
- [ ] Cotas de tamaño (`MAX_*`) en todo parámetro que dimensiona un cálculo y límite de iteraciones en las búsquedas *(C-18)*
- [ ] Nada se recorta, fusiona ni descarta en silencio: duplicados → error, cota alcanzada → `UserWarning` *(C-13, C-16)*
- [ ] Listas de registros (`list[dict]`): comprobar tipo y claves con mensaje `items[i]: falta la clave …`

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
- [ ] Caso a escala: un tamaño 10× el caso típico (c = 150, n = 1000) con tiempo medido; fórmulas con potencias/factoriales sustituidas por recurrencias estables *(C-11, C-12)*
- [ ] Resultados sin `-0.0` (`round(x, 10) + 0.0`) y empates de heurísticas con tolerancia relativa *(C-21, C-26)*

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
- [ ] **Los ejemplos de README y docs son tests** y los doctests están activos (`--doctest-modules` en `addopts`, `--import-mode=importlib`) *(C-10, C-19)*
- [ ] Cada símbolo de `__all__` aparece en README y Sphinx (test que compara ambos) *(C-17)*
- [ ] En ejemplos, mostrar valores redondeados, no desigualdades con límites inventados *(C-20)*

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
- [ ] **Política de idioma comprobada por un test** (`tests/test_idioma.py`: mensajes, avisos y docstrings recorridos con `ast`, con control negativo); distinguir *claves de datos* (inmutables, en inglés) de *cabeceras de presentación* (`.rename(columns=…)`) *(C-30, C-31)*
- [ ] Reemplazos masivos (glosarios) solo con revisión del diff y suite completa después de cada paso *(C-31)*
- [ ] Capturas amplias (`except Exception`) solo con un parámetro explícito para propagar el error *(C-29)*

---

## NIVEL 3 → 4: Publicada y mantenida

### Dimensión: Versioning y releases

- [ ] Versionado semántico (MAJOR.MINOR.PATCH)
- [ ] Una sola fuente de verdad para la versión (recomendado: `importlib.metadata` o `setuptools-scm`)
- [ ] Tags git para cada release (`vX.Y.Z`)
- [ ] CI de publicación a PyPI en push de tag
- [ ] `twine check dist/*` en CI antes de publicar
- [ ] El job de publicación verifica que el tag coincide con la versión del paquete y repite tests, linter y tipos antes de construir
- [ ] Test del fallback de `__version__` (paquete sin instalar) y de que los metadatos instalados coinciden *(C-24, C-08)*
- [ ] Cada rama de trabajo parte de `origin/main` recién traído (`git merge-base --is-ancestor origin/main HEAD`); tras un merge *squash*, reiniciarla desde `main` *(C-28)*

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
- [ ] **Complejidad anunciada verificada empíricamente** (tabla de tiempos con n creciente; test de tiempo con margen amplio) *(C-11)*

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
