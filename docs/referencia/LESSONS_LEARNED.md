# LESSONS LEARNED — pccpy

> Revisión forense basada en 102 commits, historial git completo, CLAUDE.md, suite de 344 tests y outputs de CI.
> Ordenadas por impacto descendente. Cada lección incluye: ¿qué pasó?, ¿por qué?, ¿cómo evitarlo?

---

## L-01 · Renombrar un módulo Python mientras ya está publicado es costoso (IMPACTO: CRÍTICO)

**¿Qué pasó?**
El proyecto nació como `spyc` (PyPI: `spyc`, módulo Python: `spyc`). Se renombró a `pccpy` — PyPI: `pccpy`, módulo Python: `pccpy` — sin coordinar todos los artefactos de una vez. Resultado: >20 commits de limpieza residual (`docs: fix README code examples - import spyc not pccpy`, `docs: corregir nombre spyc → pccpy en CONTRIBUTING`, `ci: corrige referencias spyc→pccpy`, commits `chore: delete src/spyc/*`). El CLAUDE.md activo todavía referencia `src/spyc` en comandos de mypy y pytest.

**Evidencia:** commits `85537d5` (README import erróneo), `3fc99f2`, `3db3c6e`, `454619a`, `3fb309c`, `ccefba7`–`6cb8e00` (16 commits de borrado uno a uno), CLAUDE.md líneas `mypy src/spyc`, `pytest --cov=spyc`.

**¿Por qué?**
El renombre se ejecutó en ramas separadas y en lotes (tests batch 1, tests batch 2, src batch 2), sin una lista de verificación que cubriera CI, CLAUDE.md, docs RST y README.

**¿Cómo evitarlo?**
1. Crear un checklist de renombre antes de empezar: `grep -r "nombre_viejo" . --include="*.py" --include="*.toml" --include="*.yml" --include="*.md" --include="*.rst" --include="*.yaml"`.
2. Ejecutar el grep en CI como gate: si aparece el nombre antiguo, el build falla.
3. Renombrar PyPI package y módulo Python al mismo tiempo en un solo PR atómico.
4. Actualizar CLAUDE.md como primer archivo del PR de renombre, no al final.

---

## L-02 · La cobertura del 90% oculta un módulo con el 19% (IMPACTO: ALTO)

**¿Qué pasó?**
`src/pccpy/charts/timeweighted_attr.py` (EWMA/CUSUM para atributos P/C/U) tiene 19% de cobertura. El número global del proyecto —90%— enmascara este módulo de 77 declaraciones con solo 15 cubiertas.

**Evidencia:** salida de `pytest --cov=pccpy --cov-report=term-missing`:
```
src/pccpy/charts/timeweighted_attr.py  77  62  19%  23-27, 31-35, 41-70, 96, 119, 145, 151-180, 210, 233, 259
```

**¿Por qué?**
El módulo fue añadido en v0.7.0 (`feat: v0.7.0 — EWMA y CUSUM para cartas de atributos`) sin tests específicos; `test_charts.py` no incluye ningún caso de `ewma_p_chart`, `ewma_c_chart`, `cusum_p_chart`, `cusum_u_chart`.

**¿Cómo evitarlo?**
Añadir a CI el umbral `--cov-fail-under=80` por módulo, no solo global. Con `pytest-cov` + `coverage` se puede configurar en `pyproject.toml`:
```toml
[tool.coverage.report]
fail_under = 85
```
O revisar el reporte de cobertura por archivo antes de cada PR de feature.

---

## L-03 · Los datos reales contienen NaN/inf y DataFrames con columnas no numéricas (IMPACTO: ALTO)

**¿Qué pasó?**
Las versiones anteriores de `as_1d()` y `to_subgroups()` lanzaban errores opacos de numpy cuando los datos de entrada tenían valores no finitos o columnas de texto. Los usuarios veían `"could not convert string to float"` sin orientación.

**Evidencia:** commit `39bd66a` — "fix: mejorar compatibilidad con datos reales y casos límite". Cambios en `_data.py`, `capability.py`, `msa.py`, `results.py`, `tolerance.py`.

**¿Por qué?**
Las funciones de entrada validaban el tipo (array-like) pero no el contenido. En una librería científica es tentador asumir que los datos llegan limpios.

**¿Cómo evitarlo?**
La capa de ingesta de datos debe tener tres comportamientos explícitos:
1. Datos inválidos recuperables (NaN/inf): `UserWarning` + filtrado automático.
2. Datos inválidos no recuperables (array vacío tras filtrar): `ValueError` con mensaje claro.
3. Columnas mixtas en DataFrame: `UserWarning` + filtrado de no numéricas.
Documentar este contrato en el docstring de cada función de ingesta.

---

## L-04 · CI no detectó los fallos de Python 3.9 hasta después del merge (IMPACTO: ALTO)

**¿Qué pasó?**
La v0.10.6 introdujo código incompatible con Python 3.9: `scipy.stats.normaltest` lanza `SmallSampleWarning` en Python 3.11+ pero `ValueError` en 3.9 para n < 8. El CI corría en la matriz multi-versión pero las correcciones llegaron como commits separados (`ci: corrige fallos de ruff, pytest (Python 3.9) y Sphinx para v0.10.6`).

**Evidencia:** commits `44f7f69`, `a5b058d` (merge), `322a24e` — todos corrigen fallos CI descubiertos tras el merge de la feature principal.

**¿Por qué?**
La feature se desarrolló y testeó localmente en Python 3.11 y se subió sin confirmar el pase en 3.9 localmente.

**¿Cómo evitarlo?**
1. Antes de abrir un PR, correr `tox -e py39` o `python3.9 -m pytest` localmente.
2. CI con `fail-fast: false` ya existe — buen patrón. Añadir comentario que muestre versión de Python al fallar.
3. La regla del CLAUDE.md dice "avances incrementales con checkpoint" — aplicarla también para la matrix de versiones.

---

## L-05 · `capability_analysis()` sin límites lanzaba error; el caso es válido (IMPACTO: ALTO)

**¿Qué pasó?**
Un usuario quería calcular estadísticos de proceso sin tener especificaciones definidas (exploración inicial). La función lanzaba `ValueError`. El fix de `39bd66a` hace que `lsl`/`usl` sean opcionales, devolviendo `NaN` en los índices.

**Evidencia:** commit `39bd66a`, sección "capability_analysis sin especificaciones". Mensaje original en código pre-fix: `ValueError("Se requiere al menos lsl o usl")`.

**¿Por qué?**
La API fue diseñada pensando en el caso de uso de producción (siempre hay especificaciones). El caso exploratorio no se consideró.

**¿Cómo evitarlo?**
Al diseñar una API, listar explícitamente los casos degenerados (sin datos, con NaN, sin parámetros opcionales) y decidir: ¿error, warning o resultado parcial? Documentar la decisión en el docstring.

---

## L-06 · Las zonas sigma no se mostraban en cartas asimétricas (IMPACTO: MEDIO)

**¿Qué pasó?**
Las cartas MR, R y S (distribución asimétrica, límites no simétricos respecto a la media) no mostraban las bandas ±1σ/±2σ porque la condición de dibujo era `if zones and panel.symmetric`.

**Evidencia:** commit `314cb86` — "fix: mostrar zonas sigma en cartas asimétricas (MR, R, S, etc.) (v0.4.8)". Cambio en `plotting.py`: se eliminó `panel.symmetric` de la condición.

**¿Por qué?**
La condición `panel.symmetric` fue añadida para no dibujar líneas negativas en cartas donde la media está cerca de cero. El efecto secundario fue suprimir completamente las zonas.

**¿Cómo evitarlo?**
Separar la lógica de "dibujar zonas" de la lógica de "recortar zonas bajo cero". Matplotlib recorta naturalmente al rango de los datos, por lo que la condición `symmetric` es innecesaria.

---

## L-07 · El CLAUDE.md nunca se actualizó tras el renombre spyc→pccpy (IMPACTO: MEDIO)

**¿Qué pasó?**
El archivo CLAUDE.md contiene referencias activas a `src/spyc` en comandos de pytest, mypy y en la sección "Mapa del código". Cualquier sesión nueva de Claude Code que lea el CLAUDE.md ejecutará comandos incorrectos.

**Evidencia:** CLAUDE.md líneas activas: `pytest --cov=spyc`, `mypy src/spyc`, `src/spyc/` en mapa de código. Estado actual del proyecto: `src/pccpy/`.

**¿Por qué?**
El CLAUDE.md fue creado en v0.4.3 (pre-renombre) y no fue incluido en el checklist del renombre.

**¿Cómo evitarlo?**
Incluir el CLAUDE.md en el grep de renombre del punto L-01. Tratar CLAUDE.md como código de primer nivel, no como documentación auxiliar.

---

## L-08 · setuptools>=77 con PEP 639 rechaza `license` SPDX + classifier duplicado (IMPACTO: MEDIO)

**¿Qué pasó?**
Con setuptools>=77.0.3 (PEP 639), el campo `license = "MIT"` y el classifier `License :: OSI Approved :: MIT License` son mutuamente excluyentes. El build fallaba.

**Evidencia:** commit `e894a25` — "fix: eliminar classifier de licencia duplicado (PEP 639)".

**¿Por qué?**
PEP 639 cambió la semántica del campo `license` de texto libre a expresión SPDX. La migración fue silenciosa hasta setuptools 77.

**¿Cómo evitarlo?**
En `pyproject.toml`, con setuptools>=77: usar solo `license = "MIT"` (SPDX). No añadir el classifier de licencia. Añadir `python -m build` al pre-commit hook o al CI de cada PR.

---

## L-09 · El módulo `_wizard.py` tiene 62% de cobertura pero es parte de la API pública (IMPACTO: MEDIO)

**¿Qué pasó?**
`wizard()` y `WidgetSession` están exportados en `__all__` de `__init__.py` pero `_wizard.py` tiene 62% de cobertura. Las líneas 911–1033 (modo `'widget'` con ipywidgets) no tienen tests.

**Evidencia:** reporte de cobertura, líneas `917-1033 src/pccpy/_wizard.py`.

**¿Por qué?**
El modo `'widget'` requiere ipywidgets y un kernel Jupyter — difícil de testear en CI headless. No se añadieron mocks.

**¿Cómo evitarlo?**
Para código que requiere dependencias opcionales de entorno (widgets, GUI), usar `unittest.mock.patch` para simular la importación. Ejemplo: `with patch.dict('sys.modules', {'ipywidgets': Mock()}): ...`.

---

## L-10 · Versión en `pyproject.toml` se desincronizó de `__init__.py` en dos ocasiones (IMPACTO: BAJO)

**¿Qué pasó?**
El commit `fb8fc3d` ("revert version to 0.4.3") muestra que `pyproject.toml` y `__init__.py` tenían versiones diferentes en el mismo punto del historial. También el commit `2be31df` bumpeó "0.10.7 → 0.10.8" pero `pip show pccpy` reporta 0.10.6 (instalación previa).

**Evidencia:** commit `fb8fc3d` modifica tanto `pyproject.toml` como `src/spyc/__init__.py` para alinear a `0.4.3`.

**¿Por qué?**
La versión se gestiona manualmente en dos lugares. Es fácil actualizar uno y olvidar el otro.

**¿Cómo evitarlo?**
Usar `importlib.metadata` en `__init__.py`:
```python
from importlib.metadata import version
__version__ = version("pccpy")
```
O usar `setuptools-scm` para derivar la versión del tag git. Así hay una sola fuente de verdad.
