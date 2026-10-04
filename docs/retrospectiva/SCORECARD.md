# SCORECARD — walopy (14 dimensiones, escala 0–5)

> Medido el 2026-10-02 sobre `e89f285` (v0.3.0) más la infraestructura de agentes de esta rama. Cada nota tiene un **criterio explícito para el 4**
> y el comando que lo comprueba. 0 ausente · 1 rudimentario · 2 funcional · 3 sólido (cumple parte del criterio del 4) · 4 maduro (cumple **todo** el criterio) · 5 excelente (criterio del 4 + lo indicado en «Para el 5»).
> Un 4 exige cumplir todos los puntos del criterio; si falta uno, la nota es 3. `tests/test_scorecard.py` recalcula la media de esta tabla.

| # | Dimensión | Nota | Criterio para el 4 (todo) | Evidencia (HECHO) | Para el 5 |
|---|---|---|---|---|---|
| 1 | Estructura del repositorio | 4 | layout `src/`; `pyproject.toml` completo; LICENSE; `.gitignore` cubre `build/`, `dist/`, `docs/_build/`, `.coverage` y cachés; `py.typed` en el wheel; CLAUDE.md, AGENTS.md, Makefile y CODEOWNERS | `unzip -l dist/*.whl \| grep py.typed` → presente; `git check-ignore docs/_build/x .venv/x` → ignorados; los 4 archivos existen | plantilla de proyecto verificada en CI |
| 2 | Diseño de API pública | 4 | `__all__` completo y documentado (test); contrato de entradas sobre toda la API; resultados tipados; cambios incompatibles en el CHANGELOG | `tests/test_documentacion.py`, `tests/test_contrato_entradas.py` (70 funciones: 67 en la tabla + 3 exentas justificadas); sección «Cambios que rompen compatibilidad» en `[0.3.0]` | política de deprecación (`DeprecationWarning` + plazo) |
| 3 | Validación de entradas | 4 | capa central única (`_utils.py`); barrido de entradas patológicas sobre toda la API sin excepciones inesperadas; cotas de tamaño; NaN rechazado antes de comparar | contrato: 0 fallos; `W-01…W-22` con test que falla en v0.2.8 (`make regresion`) | pruebas basadas en propiedades; magnitudes extremas (K-08) |
| 4 | Corrección numérica | 4 | resultados contrastados con referencias independientes fijas; caso a escala (≥ 10× el típico); complejidad verificada | `tests/test_referencias_externas.py`, `tests/test_mmc_estable.py` (c hasta 1000), `tests/test_complejidad.py` | cota de error documentada por modelo |
| 5 | Suite de pruebas | 4 | cobertura global ≥ 85 % **y** todos los módulos ≥ 70 %; los tests de regresión fallan en el tag anterior; mutación de una línea mata a los mutantes de los fixes | `make cov` → 94,7 % / mínimo 86,3 %; `make regresion` → 24 selectores OK; `make mutaciones` → 17/17 muertos | puntuación de mutación sistemática |
| 6 | Tipado estático | 4 | `mypy` sin errores sobre `src/`; `py.typed` en el wheel | `make types` → «Success: no issues found in 16 source files» | `mypy --strict` en los módulos centrales |
| 7 | Gestión de dependencias | 4 | cotas inferiores probadas (job de mínimos); prueba periódica con las últimas versiones; `pip-audit` en el CI | jobs «Tests con dependencias mínimas», «Tests con las últimas dependencias» (semanal) y «Auditoría de dependencias» en `ci.yml` | archivo de bloqueo de herramientas y actualización automática (Dependabot) |
| 8 | CI/CD | 4 | todos los gates en el CI; matriz de todas las versiones de `classifiers` (3.9–3.13); la publicación repite tests/lint y comprueba tag == versión del wheel | `ci.yml` (jobs: tests ×5, mínimos, calidad, cobertura, regresión, paquete, docs, auditoría); `publish.yml` + `scripts/comprobar_version_release.py` | acciones fijadas por SHA, `attestations`, `concurrency` |
| 9 | Documentación | 4 | `sphinx -W` sin avisos; ejemplos del README ejecutados como tests; `__all__` comparado con las docs; doctests activos | `make docs`; `tests/test_readme.py` (61 bloques), `tests/test_documentacion.py`, `--doctest-modules` | tutoriales por dominio; docs versionadas y publicadas |
| 10 | Rendimiento | 3 | benchmarks reproducibles **y** complejidad verificada **y** línea base guardada con comparación automática entre versiones | `benchmarks/bench_core.py` y `tests/test_complejidad.py` existen; **no hay línea base guardada ni comparación automática** | regresión de rendimiento bloqueante en el CI |
| 11 | Seguridad | 3 | `pip-audit` en el CI; `SECURITY.md`; cotas de tamaño; **y** procedencia (`attestations`), actualización automática de dependencias y acciones fijadas por SHA | cumple los tres primeros; `attestations: false` en `publish.yml`; no hay `dependabot.yml`; `uses: …@v4` sin SHA | CodeQL / escaneo de secretos; OpenSSF Scorecard |
| 12 | Versionado y releases | 3 | fuente única de la versión con test; guarda tag == wheel; CHANGELOG; **un tag por cada versión publicada en PyPI** | literal `__version__` + `test_version.py`; `make release-check`; PyPI tiene `0.2.6` y no existe el tag `v0.2.6` (`pip index versions walopy` vs `git ls-remote --tags origin`) | releases automatizados desde el CHANGELOG |
| 13 | Comunidad y contribución | 3 | CONTRIBUTING, plantillas, código de conducta, SECURITY y CODEOWNERS; **y** evidencia de respuesta a issues en < 7 días | los cinco archivos existen; actividad de issues y protección de ramas: NO VERIFICADO (configuración de GitHub) | `good first issue`, guía de revisión |
| 14 | Developer Experience | 4 | CLAUDE.md + AGENTS.md; un comando que ejecuta todo (`make check`); hooks de agente probados; ejemplos que se ejecutan | `make check` → código 0 en 101 s; hooks probados una a una (ver RESUMEN_EJECUTIVO); `make examples` | `pre-commit` y entorno reproducible (devcontainer) |

**Media aritmética: 3,71** (52 / 14; diez dimensiones en 4 y cuatro en 3).

## Diferencias con `docs/auditoria/SCORECARD.md` (3,8)
- Versionado y releases baja de 4 a 3: la tabla anterior no aplicaba el criterio «un tag por versión publicada» y hay una versión (0.2.6) sin tag.
- Seguridad, Rendimiento y Comunidad se mantienen en 3, ahora con el criterio explícito de lo que falta.
- La media baja de 3,8 a 3,7 por el criterio más estricto, no por un empeoramiento del repo.

## Dimensiones más rezagadas
Cuatro empatan en 3: **Rendimiento (10), Seguridad (11), Versionado y releases (12) y Comunidad (13)**.
Desempate por impacto observado: en el historial hay al menos tres incidentes de publicación (v0.2.4 sin publicar, v0.2.2 «ya ocupada» y el fallo de v0.2.7, que se «arregló» con `attestations: false`) y ocho mensajes de la persona usuaria sobre fallos o versiones de release; ninguna de las otras tres dimensiones tiene incidentes observados.
→ **Versionado y releases** es la más rezagada.

## Acción de mayor impacto
Un workflow de **ensayo de publicación en TestPyPI** (`workflow_dispatch`) que construya el wheel, ejecute `release-check` y publique con `attestations: true`.
Ataca la causa de los incidentes observados (configuración de publicación probada solo en producción), permite activar `attestations` con evidencia (sube Seguridad) y no toca PyPI real.
Estado: **no implementado** (cambia workflows y requiere configurar el publicador de confianza en TestPyPI, fuera del repo); NO VERIFICADO que funcione hasta ejecutarlo.
