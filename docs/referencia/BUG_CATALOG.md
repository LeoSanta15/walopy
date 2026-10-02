# BUG CATALOG — pccpy

> Fichas de todos los bugs verificados en el historial git + taxonomía de clases de error.
> Fuente: `git log --all --oneline` (102 commits), mensajes de commit, diffs.

---

## FICHAS DE BUGS

---

### BUG-01 · Zonas sigma no visibles en cartas asimétricas

| Campo | Detalle |
|---|---|
| **ID** | BUG-01 |
| **Síntoma** | Las cartas MR, R y S no mostraban las bandas ±1σ/±2σ aunque `zones=True` |
| **Causa raíz** | Condición `if zones and panel.symmetric` en `plotting.py` — las cartas asimétricas tienen `symmetric=False` y quedaban excluidas |
| **Cómo se detectó** | Revisión visual de salida de gráficos; commit de fix en v0.4.8 |
| **Solución aplicada** | Eliminada la condición `panel.symmetric`; matplotlib recorta naturalmente líneas por debajo del rango visible |
| **Archivo/línea** | `src/pccpy/plotting.py` (commit `314cb86`) |
| **Test de regresión** | NO VERIFICADO — no hay test que confirme que las zonas están presentes en cartas MR/R/S |
| **¿Puede ocurrir en otras libs?** | Sí — cualquier librería de visualización que añada condiciones de "simetría" para controlar trazado. |

---

### BUG-02 · `as_1d()` lanzaba `ValueError` opaco ante NaN/inf en datos

| Campo | Detalle |
|---|---|
| **ID** | BUG-02 |
| **Síntoma** | Usuarios con datos reales (ficheros CSV con celdas vacías) recibían `ValueError` sin contexto |
| **Causa raíz** | `as_1d()` llamaba `np.asarray(..., dtype=float)` que silenciosamente convierte NaN pero luego operaciones de scipy fallaban; no había filtrado previo |
| **Cómo se detectó** | Uso en producción / datos reales; commit `39bd66a` lo documenta como mejora de compatibilidad |
| **Solución aplicada** | Filtrado de valores no finitos con `UserWarning`; si no quedan valores válidos, `ValueError` con mensaje descriptivo |
| **Archivo/línea** | `src/pccpy/_data.py`, función `as_1d()` (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_charts.py` actualizado en `39bd66a` |
| **¿Puede ocurrir en otras libs?** | Sí — es el error más común en librerías científicas que reciben datos de usuarios finales. |

---

### BUG-03 · `to_subgroups()` fallaba con DataFrame con columnas de texto

| Campo | Detalle |
|---|---|
| **ID** | BUG-03 |
| **Síntoma** | Error `"could not convert string to float"` al pasar un DataFrame con columna de fecha o etiqueta |
| **Causa raíz** | `np.asarray(df)` sin filtrar columnas no numéricas |
| **Cómo se detectó** | Uso con datos industriales reales; commit `39bd66a` |
| **Solución aplicada** | Filtrado automático de columnas no numéricas con `UserWarning` que sugiere `subgroup='nombre_columna'` |
| **Archivo/línea** | `src/pccpy/_data.py`, función `to_subgroups()` (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_charts.py` actualizado |
| **¿Puede ocurrir en otras libs?** | Sí — cualquier librería que acepte DataFrames como entrada de subgrupos. |

---

### BUG-04 · `capability_analysis()` lanzaba `ValueError` sin límites de especificación

| Campo | Detalle |
|---|---|
| **ID** | BUG-04 |
| **Síntoma** | `capability_analysis(x)` sin `lsl`/`usl` lanzaba `ValueError("Se requiere al menos lsl o usl")` |
| **Causa raíz** | Diseño de API que asumía que los límites son siempre necesarios; no consideró el caso exploratorio |
| **Cómo se detectó** | Uso real; commit `39bd66a` |
| **Solución aplicada** | `lsl` y `usl` son ahora opcionales; sin ellos los índices Cp/Cpk/Pp/Ppk se devuelven como `NaN` |
| **Archivo/línea** | `src/pccpy/capability.py` (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_capability.py` actualizado |
| **¿Puede ocurrir en otras libs?** | Sí — patrón frecuente en APIs estadísticas con parámetros que "siempre" se necesitan en producción. |

---

### BUG-05 · `ZeroDivisionError` en `capability_analysis()` con datos constantes

| Campo | Detalle |
|---|---|
| **ID** | BUG-05 |
| **Síntoma** | `capability_analysis(np.ones(30))` lanzaba `ZeroDivisionError` o `ValueError` |
| **Causa raíz** | `_indices()`, `_expected_ppm()` y `_z_bench()` no manejaban `sigma=0` |
| **Cómo se detectó** | Commit `39bd66a`; caso límite de datos de proceso en calibración |
| **Solución aplicada** | Retorno de `NaN` con `UserWarning` al detectar desviación estándar = 0 |
| **Archivo/línea** | `src/pccpy/capability.py` funciones privadas (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_capability.py` actualizado |
| **¿Puede ocurrir en otras libs?** | Sí — división por cero con sigma en cualquier análisis estadístico. |

---

### BUG-06 · `zone_chart` fallaba con nuevo error de `subgroup_size=1`

| Campo | Detalle |
|---|---|
| **ID** | BUG-06 |
| **Síntoma** | `zone_chart(data)` con datos individuales fallaba internamente con el nuevo error de validación de `to_subgroups()` |
| **Causa raíz** | `to_subgroups(arr, 1)` fue modificado para rechazar `subgroup_size=1` con mensaje que apunta a `imr_chart()`. `zone_chart` usa internamente `to_subgroups` con tamaño 1. |
| **Cómo se detectó** | Commit `39bd66a` — detectado al aplicar la validación general de `subgroup_size=1` |
| **Solución aplicada** | Añadido parámetro `_allow_size_1=True` para llamadas internas legítimas |
| **Archivo/línea** | `src/pccpy/_data.py`, `src/pccpy/charts/advanced.py` (commit `39bd66a`) |
| **Test de regresión** | SÍ — `test_advanced_charts.py` existente cubre `zone_chart` |
| **¿Puede ocurrir en otras libs?** | Sí — añadir validación de entrada puede romper llamadas internas que usan el mismo camino. |

---

### BUG-07 · Import de openpyxl daba error opaco sin orientación al usuario

| Campo | Detalle |
|---|---|
| **ID** | BUG-07 |
| **Síntoma** | `result.to_excel("salida.xlsx")` lanzaba `ImportError: No module named 'openpyxl'` sin mensaje de qué instalar |
| **Causa raíz** | El `ImportError` de `pd.ExcelWriter(engine="openpyxl")` se propagaba sin capturar |
| **Cómo se detectó** | Commit `39bd66a` / v0.10.7; openpyxl es dependencia opcional |
| **Solución aplicada** | Helper `_excel_writer()` en `_data.py` que captura `ImportError` y da instrucción explícita `pip install pccpy[excel]` |
| **Archivo/línea** | `src/pccpy/_data.py`, función `_excel_writer()` (commit `39bd66a`) |
| **Test de regresión** | NO VERIFICADO — no hay test que simule ausencia de openpyxl |
| **¿Puede ocurrir en otras libs?** | Sí — patrón universal para dependencias opcionales. |

---

### BUG-08 · CI tests.yml tenía referencias a `spyc` tras el renombre

| Campo | Detalle |
|---|---|
| **ID** | BUG-08 |
| **Síntoma** | CI corría `pytest --cov=spyc` y `mypy src/spyc` — el módulo ya no existía |
| **Causa raíz** | El renombre de módulo no actualizó los workflows de GitHub Actions |
| **Cómo se detectó** | Primer run de CI tras el renombre; commit `3de6dc5` |
| **Solución aplicada** | Sed en los workflows: `--cov=spyc → --cov=pccpy`, `src/spyc → src/pccpy` |
| **Archivo/línea** | `.github/workflows/tests.yml`, `.github/workflows/publish.yml` (commit `3de6dc5`) |
| **Test de regresión** | N/A — es un bug de infraestructura CI |
| **¿Puede ocurrir en otras libs?** | Sí — renombres de paquete deben incluir todos los artefactos de CI. |

---

### BUG-09 · PEP 639: `license` SPDX + classifier duplicado con setuptools>=77

| Campo | Detalle |
|---|---|
| **ID** | BUG-09 |
| **Síntoma** | `python -m build` fallaba con error de setuptools sobre license classifier duplicado |
| **Causa raíz** | PEP 639 adoptado en setuptools>=77: `license = "MIT"` y `License :: OSI Approved :: MIT License` son mutuamente excluyentes |
| **Cómo se detectó** | Al intentar publicar en PyPI; commit `e894a25` |
| **Solución aplicada** | Eliminar el classifier `License :: ...` del `pyproject.toml` |
| **Archivo/línea** | `pyproject.toml` (commit `e894a25`) |
| **Test de regresión** | N/A — build funciona. Se podría añadir `twine check dist/*` al CI |
| **¿Puede ocurrir en otras libs?** | Sí — cualquier paquete que migre a setuptools>=77 sin revisar PEP 639. |

---

### BUG-10 · Python 3.9: `stats.normaltest` lanza `ValueError` para n < 8

| Campo | Detalle |
|---|---|
| **ID** | BUG-10 |
| **Síntoma** | `diagnose(x)` con menos de 8 puntos fallaba en Python 3.9 (`ValueError` de scipy) |
| **Causa raíz** | En Python 3.11+, `scipy.stats.normaltest` emite `SmallSampleWarning` para n<8. En Python 3.9 con scipy más antiguo lanza `ValueError`. No se manejaba la excepción. |
| **Cómo se detectó** | CI multi-versión; commit `44f7f69` |
| **Solución aplicada** | Guardar n antes del `try`; capturar la excepción y devolver resultado parcial |
| **Archivo/línea** | `src/pccpy/_diagnose.py` (commit `44f7f69`) |
| **Test de regresión** | SÍ — `test_diagnose.py` cubre casos con n < 8 |
| **¿Puede ocurrir en otras libs?** | Sí — scipy cambia comportamiento de warnings/errores entre versiones menores. |

---

### BUG-11 · Sphinx: `autoclass WidgetSession` generaba advertencia duplicada

| Campo | Detalle |
|---|---|
| **ID** | BUG-11 |
| **Síntoma** | `sphinx-build -W` fallaba con 18 warnings (duplicados y referencias cruzadas ambiguas) |
| **Causa raíz** | `wizard.md` usaba `.. autoclass:: pccpy.WidgetSession` cuando ya estaba documentado en otro lugar; referencias cruzadas sin namespace explícito |
| **Cómo se detectó** | CI job `documentacion`; commit `819ca11` |
| **Solución aplicada** | Reemplazar `autoclass` con tabla Markdown manual en `wizard.md`; corregir referencias cruzadas |
| **Archivo/línea** | `docs/source/referencia/wizard.rst`, `docs/source/wizard.md` (commit `819ca11`) |
| **Test de regresión** | SÍ — CI corre `sphinx-build -W` |
| **¿Puede ocurrir en otras libs?** | Sí — `autoclass` + documentación manual del mismo símbolo siempre genera duplicado. |

---

### BUG-12 · Plots contaminaban estilos globales de matplotlib (incompatibilidad con seaborn)

| Campo | Detalle |
|---|---|
| **ID** | BUG-12 |
| **Síntoma** | En entornos con seaborn importado antes de pccpy, los gráficos de control aparecían con estilos de seaborn; viceversa, pccpy alteraba los gráficos del usuario |
| **Causa raíz** | Las funciones `plot_*` modificaban `rcParams` globalmente sin restaurar el estado anterior |
| **Cómo se detectó** | Uso en Jupyter con seaborn; commit `786fccb` |
| **Solución aplicada** | Envolver todas las funciones `plot_*` en `plt.rc_context({})` |
| **Archivo/línea** | `src/pccpy/plotting.py`, `src/pccpy/quality_tools.py` (commit `786fccb`) |
| **Test de regresión** | NO VERIFICADO — no hay test que verifique aislamiento de estilos |
| **¿Puede ocurrir en otras libs?** | Sí — cualquier librería de visualización que no use `rc_context`. |

---

## TAXONOMÍA DE CLASES DE ERROR

| Clase | Descripción | Cómo prevenirla | Cómo detectarla | Bugs en este proyecto |
|---|---|---|---|---|
| **C-01 Validación de entrada faltante** | La función acepta datos inválidos (NaN, inf, tipo incorrecto, vacío) y falla con error opaco aguas abajo | Capa de validación explícita en cada función pública; tests con entradas malformadas | `pytest` con casos borde; `mypy` para tipos | BUG-02, BUG-03, BUG-05 |
| **C-02 Caso degenerado no considerado** | El diseño de API no contempló valores extremos válidos (sin límites, datos constantes, n<8) | Listar casos degenerados al diseñar la API; documentar en docstring | Tests parametrizados con valores límite | BUG-04, BUG-05, BUG-10 |
| **C-03 Import opcional sin mensaje orientativo** | Dependencia opcional ausente genera `ImportError` crudo sin guía al usuario | Capturar `ImportError` de opcionales; mensaje con `pip install ...` | Test que simula ausencia con `unittest.mock` | BUG-07 |
| **C-04 CI que no detecta el fallo** | El build/test local pasa pero CI falla por diferencia de entorno (versión Python, Node) | Correr la matrix localmente con tox antes del PR; CI fail-fast desactivado | Primera ejecución en CI; logs de CI | BUG-08, BUG-09, BUG-10, BUG-11 |
| **C-05 Documentación desactualizada** | Código o comandos en docs/CLAUDE.md apuntan al estado anterior | Incluir docs en el checklist de cada PR; grep de términos obsoletos en CI | Grep automatizado; revisión de CLAUDE.md en cada sesión | BUG-08, L-01, L-07 |
| **C-06 Efecto secundario de refactor** | Validación añadida en función base rompe llamada interna válida | Al añadir validación, buscar todas las llamadas internas con `grep`; añadir parámetro escape-hatch explícito | Tests de integración de módulos que se llaman entre sí | BUG-06 |
| **C-07 Estado global de entorno** | La librería modifica estado global (rcParams) contaminando el entorno del usuario | Usar context managers (`rc_context`, `warnings.catch_warnings`) | Test que verifica estado antes/después de la llamada | BUG-12 |
| **C-08 Versión múltiple fuente** | La versión se gestiona en N>1 lugares y se desincroniza | Única fuente de verdad: `importlib.metadata` o `setuptools-scm` | `assert pccpy.__version__ == importlib.metadata.version("pccpy")` en test | L-10 |
