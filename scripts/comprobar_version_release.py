"""Comprueba que la versión del wheel construido coincide con la del tag de release.

Uso::

    python scripts/comprobar_version_release.py v0.3.0 [directorio_dist]

Sale con código 0 si todos los artefactos de ``dist/`` (wheel y sdist) tienen la versión del tag y con 1 si no
coinciden o no hay artefactos. Un tag creado antes de subir la versión produce artefactos antiguos y PyPI
responde ``400 File exists``: esta comprobación lo detecta antes de publicar.
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path


def version_del_wheel(ruta: Path) -> str:
    with zipfile.ZipFile(ruta) as z:
        metadata = next(n for n in z.namelist() if n.endswith(".dist-info/METADATA"))
        m = re.search(r"(?m)^Version: (\S+)$", z.read(metadata).decode("utf-8"))
    if m is None:
        raise ValueError(f"{ruta.name}: METADATA sin campo Version")
    return m.group(1)


def main(tag: str, dist: str = "dist") -> int:
    esperada = tag[1:] if tag.startswith("v") else tag
    ruedas = sorted(Path(dist).glob("*.whl"))
    sdists = sorted(Path(dist).glob("*.tar.gz"))
    if not ruedas or not sdists:
        print(f"ERROR: faltan artefactos en {dist}/ (wheel: {len(ruedas)}, sdist: {len(sdists)}); ejecuta `python -m build`")
        return 1
    problemas = 0
    for rueda in ruedas:
        v = version_del_wheel(rueda)
        ok = v == esperada
        print(f"{'OK ' if ok else 'MAL'} {rueda.name}: versión {v} (tag {tag})")
        problemas += 0 if ok else 1
    for sdist in sdists:
        ok = sdist.name == f"walopy-{esperada}.tar.gz"
        print(f"{'OK ' if ok else 'MAL'} {sdist.name} (se esperaba walopy-{esperada}.tar.gz)")
        problemas += 0 if ok else 1
    if problemas:
        print(f"ERROR: el tag {tag} no coincide con la versión construida; sube la versión en src/walopy/__init__.py antes de crear el tag")
    return 1 if problemas else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(*sys.argv[1:3]))
