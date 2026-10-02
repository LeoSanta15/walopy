"""Fixtures compartidas de la suite."""
from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture
def rng() -> np.random.Generator:
    """Generador aleatorio con semilla fija para tests reproducibles."""
    return np.random.default_rng(12345)
