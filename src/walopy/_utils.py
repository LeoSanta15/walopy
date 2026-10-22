"""Validadores internos: única capa de ingesta numérica de walopy.

Todo argumento numérico que llega del usuario debe pasar por estas funciones.
NaN e infinito se rechazan *antes* de comparar (``x <= 0`` es ``False`` para NaN).
"""
from __future__ import annotations

import math
from statistics import NormalDist
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


def _beta_incompleta_reg(a: float, b: float, x: float) -> float:
    """Beta incompleta regularizada I_x(a, b) por fracciones continuas de Lentz (convergente para a, b > 0)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    frente = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))

    def fraccion(aa: float, bb: float, xx: float) -> float:
        tiny = 1e-300
        c, d = 1.0, 1.0 - (aa + bb) * xx / (aa + 1.0)
        d = 1.0 / (d if abs(d) > tiny else tiny)
        h = d
        for m in range(1, 100_000):
            m2 = 2 * m
            num = m * (bb - m) * xx / ((aa + m2 - 1.0) * (aa + m2))
            d = 1.0 + num * d
            c = 1.0 + num / c
            d = 1.0 / (d if abs(d) > tiny else tiny)
            h *= d * (c if abs(c) > tiny else tiny)
            num = -(aa + m) * (aa + bb + m) * xx / ((aa + m2) * (aa + m2 + 1.0))
            d = 1.0 + num * d
            c = 1.0 + num / c
            d = 1.0 / (d if abs(d) > tiny else tiny)
            delta = d * (c if abs(c) > tiny else tiny)
            h *= delta
            if abs(delta - 1.0) < 1e-15:
                break
        return h

    if x < (a + 1.0) / (a + b + 2.0):
        return frente * fraccion(a, b, x) / a
    return 1.0 - frente * fraccion(b, a, 1.0 - x) / b


def t_cuantil(p: float, gl: float) -> float:
    """Cuantil de orden ``p`` ∈ (0, 1) de la t de Student con ``gl`` > 0 grados de libertad (inversión numérica de la función de distribución).

    La distribución se calcula con la beta incompleta, F(t) = 1 − ½·I_{gl/(gl+t²)}(gl/2, ½) para t ≥ 0, y el cuantil se busca por bisección.
    Con ``gl`` mayor de 10⁶ se usa la normal (la diferencia relativa es menor que 10⁻⁶).
    """
    if not (0.0 < p < 1.0):
        raise ValueError(_t("utils.error.t_cuantil.p_debe_estar_entre_0_1", p=p))
    if not gl > 0.0:
        raise ValueError(_t("utils.error.t_cuantil.gl_debe_ser_positivo", gl=gl))
    if p == 0.5:
        return 0.0
    if p < 0.5:
        return -t_cuantil(1.0 - p, gl)
    if gl > 1e6:
        return NormalDist().inv_cdf(p)

    def cdf(t: float) -> float:
        return 1.0 - 0.5 * _beta_incompleta_reg(gl / 2.0, 0.5, gl / (gl + t * t))

    lo, hi = 0.0, 1.0
    while cdf(hi) < p:
        lo, hi = hi, hi * 2.0
        if hi > 1e300:
            break
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if cdf(mid) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo <= 1e-15 * max(1.0, hi):
            break
    return (lo + hi) / 2.0


def t_cuantil_975(gl: int) -> float:
    """Cuantil 0,975 de la t de Student con ``gl`` grados de libertad (tabla hasta 30; después, desarrollo de Cornish-Fisher)."""
    if gl < 1:
        raise ValueError(_t("utils.error.t_cuantil_975.gl_debe_ser_recibio", gl=gl))
    if gl <= len(_T_975):
        return _T_975[gl - 1]
    z = 1.959963984540054
    return z + (z**3 + z) / (4 * gl) + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * gl**2) + (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * gl**3)

