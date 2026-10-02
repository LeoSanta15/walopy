# Política de seguridad

## Versiones soportadas

Se corrigen vulnerabilidades en la última versión publicada en PyPI.

## Cómo reportar una vulnerabilidad

**No abras un issue público.** Usa el aviso privado de GitHub:
<https://github.com/LeoSanta15/walopy/security/advisories/new>

Incluye: versión de walopy y de Python, pasos para reproducir y el impacto esperado.
Se acusa recibo en un plazo de 7 días.

## Alcance

walopy es una librería de cálculo: no ejecuta código recibido del usuario (`eval`, `exec`, `pickle` o
`subprocess` no se usan) ni abre conexiones de red. Se consideran vulnerabilidades, entre otras, los
bloqueos o consumos de memoria ilimitados provocados por parámetros válidos y las dependencias con
CVE conocidas.
