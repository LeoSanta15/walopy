#!/bin/bash
# Stop: si la sesión cambió código, tests o configuración, corre `make check-fast` y, si falla, devuelve el error
# al agente (exit 2) para que lo corrija antes de terminar.
# - stop_hook_active=true en la entrada → exit 0 (evita bucles).
# - Sin cambios en código/tests/pyproject → no ejecuta nada.
set -uo pipefail

PYTHON="${PYTHON:-python}"
ENTRADA="$(cat || true)"

ACTIVO="$(printf '%s' "$ENTRADA" | "$PYTHON" -c 'import json,sys
try:
    print("1" if json.load(sys.stdin).get("stop_hook_active") else "0")
except Exception:
    print("0")' 2>/dev/null || echo 0)"
if [ "$ACTIVO" = "1" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}" || exit 0
git rev-parse --is-inside-work-tree > /dev/null 2>&1 || exit 0

# Cambios sin confirmar (incluye archivos nuevos) en código, tests, scripts, ejemplos, benchmarks o pyproject.
if ! git status --porcelain | grep -qE '^.. "?(src/|tests/|scripts/|examples/|benchmarks/|pyproject\.toml|Makefile)'; then
  exit 0
fi

command -v make > /dev/null 2>&1 || exit 0

SALIDA="$(make check-fast PYTHON="$PYTHON" 2>&1)"
ESTADO=$?
if [ "$ESTADO" -ne 0 ]; then
  {
    echo "make check-fast falló (código $ESTADO). Corrige el error antes de terminar:"
    echo
    printf '%s\n' "$SALIDA" | tail -n 60
  } >&2
  exit 2
fi
exit 0
