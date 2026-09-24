"""Inventory models: EOQ, reorder point / safety stock, newsvendor."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import NormalDist

from ._utils import as_positive, as_nonneg, as_fraction


# ---------------------------------------------------------------------------
# Economic Order Quantity
# ---------------------------------------------------------------------------

@dataclass
class EOQResult:
    """Economic Order Quantity result.

    Attributes
    ----------
    eoq : float
        Optimal order quantity Q*.
    total_cost : float
        Minimum total cost per period at Q*.
    holding_cost_total : float
        Annual holding cost component at Q*.
    ordering_cost_total : float
        Annual ordering cost component at Q*.
    order_frequency : float
        Number of orders per period.
    cycle_time : float
        Average time between orders (1 / order_frequency).
    params : dict
    """

    eoq: float
    total_cost: float
    holding_cost_total: float
    ordering_cost_total: float
    order_frequency: float
    cycle_time: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"EOQ (order quantity): {self.eoq:.4g} units\n"
            f"Order frequency     : {self.order_frequency:.4g} orders/period\n"
            f"Cycle time          : {self.cycle_time:.4g} periods\n"
            f"Total cost          : {self.total_cost:.6g}\n"
            f"  Holding cost      : {self.holding_cost_total:.6g}\n"
            f"  Ordering cost     : {self.ordering_cost_total:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd
        return pd.DataFrame([{
            "EOQ": self.eoq,
            "Total cost": self.total_cost,
            "Holding cost": self.holding_cost_total,
            "Ordering cost": self.ordering_cost_total,
            "Order frequency": self.order_frequency,
            "Cycle time": self.cycle_time,
        }])

    def plot(self, **kwargs) -> "plt.Figure":
        from .plotting import plot_eoq
        return plot_eoq(self, **kwargs)


def eoq(
    demand_rate: float,
    ordering_cost: float,
    holding_cost: float,
) -> EOQResult:
    """Economic Order Quantity — Wilson / Harris formula.

    Q* = sqrt(2 · D · K / h)

    Parameters
    ----------
    demand_rate : float
        Demand per period *D* (units/period).
    ordering_cost : float
        Fixed cost per order *K* ($/order).
    holding_cost : float
        Holding cost per unit per period *h* ($/unit/period).

    Returns
    -------
    EOQResult

    Examples
    --------
    >>> r = eoq(demand_rate=1000, ordering_cost=50, holding_cost=2)
    >>> round(r.eoq, 1)
    223.6
    """
    D = as_positive(demand_rate, "demand_rate")
    K = as_positive(ordering_cost, "ordering_cost")
    h = as_positive(holding_cost, "holding_cost")

    q   = math.sqrt(2 * D * K / h)
    n   = D / q
    hc  = (q / 2) * h
    oc  = (D / q) * K
    tc  = hc + oc  # equal at EOQ → tc = sqrt(2*D*K*h)

    return EOQResult(
        eoq=q,
        total_cost=tc,
        holding_cost_total=hc,
        ordering_cost_total=oc,
        order_frequency=n,
        cycle_time=1.0 / n,
        params={"demand_rate": D, "ordering_cost": K, "holding_cost": h},
    )


# ---------------------------------------------------------------------------
# Reorder point and safety stock
# ---------------------------------------------------------------------------

@dataclass
class ReorderResult:
    """Reorder point and safety stock result.

    Attributes
    ----------
    reorder_point : float
        Inventory level at which to place a replenishment order.
    safety_stock : float
        Buffer stock = z · σ_{DLT}.
    service_level : float
        Cycle service level (P(no stockout per cycle)).
    z_score : float
        Safety factor z corresponding to the service level.
    mean_demand_lt : float
        Expected demand during lead time D̄ · L̄.
    std_demand_lt : float
        Std dev of demand during lead time √(L̄σ_D² + D̄²σ_L²).
    params : dict
    """

    reorder_point: float
    safety_stock: float
    service_level: float
    z_score: float
    mean_demand_lt: float
    std_demand_lt: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"Reorder point   : {self.reorder_point:.4g} units\n"
            f"Safety stock    : {self.safety_stock:.4g} units\n"
            f"Service level   : {self.service_level:.2%}\n"
            f"z-score         : {self.z_score:.4g}\n"
            f"Mean demand LT  : {self.mean_demand_lt:.4g}\n"
            f"Std demand LT   : {self.std_demand_lt:.4g}"
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd
        return pd.DataFrame([{
            "Reorder point": self.reorder_point,
            "Safety stock": self.safety_stock,
            "Service level": self.service_level,
            "z-score": self.z_score,
            "Mean demand LT": self.mean_demand_lt,
            "Std demand LT": self.std_demand_lt,
        }])


def reorder_point(
    demand_rate: float,
    lead_time: float,
    *,
    demand_std: float = 0.0,
    lead_time_std: float = 0.0,
    service_level: float = 0.95,
) -> ReorderResult:
    """Compute the reorder point (ROP) and safety stock.

    ROP = D̄ · L̄ + z · σ_{DLT}

    where σ_{DLT} = √(L̄ · σ_D² + D̄² · σ_L²)  and  z is the z-score
    corresponding to the desired cycle service level.

    Parameters
    ----------
    demand_rate : float
        Mean demand rate D̄ (units/period).
    lead_time : float
        Mean lead time L̄ (in same time units as demand_rate).
    demand_std : float
        Standard deviation of demand per period σ_D (default 0).
    lead_time_std : float
        Standard deviation of lead time σ_L (default 0).
    service_level : float
        Probability of no stockout per replenishment cycle ∈ (0, 1).
        Default 0.95.

    Returns
    -------
    ReorderResult

    Examples
    --------
    >>> r = reorder_point(demand_rate=50, lead_time=2, demand_std=10, service_level=0.95)
    >>> r.safety_stock > 0
    True
    """
    D   = as_positive(demand_rate, "demand_rate")
    LT  = as_positive(lead_time, "lead_time")
    sd  = as_nonneg(demand_std, "demand_std")
    sl  = as_nonneg(lead_time_std, "lead_time_std")
    svc = as_fraction(service_level, "service_level")
    if svc == 0.0 or svc == 1.0:
        raise ValueError("'service_level' must be strictly between 0 and 1.")

    mean_dlt = D * LT
    var_dlt  = LT * sd**2 + D**2 * sl**2
    std_dlt  = math.sqrt(var_dlt)

    z   = NormalDist().inv_cdf(svc)
    ss  = z * std_dlt
    rop = mean_dlt + ss

    return ReorderResult(
        reorder_point=rop,
        safety_stock=ss,
        service_level=svc,
        z_score=z,
        mean_demand_lt=mean_dlt,
        std_demand_lt=std_dlt,
        params={"demand_rate": D, "lead_time": LT, "demand_std": sd,
                "lead_time_std": sl},
    )


# ---------------------------------------------------------------------------
# Newsvendor problem
# ---------------------------------------------------------------------------

@dataclass
class NewsvendorResult:
    """Result of the newsvendor model.

    Attributes
    ----------
    optimal_qty : float
        Optimal order quantity Q* = F^{-1}(CR).
    critical_ratio : float
        Cu / (Cu + Co).
    expected_profit : float
        Expected profit at Q*.
    expected_sales : float
        E[min(D, Q*)].
    expected_leftover : float
        E[max(Q* - D, 0)].
    expected_stockout : float
        E[max(D - Q*, 0)].
    underage_cost : float
        Cu = price − cost.
    overage_cost : float
        Co = cost − salvage.
    params : dict
    """

    optimal_qty: float
    critical_ratio: float
    expected_profit: float
    expected_sales: float
    expected_leftover: float
    expected_stockout: float
    underage_cost: float
    overage_cost: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"Optimal quantity   : {self.optimal_qty:.4g} units\n"
            f"Critical ratio     : {self.critical_ratio:.4g}\n"
            f"Expected profit    : {self.expected_profit:.6g}\n"
            f"Expected sales     : {self.expected_sales:.4g}\n"
            f"Expected leftover  : {self.expected_leftover:.4g}\n"
            f"Expected stockout  : {self.expected_stockout:.4g}\n"
            f"Underage cost Cu   : {self.underage_cost:.4g}\n"
            f"Overage cost  Co   : {self.overage_cost:.4g}"
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd
        return pd.DataFrame([{
            "Q*": self.optimal_qty,
            "Critical ratio": self.critical_ratio,
            "Expected profit": self.expected_profit,
            "Expected sales": self.expected_sales,
            "Expected leftover": self.expected_leftover,
            "Expected stockout": self.expected_stockout,
            "Cu": self.underage_cost,
            "Co": self.overage_cost,
        }])


def newsvendor(
    demand_mean: float,
    demand_std: float,
    price: float,
    cost: float,
    *,
    salvage: float = 0.0,
) -> NewsvendorResult:
    """Newsvendor (single-period inventory) model with normal demand.

    Optimal quantity Q* = F^{-1}(Cu / (Cu + Co)) where
    Cu = price − cost  (underage / lost-profit cost),
    Co = cost − salvage  (overage / holding cost for unsold units).

    Parameters
    ----------
    demand_mean : float
        Mean demand μ_D.
    demand_std : float
        Standard deviation of demand σ_D (≥ 0; 0 = deterministic).
    price : float
        Selling price per unit.
    cost : float
        Purchase / production cost per unit.
    salvage : float
        Salvage value per unsold unit (default 0).

    Returns
    -------
    NewsvendorResult

    Examples
    --------
    >>> r = newsvendor(demand_mean=100, demand_std=20, price=10, cost=6, salvage=2)
    >>> 100 < r.optimal_qty < 130
    True
    """
    mu  = as_positive(demand_mean, "demand_mean")
    sig = as_nonneg(demand_std, "demand_std")
    p   = as_positive(price, "price")
    c   = as_positive(cost, "cost")
    s   = as_nonneg(salvage, "salvage")

    if c >= p:
        raise ValueError("'cost' must be less than 'price' (otherwise Cu ≤ 0).")
    if s >= c:
        raise ValueError("'salvage' must be less than 'cost' (otherwise Co ≤ 0).")

    Cu = p - c          # underage cost (opportunity loss)
    Co = c - s          # overage cost  (holding/disposal loss)
    CR = Cu / (Cu + Co) # critical ratio

    nd = NormalDist(mu=mu, sigma=sig) if sig > 0 else None

    if nd is None:
        Q = mu
    else:
        Q = nd.inv_cdf(CR)

    # Expected sales  E[min(D, Q)] and leftover E[max(Q-D, 0)]
    if nd is None or sig < 1e-12:
        exp_sales    = min(mu, Q)
        exp_leftover = max(Q - mu, 0.0)
        exp_stockout = max(mu - Q, 0.0)
    else:
        z = (Q - mu) / sig
        phi_z  = nd.pdf(Q)        # = NormalDist().pdf(z) / sig
        Phi_z  = nd.cdf(Q)
        # Standard normal loss function: L(z) = phi(z) - z*(1-Phi(z))
        # E[max(D-Q,0)] = sig * L(z) using standard normal N(0,1)
        from statistics import NormalDist as _ND
        _std = _ND()
        z_std   = (Q - mu) / sig
        phi_std = _std.pdf(z_std)
        Phi_std = _std.cdf(z_std)
        exp_stockout = sig * (phi_std - z_std * (1 - Phi_std))
        exp_leftover = Q - mu + exp_stockout   # identity: E[leftover] - E[stockout] = Q - mu
        exp_sales    = mu - exp_stockout

    exp_profit = (p - c) * exp_sales - (c - s) * exp_leftover

    return NewsvendorResult(
        optimal_qty=Q,
        critical_ratio=CR,
        expected_profit=exp_profit,
        expected_sales=exp_sales,
        expected_leftover=exp_leftover,
        expected_stockout=exp_stockout,
        underage_cost=Cu,
        overage_cost=Co,
        params={"demand_mean": mu, "demand_std": sig,
                "price": p, "cost": c, "salvage": s},
    )
