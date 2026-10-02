# RESUMEN EJECUTIVO — walopy (2026-10-02)

**Estado:** v0.3.0 publicada (PyPI y tag `v0.3.0` sobre `e89f285`: `pip index versions walopy`, `git ls-remote --tags origin`). Esta rama añade infraestructura para agentes, la versión con fuente única literal y la guarda de release.
**Medido con `make check` (código 0, 96 s):** 1 288 tests (3.11, 3.9 y 3.9 con numpy 1.22/pandas 1.4); cobertura 94,7 % (módulo menor 86,3 %); ruff y mypy limpios; build + `twine check` + `py.typed` en el wheel; `sphinx -W`; 5 ejemplos; 24 selectores de regresión OK contra `v0.2.8`; 17/17 mutantes muertos.

## Pruebas de la infraestructura
| Prueba | Resultado |
|---|---|
| `make check` termina con exit 0 | ✅ 96 s |
| `CLAUDE_CODE_REMOTE=true .claude/hooks/session-start.sh` | ✅ exit 0 (6 s; idempotente: segunda ejecución también 6 s) |
| Salto local (`env -u CLAUDE_CODE_REMOTE`) | ✅ exit 0 en 4 ms, sin salida (nota: en esta sesión web la variable ya vale `true`) |
| `.claude/settings.json` es JSON válido | ✅ `python -m json.tool` |
| Hook Stop sin cambios en código / solo docs | ✅ exit 0 y `make` no se ejecuta (comprobado con un `make` espía) |
| Hook Stop con cambio válido (src y test nuevo) | ✅ corre `check-fast`, exit 0 |
| Hook Stop con `import os` sin usar inyectado (copia del repo) | ✅ exit 2 con el error de ruff (`F401`) en stderr |
| Hook Stop con un test que falla | ✅ exit 2 con el fallo de pytest |
| Hook Stop con `stop_hook_active=true` | ✅ exit 0 y no ejecuta nada (aun con el fallo presente) |
| `make release-check TAG=v0.3.0` | ✅ exit 0 |
| `make release-check TAG=v0.3.1` | ✅ falla (exit 2): «el tag v0.3.1 no coincide con la versión construida» |
| El wheel contiene `py.typed` | ✅ `unzip -l dist/*.whl` |
| Versión: `pyproject 0.3.1` → `__version__` | ✅ reproducido el defecto original (0.3.0 con metadatos); con el literal ya no ocurre |

## Scorecard (media 3,71; `tests/test_scorecard.py` la recalcula)
Diez dimensiones en 4 y cuatro en 3 (Rendimiento, Seguridad, Versionado y releases, Comunidad). **Más rezagada: Versionado y releases** (desempate por impacto observado: ocho mensajes de la persona usuaria y tres incidentes de publicación en el historial).
**Acción de mayor impacto:** ensayo de publicación en TestPyPI (`workflow_dispatch`, con `release-check` y `attestations: true`): ataca la causa de los incidentes y desbloquea Seguridad. No implementado (cambia workflows y necesita configuración externa).

## Lo que cambió (resumen)
Versión: literal en `__init__.py` + `[tool.setuptools.dynamic]`. `Makefile`, `AGENTS.md`, `.claude/` (permisos + 2 hooks), CODEOWNERS, plantilla de PR, `.gitignore`. `publish.yml`: guarda wheel == tag y lint idéntico al CI. Scripts: `comprobar_version_release.py`, `verificar_mutaciones.py`, `notas_release.py`. Tests nuevos: versión (5), `scorecard`, `notas_release`, `rcParams` (19 gráficas), `exchange_curve` (2). `CLAUDE.md` con estado verificado, reglas etiquetadas y deuda.

## Contradicciones halladas entre docs, tests y código
1. `ruff` con cuatro variantes de comando (PR template, `publish.yml`, «definición de terminado» vs. CI) → unificado en `make lint`.
2. R-07 exigía `plt.rc_context`; el código no lo usa y el test solo cubría 2 de 19 gráficas (un mutante sobrevivió) → regla corregida, test ampliado.
3. El CHANGELOG `[0.3.0]` decía que `0.2.4` se publicó; PyPI no lo lista → corregido en `[Sin publicar]`.
4. `docs/auditoria/SCORECARD.md` daba 4 a Versionado con un tag ausente (3,8 de media); con criterio explícito es 3 (3,71).
5. `test_trazabilidad` aceptaba cualquier mención del `W-nn` en el catálogo (borrando las 25 fichas solo fallaban 6) → exige la fila de la ficha.
6. R-05 de `CLAUDE.md` y `ea1c050` establecían la versión vía `importlib.metadata`, que se congela al instalar → invertida a petición (literal + dynamic).
7. `DIAGNOSTICO.md` conserva cifras de v0.2.8 sin marca histórica → marcado.
8. `rendimiento.md` etiquetaba «walopy 0.2.8» por metadatos obsoletos → medido de nuevo con 0.3.0.

## NO VERIFICADO
- Protección de ramas y exigencia de revisión de CODEOWNERS (configuración de GitHub, fuera del repo).
- Causa exacta de los fallos de publicación de v0.2.4 y v0.2.7 (los logs completos no se conservan).
- Que `attestations: true` funcione con el publicador de confianza actual (requiere TestPyPI).
- Tiempo de respuesta a issues y actividad de la comunidad.
- Por qué `0.1.0` y `0.2.0` no aparecen en `pip index versions walopy`.
- Los cambios de `publish.yml` no se ejecutaron en GitHub (solo se probó en local la comprobación de versión y la sintaxis YAML).
