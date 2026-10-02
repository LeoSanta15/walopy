"""Inventory models: EOQ, EBQ, reorder point, newsvendor, multi-item, constrained, dynamic lot-sizing."""
from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import NormalDist

from ._utils import as_float_list, as_fraction, as_nonneg, as_positive

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

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "EOQ": self.eoq,
            "Total cost": self.total_cost,
            "Holding cost": self.holding_cost_total,
            "Ordering cost": self.ordering_cost_total,
            "Order frequency": self.order_frequency,
            "Cycle time": self.cycle_time,
        }])

    def plot(self, **kwargs) -> plt.Figure:
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

    def to_frame(self) -> pd.DataFrame:
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

    def to_frame(self) -> pd.DataFrame:
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


# ---------------------------------------------------------------------------
# Economic Batch Quantity (EBQ / EPQ)
# ---------------------------------------------------------------------------

@dataclass
class EBQResult:
    """Economic Batch Quantity (EPQ) result.

    Attributes
    ----------
    ebq : float
        Optimal production batch Q*.
    total_cost : float
        Minimum total cost per period.
    holding_cost_total : float
        Annual holding cost component at Q*.
    setup_cost_total : float
        Annual setup cost component at Q*.
    max_inventory : float
        Maximum inventory level = Q*(1 − D/P).
    avg_inventory : float
        Average inventory level = max_inventory / 2.
    production_time : float
        Fraction of cycle spent producing = Q*/P.
    cycle_time : float
        Length of one replenishment cycle = Q*/D.
    order_frequency : float
        Number of production runs per period = D/Q*.
    params : dict
    """

    ebq: float
    total_cost: float
    holding_cost_total: float
    setup_cost_total: float
    max_inventory: float
    avg_inventory: float
    production_time: float
    cycle_time: float
    order_frequency: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"EBQ (batch size)    : {self.ebq:.4g} units\n"
            f"Max inventory       : {self.max_inventory:.4g}\n"
            f"Avg inventory       : {self.avg_inventory:.4g}\n"
            f"Order frequency     : {self.order_frequency:.4g} runs/period\n"
            f"Cycle time          : {self.cycle_time:.4g} periods\n"
            f"Production time/cyc : {self.production_time:.4g} periods\n"
            f"Total cost          : {self.total_cost:.6g}\n"
            f"  Holding cost      : {self.holding_cost_total:.6g}\n"
            f"  Setup cost        : {self.setup_cost_total:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "EBQ": self.ebq,
            "Total cost": self.total_cost,
            "Holding cost": self.holding_cost_total,
            "Setup cost": self.setup_cost_total,
            "Max inventory": self.max_inventory,
            "Avg inventory": self.avg_inventory,
            "Order frequency": self.order_frequency,
            "Cycle time": self.cycle_time,
        }])


def ebq(
    demand_rate: float,
    setup_cost: float,
    holding_cost: float,
    production_rate: float,
) -> EBQResult:
    """Economic Batch Quantity (Economic Production Quantity).

    Q* = sqrt(2 · D · S / (h · (1 − D/P)))

    Parameters
    ----------
    demand_rate : float
        Demand per period D (units/period).
    setup_cost : float
        Fixed setup cost per production run S ($/run).
    holding_cost : float
        Holding cost per unit per period h ($/unit/period).
    production_rate : float
        Production rate P (units/period).  Must exceed demand_rate.

    Returns
    -------
    EBQResult

    Examples
    --------
    >>> r = ebq(demand_rate=1000, setup_cost=50, holding_cost=2, production_rate=4000)
    >>> round(r.ebq, 1)
    258.2
    """
    D = as_positive(demand_rate, "demand_rate")
    S = as_positive(setup_cost, "setup_cost")
    h = as_positive(holding_cost, "holding_cost")
    P = as_positive(production_rate, "production_rate")
    if D >= P:
        raise ValueError(f"production_rate ({P}) must exceed demand_rate ({D}).")

    fraction = 1.0 - D / P
    q   = math.sqrt(2 * D * S / (h * fraction))
    n   = D / q
    max_inv = q * fraction
    avg_inv = max_inv / 2.0
    hc  = avg_inv * h
    sc  = n * S
    tc  = hc + sc

    return EBQResult(
        ebq=q,
        total_cost=tc,
        holding_cost_total=hc,
        setup_cost_total=sc,
        max_inventory=max_inv,
        avg_inventory=avg_inv,
        production_time=q / P,
        cycle_time=q / D,
        order_frequency=n,
        params={"demand_rate": D, "setup_cost": S, "holding_cost": h, "production_rate": P},
    )


# ---------------------------------------------------------------------------
# Multi-item EOQ / EBQ (independent items)
# ---------------------------------------------------------------------------

@dataclass
class MultiItemResult:
    """Result for a multi-item independent inventory analysis.

    Attributes
    ----------
    items : list[dict]
        Per-item results with keys: name, eoq/ebq, total_cost, holding_cost,
        ordering_cost, order_frequency, cycle_time.
    total_cost : float
        Sum of individual optimal costs.
    params : dict
    """

    items: list
    total_cost: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items)

    def summary(self) -> str:
        df = self.to_frame()
        lines = [df.to_string(index=False), f"\nTotal cost: {self.total_cost:.6g}"]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def eoq_multi(
    demand_rates: Sequence[float],
    ordering_costs: Sequence[float],
    holding_costs: Sequence[float],
    *,
    names: Sequence[str] | None = None,
) -> MultiItemResult:
    """Independent multi-item Economic Order Quantity.

    Solves each item independently; no shared constraints.

    Parameters
    ----------
    demand_rates : sequence of float
        Demand rate D_i for each item.
    ordering_costs : sequence of float
        Fixed ordering cost K_i for each item.
    holding_costs : sequence of float
        Holding cost h_i per unit per period for each item.
    names : sequence of str, optional
        Item names.  Defaults to Item-1, Item-2, …

    Returns
    -------
    MultiItemResult

    Examples
    --------
    >>> r = eoq_multi([1000, 500], [50, 30], [2, 1])
    >>> len(r.items) == 2
    True
    """
    demand_rates   = list(demand_rates)
    ordering_costs = list(ordering_costs)
    holding_costs  = list(holding_costs)
    n = len(demand_rates)
    if len(ordering_costs) != n or len(holding_costs) != n:
        raise ValueError("All input sequences must have the same length.")
    if names is None:
        names = [f"Item-{i+1}" for i in range(n)]

    items = []
    total_cost = 0.0
    for i in range(n):
        r = eoq(demand_rates[i], ordering_costs[i], holding_costs[i])
        items.append({
            "Name": names[i],
            "EOQ": r.eoq,
            "Total cost": r.total_cost,
            "Holding cost": r.holding_cost_total,
            "Ordering cost": r.ordering_cost_total,
            "Order frequency": r.order_frequency,
            "Cycle time": r.cycle_time,
        })
        total_cost += r.total_cost

    return MultiItemResult(items=items, total_cost=total_cost,
                           params={"n_items": n})


def ebq_multi(
    demand_rates: Sequence[float],
    setup_costs: Sequence[float],
    holding_costs: Sequence[float],
    production_rates: Sequence[float],
    *,
    names: Sequence[str] | None = None,
) -> MultiItemResult:
    """Independent multi-item Economic Batch Quantity.

    Parameters
    ----------
    demand_rates : sequence of float
    setup_costs : sequence of float
    holding_costs : sequence of float
    production_rates : sequence of float
    names : sequence of str, optional

    Returns
    -------
    MultiItemResult

    Examples
    --------
    >>> r = ebq_multi([1000, 500], [50, 30], [2, 1], [4000, 2000])
    >>> len(r.items) == 2
    True
    """
    demand_rates    = list(demand_rates)
    setup_costs     = list(setup_costs)
    holding_costs   = list(holding_costs)
    production_rates = list(production_rates)
    n = len(demand_rates)
    if not (len(setup_costs) == len(holding_costs) == len(production_rates) == n):
        raise ValueError("All input sequences must have the same length.")
    if names is None:
        names = [f"Item-{i+1}" for i in range(n)]

    items = []
    total_cost = 0.0
    for i in range(n):
        r = ebq(demand_rates[i], setup_costs[i], holding_costs[i], production_rates[i])
        items.append({
            "Name": names[i],
            "EBQ": r.ebq,
            "Total cost": r.total_cost,
            "Holding cost": r.holding_cost_total,
            "Setup cost": r.setup_cost_total,
            "Max inventory": r.max_inventory,
            "Avg inventory": r.avg_inventory,
            "Order frequency": r.order_frequency,
        })
        total_cost += r.total_cost

    return MultiItemResult(items=items, total_cost=total_cost,
                           params={"n_items": n})


# ---------------------------------------------------------------------------
# Constrained multi-item EOQ (Lagrangian relaxation)
# ---------------------------------------------------------------------------

def _eoq_lagrangian_bisect(
    D: list, K: list, h: list,
    weights: list, bound: float,
    other_lambdas: list | None = None,
    other_weights: list | None = None,
    tol: float = 1e-9,
) -> tuple[float, list[float]]:
    """Find λ via bisect for a single constraint sum(w_i * Q_i(λ)) = bound."""
    n = len(D)

    def h_eff(i: int, lam: float) -> float:
        base = h[i] + lam * weights[i]
        if other_lambdas and other_weights:
            for lj, wj in zip(other_lambdas, other_weights):
                base += lj * wj[i]
        return max(base, 1e-15)

    def Q_i(i: int, lam: float) -> float:
        return math.sqrt(2 * D[i] * K[i] / h_eff(i, lam))

    def total(lam: float) -> float:
        return sum(weights[i] * Q_i(i, lam) for i in range(n))

    # If unconstrained is feasible, λ = 0
    if total(0.0) <= bound + tol:
        return 0.0, [Q_i(i, 0.0) for i in range(n)]

    # Find upper bound for λ
    hi = 1.0
    for _ in range(200):
        if total(hi) <= bound:
            break
        hi *= 2.0
    else:
        raise ValueError("La restricción no se puede satisfacer con ninguna cantidad de pedido positiva.")

    lo = 0.0
    for _ in range(120):
        mid = (lo + hi) / 2.0
        if total(mid) > bound:
            lo = mid
        else:
            hi = mid
        if (hi - lo) < tol:
            break

    lam_opt = (lo + hi) / 2.0
    return lam_opt, [Q_i(i, lam_opt) for i in range(n)]


@dataclass
class ConstrainedMultiEOQResult:
    """Constrained multi-item EOQ result (Lagrangian relaxation).

    Attributes
    ----------
    items : list[dict]
        Per-item optimal quantities and costs.
    total_cost : float
        Total inventory cost at optimal quantities.
    unconstrained_total_cost : float
        Total cost of unconstrained EOQ (lower bound).
    lagrange_multipliers : dict[str, float]
        Lagrange multiplier λ for each constraint.
    binding_constraints : list[str]
        Names of active (binding) constraints.
    params : dict
    """

    items: list
    total_cost: float
    unconstrained_total_cost: float
    lagrange_multipliers: dict
    binding_constraints: list
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items)

    def summary(self) -> str:
        lines = [
            f"Total cost (constrained)  : {self.total_cost:.6g}",
            f"Total cost (unconstrained): {self.unconstrained_total_cost:.6g}",
            f"Binding constraints: {', '.join(self.binding_constraints) or 'none'}",
            "",
        ]
        for row in self.items:
            lines.append(
                f"  {row['Name']:<16} Q*={row['Q*']:.4g}  TC={row['Total cost']:.4g}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def eoq_multi_constrained(
    demand_rates: Sequence[float],
    ordering_costs: Sequence[float],
    holding_costs: Sequence[float],
    *,
    names: Sequence[str] | None = None,
    budget: float | None = None,
    budget_unit_costs: Sequence[float] | None = None,
    space: float | None = None,
    space_per_unit: Sequence[float] | None = None,
    constraints: list[dict] | None = None,
) -> ConstrainedMultiEOQResult:
    """Constrained multi-item EOQ via Lagrangian relaxation.

    Minimises sum of inventory costs subject to linear constraints on
    order quantities:  sum_i(w_ij · Q_i) ≤ B_j.

    Convenience shortcuts
    ---------------------
    budget / budget_unit_costs
        Budget constraint on *average* inventory investment:
        sum(c_i · Q_i / 2) ≤ budget.
        Pass ``budget_unit_costs`` = unit purchase costs c_i.
    space / space_per_unit
        Space constraint on average inventory:
        sum(s_i · Q_i / 2) ≤ space.

    Generic constraints
    -------------------
    constraints : list of dict, each with keys
        ``name`` (str), ``weights`` (list of floats a_i),
        ``bound`` (float B) — enforces sum(a_i · Q_i) ≤ B.

    Parameters
    ----------
    demand_rates, ordering_costs, holding_costs : sequence of float
    names : sequence of str, optional
    budget : float, optional
    budget_unit_costs : sequence of float, optional
    space : float, optional
    space_per_unit : sequence of float, optional
    constraints : list of dict, optional

    Returns
    -------
    ConstrainedMultiEOQResult

    Examples
    --------
    >>> r = eoq_multi_constrained(
    ...     [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
    ...     budget=5000, budget_unit_costs=[10, 8, 12],
    ... )
    >>> r.total_cost > 0
    True
    """
    D = as_float_list(demand_rates, "demand_rates")
    K = as_float_list(ordering_costs, "ordering_costs")
    h = as_float_list(holding_costs, "holding_costs")
    n = len(D)
    if len(K) != n or len(h) != n:
        raise ValueError("Todas las secuencias de entrada deben tener la misma longitud.")
    if names is None:
        names = [f"Item-{i+1}" for i in range(n)]

    # Build constraint list
    all_constraints: list[dict] = []
    if budget is not None:
        if budget_unit_costs is None:
            raise ValueError("'budget_unit_costs' es obligatorio cuando se indica 'budget'.")
        bc = as_float_list(budget_unit_costs, "budget_unit_costs", kind="nonneg")
        if len(bc) != n:
            raise ValueError("'budget_unit_costs' debe tener la misma longitud que demand_rates.")
        all_constraints.append(
            {"name": "budget", "weights": [c / 2 for c in bc], "bound": as_positive(budget, "budget")}
        )
    if space is not None:
        if space_per_unit is None:
            raise ValueError("'space_per_unit' es obligatorio cuando se indica 'space'.")
        sw = as_float_list(space_per_unit, "space_per_unit", kind="nonneg")
        if len(sw) != n:
            raise ValueError("'space_per_unit' debe tener la misma longitud que demand_rates.")
        all_constraints.append(
            {"name": "space", "weights": [s / 2 for s in sw], "bound": as_positive(space, "space")}
        )
    if constraints:
        for j, c in enumerate(constraints):
            if not isinstance(c, dict) or not {"name", "weights", "bound"} <= set(c):
                raise ValueError(f"constraints[{j}] debe ser un diccionario con 'name', 'weights' y 'bound'.")
            w = as_float_list(c["weights"], f"constraints[{j}]['weights']", kind="nonneg")
            if len(w) != n:
                raise ValueError(f"La restricción '{c['name']}': 'weights' tiene una longitud distinta a demand_rates.")
            all_constraints.append(
                {"name": c["name"], "weights": w, "bound": as_positive(c["bound"], f"constraints[{j}]['bound']")}
            )

    # Unconstrained solution
    Q_unc = [math.sqrt(2 * D[i] * K[i] / h[i]) for i in range(n)]
    tc_unc = sum((h[i] * Q_unc[i] / 2 + D[i] * K[i] / Q_unc[i]) for i in range(n))

    if not all_constraints:
        # No constraints — return unconstrained
        items = []
        for i in range(n):
            tc_i = h[i] * Q_unc[i] / 2 + D[i] * K[i] / Q_unc[i]
            items.append({"Name": names[i], "Q*": Q_unc[i], "Total cost": tc_i,
                          "Holding cost": h[i] * Q_unc[i] / 2, "Ordering cost": D[i] * K[i] / Q_unc[i]})
        return ConstrainedMultiEOQResult(
            items=items, total_cost=tc_unc, unconstrained_total_cost=tc_unc,
            lagrange_multipliers={}, binding_constraints=[], params={"n_items": n})

    # Coordinate descent on Lagrange multipliers
    lambdas = {c["name"]: 0.0 for c in all_constraints}
    Q_opt = Q_unc[:]
    binding: list[str] = []

    for _iter in range(200):
        Q_prev = Q_opt[:]
        for c in all_constraints:
            cname = c["name"]
            w = c["weights"]
            b = c["bound"]
            # Effective holding cost from other lambdas
            h_eff = [h[i] for i in range(n)]
            for c2 in all_constraints:
                if c2["name"] != cname:
                    lj = lambdas[c2["name"]]
                    for i in range(n):
                        h_eff[i] += lj * c2["weights"][i]

            # Check if this constraint is violated with current λ_others
            Q_check = [math.sqrt(2 * D[i] * K[i] / max(h_eff[i], 1e-15)) for i in range(n)]
            if sum(w[i] * Q_check[i] for i in range(n)) <= b + 1e-9:
                lambdas[cname] = 0.0
                Q_opt = [math.sqrt(2 * D[i] * K[i] / max(h_eff[i], 1e-15)) for i in range(n)]
            else:
                lam_j, Q_j = _eoq_lagrangian_bisect(D, K, h_eff, w, b)
                lambdas[cname] = lam_j
                Q_opt = Q_j

        if max(abs(Q_opt[i] - Q_prev[i]) for i in range(n)) < 1e-8:
            break

    # Final Q using all lambdas
    h_final = [h[i] + sum(lambdas[c["name"]] * c["weights"][i] for c in all_constraints) for i in range(n)]
    Q_opt = [math.sqrt(2 * D[i] * K[i] / max(h_final[i], 1e-15)) for i in range(n)]

    # Binding = constraints where λ > 1e-10
    binding = [c["name"] for c in all_constraints if lambdas[c["name"]] > 1e-10]

    tc_opt = sum(h[i] * Q_opt[i] / 2 + D[i] * K[i] / Q_opt[i] for i in range(n))
    items = []
    for i in range(n):
        tc_i = h[i] * Q_opt[i] / 2 + D[i] * K[i] / Q_opt[i]
        items.append({"Name": names[i], "Q*": Q_opt[i], "Total cost": tc_i,
                      "Holding cost": h[i] * Q_opt[i] / 2, "Ordering cost": D[i] * K[i] / Q_opt[i]})

    return ConstrainedMultiEOQResult(
        items=items,
        total_cost=tc_opt,
        unconstrained_total_cost=tc_unc,
        lagrange_multipliers=lambdas,
        binding_constraints=binding,
        params={"n_items": n},
    )


# ---------------------------------------------------------------------------
# Dynamic lot-sizing: Lot-for-Lot and Silver-Meal
# ---------------------------------------------------------------------------

@dataclass
class LotSizingResult:
    """Dynamic lot-sizing result.

    Attributes
    ----------
    orders : list[dict]
        Each dict: {period, order_qty, covers_periods}.
    total_cost : float
        Total setup + holding cost over the horizon.
    total_setup_cost : float
    total_holding_cost : float
    n_orders : int
    method : str
    params : dict
    """

    orders: list
    total_cost: float
    total_setup_cost: float
    total_holding_cost: float
    n_orders: int
    method: str
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.orders)

    def summary(self) -> str:
        lines = [
            f"Method              : {self.method}",
            f"Number of orders    : {self.n_orders}",
            f"Total cost          : {self.total_cost:.6g}",
            f"  Setup cost        : {self.total_setup_cost:.6g}",
            f"  Holding cost      : {self.total_holding_cost:.6g}",
            "",
            f"{'Period':<8} {'Order qty':>10} {'Covers':>20}",
            "-" * 42,
        ]
        for o in self.orders:
            covers = str(o["covers_periods"])
            lines.append(f"{o['period']:<8} {o['order_qty']:>10.4g} {covers:>20}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def lot_for_lot(
    demands: Sequence[float],
    setup_cost: float,
    holding_cost: float,
) -> LotSizingResult:
    """Lot-for-Lot (L4L) dynamic lot-sizing heuristic.

    Orders exactly the demand for each period — zero inventory carried forward.
    Minimises holding cost at the expense of one setup per period with demand > 0.

    Parameters
    ----------
    demands : sequence of float
        Demand d_t for periods t = 1, 2, …, T.
    setup_cost : float
        Fixed setup cost S per order.
    holding_cost : float
        Holding cost h per unit per period.

    Returns
    -------
    LotSizingResult

    Examples
    --------
    >>> r = lot_for_lot([100, 80, 120, 60], setup_cost=200, holding_cost=1)
    >>> r.total_holding_cost
    0.0
    """
    demands    = as_float_list(demands, "demands", kind="nonneg")
    setup_cost = as_positive(setup_cost, "setup_cost")
    holding_cost = as_positive(holding_cost, "holding_cost")

    orders = []
    total_setup = 0.0
    for t, d in enumerate(demands, 1):
        if d > 0:
            orders.append({"period": t, "order_qty": d, "covers_periods": [t]})
            total_setup += setup_cost

    return LotSizingResult(
        orders=orders,
        total_cost=total_setup,
        total_setup_cost=total_setup,
        total_holding_cost=0.0,
        n_orders=len(orders),
        method="Lot-for-Lot",
        params={"setup_cost": setup_cost, "holding_cost": holding_cost},
    )


def silver_meal(
    demands: Sequence[float],
    setup_cost: float,
    holding_cost: float,
) -> LotSizingResult:
    """Silver-Meal heuristic for dynamic lot-sizing.

    Extends each order to cover additional periods as long as the average
    cost per period (setup + holding) keeps decreasing.

    Parameters
    ----------
    demands : sequence of float
        Demand d_t for periods t = 1, 2, …, T.
    setup_cost : float
        Fixed setup cost S per order.
    holding_cost : float
        Holding cost h per unit per period (charged for periods held).

    Returns
    -------
    LotSizingResult

    Examples
    --------
    >>> r = silver_meal([100, 80, 120, 60], setup_cost=200, holding_cost=1)
    >>> r.total_cost <= lot_for_lot([100, 80, 120, 60], 200, 1).total_cost
    True
    """
    demands    = as_float_list(demands, "demands", kind="nonneg")
    setup_cost = as_positive(setup_cost, "setup_cost")
    holding_cost = as_positive(holding_cost, "holding_cost")
    T = len(demands)

    orders: list[dict] = []
    total_setup   = 0.0
    total_holding = 0.0
    t = 0
    while t < T:
        if demands[t] == 0:
            t += 1
            continue
        # Extend coverage greedily while avg cost/period decreases
        order_qty  = demands[t]
        hold_accum = 0.0
        prev_avg   = setup_cost  # avg cost for k=1
        covers     = [t + 1]
        k = 1
        while t + k < T:
            hold_accum += k * holding_cost * demands[t + k]
            new_avg = (setup_cost + hold_accum) / (k + 1)
            if new_avg >= prev_avg:
                break
            prev_avg   = new_avg
            order_qty += demands[t + k]
            covers.append(t + k + 1)
            k += 1

        # Recompute holding cost for this run
        run_holding = sum(j * holding_cost * demands[t + j] for j in range(1, len(covers)))
        orders.append({"period": t + 1, "order_qty": order_qty, "covers_periods": covers})
        total_setup   += setup_cost
        total_holding += run_holding
        t += len(covers)

    return LotSizingResult(
        orders=orders,
        total_cost=total_setup + total_holding,
        total_setup_cost=total_setup,
        total_holding_cost=total_holding,
        n_orders=len(orders),
        method="Silver-Meal",
        params={"setup_cost": setup_cost, "holding_cost": holding_cost},
    )


# ---------------------------------------------------------------------------
# EOQ with all-units quantity discount
# ---------------------------------------------------------------------------

@dataclass
class QuantityDiscountResult:
    """EOQ with all-units quantity discounts result.

    Attributes
    ----------
    optimal_qty : float
        Optimal order quantity considering price breaks.
    unit_price : float
        Unit price at optimal_qty.
    total_cost : float
        Minimum annual total cost (purchase + ordering + holding).
    purchase_cost : float
        Annual purchase cost D * unit_price.
    ordering_cost_total : float
        Annual ordering cost (D/Q) * K.
    holding_cost_total : float
        Annual holding cost (Q/2) * h * unit_price.
    break_idx : int
        Index of the selected price break.
    candidates : list[dict]
        All evaluated candidates (one per break).
    params : dict
    """

    optimal_qty: float
    unit_price: float
    total_cost: float
    purchase_cost: float
    ordering_cost_total: float
    holding_cost_total: float
    break_idx: int
    candidates: list
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"Optimal order qty  : {self.optimal_qty:.4g} units\n"
            f"Unit price         : {self.unit_price:.4g}\n"
            f"Total cost/year    : {self.total_cost:.6g}\n"
            f"  Purchase cost    : {self.purchase_cost:.6g}\n"
            f"  Ordering cost    : {self.ordering_cost_total:.6g}\n"
            f"  Holding cost     : {self.holding_cost_total:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.candidates)


def eoq_quantity_discount(
    demand_rate: float,
    ordering_cost: float,
    holding_cost_rate: float,
    price_breaks: Sequence[tuple],
) -> QuantityDiscountResult:
    """EOQ with all-units quantity discounts.

    For each price break, computes the EOQ using h = holding_cost_rate × unit_price
    and checks whether it falls within the valid range.  Returns the break with
    minimum total annual cost (purchase + ordering + holding).

    Parameters
    ----------
    demand_rate : float
        Annual demand D.
    ordering_cost : float
        Fixed ordering cost per order K.
    holding_cost_rate : float
        Holding cost as fraction of unit price (e.g. 0.20 = 20% per year).
    price_breaks : sequence of (min_qty, unit_price) tuples
        Sorted ascending by min_qty.  Example: [(0, 10), (500, 9.5), (1000, 9)].

    Returns
    -------
    QuantityDiscountResult

    Examples
    --------
    >>> r = eoq_quantity_discount(
    ...     demand_rate=1000, ordering_cost=50, holding_cost_rate=0.2,
    ...     price_breaks=[(0, 10.0), (500, 9.5), (1000, 9.0)],
    ... )
    >>> r.total_cost > 0
    True
    """
    D  = as_positive(demand_rate, "demand_rate")
    K  = as_positive(ordering_cost, "ordering_cost")
    Ih = as_positive(holding_cost_rate, "holding_cost_rate")

    breaks = list(price_breaks)
    if len(breaks) < 1:
        raise ValueError("price_breaks must contain at least one entry.")

    # Sort by min_qty
    breaks.sort(key=lambda x: x[0])
    # Upper bounds for each break
    upper_bounds = [breaks[j + 1][0] - 1e-9 for j in range(len(breaks) - 1)] + [math.inf]

    candidates: list[dict] = []
    best: dict | None = None

    for idx, (min_q, price) in enumerate(breaks):
        h = Ih * price
        q_eoq = math.sqrt(2 * D * K / h)
        # Adjust to valid range
        lo = min_q
        hi = upper_bounds[idx]
        q_adj = max(lo, min(q_eoq, hi))

        pc = D * price
        oc = (D / q_adj) * K
        hc = (q_adj / 2) * h
        tc = pc + oc + hc
        candidates.append({
            "Break idx": idx,
            "Min qty": min_q,
            "Unit price": price,
            "EOQ": q_eoq,
            "Adj Q": q_adj,
            "Purchase cost": pc,
            "Ordering cost": oc,
            "Holding cost": hc,
            "Total cost": tc,
            "Feasible": lo <= q_adj <= (upper_bounds[idx] + 1e-9),
        })
        if best is None or tc < best["Total cost"]:
            best = candidates[-1]

    if best is None:
        raise ValueError("No feasible price break found.")

    return QuantityDiscountResult(
        optimal_qty=best["Adj Q"],
        unit_price=best["Unit price"],
        total_cost=best["Total cost"],
        purchase_cost=best["Purchase cost"],
        ordering_cost_total=best["Ordering cost"],
        holding_cost_total=best["Holding cost"],
        break_idx=best["Break idx"],
        candidates=candidates,
        params={"demand_rate": D, "ordering_cost": K, "holding_cost_rate": Ih},
    )


# ---------------------------------------------------------------------------
# Wagner-Whitin (optimal dynamic lot-sizing)
# ---------------------------------------------------------------------------

def wagner_whitin(
    demands: Sequence[float],
    setup_cost: float,
    holding_cost: float,
) -> LotSizingResult:
    """Wagner-Whitin optimal dynamic lot-sizing via dynamic programming.

    Finds the exact minimum-cost ordering policy over a finite horizon,
    unlike Silver-Meal (heuristic).  Time complexity O(n²).

    Parameters
    ----------
    demands : sequence of float
        Demand d_t for periods t = 1, 2, …, T.
    setup_cost : float
        Fixed setup / ordering cost S per order.
    holding_cost : float
        Holding cost h per unit per period.

    Returns
    -------
    LotSizingResult
        ``method`` is ``'Wagner-Whitin'``.

    Examples
    --------
    >>> r = wagner_whitin([100, 80, 120, 60], setup_cost=200, holding_cost=1)
    >>> r.total_cost <= wagner_whitin.__doc__ and True  # optimal ≤ Silver-Meal
    True
    """
    demands_v = as_float_list(demands, "demands", kind="nonneg")
    K = as_positive(setup_cost, "setup_cost")
    h = as_positive(holding_cost, "holding_cost")
    n = len(demands_v)

    INF = float("inf")
    dp = [INF] * (n + 1)   # dp[j] = min cost to satisfy demands 0..j-1
    dp[0] = 0.0
    last = [-1] * (n + 1)  # last[j] = period i where order was placed

    for j in range(1, n + 1):
        for i in range(1, j + 1):
            # Order at start of period i to cover demands i..j (1-indexed)
            hold = h * sum((k - i) * demands_v[k - 1] for k in range(i, j + 1))
            cost = dp[i - 1] + K + hold
            if cost < dp[j]:
                dp[j] = cost
                last[j] = i

    # Reconstruct orders
    orders = []
    j = n
    while j > 0:
        i = last[j]
        qty = sum(demands_v[k - 1] for k in range(i, j + 1))
        orders.append({
            "period": i,
            "order_qty": qty,
            "covers_periods": list(range(i, j + 1)),
        })
        j = i - 1
    orders.reverse()

    total_setup = len(orders) * K
    total_holding = dp[n] - total_setup
    return LotSizingResult(
        orders=orders,
        total_cost=dp[n],
        total_setup_cost=total_setup,
        total_holding_cost=total_holding,
        n_orders=len(orders),
        method="Wagner-Whitin",
        params={"setup_cost": K, "holding_cost": h},
    )


# ---------------------------------------------------------------------------
# (r, Q) Continuous review policy
# ---------------------------------------------------------------------------

@dataclass
class RQPolicyResult:
    """(r, Q) continuous review inventory policy result.

    Attributes
    ----------
    order_qty : float
        EOQ-based order quantity Q*.
    reorder_point : float
        Reorder point r = mean demand during LT + safety stock.
    safety_stock : float
        Safety stock SS = z · σ_DLT.
    service_level : float
        Cycle service level P(no stockout per cycle).
    avg_inventory : float
        Average on-hand inventory ≈ Q*/2 + SS.
    total_cost : float
        Annual holding + ordering cost at (Q*, r).
    """

    order_qty: float
    reorder_point: float
    safety_stock: float
    service_level: float
    avg_inventory: float
    total_cost: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"(r, Q) continuous review policy\n"
            f"  Order quantity Q*   : {self.order_qty:.4g}\n"
            f"  Reorder point r     : {self.reorder_point:.4g}\n"
            f"  Safety stock SS     : {self.safety_stock:.4g}\n"
            f"  Service level       : {self.service_level:.2%}\n"
            f"  Avg inventory       : {self.avg_inventory:.4g}\n"
            f"  Total cost          : {self.total_cost:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "Q*": self.order_qty,
            "r": self.reorder_point,
            "Safety stock": self.safety_stock,
            "Service level": self.service_level,
            "Avg inventory": self.avg_inventory,
            "Total cost": self.total_cost,
        }])


def rq_policy(
    demand_rate: float,
    ordering_cost: float,
    holding_cost: float,
    lead_time: float,
    *,
    demand_std: float = 0.0,
    lead_time_std: float = 0.0,
    service_level: float = 0.95,
) -> RQPolicyResult:
    """(r, Q) continuous-review inventory policy.

    Combines the EOQ as order quantity and a statistically-derived reorder
    point.  The two decisions are determined independently.

    Parameters
    ----------
    demand_rate : float
        Mean demand per period D̄.
    ordering_cost : float
        Fixed ordering cost K per order.
    holding_cost : float
        Holding cost h per unit per period.
    lead_time : float
        Mean replenishment lead time L̄.
    demand_std : float
        Std dev of demand per period σ_D (default 0).
    lead_time_std : float
        Std dev of lead time σ_L (default 0).
    service_level : float
        Cycle service level ∈ (0, 1). Default 0.95.

    Returns
    -------
    RQPolicyResult
    """
    from statistics import NormalDist
    D   = as_positive(demand_rate,  "demand_rate")
    K   = as_positive(ordering_cost, "ordering_cost")
    h   = as_positive(holding_cost,  "holding_cost")
    LT  = as_positive(lead_time,     "lead_time")
    sd  = as_nonneg(demand_std,      "demand_std")
    sl  = as_nonneg(lead_time_std,   "lead_time_std")
    svc = as_fraction(service_level, "service_level")
    if svc <= 0.0 or svc >= 1.0:
        raise ValueError("'service_level' must be strictly between 0 and 1.")

    Q   = math.sqrt(2 * D * K / h)
    mean_dlt = D * LT
    std_dlt  = math.sqrt(LT * sd**2 + D**2 * sl**2)
    z   = NormalDist().inv_cdf(svc)
    SS  = z * std_dlt
    r   = mean_dlt + SS
    avg_inv  = Q / 2 + SS
    total_cost = (D / Q) * K + avg_inv * h

    return RQPolicyResult(
        order_qty=Q,
        reorder_point=r,
        safety_stock=SS,
        service_level=svc,
        avg_inventory=avg_inv,
        total_cost=total_cost,
        params={"demand_rate": D, "ordering_cost": K, "holding_cost": h,
                "lead_time": LT, "demand_std": sd, "lead_time_std": sl},
    )


# ---------------------------------------------------------------------------
# (R, S) Periodic review policy
# ---------------------------------------------------------------------------

@dataclass
class RSPolicyResult:
    """(R, S) periodic-review inventory policy result.

    Attributes
    ----------
    review_period : float
        Review interval R.
    order_up_to : float
        Order-up-to level S = mean demand over (R+L) + safety stock.
    safety_stock : float
        Safety stock SS = z · σ_{R+L}.
    service_level : float
        Cycle service level.
    avg_inventory : float
        Average on-hand inventory ≈ D·R/2 + SS.
    total_cost : float
        Annual holding + ordering cost at (R, S).
    """

    review_period: float
    order_up_to: float
    safety_stock: float
    service_level: float
    avg_inventory: float
    total_cost: float
    params: dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"(R, S) periodic review policy\n"
            f"  Review period R     : {self.review_period:.4g}\n"
            f"  Order-up-to S       : {self.order_up_to:.4g}\n"
            f"  Safety stock SS     : {self.safety_stock:.4g}\n"
            f"  Service level       : {self.service_level:.2%}\n"
            f"  Avg inventory       : {self.avg_inventory:.4g}\n"
            f"  Total cost          : {self.total_cost:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame([{
            "R": self.review_period,
            "S": self.order_up_to,
            "Safety stock": self.safety_stock,
            "Service level": self.service_level,
            "Avg inventory": self.avg_inventory,
            "Total cost": self.total_cost,
        }])


def rs_policy(
    demand_rate: float,
    ordering_cost: float,
    holding_cost: float,
    lead_time: float,
    review_period: float,
    *,
    demand_std: float = 0.0,
    lead_time_std: float = 0.0,
    service_level: float = 0.95,
) -> RSPolicyResult:
    """(R, S) periodic-review inventory policy.

    The inventory position is checked every R periods and an order is
    placed to bring it up to S.

    Parameters
    ----------
    demand_rate : float
        Mean demand per period D̄.
    ordering_cost : float
        Fixed ordering cost K per order.
    holding_cost : float
        Holding cost h per unit per period.
    lead_time : float
        Mean replenishment lead time L̄.
    review_period : float
        Review interval R (periods between inventory checks).
    demand_std : float
        Std dev of demand per period σ_D (default 0).
    lead_time_std : float
        Std dev of lead time σ_L (default 0).
    service_level : float
        Cycle service level ∈ (0, 1). Default 0.95.

    Returns
    -------
    RSPolicyResult
    """
    from statistics import NormalDist
    D   = as_positive(demand_rate,   "demand_rate")
    K   = as_positive(ordering_cost, "ordering_cost")
    h   = as_positive(holding_cost,  "holding_cost")
    LT  = as_positive(lead_time,     "lead_time")
    R   = as_positive(review_period, "review_period")
    sd  = as_nonneg(demand_std,      "demand_std")
    sl  = as_nonneg(lead_time_std,   "lead_time_std")
    svc = as_fraction(service_level, "service_level")
    if svc <= 0.0 or svc >= 1.0:
        raise ValueError("'service_level' must be strictly between 0 and 1.")

    # Exposure period = R + L
    RL = R + LT
    mean_rl = D * RL
    std_rl  = math.sqrt(RL * sd**2 + D**2 * sl**2)
    z       = NormalDist().inv_cdf(svc)
    SS      = z * std_rl
    S       = mean_rl + SS
    avg_inv = D * R / 2 + SS
    total_cost = (1.0 / R) * K + avg_inv * h

    return RSPolicyResult(
        review_period=R,
        order_up_to=S,
        safety_stock=SS,
        service_level=svc,
        avg_inventory=avg_inv,
        total_cost=total_cost,
        params={"demand_rate": D, "ordering_cost": K, "holding_cost": h,
                "lead_time": LT, "review_period": R, "demand_std": sd,
                "lead_time_std": sl},
    )


# ---------------------------------------------------------------------------
# Exchange curves
# ---------------------------------------------------------------------------

@dataclass
class ExchangeCurveResult:
    """Aggregate exchange-curve result for a family of items.

    Attributes
    ----------
    n_orders_eoq : float
        Total orders per year at the individual-EOQ point (k = 1).
    investment_eoq : float
        Total average inventory investment at the EOQ point.
    multiplier : float
        Scaling factor k applied to all EOQ quantities (k = 1 → EOQ).
    n_orders_optimal : float
        Total orders per year at the chosen policy point.
    investment_optimal : float
        Total average inventory investment at the chosen policy point.
    target : str
        Description of the target used (``'eoq'``, ``'orders'``, or
        ``'investment'``).
    optimal_quantities : list[dict]
        Per-item dicts with keys ``name``, ``Q_eoq``, ``Q_optimal``,
        ``n_orders``, ``investment``.
    curve_points : list[dict]
        Points on the exchange hyperbola: ``[{'N': …, 'I': …}, …]``.
    """

    n_orders_eoq: float
    investment_eoq: float
    multiplier: float
    n_orders_optimal: float
    investment_optimal: float
    target: str
    optimal_quantities: list
    curve_points: list

    def to_frame(self) -> pd.DataFrame:
        """Per-item quantities DataFrame: name, Q_eoq, Q_optimal, n_orders, investment."""
        import pandas as pd
        return pd.DataFrame(self.optimal_quantities)

    def curve_to_frame(self) -> pd.DataFrame:
        """Exchange-curve hyperbola DataFrame: columns N (orders/yr) and I (investment)."""
        import pandas as pd
        return pd.DataFrame(self.curve_points)

    def summary(self) -> str:
        lines = [
            f"Target                  : {self.target}",
            f"Multiplier k            : {self.multiplier:.4f}",
            f"N orders/yr  (EOQ)      : {self.n_orders_eoq:.4g}",
            f"N orders/yr  (optimal)  : {self.n_orders_optimal:.4g}",
            f"Investment   (EOQ)      : {self.investment_eoq:.4g}",
            f"Investment   (optimal)  : {self.investment_optimal:.4g}",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def exchange_curve(
    items: list,
    *,
    target_orders: float | None = None,
    target_investment: float | None = None,
    n_curve_points: int = 50,
) -> ExchangeCurveResult:
    """Aggregate exchange curve for a family of inventory items.

    For a family of items each managed with an EOQ policy, varying a common
    multiplier *k* on all order quantities traces a hyperbola in the
    (N orders/year, average investment) plane:

        N(k) = N* / k        I(k) = k · I*       →    N · I = N* · I*

    The function computes the EOQ point (k=1) and, when a target is
    supplied, solves for the k that meets it and re-scales all quantities.

    Parameters
    ----------
    items : list of dict
        Each dict must contain:

        - ``demand`` (float) — annual demand Di.
        - ``ordering_cost`` (float) — setup/ordering cost Ki.
        - ``holding_cost`` (float) — holding cost per unit per year hi.

        Optional keys:

        - ``unit_value`` (float) — unit value vi for investment calculation
          (default 1).
        - ``name`` (str) — item label (default ``'I1'``, ``'I2'``, …).

    target_orders : float, optional
        Desired total orders per year.  Solves k = N* / target_orders.
    target_investment : float, optional
        Desired total average inventory investment.  Solves k = target / I*.
    n_curve_points : int
        Number of points on the plotted hyperbola (default 50).

    Returns
    -------
    ExchangeCurveResult

    Notes
    -----
    Only one of *target_orders* or *target_investment* may be specified.
    If neither is given the EOQ point (k = 1) is returned.
    """
    if target_orders is not None and target_investment is not None:
        raise ValueError(
            "Specify at most one of 'target_orders' or 'target_investment'."
        )
    if len(items) == 0:
        raise ValueError("'items' must contain at least one item.")

    parsed = []
    for idx, it in enumerate(items):
        D  = as_positive(float(it["demand"]),        f"items[{idx}]['demand']")
        K  = as_positive(float(it["ordering_cost"]), f"items[{idx}]['ordering_cost']")
        h  = as_positive(float(it["holding_cost"]),  f"items[{idx}]['holding_cost']")
        v  = float(it.get("unit_value", 1.0))
        nm = str(it.get("name", f"I{idx + 1}"))
        if v <= 0:
            raise ValueError(f"items[{idx}]['unit_value'] must be > 0.")
        Q_eoq = math.sqrt(2 * D * K / h)
        parsed.append({"name": nm, "D": D, "K": K, "h": h, "v": v, "Q_eoq": Q_eoq})

    N_star = sum(p["D"] / p["Q_eoq"] for p in parsed)
    I_star = sum(p["Q_eoq"] * p["v"] / 2.0 for p in parsed)

    if target_orders is not None:
        to = as_positive(target_orders, "target_orders")
        k = N_star / to
        target_label = f"orders={to:.4g}"
    elif target_investment is not None:
        ti = as_positive(target_investment, "target_investment")
        k = ti / I_star
        target_label = f"investment={ti:.4g}"
    else:
        k = 1.0
        target_label = "eoq"

    N_opt = N_star / k
    I_opt = k * I_star

    opt_qtys = []
    for p in parsed:
        Q_opt = k * p["Q_eoq"]
        n_i   = p["D"] / Q_opt
        inv_i = Q_opt * p["v"] / 2.0
        opt_qtys.append({
            "name":       p["name"],
            "Q_eoq":      round(p["Q_eoq"], 6),
            "Q_optimal":  round(Q_opt, 6),
            "n_orders":   round(n_i, 6),
            "investment": round(inv_i, 6),
        })

    # Hyperbola points: vary k from 0.1 to 5 × EOQ point
    product = N_star * I_star
    n_min = N_star * 0.1
    n_max = N_star * 10.0
    step  = (n_max - n_min) / (n_curve_points - 1)
    curve_pts = [
        {"N": round(n_min + i * step, 6),
         "I": round(product / (n_min + i * step), 6)}
        for i in range(n_curve_points)
    ]

    return ExchangeCurveResult(
        n_orders_eoq=N_star,
        investment_eoq=I_star,
        multiplier=k,
        n_orders_optimal=N_opt,
        investment_optimal=I_opt,
        target=target_label,
        optimal_quantities=opt_qtys,
        curve_points=curve_pts,
    )


# ---------------------------------------------------------------------------
# Safety-stock exchange curve (Type 2)
# ---------------------------------------------------------------------------

@dataclass
class SafetyStockCurveResult:
    """Safety-stock exchange curve result for a family of items.

    Uses a **common z-value** policy across all items, which is the standard
    aggregate approach: all items share the same cycle service level Φ(z).

    Attributes
    ----------
    z : float
        Common z-value (standard normal quantile) applied.
    service_level : float
        Cycle service level = Φ(z).
    ss_investment : float
        Total safety-stock investment = z · Σ σᵢ_DLT · vᵢ.
    target : str
        Description of the target used.
    optimal_quantities : list[dict]
        Per-item dicts: ``name``, ``sigma_dlt``, ``safety_stock``,
        ``investment``, ``reorder_point`` (only when ``demand_rate`` supplied).
    curve_points : list[dict]
        Points on the curve: ``[{'z': …, 'service_level': …,
        'ss_investment': …}, …]``.
    """

    z: float
    service_level: float
    ss_investment: float
    target: str
    optimal_quantities: list
    curve_points: list

    def to_frame(self) -> pd.DataFrame:
        """Per-item safety-stock DataFrame."""
        import pandas as pd
        return pd.DataFrame(self.optimal_quantities)

    def curve_to_frame(self) -> pd.DataFrame:
        """Full exchange curve DataFrame: z, service_level, ss_investment."""
        import pandas as pd
        return pd.DataFrame(self.curve_points)

    def summary(self) -> str:
        lines = [
            f"Target          : {self.target}",
            f"z               : {self.z:.4f}",
            f"Service level   : {self.service_level:.4%}",
            f"SS investment   : {self.ss_investment:.4g}",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def safety_stock_curve(
    items: list,
    *,
    target_service_level: float | None = None,
    target_ss_investment: float | None = None,
    n_curve_points: int = 60,
) -> SafetyStockCurveResult:
    """Safety-stock exchange curve for a family of items (common-z policy).

    With a **common z** all items share the same cycle service level Φ(z).
    Varying z traces the exchange curve between aggregate SS investment and
    service level:

        SS_investment(z) = z · Σ σᵢ_DLT · vᵢ

    Parameters
    ----------
    items : list of dict
        Each dict must contain:

        - ``demand_std`` (float) — standard deviation of demand per unit time.
        - ``lead_time`` (float) — replenishment lead time (same time unit).

        Optional keys:

        - ``lead_time_std`` (float) — std dev of lead time (default 0).
        - ``demand_rate`` (float) — mean demand per unit time; used to
          compute the reorder point r = D·L + SS (default: omitted).
        - ``unit_value`` (float) — unit value for investment (default 1).
        - ``name`` (str) — item label (default ``'I1'``, ``'I2'``, …).

    target_service_level : float, optional
        Desired cycle service level ∈ (0, 1).  Solves z = Φ⁻¹(SL).
    target_ss_investment : float, optional
        Desired total SS investment.  Solves z = target / (Σ σᵢ_DLT · vᵢ).
    n_curve_points : int
        Number of points on the plotted curve (default 60, z from −2 to 4).

    Returns
    -------
    SafetyStockCurveResult

    Notes
    -----
    Only one of *target_service_level* or *target_ss_investment* may be given.
    If neither is supplied, z = 0 (50 % service level) is used as the
    baseline; pass ``target_service_level=0.95`` for the typical default.
    """
    if target_service_level is not None and target_ss_investment is not None:
        raise ValueError(
            "Specify at most one of 'target_service_level' or 'target_ss_investment'."
        )
    if len(items) == 0:
        raise ValueError("'items' must contain at least one item.")

    _norm = NormalDist()

    parsed = []
    for idx, it in enumerate(items):
        sd   = as_nonneg(float(it["demand_std"]),  f"items[{idx}]['demand_std']")
        L    = as_positive(float(it["lead_time"]), f"items[{idx}]['lead_time']")
        sl   = float(it.get("lead_time_std", 0.0))
        v    = float(it.get("unit_value", 1.0))
        nm   = str(it.get("name", f"I{idx + 1}"))
        D    = it.get("demand_rate")
        D    = float(D) if D is not None else None
        if v <= 0:
            raise ValueError(f"items[{idx}]['unit_value'] must be > 0.")
        if sl < 0:
            raise ValueError(f"items[{idx}]['lead_time_std'] must be ≥ 0.")
        # σ_DLT = √(L·σ_D² + D²·σ_L²)  — reduces to σ_D·√L when σ_L=0
        if D is not None and sl > 0:
            sigma_dlt = math.sqrt(L * sd**2 + D**2 * sl**2)
        else:
            sigma_dlt = sd * math.sqrt(L)
        parsed.append({"name": nm, "sigma_dlt": sigma_dlt, "v": v, "D": D, "L": L})

    total_sigma_v = sum(p["sigma_dlt"] * p["v"] for p in parsed)

    # Solve for z
    if target_service_level is not None:
        sl_val = float(target_service_level)
        if not (0.0 < sl_val < 1.0):
            raise ValueError("'target_service_level' must be strictly between 0 and 1.")
        z = _norm.inv_cdf(sl_val)
        target_label = f"service_level={sl_val:.4%}"
    elif target_ss_investment is not None:
        ti = as_positive(float(target_ss_investment), "target_ss_investment")
        if total_sigma_v == 0.0:
            raise ValueError(
                "All items have demand_std=0 — safety stock is always 0."
            )
        z = ti / total_sigma_v
        target_label = f"ss_investment={ti:.4g}"
    else:
        z = 0.0
        target_label = "baseline (z=0)"

    sl_result = _norm.cdf(z)
    ss_inv    = z * total_sigma_v

    opt_qtys = []
    for p in parsed:
        ss_i   = z * p["sigma_dlt"]
        inv_i  = z * p["sigma_dlt"] * p["v"]
        row: dict = {
            "name":          p["name"],
            "sigma_dlt":     round(p["sigma_dlt"], 6),
            "safety_stock":  round(ss_i, 6),
            "investment":    round(inv_i, 6),
        }
        if p["D"] is not None:
            row["reorder_point"] = round(p["D"] * p["L"] + ss_i, 6)
        opt_qtys.append(row)

    # Curve: z from −2 to 4
    z_min, z_max = -2.0, 4.0
    step = (z_max - z_min) / (n_curve_points - 1)
    curve_pts = []
    for i in range(n_curve_points):
        zi   = z_min + i * step
        sli  = _norm.cdf(zi)
        ssi  = zi * total_sigma_v
        curve_pts.append({
            "z":             round(zi, 4),
            "service_level": round(sli, 6),
            "ss_investment": round(ssi, 6),
        })

    return SafetyStockCurveResult(
        z=z,
        service_level=sl_result,
        ss_investment=ss_inv,
        target=target_label,
        optimal_quantities=opt_qtys,
        curve_points=curve_pts,
    )


# ---------------------------------------------------------------------------
# ABC / XYZ / ABC-XYZ classification
# ---------------------------------------------------------------------------

@dataclass
class ABCResult:
    """ABC Pareto classification result.

    Attributes
    ----------
    items : list[dict]
        Items sorted descending by annual value; each dict has keys
        ``name``, ``demand``, ``unit_value``, ``annual_value``,
        ``cumulative_pct``, ``pct_value``, ``rank``, ``class``.
    class_summary : dict
        ``{A: {count, pct_items, pct_value}, B: …, C: …}``.
    total_value : float
        Total annual inventory value.
    thresholds : dict
        ``{a: float, b: float}`` used for classification.
    """

    items: list
    class_summary: dict
    total_value: float
    thresholds: dict

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items)

    def summary(self) -> str:
        lines = [
            f"Total annual value : {self.total_value:.6g}",
            f"{'Class':<6} {'Items':>6}  {'%Items':>7}  {'%Value':>7}",
            "-" * 32,
        ]
        for cls in ["A", "B", "C"]:
            s = self.class_summary[cls]
            lines.append(
                f"  {cls}    {s['count']:>4}    {s['pct_items']:>6.1%}   {s['pct_value']:>6.1%}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


@dataclass
class XYZResult:
    """XYZ demand-variability classification result.

    Attributes
    ----------
    items : list[dict]
        Each dict has keys ``name``, ``cv``, ``class``.
    class_summary : dict
        ``{X: {count, pct_items}, Y: …, Z: …}``.
    thresholds : dict
        ``{x: float, y: float}`` CV boundaries.
    """

    items: list
    class_summary: dict
    thresholds: dict

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items)

    def summary(self) -> str:
        t = self.thresholds
        ranges = {
            "X": f"CV ≤ {t['x']:.2g}",
            "Y": f"{t['x']:.2g} < CV ≤ {t['y']:.2g}",
            "Z": f"CV > {t['y']:.2g}",
        }
        lines = [
            f"{'Class':<6} {'Items':>6}  {'%Items':>7}  {'CV range'}",
            "-" * 42,
        ]
        for cls in ["X", "Y", "Z"]:
            s = self.class_summary[cls]
            lines.append(
                f"  {cls}    {s['count']:>4}    {s['pct_items']:>6.1%}   {ranges[cls]}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


@dataclass
class ABCXYZResult:
    """Combined ABC-XYZ classification result.

    Attributes
    ----------
    items : list[dict]
        Each dict has keys ``name``, ``annual_value``, ``cv``,
        ``abc_class``, ``xyz_class``, ``combined_class``.
    matrix : dict
        ``{(abc, xyz): count}`` for all 9 cells.
    """

    items: list
    matrix: dict

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.items)

    def matrix_frame(self) -> pd.DataFrame:
        """Pivot table ABC (rows) × XYZ (columns) with item counts."""
        import pandas as pd
        data = {
            xyz: {abc: self.matrix.get((abc, xyz), 0) for abc in ["A", "B", "C"]}
            for xyz in ["X", "Y", "Z"]
        }
        return pd.DataFrame(data, index=["A", "B", "C"])

    def summary(self) -> str:
        lines = ["ABC\\XYZ   X     Y     Z   Total"]
        for abc in ["A", "B", "C"]:
            row_total = sum(self.matrix.get((abc, xyz), 0) for xyz in ["X", "Y", "Z"])
            lines.append(
                f"   {abc}    "
                + "".join(f"  {self.matrix.get((abc, xyz), 0):3d}" for xyz in ["X", "Y", "Z"])
                + f"   {row_total:4d}"
            )
        col_totals = [sum(self.matrix.get((abc, xyz), 0) for abc in ["A", "B", "C"]) for xyz in ["X", "Y", "Z"]]
        grand = sum(col_totals)
        lines.append("Total  " + "".join(f"  {c:3d}" for c in col_totals) + f"   {grand:4d}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def _leer_items(items, nombre: str = "items") -> list:
    """Valida que ``items`` sea una lista no vacía de diccionarios."""
    if isinstance(items, (str, bytes, dict)) or not hasattr(items, "__iter__"):
        raise TypeError(f"'{nombre}' debe ser una lista de diccionarios, se recibió {type(items).__name__!r}.")
    items = list(items)
    if not items:
        raise ValueError(f"'{nombre}' debe contener al menos un elemento.")
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise TypeError(f"{nombre}[{i}] debe ser un diccionario, se recibió {type(it).__name__!r}.")
    return items


def _clave(it: dict, i: int, clave: str, nombre: str = "items"):
    """Devuelve ``it[clave]`` o lanza un ValueError que indica el elemento y la clave que faltan."""
    if clave not in it:
        raise ValueError(f"{nombre}[{i}]: falta la clave '{clave}'.")
    return it[clave]


def abc_analysis(
    items: list,
    *,
    a_threshold: float = 0.80,
    b_threshold: float = 0.95,
) -> ABCResult:
    """ABC Pareto classification of inventory items by annual value.

    Items are sorted descending by annual value (demand × unit_value).
    Classification follows cumulative percentage of total value:

    - **A**: items whose cumulative value has not yet exceeded
      *a_threshold* (typically top ~80% of value, ~20% of items).
    - **B**: next band up to *b_threshold* (~15% of value).
    - **C**: remainder (~5% of value, ~50% of items).

    Parameters
    ----------
    items : list of dict
        Each dict must have ``'demand'`` (annual demand) and
        ``'unit_value'``.  Optional ``'name'`` key.
    a_threshold : float
        Cumulative value fraction that ends class A (default 0.80).
    b_threshold : float
        Cumulative value fraction that ends class B (default 0.95).

    Returns
    -------
    ABCResult
    """
    items = _leer_items(items)
    if not (0.0 < a_threshold < b_threshold < 1.0):
        raise ValueError("Debe cumplirse 0 < a_threshold < b_threshold < 1.")

    enriched = []
    for i, it in enumerate(items):
        nm  = it.get("name", f"Item{i + 1}")
        D   = as_nonneg(_clave(it, i, "demand"), f"items[{i}]['demand']")
        v   = as_positive(_clave(it, i, "unit_value"), f"items[{i}]['unit_value']")
        enriched.append({"name": str(nm), "demand": D, "unit_value": v,
                         "annual_value": D * v, "index": i})

    enriched.sort(key=lambda x: -x["annual_value"])
    n           = len(enriched)
    total_value = sum(e["annual_value"] for e in enriched)
    if total_value <= 0.0:
        raise ValueError("El valor anual total es cero (todas las demandas son 0): no hay nada que clasificar.")

    cum = 0.0
    class_agg: dict = {"A": {"count": 0, "value": 0.0},
                        "B": {"count": 0, "value": 0.0},
                        "C": {"count": 0, "value": 0.0}}
    for i, e in enumerate(enriched):
        prev_pct = cum / total_value
        cum += e["annual_value"]
        e["cumulative_pct"] = cum / total_value
        e["pct_value"]      = e["annual_value"] / total_value
        e["rank"]           = i + 1
        if prev_pct < a_threshold:
            cls = "A"
        elif prev_pct < b_threshold:
            cls = "B"
        else:
            cls = "C"
        e["class"] = cls
        class_agg[cls]["count"] += 1
        class_agg[cls]["value"] += e["annual_value"]

    class_summary = {
        cls: {
            "count":     class_agg[cls]["count"],
            "pct_items": class_agg[cls]["count"] / n,
            "pct_value": class_agg[cls]["value"] / total_value,
        }
        for cls in ["A", "B", "C"]
    }

    return ABCResult(
        items=enriched,
        class_summary=class_summary,
        total_value=total_value,
        thresholds={"a": a_threshold, "b": b_threshold},
    )


def xyz_analysis(
    items: list,
    *,
    x_threshold: float = 0.5,
    y_threshold: float = 1.0,
) -> XYZResult:
    """XYZ classification of inventory items by demand variability (CV).

    - **X**: CV ≤ *x_threshold* — stable, predictable demand.
    - **Y**: *x_threshold* < CV ≤ *y_threshold* — moderate variability.
    - **Z**: CV > *y_threshold* — erratic, hard to forecast.

    Parameters
    ----------
    items : list of dict
        Each dict must supply the coefficient of variation in one of two ways:

        - ``'cv'`` directly, **or**
        - ``'demand_std'`` **+** (``'demand_mean'`` or ``'demand_rate'``).

        Optional ``'name'`` key.
    x_threshold : float
        Upper CV boundary for class X (default 0.5).
    y_threshold : float
        Upper CV boundary for class Y (default 1.0).

    Returns
    -------
    XYZResult
    """
    items = _leer_items(items)
    if not (0.0 <= x_threshold < y_threshold):
        raise ValueError("Debe cumplirse 0 ≤ x_threshold < y_threshold.")

    enriched = []
    for i, it in enumerate(items):
        nm = it.get("name", f"Item{i + 1}")
        if "cv" in it:
            cv = as_nonneg(it["cv"], f"items[{i}]['cv']")
        else:
            std  = as_nonneg(_clave(it, i, "demand_std"), f"items[{i}]['demand_std']")
            if "demand_mean" in it:
                mean = it["demand_mean"]
            elif "demand_rate" in it:
                mean = it["demand_rate"]
            else:
                raise ValueError(f"items[{i}]: falta 'cv' o ('demand_std' y 'demand_mean'/'demand_rate').")
            mean = as_positive(mean, f"items[{i}]['demand_mean']")
            cv = std / mean
        if cv <= x_threshold:
            cls = "X"
        elif cv <= y_threshold:
            cls = "Y"
        else:
            cls = "Z"
        enriched.append({"name": str(nm), "cv": cv, "class": cls})

    n = len(enriched)
    class_agg: dict = {"X": 0, "Y": 0, "Z": 0}
    for e in enriched:
        class_agg[e["class"]] += 1

    class_summary = {
        cls: {"count": class_agg[cls], "pct_items": class_agg[cls] / n}
        for cls in ["X", "Y", "Z"]
    }

    return XYZResult(
        items=enriched,
        class_summary=class_summary,
        thresholds={"x": x_threshold, "y": y_threshold},
    )


def abc_xyz(
    items: list,
    *,
    a_threshold: float = 0.80,
    b_threshold: float = 0.95,
    x_threshold: float = 0.5,
    y_threshold: float = 1.0,
) -> ABCXYZResult:
    """Combined ABC-XYZ classification.

    Each item requires fields for both ABC (``demand``, ``unit_value``) and
    XYZ (``cv`` or ``demand_std`` + ``demand_mean``/``demand_rate``).

    Parameters
    ----------
    items : list of dict
        Must supply fields required by both :func:`abc_analysis` and
        :func:`xyz_analysis`.  ``name`` is optional.
    a_threshold, b_threshold : float
        ABC thresholds (see :func:`abc_analysis`).
    x_threshold, y_threshold : float
        XYZ thresholds (see :func:`xyz_analysis`).

    Returns
    -------
    ABCXYZResult
    """
    abc_r = abc_analysis(items, a_threshold=a_threshold, b_threshold=b_threshold)
    xyz_r = xyz_analysis(items, x_threshold=x_threshold, y_threshold=y_threshold)

    combined = []
    matrix: dict = {}
    for e_abc in abc_r.items:
        nm      = e_abc["name"]
        e_xyz   = xyz_r.items[e_abc["index"]]
        abc_cls = e_abc["class"]
        xyz_cls = e_xyz["class"]
        key     = (abc_cls, xyz_cls)
        matrix[key] = matrix.get(key, 0) + 1
        combined.append({
            "name":          nm,
            "annual_value":  e_abc["annual_value"],
            "cv":            e_xyz["cv"],
            "abc_class":     abc_cls,
            "xyz_class":     xyz_cls,
            "combined_class": f"{abc_cls}{xyz_cls}",
        })

    return ABCXYZResult(items=combined, matrix=matrix)


# ---------------------------------------------------------------------------
# MRP — single-level Material Requirements Planning
# ---------------------------------------------------------------------------

@dataclass
class MRPResult:
    """Single-level MRP result.

    Attributes
    ----------
    item_name : str
    periods : list
        Period labels (1, 2, … or user-supplied).
    gross_requirements : list[float]
    scheduled_receipts : list[float]
    projected_on_hand : list[float]
        Ending on-hand inventory after all transactions each period.
    net_requirements : list[float]
    planned_receipts : list[float]
        Planned order receipts arriving this period.
    planned_releases : list[float]
        Planned order releases (issued *lead_time* periods before receipt).
    past_due_releases : float
        Cantidad total de órdenes planificadas cuya liberación debió ocurrir antes del
        periodo 1 (el lead time no cabe en el horizonte); no aparece en ``planned_releases``.
    """

    item_name: str
    periods: list
    gross_requirements: list
    scheduled_receipts: list
    projected_on_hand: list
    net_requirements: list
    planned_receipts: list
    planned_releases: list
    past_due_releases: float = 0.0

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame({
            "Period":          self.periods,
            "Gross_Req":       self.gross_requirements,
            "Sched_Receipt":   self.scheduled_receipts,
            "Proj_On_Hand":    self.projected_on_hand,
            "Net_Req":         self.net_requirements,
            "Planned_Receipt": self.planned_receipts,
            "Planned_Release": self.planned_releases,
        })

    def summary(self) -> str:
        hdr = f"{'Period':>8} {'GR':>8} {'SR':>8} {'OH':>8} {'NR':>8} {'PR':>8} {'PO':>8}"
        lines = [f"Item: {self.item_name}", hdr, "-" * len(hdr)]
        for i, p in enumerate(self.periods):
            lines.append(
                f"{p!s:>8} {self.gross_requirements[i]:>8.2f}"
                f" {self.scheduled_receipts[i]:>8.2f}"
                f" {self.projected_on_hand[i]:>8.2f}"
                f" {self.net_requirements[i]:>8.2f}"
                f" {self.planned_receipts[i]:>8.2f}"
                f" {self.planned_releases[i]:>8.2f}"
            )
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()


def mrp(
    gross_requirements: Sequence[float],
    *,
    initial_on_hand: float = 0.0,
    scheduled_receipts: Sequence[float] | None = None,
    lead_time: int = 1,
    lot_size: float | str = "LFL",
    safety_stock: float = 0.0,
    item_name: str = "Item",
    periods: Sequence | None = None,
) -> MRPResult:
    """Single-level Material Requirements Planning (MRP).

    Computes the standard MRP table: gross requirements → net requirements →
    planned receipts → planned order releases.

    Parameters
    ----------
    gross_requirements : sequence of float
        Demand for each period (length T).
    initial_on_hand : float
        On-hand inventory at the start of period 1 (default 0).
    scheduled_receipts : sequence of float, optional
        Already-ordered receipts arriving each period (length T, default all 0).
    lead_time : int
        Replenishment lead time in periods (default 1).
    lot_size : float or ``'LFL'``
        Order policy: ``'LFL'`` (lot-for-lot) places the exact net requirement;
        a positive float rounds up to the nearest multiple of that quantity.
    safety_stock : float
        Minimum desired ending on-hand each period (default 0).
    item_name : str
        Label for the item (default ``'Item'``).
    periods : sequence, optional
        Period labels (default 1, 2, …, T).

    Returns
    -------
    MRPResult
    """
    GR  = as_float_list(gross_requirements, "gross_requirements", kind="nonneg")
    T   = len(GR)

    SR  = [0.0] * T
    if scheduled_receipts is not None:
        SR = as_float_list(scheduled_receipts, "scheduled_receipts", kind="nonneg", min_len=0)
        if len(SR) != T:
            raise ValueError("'scheduled_receipts' debe tener la misma longitud que 'gross_requirements'.")

    if isinstance(lead_time, bool) or not isinstance(lead_time, int) or lead_time < 0:
        raise ValueError("'lead_time' debe ser un entero no negativo.")

    SS = as_nonneg(safety_stock, "safety_stock")
    initial_on_hand = as_nonneg(initial_on_hand, "initial_on_hand")
    if isinstance(lot_size, str):
        if lot_size.upper() != "LFL":
            raise ValueError("'lot_size' debe ser 'LFL' o un número positivo.")
        lot_q: float | None = None
    else:
        lot_q = as_positive(lot_size, "lot_size")

    if periods is not None and len(list(periods)) != T:
        raise ValueError("'periods' debe tener la misma longitud que 'gross_requirements'.")

    pds = list(periods) if periods is not None else list(range(1, T + 1))

    OH  = initial_on_hand
    NR_out: list  = [0.0] * T
    PR_out: list  = [0.0] * T
    OH_out: list  = [0.0] * T

    for t in range(T):
        available = OH + SR[t] - GR[t]
        nr = max(0.0, SS - available)
        if nr > 0.0:
            pr = nr if lot_q is None else math.ceil(nr / lot_q) * lot_q
        else:
            pr = 0.0
        OH = available + pr
        NR_out[t] = nr
        PR_out[t] = pr
        OH_out[t] = OH

    # Planned releases: release at period (t - lead_time) for receipt at t
    POR: list = [0.0] * T
    past_due = 0.0
    for t in range(T):
        if PR_out[t] > 0.0:
            rel = t - lead_time
            if rel < 0:
                past_due += PR_out[t]
            else:
                POR[rel] += PR_out[t]
    if past_due > 0.0:
        warnings.warn(
            f"{past_due:g} unidades planificadas debieron liberarse antes del periodo 1 "
            f"(lead_time={lead_time} no cabe en el horizonte); consulte 'past_due_releases'.",
            UserWarning, stacklevel=2,
        )

    return MRPResult(
        item_name=item_name,
        periods=pds,
        gross_requirements=GR,
        scheduled_receipts=SR,
        projected_on_hand=OH_out,
        net_requirements=NR_out,
        planned_receipts=PR_out,
        planned_releases=POR,
        past_due_releases=past_due,
    )
