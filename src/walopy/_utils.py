"""Validadores internos: única capa de ingesta numérica de walopy.

Todo argumento numérico que llega del usuario debe pasar por estas funciones.
NaN e infinito se rechazan *antes* de comparar (``x <= 0`` es ``False`` para NaN).
"""
from __future__ import annotations

from typing import Any

import numpy as np

from ._i18n import t as _t


def _to_float(value: Any, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise TypeError(_t("utils.error.to_float.debe_ser_numero_recibio_booleano", name=name, value=value))
    try:
        return float(value)
    except (TypeError, ValueError):
        raise TypeError(_t("utils.error.to_float.debe_ser_numero_recibio", name=name, __name__=type(value).__name__)) from None


def as_positive(value: float, name: str) -> float:
    """Valida que un escalar sea finito y estrictamente positivo."""
    v = _to_float(value, name)
    if not np.isfinite(v) or v <= 0:
        raise ValueError(_t("utils.error.as_positive.debe_ser_numero_finito_positivo", name=name, value=value))
    return v


def as_nonneg(value: float, name: str) -> float:
    """Valida que un escalar sea finito y no negativo."""
    v = _to_float(value, name)
    if not np.isfinite(v) or v < 0:
        raise ValueError(_t("utils.error.as_nonneg.debe_ser_finito_recibio", name=name, value=value))
    return v


def as_fraction(value: float, name: str) -> float:
    """Valida que un escalar esté en [0, 1]."""
    v = _to_float(value, name)
    if not np.isfinite(v) or not (0.0 <= v <= 1.0):
        raise ValueError(_t("utils.error.as_fraction.debe_ser_valor_finito_recibio", name=name, value=value))
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
            _t("utils.error.as_int_positive.debe_ser_entero_positivo_recibio", name=name, __name__=type(value).__name__, value=value)
        )
    v = int(value)
    if v < 1:
        raise ValueError(_t("utils.error.as_int_positive.debe_ser_recibio", name=name, value=value))
    if max is not None and v > max:
        raise ValueError(_t("utils.error.as_int_positive.puede_superar_recibio", name=name, max=max, value=value))
    return v


def as_nonempty(seq: Any, name: str) -> None:
    """Lanza ValueError si la secuencia está vacía."""
    if len(seq) == 0:
        raise ValueError(_t("utils.error.as_nonempty.debe_contener_menos_elemento", name=name))


def as_finite_scalar(value: float, name: str) -> float:
    """Acepta cualquier número real finito (positivo, cero o negativo)."""
    v = _to_float(value, name)
    if not np.isfinite(v):
        raise ValueError(_t("utils.error.as_finite_scalar.debe_ser_numero_finito_recibio", name=name, value=value))
    return v


def as_float_list(seq: Any, name: str, *, kind: str = "positive", min_len: int = 1) -> list[float]:
    """Convierte una secuencia en ``list[float]`` validando cada elemento.

    ``kind``: ``'positive'`` (> 0), ``'nonneg'`` (>= 0) o ``'finite'`` (cualquier real finito).
    Rechaza cadenas, escalares y diccionarios; exige al menos ``min_len`` elementos.
    """
    if isinstance(seq, (str, bytes, dict)) or not hasattr(seq, "__iter__"):
        raise TypeError(_t("utils.error.as_float_list.debe_ser_secuencia_numeros_recibio", name=name, __name__=type(seq).__name__))
    check = {"positive": as_positive, "nonneg": as_nonneg, "finite": as_finite_scalar}[kind]
    out = [check(v, f"{name}[{i}]") for i, v in enumerate(seq)]
    if len(out) < min_len:
        if min_len == 1:
            raise ValueError(_t("utils.error.as_nonempty.debe_contener_menos_elemento", name=name))
        raise ValueError(_t("utils.error.as_float_list.debe_contener_menos_elementos_recibieron", name=name, min_len=min_len, expr=len(out)))
    return out


# Cuantil 0,975 de la t de Student (intervalo de confianza bilateral al 95 %), grados de libertad 1..30
_T_975 = (
    12.7062, 4.3027, 3.1824, 2.7764, 2.5706, 2.4469, 2.3646, 2.3060, 2.2622, 2.2281,
    2.2010, 2.1788, 2.1604, 2.1448, 2.1314, 2.1199, 2.1098, 2.1009, 2.0930, 2.0860,
    2.0796, 2.0739, 2.0687, 2.0639, 2.0595, 2.0555, 2.0518, 2.0484, 2.0452, 2.0423,
)


def t_cuantil_975(gl: int) -> float:
    """Cuantil 0,975 de la t de Student con ``gl`` grados de libertad (tabla hasta 30; después, desarrollo de Cornish-Fisher)."""
    if gl < 1:
        raise ValueError(_t("utils.error.t_cuantil_975.gl_debe_ser_recibio", gl=gl))
    if gl <= len(_T_975):
        return _T_975[gl - 1]
    z = 1.959963984540054
    return z + (z**3 + z) / (4 * gl) + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * gl**2) + (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * gl**3)

