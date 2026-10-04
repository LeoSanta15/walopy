"""Red abierta de colas de Jackson."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from ._i18n import t as _t
from ._utils import as_int_positive, as_nonempty, as_nonneg, as_positive

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class StationMetrics:
    """Métricas por estación en una red de Jackson.

    Attributes
    ----------
    name : str
    lam_total : float
        Tasa total de llegadas (externas + ruteadas desde otras estaciones).
    lam_external : float
        Tasa de llegadas externas (Poisson).
    mu : float
        Tasa de servicio por servidor.
    servers : int
        Número de servidores.
    rho : float
        Utilización = lam_total / (servidores × mu).
    L, Lq, W, Wq : float
        Métricas M/M/c estándar.
    """

    name: str
    lam_total: float
    lam_external: float
    mu: float
    servers: int
    rho: float
    L: float
    Lq: float
    W: float
    Wq: float


@dataclass
class JacksonResult:
    """Resultado del análisis de una red abierta de Jackson.

    Attributes
    ----------
    stations : list[StationMetrics]
        Métricas por estación.
    L_system : float
        Total esperado de clientes en todas las estaciones (suma de L_j).
    W_system : float
        Tiempo medio de permanencia en la red = L_system / tasa total de llegadas externas.
    params : dict
    """

    stations: list[StationMetrics]
    L_system: float
    W_system: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            _t("network.cabecera.to_frame.estacion"):   s.name,
            _t("network.cabecera.to_frame.ext"):     s.lam_external,
            _t("network.cabecera.to_frame.total"):   s.lam_total,
            "μ":         s.mu,
            "c":         s.servers,
            "ρ":         s.rho,
            "L":         s.L,
            "Lq":        s.Lq,
            "W":         s.W,
            "Wq":        s.Wq,
        } for s in self.stations])

    def summary(self) -> str:
        hdr = (
            f"{_t('network.texto_en_expresion.summary.estacion'):<20} {_t('network.texto_en_expresion.summary.ext'):>8} {_t('network.texto_en_expresion.summary.tot'):>8} {'c':>4} {'ρ':>6} {_t('network.texto_en_expresion.summary.texto'):>8} {_t('network.texto_en_expresion.summary.lq'):>8} {_t('network.texto_en_expresion.summary.texto_2'):>10} {_t('network.texto_en_expresion.summary.wq'):>10}"
        )
        sep = "-" * len(hdr)
        lines = [hdr, sep]
        for s in self.stations:
            lines.append(
                f"{s.name:<20} {s.lam_external:>8.4g} {s.lam_total:>8.4g} "
                f"{s.servers:>4d} {s.rho:>6.3f} {s.L:>8.4g} {s.Lq:>8.4g} "
                f"{s.W:>10.4g} {s.Wq:>10.4g}"
            )
        lines += [
            sep,
            _t("network.etiqueta.summary.sistema_clientes_totales_red", L_system=self.L_system),
            _t("network.etiqueta.summary.sistema_tiempo_medio_permanencia_red", W_system=self.W_system),
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def jackson_network(
    station_names: Sequence[str],
    mu: Sequence[float],
    gamma: Sequence[float],
    routing: Sequence[Sequence[float]],
    *,
    servers: Sequence[int] | None = None,
) -> JacksonResult:
    """Analiza una red abierta de colas de Jackson.

    En una red abierta de Jackson los clientes llegan desde fuera según procesos
    de Poisson (tasas *gamma*), reciben servicio exponencial en cada estación que
    visitan y se enrutan de forma probabilística entre estaciones hasta salir
    del sistema. Por el teorema de Jackson cada estación se comporta como una cola
    M/M/c independiente con la tasa de llegada efectiva obtenida de las ecuaciones de tráfico.

    Parameters
    ----------
    station_names : sequence of str
        Nombres de las J estaciones.
    mu : sequence of float
        Tasa de servicio μ_j por servidor en cada estación.
    gamma : sequence of float
        Tasa de llegadas externas (Poisson) γ_j en cada estación (0 si no hay).
    routing : (J, J) array-like
        Matriz de ruteo P donde P[i][j] = probabilidad de ir de la estación *i* a la
        estación *j* tras el servicio en *i*. Las filas deben sumar ≤ 1; la fracción
        restante sale del sistema.
    servers : sequence of int, optional
        Número de servidores c_j en cada estación. Por defecto 1 en todas.

    Returns
    -------
    JacksonResult

    Raises
    ------
    ValueError
        Si el sistema es inestable (ρ_j ≥ 1 en alguna estación).

    Examples
    --------
    >>> # Two stations in tandem (all customers go station 1 → 2 → exit)
    >>> r = jackson_network(
    ...     ["Intake", "Processing"],
    ...     mu=[10.0, 8.0],
    ...     gamma=[5.0, 0.0],
    ...     routing=[[0.0, 1.0], [0.0, 0.0]],
    ... )
    >>> r.stations[0].lam_total, r.stations[1].lam_total
    (5.0, 5.0)
    """
    names = list(station_names)
    as_nonempty(names, "station_names")
    J = len(names)

    mu_arr    = np.array([as_positive(m, f"mu[{i}]") for i, m in enumerate(mu)], dtype=float)
    gamma_arr = np.array([as_nonneg(g, f"gamma[{i}]") for i, g in enumerate(gamma)], dtype=float)

    if len(mu_arr) != J or len(gamma_arr) != J:
        raise ValueError(_t("network.error.jackson_network.mu_gamma_station_names_deben"))

    P = np.array(routing, dtype=float)
    if P.shape != (J, J):
        raise ValueError(_t("network.error.jackson_network.routing_debe_ser_matriz_recibio", J=J, J2=J, shape=P.shape))
    if np.any(P < 0):
        raise ValueError(_t("network.error.jackson_network.todas_probabilidades_ruteo_deben_ser"))
    row_sums = P.sum(axis=1)
    if np.any(row_sums > 1.0 + 1e-10):
        raise ValueError(_t("network.error.jackson_network.filas_matriz_ruteo_deben_sumar"))

    if servers is None:
        c_arr = np.ones(J, dtype=int)
    else:
        c_arr = np.array([as_int_positive(c, f"servers[{i}]") for i, c in enumerate(servers)], dtype=int)
        if len(c_arr) != J:
            raise ValueError(_t("network.error.jackson_network.servers_debe_tener_misma_longitud"))

    # Traffic equations: λ = γ + P^T λ  →  (I − P^T) λ = γ
    A   = np.eye(J) - P.T
    lam = np.linalg.solve(A, gamma_arr)

    if np.any(lam < 0):
        raise ValueError(_t("network.error.jackson_network.tasas_llegada_efectivas_negativas_revise"))

    # Analyse each station as M/M/c
    from .queuing import mm1, mmc

    station_list: list[StationMetrics] = []
    for j in range(J):
        lj  = float(lam[j])
        muj = float(mu_arr[j])
        cj  = int(c_arr[j])
        rho_j = lj / (cj * muj)
        if rho_j >= 1.0:
            raise ValueError(
                _t("network.error.jackson_network.estacion_inestable_aumente_capacidad_reduzca", expr=names[j], rho_j=rho_j)
            )
        res = mm1(lj, muj) if cj == 1 else mmc(lj, muj, cj)
        station_list.append(StationMetrics(
            name=names[j],
            lam_total=lj,
            lam_external=float(gamma_arr[j]),
            mu=muj,
            servers=cj,
            rho=res.rho,
            L=res.L,
            Lq=res.Lq,
            W=res.W,
            Wq=res.Wq,
        ))

    L_system = sum(s.L for s in station_list)
    total_ext = float(gamma_arr.sum())
    W_system  = L_system / total_ext if total_ext > 0 else float("inf")

    return JacksonResult(
        stations=station_list,
        L_system=L_system,
        W_system=W_system,
        params={"J": J, "total_gamma": total_ext},
    )
