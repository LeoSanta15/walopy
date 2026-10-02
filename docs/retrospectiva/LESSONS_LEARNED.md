# LESSONS_LEARNED — walopy

> Lecciones con evidencia de este repositorio (historial de git, la sesión de trabajo y las auditorías). Formato: qué pasó · por qué · cómo evitarlo · dónde quedó automatizado.
> Impacto: ALTO = produjo un fallo de release o un resultado incorrecto; MEDIO = costó rondas de trabajo; BAJO = molestia.

## Lo que muestran las sesiones previas (minería de `~/.claude/projects/`)
Solo existe **una** sesión (`d65912fa…jsonl`, 6 483 líneas, 83 mensajes de la persona usuaria). Peticiones repetidas, que son candidatas a automatizar:

| Petición repetida | Veces | Automatización |
|---|---|---|
| «Dame el changelog / el cuerpo del release» | 7 (entre v0.2.1 y v0.3.0) | `make notas-release VERSION=X.Y.Z` (extrae la sección del CHANGELOG; probado) |
| «¿Qué falta?» (4) / «¿Qué sigue?» (2) / «¿Está todo listo?» y «¿Estamos listos para el release?» (2) | 8 | `make check` (una orden con el estado real) y `make release-check` |
| «¿La documentación está actualizada?» | 4 | `tests/test_documentacion.py`, `tests/test_readme.py` y `sphinx -W` dentro de `make check` |
| «Haz el merge» (incluye las condicionadas al CI) | 7 | No se automatiza a propósito: es una decisión de la persona responsable |
| «La versión vX ya está ocupada / ya fue publicada, sería la siguiente» | 2 | `make release-check` + (pendiente) ensayo en TestPyPI |
| «Falló el release» (con logs pegados) | 6 mensajes | Guarda de versión en `publish.yml`; el log completo no se conserva (L-06) |
| Correcciones de alcance: «Excluir 3 porque ya hice otra librería (pccpy)», «Forecasting y SPC ya existen» | 2 | Registrar el alcance en CLAUDE.md (hecho en «Descripción») |
| «Siempre idioma en español» | 1 (explícita) | `tests/test_idioma.py` (R-03) |

## Lecciones

**L-01 · La «fuente única de versión» vía `importlib.metadata` queda congelada al instalar (IMPACTO: ALTO).**
*Qué pasó:* `ea1c050` movió la versión a `importlib.metadata`. Tras subir `pyproject.toml` a 0.3.1 (reproducido), `walopy.__version__` seguía en 0.3.0; en esta sesión dos entornos mostraban `0.3.0` frente a `0.2.8` en los metadatos, y `rendimiento.md` salió con «walopy 0.2.8». *Por qué:* los metadatos se escriben al instalar y no se refrescan. *Cómo evitarlo:* literal `__version__` en `__init__.py` + `[tool.setuptools.dynamic]`; `test_version.py` comprueba el literal, la ausencia de `importlib.metadata` y la coincidencia con los metadatos instalados (que además detecta entornos obsoletos). *Automatizado:* `tests/test_version.py`, MU-11.

**L-02 · Un gate escrito en cuatro sitios acaba siendo cuatro gates distintos (IMPACTO: MEDIO).**
*Qué pasó:* `ruff` se ejecutaba sobre `src/ tests/` en `publish.yml`, la plantilla de PR y la «definición de terminado», y sobre cinco directorios en el CI. Un cambio en `scripts/` podía pasar el release y fallar el CI. *Cómo evitarlo:* un `Makefile` es la única definición; el CI, la documentación y los hooks lo invocan o lo copian literalmente. *Automatizado:* `Makefile`, `make lint`.

**L-03 · Una regla que nadie probó contra el repo puede ser falsa (IMPACTO: MEDIO).**
*Qué pasó:* R-07 decía «gráficas dentro de `plt.rc_context`»; `grep rc_context src/` da 0 y el invariante real (no tocar `rcParams`) solo se probaba en 2 de 15 gráficas. *Cómo evitarlo:* cada regla lleva su etiqueta (`[test]`, `[CI]`, `[comando]`, `[guía]`) y se ejecuta contra el repo antes de adoptarla (`CLAUDE_MD_RULES.md`). *Automatizado:* `test_plot_no_modifica_rcparams` ×15.

**L-04 · Un test de regresión que no falla sin el fix no protege nada (IMPACTO: ALTO).**
*Qué pasó:* dos tests (`-0.0` y fallback de versión) pasaban con el código antiguo; `exchange_curve` (v0.2.7) y `EOQResult.plot()` (v0.2.1) se «arreglaron» sin test. *Cómo evitarlo:* comparar contra el tag anterior (`make regresion`) y mutar una línea (`make mutaciones`, 17 mutantes). *Automatizado:* R-16, `tests/regresiones.json`.

**L-05 · CI verde no significa gates cumplidos (IMPACTO: ALTO).**
*Qué pasó:* v0.2.8 salió con CI en verde, 82–215 errores de ruff, 78 de mypy y 80 % de cobertura. *Cómo evitarlo:* los gates del Playbook son jobs del CI, no comandos de una lista. *Automatizado:* `ci.yml` (calidad, cobertura global y por módulo, build, docs, regresión).

**L-06 · Los fallos de publicación se arreglaron sin ver el error (IMPACTO: ALTO).**
*Qué pasó:* v0.2.4 y v0.2.7 fallaron; los mensajes de la persona usuaria traen logs truncados («the available log excerpt does not include the failing command») y el arreglo de v0.2.7 fue `attestations: false` sin causa verificada. v0.2.2 y v0.2.4 se «ocuparon» en PyPI. *Cómo evitarlo:* guarda tag == wheel en el workflow de publicación, `make release-check TAG=…` antes de crear el tag, y un ensayo en TestPyPI (pendiente) que muestre el error real. Nunca cambiar la versión de una acción por intuición (R-18). *Automatizado:* `scripts/comprobar_version_release.py`, `publish.yml`.

**L-07 · Ejecutar código antiguo sin cotas puede matar el runner (IMPACTO: MEDIO).**
*Qué pasó:* `verificar_regresion.py` ejecuta tests contra v0.2.8, que no tiene cotas de tamaño: `monte_carlo_gg1(n=10**9)` llegó a 7,7 GB y el runner recibió una señal de apagado (código 143). *Cómo evitarlo:* `RLIMIT_AS` de 4 096 MB por selector (pico medido: 105 MB tras el límite). *Automatizado:* `--memoria-mb`.

**L-08 · Las ramas parten de una base vieja o de una referencia desactualizada (IMPACTO: MEDIO).**
*Qué pasó:* la rama partió de v0.2.0 (conflictos en 6 archivos) y, dos veces, `git fetch origin main` dejó `origin/main` desactualizado (en esta sesión: un `checkout -B` sobre la base vieja). *Cómo evitarlo:* `git fetch origin +refs/heads/main:refs/remotes/origin/main` y `git merge-base --is-ancestor origin/main HEAD`. *Automatizado:* R-17 y la plantilla de PR.

**L-09 · Una cifra copiada no es una cifra verificada (IMPACTO: MEDIO).**
*Qué pasó:* el CHANGELOG decía que `0.2.4` se publicó (no existe en PyPI); el SCORECARD anterior daba 4 a Versionado con un tag ausente; `rendimiento.md` etiquetaba 0.2.8. *Cómo evitarlo:* recalcular cada cifra al escribirla (`pip index versions`, `git ls-remote --tags`, `pytest`) y comprobar las que viven en documentos (`tests/test_scorecard.py`).

**L-10 · Pegar un glosario sobre todo el árbol rompe datos (IMPACTO: BAJO).**
*Qué pasó:* una traducción masiva cambió la clave `"method"` y un valor `"Name"`. *Cómo evitarlo:* claves de datos ≠ cabeceras mostradas; suite completa tras cada paso. *Automatizado:* `tests/test_idioma.py` + contrato.

**L-11 · El CI ejecuta cada commit dos veces (IMPACTO: BAJO).**
*Qué pasó:* `ci.yml` se dispara por `push` a `claude/**` y por `pull_request`: 28 checks en el PR #15 (dos ejecuciones). *Estado:* sin corregir (cambia el workflow); propuesta en `RESUMEN_EJECUTIVO.md`.

## Qué funcionó bien
- Validar contra la versión anterior (worktree + tests actuales) encontró defectos que ninguna revisión manual vio (L-04).
- El barrido de contrato sobre toda la API encontró 30 excepciones inesperadas y 2 bloqueos en una pasada.
- Probar los hooks en una copia del repo con un fallo inyectado dio evidencia directa de los cuatro comportamientos requeridos.
