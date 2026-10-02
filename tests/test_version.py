"""La versión tiene una sola fuente de verdad: pyproject.toml (vía metadatos)."""
from __future__ import annotations

from importlib.metadata import version

import walopy


def test_version_coincide_con_metadatos():
    assert walopy.__version__ == version("walopy")


def test_version_tiene_formato_semver():
    partes = walopy.__version__.split(".")
    assert len(partes) == 3 and all(p.isdigit() for p in partes)
