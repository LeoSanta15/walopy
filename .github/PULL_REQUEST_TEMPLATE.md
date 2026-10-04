## Resumen
<!-- Qué cambia y por qué (1–3 puntos) -->

## Tipo de cambio
- [ ] Corrección de bug (con test de regresión que falla en el tag anterior, entrada `W-nn` en `tests/regresiones.json` y ficha en `docs/referencia/BUG_CATALOG.md`)
- [ ] Nueva funcionalidad
- [ ] Documentación / mantenimiento
- [ ] Cambio que rompe compatibilidad (documentado en CHANGELOG)

## Lista de verificación ("terminado")
- [ ] `make check` termina con código 0 (lint, tipos, tests, cobertura global y por módulo, build, docs, ejemplos, referencias obsoletas y regresiones)
- [ ] Funciones nuevas: test de caso borde (vacío, NaN/inf, n mínimo, degenerado) y símbolo documentado
- [ ] Si corrige un bug: `make regresion` y `make mutaciones` en verde (R-16)
- [ ] La rama parte de `origin/main` (`git merge-base --is-ancestor origin/main HEAD`, R-17)
- [ ] Si sube la versión: solo en `src/walopy/__init__.py`, y `make release-check TAG=vX.Y.Z` correcto
- [ ] `CHANGELOG.md`, README y referencia Sphinx actualizados si aplica

## Plan de pruebas
<!-- Comandos ejecutados y resultado -->
