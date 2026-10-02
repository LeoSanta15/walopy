"""Estimación de parámetros a partir de tiempos observados de llegada y de servicio."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class FitResult:
    """Parámetros estimados a partir de tiempos entre llegadas y/o de servicio observados.

    Attributes
    ----------
    lam : float or None
        Tasa de llegadas estimada λ = 1 / media(tiempos entre llegadas).
    mu : float or None
        Tasa de servicio estimada μ = 1 / media(service_times).
    ca2 : float or None
        CV² estimado de los tiempos entre llegadas.
    cs2 : float or None
        CV² estimado de los tiempos de servicio.
    n_arrivals : int
        Número de intervalos entre llegadas utilizados.
    n_services : int
        Número de observaciones de tiempo de servicio utilizadas.
    mean_ia, std_ia : float or None
        Media y desviación muestrales de los tiempos entre llegadas.
    mean_svc, std_svc : float or None
        Media y desviación muestrales de los tiempos de servicio.
    """

    lam: float | None
    mu: float | None
    ca2: float | None
    cs2: float | None
    n_arrivals: int
    n_services: int
    mean_ia: float | None = None
    mean_svc: float | None = None
    std_ia: float | None = None
    std_svc: float | None = None
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        lines = ["Ajuste (FitResult)"]
        if self.lam is not None:
            lines += [
                f"  λ (tasa de llegada)     : {self.lam:.6g}  (n={self.n_arrivals})",
                f"  media entre llegadas    : {self.mean_ia:.6g}",
                f"  desv. entre llegadas    : {self.std_ia:.6g}",
                f"  ca² (CV² de llegadas)   : {self.ca2:.6g}",
            ]
        if self.mu is not None:
            lines += [
                f"  μ (tasa de servicio)    : {self.mu:.6g}  (n={self.n_services})",
                f"  media de servicio       : {self.mean_svc:.6g}",
                f"  desv. de servicio       : {self.std_svc:.6g}",
                f"  cs² (CV² de servicio)   : {self.cs2:.6g}",
            ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def to_model_kwargs(self) -> dict:
        """Devuelve un diccionario listo para desempaquetar en ``mm1()``, ``kingman()``, etc."""
        out: dict = {}
        if self.lam is not None:
            out["lam"] = self.lam
        if self.mu is not None:
            out["mu"] = self.mu
        if self.ca2 is not None:
            out["ca2"] = self.ca2
        if self.cs2 is not None:
            out["cs2"] = self.cs2
        return out

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "λ": self.lam,
            "μ": self.mu,
            "ca²": self.ca2,
            "cs²": self.cs2,
            "mean_ia": self.mean_ia,
            "std_ia": self.std_ia,
            "mean_svc": self.mean_svc,
            "std_svc": self.std_svc,
            "n_arrivals": self.n_arrivals,
            "n_services": self.n_services,
        }])


def _fit_times(times: np.ndarray, name: str) -> tuple[float, float, float, float]:
    """Devuelve (tasa, cv2, media, desviación) a partir de un arreglo 1D de duraciones positivas."""
    arr = np.asarray(times, dtype=float).ravel()
    if arr.size < 2:
        raise ValueError(f"'{name}' debe contener al menos 2 observaciones.")
    if np.any(arr <= 0) or not np.all(np.isfinite(arr)):
        raise ValueError(f"Todos los valores de '{name}' deben ser finitos y estrictamente positivos.")
    mean = float(np.mean(arr))
    std  = float(np.std(arr, ddof=1))
    rate = 1.0 / mean
    cv2  = (std / mean) ** 2
    return rate, cv2, mean, std


def fit_from_data(
    inter_arrivals: np.ndarray | None = None,
    service_times: np.ndarray | None = None,
    *,
    arrival_timestamps: np.ndarray | None = None,
) -> FitResult:
    """Estima los parámetros de un modelo de colas a partir de datos observados.

    Indique los tiempos entre llegadas **o** las marcas de tiempo de llegada (no ambos).
    Debe proporcionarse al menos uno de los arreglos de llegadas o de servicio.

    Parameters
    ----------
    inter_arrivals : array-like of float, optional
        Intervalos observados entre llegadas (todos estrictamente positivos).
    service_times : array-like of float, optional
        Duraciones de servicio observadas (todas estrictamente positivas).
    arrival_timestamps : array-like of float, optional
        Marcas de tiempo absolutas de llegada en orden ascendente; los tiempos
        entre llegadas se obtienen como diferencias consecutivas.

    Returns
    -------
    FitResult
        λ, μ, ca², cs² estimados y estadísticos muestrales.


    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si no se indica ninguna muestra, si se indican ``inter_arrivals`` y ``arrival_timestamps`` a la vez, o si hay menos de 2 observaciones.
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> import numpy as np
    >>> rng = np.random.default_rng(42)
    >>> ia  = rng.exponential(scale=0.2, size=1000)   # true λ = 5
    >>> svc = rng.exponential(scale=0.1, size=1000)   # true μ = 10
    >>> fit = fit_from_data(ia, svc)
    >>> round(fit.lam, 1), round(fit.mu, 1)  # cercano a los valores verdaderos (5.0, 10.0)
    (4.9, 9.8)
    """
    if inter_arrivals is not None and arrival_timestamps is not None:
        raise ValueError("Indique 'inter_arrivals' o 'arrival_timestamps', no ambos.")

    if arrival_timestamps is not None:
        ts = np.asarray(arrival_timestamps, dtype=float).ravel()
        if ts.size < 2:
            raise ValueError("'arrival_timestamps' debe contener al menos 2 marcas de tiempo.")
        if not np.all(np.isfinite(ts)):
            raise ValueError("'arrival_timestamps' debe ser finito.")
        inter_arrivals = np.diff(ts)

    if inter_arrivals is None and service_times is None:
        raise ValueError(
            "Indique al menos uno de 'inter_arrivals', 'arrival_timestamps' o 'service_times'."
        )

    lam = mu = ca2 = cs2 = None
    n_arr = n_svc = 0
    mean_ia = mean_svc = std_ia = std_svc = None

    if inter_arrivals is not None:
        lam, ca2, mean_ia, std_ia = _fit_times(
            np.asarray(inter_arrivals, dtype=float), "inter_arrivals"
        )
        n_arr = int(np.asarray(inter_arrivals).size)

    if service_times is not None:
        mu, cs2, mean_svc, std_svc = _fit_times(
            np.asarray(service_times, dtype=float), "service_times"
        )
        n_svc = int(np.asarray(service_times).size)

    return FitResult(
        lam=lam,
        mu=mu,
        ca2=ca2,
        cs2=cs2,
        n_arrivals=n_arr,
        n_services=n_svc,
        mean_ia=mean_ia,
        mean_svc=mean_svc,
        std_ia=std_ia,
        std_svc=std_svc,
    )
