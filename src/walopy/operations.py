"""OEE, efficiency, utilization, throughput and unit-cost analysis."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ._utils import as_positive, as_nonneg, as_fraction


@dataclass
class OEEResult:
    """Overall Equipment Effectiveness decomposition.

    Attributes
    ----------
    availability : float
        A — fraction of planned time the asset was running.
    performance : float
        P — fraction of actual speed vs. ideal speed.
    quality : float
        Q — fraction of good units out of total units produced.
    oee : float
        OEE = A × P × Q.
    params : dict
        Raw input values retained for reference.
    """

    availability: float
    performance: float
    quality: float
    oee: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd

        return pd.DataFrame([{
            "Availability (A)": self.availability,
            "Performance (P)": self.performance,
            "Quality (Q)": self.quality,
            "OEE": self.oee,
            **self.params,
        }])

    def summary(self) -> str:
        lines = [
            f"Availability (A) : {self.availability:.2%}",
            f"Performance  (P) : {self.performance:.2%}",
            f"Quality      (Q) : {self.quality:.2%}",
            f"OEE              : {self.oee:.2%}",
        ]
        for k, v in self.params.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> "plt.Figure":
        from .plotting import plot_oee
        return plot_oee(self, **kwargs)


def oee(
    availability: float,
    performance: float,
    quality: float,
    *,
    planned_time: float | None = None,
    downtime: float | None = None,
    ideal_cycle_time: float | None = None,
    actual_cycle_time: float | None = None,
    total_units: float | None = None,
    defective_units: float | None = None,
) -> OEEResult:
    """Compute Overall Equipment Effectiveness (OEE).

    You can either supply the three factors directly (A, P, Q each in [0,1])
    or let the function derive them from raw inputs.

    Parameters
    ----------
    availability : float
        Fraction of planned production time the equipment was available [0, 1].
        Pass 0.0 if you prefer to derive from ``planned_time`` and ``downtime``.
    performance : float
        Fraction of actual vs. ideal throughput rate [0, 1].
        Pass 0.0 if you prefer to derive from cycle times.
    quality : float
        Fraction of good units [0, 1].
        Pass 0.0 if you prefer to derive from unit counts.
    planned_time : float, optional
        Total planned production time.
    downtime : float, optional
        Total unplanned downtime.
    ideal_cycle_time : float, optional
        Ideal (minimum) cycle time per unit.
    actual_cycle_time : float, optional
        Actual average cycle time per unit.
    total_units : float, optional
        Total units produced (good + defective).
    defective_units : float, optional
        Defective / rework units.

    Returns
    -------
    OEEResult
    """
    params: dict = {}

    # Derive availability
    if availability == 0.0 and planned_time is not None and downtime is not None:
        planned_time = as_positive(planned_time, "planned_time")
        downtime     = as_nonneg(downtime, "downtime")
        availability = (planned_time - downtime) / planned_time
        params["planned_time"] = planned_time
        params["downtime"]     = downtime

    # Derive performance
    if performance == 0.0 and ideal_cycle_time is not None and actual_cycle_time is not None:
        ideal_cycle_time  = as_positive(ideal_cycle_time, "ideal_cycle_time")
        actual_cycle_time = as_positive(actual_cycle_time, "actual_cycle_time")
        performance       = ideal_cycle_time / actual_cycle_time
        params["ideal_cycle_time"]  = ideal_cycle_time
        params["actual_cycle_time"] = actual_cycle_time

    # Derive quality
    if quality == 0.0 and total_units is not None and defective_units is not None:
        total_units     = as_positive(total_units, "total_units")
        defective_units = as_nonneg(defective_units, "defective_units")
        quality         = (total_units - defective_units) / total_units
        params["total_units"]     = total_units
        params["defective_units"] = defective_units

    availability = as_fraction(availability, "availability")
    performance  = as_fraction(performance, "performance")
    quality      = as_fraction(quality, "quality")
    oee_val      = availability * performance * quality
    return OEEResult(
        availability=availability,
        performance=performance,
        quality=quality,
        oee=oee_val,
        params=params,
    )


# ---------------------------------------------------------------------------
# Utilization & efficiency
# ---------------------------------------------------------------------------

@dataclass
class UtilizationResult:
    """Utilization and efficiency metrics for a resource.

    Attributes
    ----------
    utilization : float
        Fraction of capacity actually consumed (λ/μ or similar).
    efficiency : float
        Output actually produced / theoretical maximum output.
    throughput : float
        Actual units (or work) completed per unit time.
    capacity : float
        Maximum achievable throughput.
    params : dict
    """

    utilization: float
    efficiency: float
    throughput: float
    capacity: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd

        return pd.DataFrame([{
            "Utilization": self.utilization,
            "Efficiency": self.efficiency,
            "Throughput": self.throughput,
            "Capacity": self.capacity,
            **self.params,
        }])

    def summary(self) -> str:
        return (
            f"Utilization : {self.utilization:.2%}\n"
            f"Efficiency  : {self.efficiency:.2%}\n"
            f"Throughput  : {self.throughput:.6g}\n"
            f"Capacity    : {self.capacity:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()


def utilization_efficiency(
    actual_output: float,
    capacity: float,
    *,
    standard_output: float | None = None,
) -> UtilizationResult:
    """Compute utilization and efficiency.

    Parameters
    ----------
    actual_output : float
        Units (or work) actually produced per unit time.
    capacity : float
        Maximum units per unit time (installed capacity).
    standard_output : float, optional
        Expected / standard output per unit time.  If provided,
        efficiency = actual_output / standard_output;
        otherwise efficiency = actual_output / capacity.

    Returns
    -------
    UtilizationResult
    """
    actual_output = as_nonneg(actual_output, "actual_output")
    capacity      = as_positive(capacity, "capacity")
    util          = actual_output / capacity
    std           = standard_output if standard_output is not None else capacity
    std           = as_positive(std, "standard_output")
    eff           = actual_output / std
    return UtilizationResult(
        utilization=util,
        efficiency=eff,
        throughput=actual_output,
        capacity=capacity,
        params={} if standard_output is None else {"standard_output": std},
    )


# ---------------------------------------------------------------------------
# Unit cost
# ---------------------------------------------------------------------------

@dataclass
class UnitCostResult:
    """Unit cost breakdown.

    Attributes
    ----------
    unit_cost : float
        Total cost per unit produced.
    fixed_cost_per_unit : float
    variable_cost_per_unit : float
    total_cost : float
    units_produced : float
    params : dict
    """

    unit_cost: float
    fixed_cost_per_unit: float
    variable_cost_per_unit: float
    total_cost: float
    units_produced: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> "pd.DataFrame":
        import pandas as pd

        return pd.DataFrame([{
            "Units produced": self.units_produced,
            "Fixed cost / unit": self.fixed_cost_per_unit,
            "Variable cost / unit": self.variable_cost_per_unit,
            "Total unit cost": self.unit_cost,
            "Total cost": self.total_cost,
            **self.params,
        }])

    def summary(self) -> str:
        return (
            f"Units produced      : {self.units_produced:.6g}\n"
            f"Fixed cost / unit   : {self.fixed_cost_per_unit:.6g}\n"
            f"Variable cost / unit: {self.variable_cost_per_unit:.6g}\n"
            f"Total unit cost     : {self.unit_cost:.6g}\n"
            f"Total cost          : {self.total_cost:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()


def unit_cost(
    fixed_cost: float,
    variable_cost_per_unit: float,
    units_produced: float,
    *,
    overhead_rate: float = 0.0,
) -> UnitCostResult:
    """Compute unit cost with fixed, variable and optional overhead.

    Parameters
    ----------
    fixed_cost : float
        Total fixed cost for the period.
    variable_cost_per_unit : float
        Variable cost per unit produced.
    units_produced : float
        Number of units produced.
    overhead_rate : float, optional
        Overhead as a fraction of variable cost (default 0).

    Returns
    -------
    UnitCostResult
    """
    fixed_cost              = as_nonneg(fixed_cost, "fixed_cost")
    variable_cost_per_unit  = as_nonneg(variable_cost_per_unit, "variable_cost_per_unit")
    units_produced          = as_positive(units_produced, "units_produced")
    overhead_rate           = as_nonneg(overhead_rate, "overhead_rate")

    vc_with_overhead = variable_cost_per_unit * (1 + overhead_rate)
    total_cost       = fixed_cost + vc_with_overhead * units_produced
    fc_per_unit      = fixed_cost / units_produced
    uc               = fc_per_unit + vc_with_overhead
    return UnitCostResult(
        unit_cost=uc,
        fixed_cost_per_unit=fc_per_unit,
        variable_cost_per_unit=vc_with_overhead,
        total_cost=total_cost,
        units_produced=units_produced,
        params={"overhead_rate": overhead_rate} if overhead_rate else {},
    )
