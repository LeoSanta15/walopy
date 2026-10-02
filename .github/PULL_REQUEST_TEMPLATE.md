## Resumen
<!-- Qué cambia y por qué (1–3 puntos) -->

## Tipo de cambio
- [ ] Corrección de bug (con test de regresión que falla en el tag anterior, entrada `W-nn` en `tests/regresiones.json` y ficha en `docs/referencia/BUG_CATALOG.md`)
- [ ] Nueva funcionalidad
- [ ] Documentación / mantenimiento
- [ ] Cambio que rompe compatibilidad (documentado en CHANGELOG)

## Lista de verificación ("terminado")
- [ ] `python -m pytest tests/ -q` sin fallos
- [ ] `python -m ruff check src/ tests/` limpio
- [ ] `python -m mypy src/walopy --ignore-missing-imports` limpio
- [ ] Cobertura global ≥ 85 % y ningún módulo público < 70 %
- [ ] Funciones nuevas: test de caso borde (vacío, NaN/inf, n mínimo, degenerado) y símbolo documentado
- [ ] Si corrige un bug: `python scripts/verificar_regresion.py --manifiesto tests/regresiones.json` en verde (R-16)
- [ ] La rama parte de `origin/main` (`git merge-base --is-ancestor origin/main HEAD`, R-17)
- [ ] `CHANGELOG.md`, README y referencia Sphinx actualizados si aplica

## Plan de pruebas
<!-- Comandos ejecutados y resultado -->
