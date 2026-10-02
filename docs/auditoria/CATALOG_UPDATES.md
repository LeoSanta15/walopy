# CATALOG_UPDATES — lecciones nuevas para el Playbook y el catálogo

> Lecciones obtenidas al auditar walopy v0.2.8 que **no estaban** en `BUG_CATALOG.md` / `LESSONS_LEARNED.md` / `PLAYBOOK.md`.
> Formato de las clases nuevas: nombre · descripción · prevención · detección · hallazgos de walopy.

## Clases de error nuevas (candidatas a C-09 en adelante)

| Clase | Descripción | Cómo prevenirla | Cómo detectarla | Hallazgos |
|---|---|---|---|---|
| **C-09 NaN pasa las comparaciones** | `if x <= 0: raise` no rechaza NaN (la comparación es `False`); `inf` tampoco. El valor llega al cálculo y produce `nan`, `inf` o `OverflowError` | Validar siempre con `math.isfinite`/`np.isfinite` **antes** de comparar; toda conversión de dato de usuario pasa por el validador central | Barrido automático con `[nan, inf, -inf, -1, 0, None, "x"]` por cada argumento y comprobar que solo salen `ValueError`/`TypeError` o resultados finitos | K-01, K-02, K-05 |
| **C-10 Documentación con API inventada** | Los ejemplos del README usan parámetros o atributos que no existen (la documentación se escribió sin ejecutarla) | Convertir los bloques de código de README/docs en tests (`tests/test_readme.py`); marcar explícitamente los no ejecutables | Ejecutar todos los bloques ```python del README en un script | K-10 |
| **C-11 Complejidad documentada ≠ real** | El docstring o el CHANGELOG anuncian O(n²) y la implementación recalcula sumas o recorridos y es O(n³) | Medir con tamaños crecientes antes de anunciar una complejidad; benchmark en `benchmarks/` | Tabla de tiempos n=100/400/1000 y ajuste del exponente | N-03 |
| **C-12 Desbordamiento por fórmula directa** | Potencias y factoriales explícitos (`a**n / n!`) desbordan `float` para tamaños realistas (c ≥ ~143) | Usar recurrencias estables (Erlang-B), `lgamma` o logaritmos; probar con tamaños 10× el caso típico | Prueba de escala: c = 150, 300, 1000 contra el balance de nacimiento-muerte | K-06 |
| **C-13 Registros duplicados fusionados en silencio** | Entradas tipo lista de diccionarios con clave de identidad (`name`) se vuelcan en un `dict` y la última pisa a la primera | Detectar duplicados al ingerir y lanzar error | Test con dos registros con el mismo nombre | N-04 |
| **C-14 Validación solo en parte de las rutas** | La capa central existe (`_utils`) pero funciones nuevas hacen `float(x)` y comparan por su cuenta | Lint/revisión: todo `float(` sobre argumentos de usuario debe pasar por `_utils`; test de contrato que recorra `__all__` | Test que itera todas las funciones públicas | K-01, K-02, K-03 |
| **C-15 CI verde que no verifica** | El CI ejecuta solo los tests; ruff, mypy, build, docs y cobertura fallan o no se miden y nadie lo ve | Los gates del Playbook (lint, tipos, cobertura, build, docs, audit) deben estar **en el CI**, no solo en la lista de comandos | Comparar `ci.yml` con la batería del Playbook; ejecutar la batería localmente | K-12 |
| **C-16 Cota numérica que recorta en silencio** | Un solucionador con intervalo fijo (`hi = 100`) devuelve el extremo cuando la solución está fuera, sin avisar | Avisar (`UserWarning`) o fallar cuando el resultado toca la cota; documentar el rango | Datos degenerados (constantes) y casi constantes | K-05 |
| **C-17 Funcionalidad publicada sin documentación** | Se publican versiones con funciones nuevas que no aparecen en README/Sphinx; el documento de referencia queda congelado | "Definición de terminado": cada símbolo nuevo de `__all__` aparece en la documentación; test que lo compruebe | Test que compare `__all__` con los símbolos documentados | K-11 |
| **C-18 Parámetros sin cota → bloqueo** | Argumentos de tamaño (`n_customers`, `K`, `budget ≤ 0` en una búsqueda iterativa) permiten cálculos que no terminan | Cotas máximas con mensaje; límite de iteraciones en bucles de búsqueda | Barrido con valores 1e7, 1e9, 0 y negativos con `signal.alarm` | K-07, N-06 |

## Lecciones nuevas (formato LESSONS_LEARNED)

**L-11 · El barrido de entradas malformadas encuentra más que los tests escritos a mano (IMPACTO: ALTO).**
*¿Qué pasó?* 357 tests pasan, pero un barrido automático de más de mil entradas sobre 67 funciones halló 30 excepciones inesperadas, 2 bloqueos y decenas de entradas basura aceptadas. *¿Por qué?* Los tests prueban lo que su autor imaginó; no recorren sistemáticamente la matriz argumento × valor patológico. *¿Cómo evitarlo?* Mantener el barrido como test permanente (tabla de llamadas válidas + valores patológicos); es barato (< 1 minuto) y protege a toda función nueva.

**L-12 · Las validaciones centralizadas solo protegen si son obligatorias (IMPACTO: ALTO).**
*¿Qué pasó?* `_utils.py` rechaza bien NaN/inf, pero las funciones añadidas en v0.2.6–v0.2.8 (CPM, Weibull, MTBF, MRP) no lo usan en todos los argumentos. *¿Cómo evitarlo?* Test de contrato sobre `__all__` + regla de revisión "todo argumento numérico de usuario pasa por `_utils`".

**L-13 · Un resultado correcto en el caso típico no demuestra corrección a escala (IMPACTO: MEDIO).**
*¿Qué pasó?* Las 30 comprobaciones numéricas pasan, pero `mmc` desborda con c ≥ ~143 y Wagner-Whitin/NEH son cúbicos. *¿Cómo evitarlo?* Añadir al validar contra referencia independiente un caso 10× mayor que el típico y medir el tiempo.

**L-14 · La documentación larga no es documentación verificada (IMPACTO: ALTO).**
*¿Qué pasó?* Un README de 1 622 líneas tiene 13 de 61 ejemplos que no se ejecutan y 8 funciones nuevas sin mención. *¿Cómo evitarlo?* Ejecutar los ejemplos en CI y comparar `__all__` con la documentación.

**L-15 · Una versión puede salir con todo en verde y sin los gates del Playbook (IMPACTO: ALTO).**
*¿Qué pasó?* v0.2.8 se publicó con CI verde, pero ruff (82–215 errores) y mypy (78) fallan y la cobertura es 80 %. *¿Cómo evitarlo?* El CI refleja la "definición de terminado"; el release depende de todos los jobs.

**L-16 · Mezclar "fusionar a main" con conflictos de historiales divergentes es frágil (IMPACTO: MEDIO).**
*¿Qué pasó?* La rama de trabajo se creó desde un commit antiguo (v0.2.0) y el PR de v0.2.8 tuvo conflictos en 6 archivos que hubo que resolver manualmente en dos rondas; `git fetch origin main` dejó una referencia local desactualizada. *¿Cómo evitarlo?* Crear cada rama desde `origin/main` recién traído; tras un merge squash, reiniciar la rama desde `main`.

## Cambios propuestos al PLAYBOOK

1. **Nivel 2 → Linter:** exigir `ruff` y `mypy` **como jobs del CI**, no solo como comandos locales.
2. **Nivel 2 → Tests:** añadir "barrido de entradas malformadas (NaN/inf/negativos/None/str/vacío) sobre todo `__all__`" como criterio.
3. **Nivel 3 → Documentación:** añadir "los ejemplos del README se ejecutan en CI" y "cada símbolo de `__all__` está documentado".
4. **Nivel 3 → Validación:** añadir "ninguna función pública lanza `ZeroDivisionError`/`OverflowError`/`KeyError`/`AttributeError` por entrada de usuario".
5. **Nivel 4 → Soporte multi-versión:** añadir "pruebas con las versiones mínimas de dependencias" (`uv pip install --resolution lowest-direct`) además de la versión mínima de Python.
6. **Nivel 5 → Rendimiento:** añadir "complejidad anunciada verificada empíricamente" y "casos a escala 10×".
7. **Plantilla de auditoría:** incorporar los scripts de esta auditoría (barrido de entradas, ejecución de bloques del README, validación contra scipy/networkx/fuerza bruta) como herramientas reutilizables.
8. **Excepción razonada en dependencias:** el Playbook pide cotas superiores (`<3`); para librerías de uso general conviene probar contra las versiones más recientes (job semanal) en lugar de limitarlas.

## Cambios propuestos a CLAUDE_MD_RULES

- **R-13 (nueva):** *Todo argumento numérico de usuario se valida con `math.isfinite` antes de comparar.* (C-09)
- **R-14 (nueva):** *Al añadir una función a `__all__`, añadirla a la documentación y a los tests de contrato de entrada.* (C-14, C-17)
- **R-15 (nueva):** *Cada complejidad anunciada tiene un benchmark que la respalda.* (C-11)
- **R-16 (nueva):** *Los ejemplos de README/docs son tests.* (C-10)
