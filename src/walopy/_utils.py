"""Validadores internos: única capa de ingesta numérica de walopy.

Todo argumento numérico que llega del usuario debe pasar por estas funciones.
NaN e infinito se rechazan *antes* de comparar (``x <= 0`` es ``False`` para NaN).
"""
from __future__ import annotations

from typing import Any

import numpy as np


def _to_float(value: Any, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(f"'{name}' debe ser un número, se recibió un booleano ({value!r}).")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise TypeError(f"'{name}' debe ser un número, se recibió {type(value).__name__!r}.") from None


def as_positive(value: float, name: str) -> float:
    """Valida que un escalar sea finito y estrictamente positivo."""
    v = _to_float(value, name)
    if not np.isfinite(v) or v <= 0:
        raise ValueError(f"'{name}' debe ser un número finito y positivo, se recibió {value!r}.")
    return v


def as_nonneg(value: float, name: str) -> float:
    """Valida que un escalar sea finito y no negativo."""
    v = _to_float(value, name)
    if not np.isfinite(v) or v < 0:
        raise ValueError(f"'{name}' debe ser finito y >= 0, se recibió {value!r}.")
    return v


def as_fraction(value: float, name: str) -> float:
    """Valida que un escalar esté en [0, 1]."""
    v = _to_float(value, name)
    if not np.isfinite(v) or not (0.0 <= v <= 1.0):
        raise ValueError(f"'{name}' debe ser un valor finito en [0, 1], se recibió {value!r}.")
    return v


# Cotas de tamaño: evitan cálculos de duración prácticamente infinita con parámetros absurdos.
MAX_SERVIDORES = 10**6
MAX_ESTADOS = 10**6
MAX_CLIENTES = 10**7


def as_int_positive(value: int, name: str, *, max: int | None = None) -> int:
    """Valida que un valor sea un entero positivo (acepta enteros de numpy; rechaza float y bool).

    Si se indica ``max``, rechaza valores mayores (cota para evitar bloqueos).
    """
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(
            f"'{name}' debe ser un entero positivo, se recibió {type(value).__name__!r} = {value!r}."
        )
    v = int(value)
    if v < 1:
        raise ValueError(f"'{name}' debe ser >= 1, se recibió {value!r}.")
    if max is not None and v > max:
        raise ValueError(f"'{name}' no puede superar {max}, se recibió {value!r}.")
    return v


def as_nonempty(seq: Any, name: str) -> None:
    """Lanza ValueError si la secuencia está vacía."""
    if len(seq) == 0:
        raise ValueError(f"'{name}' debe contener al menos un elemento.")


def as_finite_scalar(value: float, name: str) -> float:
    """Acepta cualquier número real finito (positivo, cero o negativo)."""
    v = _to_float(value, name)
    if not np.isfinite(v):
        raise ValueError(f"'{name}' debe ser un número finito, se recibió {value!r}.")
    return v


def as_float_list(seq: Any, name: str, *, kind: str = "positive", min_len: int = 1) -> list[float]:
    """Convierte una secuencia en ``list[float]`` validando cada elemento.

    ``kind``: ``'positive'`` (> 0), ``'nonneg'`` (>= 0) o ``'finite'`` (cualquier real finito).
    Rechaza cadenas, escalares y diccionarios; exige al menos ``min_len`` elementos.
    """
    if isinstance(seq, (str, bytes, dict)) or not hasattr(seq, "__iter__"):
        raise TypeError(f"'{name}' debe ser una secuencia de números, se recibió {type(seq).__name__!r}.")
    check = {"positive": as_positive, "nonneg": as_nonneg, "finite": as_finite_scalar}[kind]
    out = [check(v, f"{name}[{i}]") for i, v in enumerate(seq)]
    if len(out) < min_len:
        if min_len == 1:
            raise ValueError(f"'{name}' debe contener al menos un elemento.")
        raise ValueError(f"'{name}' debe contener al menos {min_len} elementos, se recibieron {len(out)}.")
    return out
