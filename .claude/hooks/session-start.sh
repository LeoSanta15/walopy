#!/bin/bash
# SessionStart: prepara el entorno en Claude Code en la web. Síncrono, idempotente y sin preguntas.
# En local (CLAUDE_CODE_REMOTE distinto de "true") no hace nada.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
PYTHON="${PYTHON:-python}"

# Instalación editable con extras de desarrollo, release y docs (instala solo lo que falte; repetirla es inocuo).
"$PYTHON" -m pip install --quiet --disable-pip-version-check -e ".[dev,release,docs]"

# `make regresion` necesita los tags de git; si no hay red no es un error de la sesión.
git fetch --tags --quiet origin 2>/dev/null || true

# Gráficas sin pantalla para todos los comandos de la sesión.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export MPLBACKEND=Agg' >> "$CLAUDE_ENV_FILE"
fi

echo "walopy listo: $("$PYTHON" -c 'import walopy; print(walopy.__version__)')"
