"""La versión tiene una sola fuente de verdad: el literal ``__version__`` de ``walopy/__init__.py``.

``pyproject.toml`` la lee con ``[tool.setuptools.dynamic]``. No se usa ``importlib.metadata.version()`` en
``__init__.py``: los metadatos se congelan al instalar y, tras subir la versión, ``__version__`` seguiría mostrando
la anterior hasta reinstalar (C-24).
"""
from __future__ import annotations

import ast
import re
from importlib.metadata import version
from pathlib import Path

import walopy

RAIZ = Path(__file__).resolve().parents[1]
INIT = RAIZ / "src" / "walopy" / "__init__.py"


def test_version_coincide_con_metadatos():
    """Falla si los metadatos instalados están obsoletos (tras subir la versión: ``make install``)."""
    assert walopy.__version__ == version("walopy"), "metadatos obsoletos: reinstala con `pip install -e .`"


def test_version_tiene_formato_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", walopy.__version__)


def test_la_version_es_un_literal_en_init():
    """El literal es lo que setuptools lee sin importar el paquete; sin él la fuente única se rompe."""
    arbol = ast.parse(INIT.read_text(encoding="utf-8"))
    asignaciones = [
        n for n in arbol.body
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "__version__" for t in n.targets)
    ]
    assert len(asignaciones) == 1
    assert isinstance(asignaciones[0].value, ast.Constant) and isinstance(asignaciones[0].value.value, str)


def test_init_no_lee_la_version_de_los_metadatos():
    assert "importlib.metadata" not in INIT.read_text(encoding="utf-8")


def test_pyproject_toma_la_version_dinamicamente_de_init():
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in texto
    assert re.search(r'version\s*=\s*\{\s*attr\s*=\s*"walopy\.__version__"\s*\}', texto)
    assert not re.search(r'(?m)^version\s*=\s*"\d', texto), "la versión no puede estar también como literal en pyproject.toml"
