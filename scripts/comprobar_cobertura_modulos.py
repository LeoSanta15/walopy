"""Falla si algún módulo de walopy tiene una cobertura menor que el mínimo (por defecto 70 %).

Uso:  python -m pytest --cov=walopy --cov-report=json -q && python scripts/comprobar_cobertura_modulos.py [minimo]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(minimo: float = 70.0, ruta: str = "coverage.json") -> int:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    bajos = {
        nombre: info["summary"]["percent_covered"]
        for nombre, info in datos["files"].items()
        if info["summary"]["percent_covered"] < minimo
    }
    for nombre, pct in sorted(bajos.items()):
        print(f"cobertura insuficiente: {nombre} = {pct:.1f} % (mínimo {minimo:g} %)")
    if not bajos:
        menor = min(i["summary"]["percent_covered"] for i in datos["files"].values())
        print(f"OK: todos los módulos >= {minimo:g} % (el menor tiene {menor:.1f} %)")
    return 1 if bajos else 0


if __name__ == "__main__":
    sys.exit(main(float(sys.argv[1]) if len(sys.argv) > 1 else 70.0))
