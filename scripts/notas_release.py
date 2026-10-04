"""Imprime las notas de un release a partir de ``CHANGELOG.md`` (la sección de esa versión).

Uso::

    python scripts/notas_release.py 0.3.0     # o v0.3.0
    make notas-release VERSION=0.3.0

Sale con código 1 si el CHANGELOG no tiene sección para esa versión.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def seccion(version: str, changelog: str) -> str | None:
    version = version[1:] if version.startswith("v") else version
    m = re.search(rf"(?ms)^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^---\s*$|^## \[|\Z)", changelog)
    return m.group(1).strip() if m else None


def main(version: str) -> int:
    texto = seccion(version, (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8"))
    if texto is None:
        print(f"ERROR: CHANGELOG.md no tiene una sección [{version}]", file=sys.stderr)
        return 1
    print(texto)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
