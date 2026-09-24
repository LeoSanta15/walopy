"""Parameter estimation from observed arrival / service time data."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class FitResult:
    """Parameters estimated from observed inter-arrival and/or service times.

    Attributes
    ----------
    lam : float or None
        Estimated arrival rate λ = 1 / mean(inter-arrival times).
    mu : float or None
        Estimated service rate μ = 1 / mean(service_times).
    ca2 : float or None
        Estimated squared CV of inter-arrival times.
    cs2 : float or None
        Estimated squared CV of service times.
    n_arrivals : int
        Number of inter-arrival intervals used.
    n_services : int
        Number of service time observations used.
    mean_ia, std_ia : float or None
        Sample mean and std of inter-arrival times.
    mean_svc, std_svc : float or None
        Sample mean and std of service times.
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
        lines = ["FitResult"]
        if self.lam is not None:
            lines += [
                f"  λ (arrival rate)  : {self.lam:.6g}  (n={self.n_arrivals})",
                f"  mean inter-arrival: {self.mean_ia:.6g}",
                f"  std  inter-arrival: {self.std_ia:.6g}",
                f"  ca² (arrival CV²) : {self.ca2:.6g}",
            ]
        if self.mu is not None:
            lines += [
                f"  μ (service rate)  : {self.mu:.6g}  (n={self.n_services})",
                f"  mean service time : {self.mean_svc:.6g}",
                f"  std  service time : {self.std_svc:.6g}",
                f"  cs² (service CV²) : {self.cs2:.6g}",
            ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def to_model_kwargs(self) -> dict:
        """Return a dict ready to unpack into ``mm1()``, ``kingman()``, etc."""
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

    def to_frame(self) -> "pd.DataFrame":
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
    """Return (rate, cv2, mean, std) from a 1D array of positive durations."""
    arr = np.asarray(times, dtype=float).ravel()
    if arr.size < 2:
        raise ValueError(f"'{name}' must contain at least 2 observations.")
    if np.any(arr <= 0) or not np.all(np.isfinite(arr)):
        raise ValueError(f"All values in '{name}' must be finite and strictly positive.")
    mean = float(np.mean(arr))
    std  = float(np.std(arr, ddof=1))
    rate = 1.0 / mean
    cv2  = (std / mean) ** 2
    return rate, cv2, mean, std


def fit_from_data(
    inter_arrivals: "np.ndarray | None" = None,
    service_times: "np.ndarray | None" = None,
    *,
    arrival_timestamps: "np.ndarray | None" = None,
) -> FitResult:
    """Estimate queuing model parameters from observed data.

    Pass inter-arrival times **or** arrival timestamps (not both).
    At least one of the arrival or service arrays must be provided.

    Parameters
    ----------
    inter_arrivals : array-like of float, optional
        Observed inter-arrival time intervals (all strictly positive).
    service_times : array-like of float, optional
        Observed service time durations (all strictly positive).
    arrival_timestamps : array-like of float, optional
        Absolute arrival timestamps in ascending order; inter-arrival times
        are derived as consecutive differences.

    Returns
    -------
    FitResult
        Estimated λ, μ, ca², cs² and sample statistics.

    Examples
    --------
    >>> import numpy as np
    >>> rng = np.random.default_rng(42)
    >>> ia  = rng.exponential(scale=0.2, size=1000)   # true λ = 5
    >>> svc = rng.exponential(scale=0.1, size=1000)   # true μ = 10
    >>> fit = fit_from_data(ia, svc)
    >>> round(fit.lam, 1), round(fit.mu, 1)  # ≈ (5.0, 10.0)
    """
    if inter_arrivals is not None and arrival_timestamps is not None:
        raise ValueError("Pass either 'inter_arrivals' or 'arrival_timestamps', not both.")

    if arrival_timestamps is not None:
        ts = np.asarray(arrival_timestamps, dtype=float).ravel()
        if ts.size < 2:
            raise ValueError("'arrival_timestamps' must contain at least 2 timestamps.")
        if not np.all(np.isfinite(ts)):
            raise ValueError("'arrival_timestamps' must be finite.")
        inter_arrivals = np.diff(ts)

    if inter_arrivals is None and service_times is None:
        raise ValueError(
            "Provide at least one of 'inter_arrivals', 'arrival_timestamps', or 'service_times'."
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
