"""Internal validation helpers."""
from __future__ import annotations

import numpy as np


def as_positive(value: float, name: str) -> float:
    """Validate that a scalar is finite and strictly positive."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise TypeError(f"'{name}' must be a number, got {type(value).__name__!r}.")
    if not np.isfinite(v) or v <= 0:
        raise ValueError(f"'{name}' must be a finite positive number, got {value!r}.")
    return v


def as_nonneg(value: float, name: str) -> float:
    """Validate that a scalar is finite and non-negative."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise TypeError(f"'{name}' must be a number, got {type(value).__name__!r}.")
    if not np.isfinite(v) or v < 0:
        raise ValueError(f"'{name}' must be finite and >= 0, got {value!r}.")
    return v


def as_fraction(value: float, name: str) -> float:
    """Validate that a scalar is in [0, 1]."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise TypeError(f"'{name}' must be a number, got {type(value).__name__!r}.")
    if not np.isfinite(v) or not (0.0 <= v <= 1.0):
        raise ValueError(f"'{name}' must be a finite value in [0, 1], got {value!r}.")
    return v


def as_int_positive(value: int, name: str) -> int:
    """Validate that a value is a positive integer (accepts numpy integer types)."""
    # Accept Python int and numpy integer scalars; reject float (even 2.0)
    if not isinstance(value, (int, np.integer)):
        raise TypeError(
            f"'{name}' must be a positive integer, got {type(value).__name__!r} = {value!r}."
        )
    v = int(value)
    if v < 1:
        raise ValueError(f"'{name}' must be >= 1, got {value!r}.")
    return v


def as_nonempty(seq: list, name: str) -> None:
    """Raise ValueError if sequence is empty."""
    if len(seq) == 0:
        raise ValueError(f"'{name}' must contain at least one element.")


def as_finite_scalar(value: float, name: str) -> float:
    """Accept any finite real number (positive, zero, or negative)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise TypeError(f"'{name}' must be a number, got {type(value).__name__!r}.")
    if not np.isfinite(v):
        raise ValueError(f"'{name}' must be a finite number, got {value!r}.")
    return v
