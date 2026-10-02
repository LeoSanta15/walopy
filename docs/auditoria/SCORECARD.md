# SCORECARD — walopy

> Escala 0–5: 0 ausente · 1 rudimentario · 2 funcional · 3 sólido · 4 maduro · 5 excelente.
> **Antes:** medido el 2026-10-02 sobre `2cc17c1` (v0.2.8). **Objetivo:** nota esperada si se ejecuta el `ROADMAP.md` completo. **Después:** se rellena en el Paso 6 tras cada fase (hoy: pendiente).

| # | Dimensión | Antes | Objetivo | Después | Fase que lo mueve | Evidencia clave del "antes" |
|---|---|---|---|---|---|---|
| 1 | Estructura del repositorio | 3 | 4 | — | 0 | Sin `py.typed`, metadatos obsoletos, sin SECURITY/templates |
| 2 | Diseño de API pública | 3 | 4 | — | 1, 2 | Contrato de ingesta no uniforme; API del README ≠ API real |
| 3 | Validación de entradas | 2 | 4 | — | 1 | 30 excepciones de otro tipo, 2 bloqueos y 26 entradas basura aceptadas en el barrido |
| 4 | Corrección numérica | 3 | 4 | — | 1, 2 | 30/30 contra referencias independientes; `mmc` desborda; β recortado |
| 5 | Suite de pruebas | 3 | 4 | — | 1, 2 | 357 tests OK; cobertura 80 %; `plotting.py` 0 %; sin `conftest` |
| 6 | Tipado estático | 2 | 4 | — | 0, 2 | 78 errores mypy, 43 F821, sin `py.typed` |
| 7 | Gestión de dependencias | 3 | 4 | — | 0, 2 | Compatible con mínimos y máximos; sin pin de herramientas; `pip-audit` fuera del CI |
| 8 | CI/CD | 2 | 4 | — | 2 | Solo `pytest`; sin lint/tipos/build/docs/cobertura; matriz sin 3.10/3.12 |
| 9 | Documentación | 2 | 4 | — | 3 | 13/61 bloques del README fallan; 8 funciones sin documentar; Sphinx 4/15 módulos |
| 10 | Rendimiento | 1 | 3 | — | 2, 3 | Sin benchmarks; NEH y Wagner-Whitin cúbicos frente a lo documentado |
| 11 | Seguridad | 2 | 3 | — | 0, 2, 3 | Sin SECURITY ni `pip-audit` en CI; bloqueos por parámetros sin cota |
| 12 | Versionado y releases | 3 | 4 | — | 0, 4 | Fuente única OK; fallback obsoleto; tags v0.2.4/v0.2.6 ausentes |
| 13 | Comunidad y contribución | 2 | 3 | — | 0 | CONTRIBUTING de 6 líneas; sin templates ni CoC |
| 14 | Developer Experience | 2 | 4 | — | 0, 3 | `CLAUDE.md` desactualizado; sin `examples/` |
| | **GLOBAL (media)** | **2,4** | **3,8** | — | | |

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
