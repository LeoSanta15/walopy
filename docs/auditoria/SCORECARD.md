# SCORECARD — walopy

> Escala 0–5: 0 ausente · 1 rudimentario · 2 funcional · 3 sólido · 4 maduro · 5 excelente.
> **Antes:** medido el 2026-10-02 sobre `2cc17c1` (v0.2.8). **Objetivo:** nota esperada si se ejecuta el `ROADMAP.md` completo. **Después:** autoevaluación al cerrar el Paso 6 (2026-10-02), con la evidencia de la sección de seguimiento.

| # | Dimensión | Antes | Objetivo | Después | Fase que lo mueve | Evidencia clave del "antes" |
|---|---|---|---|---|---|---|
| 1 | Estructura del repositorio | 3 | 4 | **4** | 0 | Sin `py.typed`, metadatos obsoletos, sin SECURITY/templates |
| 2 | Diseño de API pública | 3 | 4 | **4** | 1, 2 | Contrato de ingesta no uniforme; API del README ≠ API real |
| 3 | Validación de entradas | 2 | 4 | **4** | 1 | 30 excepciones de otro tipo, 2 bloqueos y 26 entradas basura aceptadas en el barrido |
| 4 | Corrección numérica | 3 | 4 | **4** | 1, 2 | 30/30 contra referencias independientes; `mmc` desborda; β recortado |
| 5 | Suite de pruebas | 3 | 4 | **4** | 1, 2 | 357 tests OK; cobertura 80 %; `plotting.py` 0 %; sin `conftest` |
| 6 | Tipado estático | 2 | 4 | **4** | 0, 2 | 78 errores mypy, 43 F821, sin `py.typed` |
| 7 | Gestión de dependencias | 3 | 4 | **4** | 0, 2 | Compatible con mínimos y máximos; sin pin de herramientas; `pip-audit` fuera del CI |
| 8 | CI/CD | 2 | 4 | **4** | 2 | Solo `pytest`; sin lint/tipos/build/docs/cobertura; matriz sin 3.10/3.12 |
| 9 | Documentación | 2 | 4 | **4** | 3 | 13/61 bloques del README fallan; 8 funciones sin documentar; Sphinx 4/15 módulos |
| 10 | Rendimiento | 1 | 3 | **3** | 2, 3 | Sin benchmarks; NEH y Wagner-Whitin cúbicos frente a lo documentado |
| 11 | Seguridad | 2 | 3 | **3** | 0, 2, 3 | Sin SECURITY ni `pip-audit` en CI; bloqueos por parámetros sin cota |
| 12 | Versionado y releases | 3 | 4 | **4** | 0, 4 | Fuente única OK; fallback obsoleto; tags v0.2.4/v0.2.6 ausentes |
| 13 | Comunidad y contribución | 2 | 3 | **3** | 0 | CONTRIBUTING de 6 líneas; sin templates ni CoC |
| 14 | Developer Experience | 2 | 4 | **4** | 0, 3 | `CLAUDE.md` desactualizado; sin `examples/` |
| | **GLOBAL (media)** | **2,4** | **3,8** | **3,8** | | |

**Nivel de madurez:** antes = 2 (parcial) · objetivo = 3 (sólido), con las bases del nivel 4 (publicada, versionada) ya cubiertas.

## Gates del Playbook (estado actual)

| Gate | Requisito | Estado |
|---|---|---|
| `pytest` | 0 fallos | OK (357) |
| `ruff check src/` | `All checks passed!` | **No** (215 con la configuración del repo; 82 con `F,E9,B,I,S`) |
| `mypy src/walopy` | `Success` | **No** (78 errores) |
| `python -m build` | `Successfully built` | OK (+ `twine check` OK) |
| Cobertura | global ≥ 85 % y módulos públicos ≥ 70 % | **No** (80 %; `plotting.py` 0 %, `__main__.py` 62 %) |
| Sin referencias obsoletas | `grep` limpio | **No** en `CLAUDE.md` (`cost_kpi_tree`, módulos faltantes) |
| CHANGELOG actualizado | entrada de la versión | OK |
| `CLAUDE.md` actualizado | refleja módulos y comandos | **No** |
| `sphinx -W` | sin warnings | OK (pero cubre 4/15 módulos) |
| Versión: metadata == `__version__` | iguales | OK (sin test que lo proteja) |
| CI cubre todas las versiones de `classifiers` | 3.9–3.13 | **No** (3.9, 3.11, 3.13) |

## Seguimiento por fase

### Fase 0 y Fase 1 — cerradas el 2026-10-02

| Medida | Antes | Después |
|---|---|---|
| Tests | 357 | **637** (0 fallos); idéntico resultado en Python 3.9, 3.11 y 3.9 con dependencias mínimas (numpy 1.22, pandas 1.4, matplotlib 3.5, plotly 5.0) |
| Warnings | `-W error` pasaba | `filterwarnings = error` en `pyproject.toml` (solo se ignora un aviso de terceros) |
| Cobertura global | 80 % | **91 %** (`fail_under = 85` activo); `plotting.py` 0 % → 99 %; `__main__.py` 62 % → 98 % |
| Módulo público con menor cobertura | 0 % (`plotting.py`) | 81 % (`bottleneck.py`) |
| ruff (F,E9,B,I,S) | 82 errores | 43 (todos `F821` de anotaciones: tarea 2.1) |
| mypy | 78 errores | 78 (tarea 2.1/2.2) |
| Contrato de entradas (67 funciones) | 30 excepciones inesperadas, 2 bloqueos, 26 entradas basura aceptadas | **0** (test permanente `tests/test_contrato_entradas.py`) |
| Hallazgos cerrados | — | K-01…K-07, K-13 (fallback), N-01, N-04…N-07, N-08, N-09, N-10 parcial |
| Hallazgos no abordados a propósito | — | K-08 (magnitudes extremas 1e308/1e-320: se aceptan sin `ValueError`; impacto bajo, fuera del contrato) |

Notas de ejecución: `eoq_multi_constrained` ya no se cuelga con presupuesto ≤ 0; `mmc` es estable hasta `MAX_SERVIDORES = 10⁶`; las cotas de tamaño están en `_utils.py`.

### Fases 2, 3 y 4 — cerradas el 2026-10-02 (versión 0.3.0 preparada)

| Medida | Antes de la auditoría | Después |
|---|---|---|
| Tests | 357 | **1 165** (incluye 70 doctests, ejemplos del README y de `examples/`); 0 fallos en Python 3.9, 3.10, 3.11 y 3.13, y en 3.9 con dependencias mínimas |
| Cobertura | 80 % (módulo menor 0 %) | **94,6 %** (módulo menor 86,3 %) |
| ruff (F,E9,B,I,S) | 82 errores | **0** (también `benchmarks/`, `scripts/`, `examples/`) |
| mypy | 78 errores | **0** |
| Sphinx `-W` | pasa, 4 de 15 módulos | pasa, **13 páginas de referencia** (todos los símbolos de `__all__`, comprobado por test) |
| Ejemplos del README | 48 de 61 se ejecutan | **61 de 61** (`tests/test_readme.py`) |
| Funciones con `Raises` / `Examples` | 2 / 23 de 70 | **70 / 70** |
| Complejidad | `wagner_whitin` n=1000: 10,2 s; `neh_flowshop` n=200: 5,3 s | **0,06 s** y **0,12 s** |
| CI | solo `pytest` en 3.9/3.11/3.13 | ruff, mypy, cobertura global y por módulo, build + `twine check` + instalación de la rueda, Sphinx, `pip-audit`, matriz 3.9–3.13, mínimos y prueba semanal con las últimas versiones; la publicación verifica antes de publicar |
| `pip-audit` | limpio | limpio (ahora en el CI) |
| Paquete | sin `py.typed` | `py.typed` incluido y comprobado en la rueda |

**Pendiente (no ejecutado):**
- Merge del PR y creación del release `v0.3.0` en GitHub (esta sesión no puede crear releases).
- Habilitar `attestations` en la publicación: requiere probar con TestPyPI (fue la causa del fallo de v0.2.7).
- Traducción al español del *cuerpo* de los docstrings (los mensajes de error, avisos, CLI, README, docs y secciones nuevas ya están en español). Columnas de DataFrame, etiquetas de `summary()` y textos de gráficas siguen en inglés porque cambiarlos rompe la API (decisión D-6).
- K-08: magnitudes extremas (1e308, 1e-320) siguen sin rechazarse de forma explícita.
- Tags históricos v0.2.4 y v0.2.6 (D-5): no se crean; la laguna queda documentada en el CHANGELOG.
