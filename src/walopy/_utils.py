"""Internal validation helpers."""
from __future__ import annotations

import numpy as np


def as_positive(value: float, name: str) -> float:
    """Validate that a scalar is finite and strictly positive."""
    v = float(value)
    if not np.isfinite(v) or v <= 0:
        raise ValueError(f"'{name}' must be a finite positive number, got {value!r}.")
    return v


def as_nonneg(value: float, name: str) -> float:
    """Validate that a scalar is finite and non-negative."""
    v = float(value)
    if not np.isfinite(v) or v < 0:
        raise ValueError(f"'{name}' must be finite and >= 0, got {value!r}.")
    return v


def as_fraction(value: float, name: str) -> float:
    """Validate that a scalar is in [0, 1]."""
    v = float(value)
    if not (0.0 <= v <= 1.0):
        raise ValueError(f"'{name}' must be in [0, 1], got {value!r}.")
    return v
