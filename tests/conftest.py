"""Fixtures compartidas de la suite."""
from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def _idioma_por_defecto(monkeypatch: pytest.MonkeyPatch):
    """Cada test empieza en español: sin ``WALOPY_LANG`` ni ``set_language()`` de otro test (los textos por defecto son los de siempre)."""
    from walopy import _i18n

    monkeypatch.delenv("WALOPY_LANG", raising=False)
    monkeypatch.setattr(_i18n, "_global", None)


@pytest.fixture
def rng() -> np.random.Generator:
    """Generador aleatorio con semilla fija para tests reproducibles."""
    return np.random.default_rng(12345)
