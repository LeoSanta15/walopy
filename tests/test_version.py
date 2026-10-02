"""La versión tiene una sola fuente de verdad: pyproject.toml (vía metadatos)."""
from __future__ import annotations

from importlib.metadata import version

import walopy


def test_version_coincide_con_metadatos():
    assert walopy.__version__ == version("walopy")


def test_version_tiene_formato_semver():
    partes = walopy.__version__.split(".")
    assert len(partes) == 3 and all(p.isdigit() for p in partes)


def test_sin_instalar_la_version_es_desconocida(monkeypatch):
    """Si no hay metadatos (ejecución desde el código fuente) no se inventa una versión antigua."""
    import importlib
    import importlib.metadata as md

    def sin_paquete(nombre):
        raise md.PackageNotFoundError(nombre)

    monkeypatch.setattr(md, "version", sin_paquete)
    try:
        recargado = importlib.reload(walopy)
        assert recargado.__version__ == "0+unknown"
    finally:
        monkeypatch.undo()
        importlib.reload(walopy)
    assert walopy.__version__ == version("walopy")
