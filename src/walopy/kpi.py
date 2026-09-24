"""KPI tree — hierarchical decomposition and cascade of operational KPIs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence


@dataclass
class KPINode:
    """A node in a KPI tree.

    Parameters
    ----------
    name : str
        KPI name.
    value : float
        Computed or provided value.
    unit : str
        Unit of measure (e.g. '%', 'units/h', '$').
    formula : str
        Human-readable formula string (for display).
    children : list[KPINode]
        Sub-KPIs that feed into this node.
    """

    name: str
    value: float
    unit: str = ""
    formula: str = ""
    children: list[KPINode] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Tree navigation
    # ------------------------------------------------------------------ #

    def find(self, name: str) -> "KPINode | None":
        """Depth-first search by name."""
        if self.name == name:
            return self
        for child in self.children:
            result = child.find(name)
            if result is not None:
                return result
        return None

    def leaves(self) -> list["KPINode"]:
        """Return all leaf nodes (nodes with no children)."""
        if not self.children:
            return [self]
        result = []
        for child in self.children:
            result.extend(child.leaves())
        return result

    # ------------------------------------------------------------------ #
    # Display
    # ------------------------------------------------------------------ #

    def to_frame(self) -> "pd.DataFrame":
        """Flatten the tree into a DataFrame (depth-first)."""
        import pandas as pd

        rows: list[dict] = []
        self._collect(rows, depth=0)
        return pd.DataFrame(rows)

    def _collect(self, rows: list[dict], depth: int) -> None:
        rows.append({
            "depth": depth,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "formula": self.formula,
        })
        for child in self.children:
            child._collect(rows, depth + 1)

    def summary(self, _indent: int = 0) -> str:
        unit_str    = f" [{self.unit}]" if self.unit else ""
        formula_str = f"  = {self.formula}" if self.formula else ""
        line = "  " * _indent + f"● {self.name}: {self.value:.6g}{unit_str}{formula_str}"
        parts = [line]
        for child in self.children:
            parts.append(child.summary(_indent + 1))
        return "\n".join(parts)

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> "plt.Figure":
        from .plotting import plot_kpi_tree
        return plot_kpi_tree(self, **kwargs)


# ---------------------------------------------------------------------------
# Pre-built KPI trees for common operations metrics
# ---------------------------------------------------------------------------

def oee_kpi_tree(
    availability: float,
    performance: float,
    quality: float,
) -> KPINode:
    """Build a KPI tree rooted at OEE.

    Parameters
    ----------
    availability : float
        A factor [0, 1].
    performance : float
        P factor [0, 1].
    quality : float
        Q factor [0, 1].

    Returns
    -------
    KPINode
        Root node with OEE and its three sub-KPIs.
    """
    oee_val = availability * performance * quality
    return KPINode(
        name="OEE",
        value=oee_val,
        unit="%",
        formula="A × P × Q",
        children=[
            KPINode(name="Availability", value=availability, unit="%", formula="(Planned − Downtime) / Planned"),
            KPINode(name="Performance",  value=performance,  unit="%", formula="Ideal CT / Actual CT"),
            KPINode(name="Quality",      value=quality,      unit="%", formula="Good units / Total units"),
        ],
    )


def throughput_kpi_tree(
    actual_throughput: float,
    capacity: float,
    defect_rate: float,
    *,
    time_unit: str = "h",
) -> KPINode:
    """Build a KPI tree rooted at effective throughput.

    Parameters
    ----------
    actual_throughput : float
        Actual good units per ``time_unit``.
    capacity : float
        Installed capacity per ``time_unit``.
    defect_rate : float
        Fraction of defective units [0, 1).
    time_unit : str
        Label for the time unit (default 'h').

    Returns
    -------
    KPINode
    """
    utilization = actual_throughput / capacity if capacity > 0 else 0.0
    good_rate   = 1.0 - defect_rate
    return KPINode(
        name="Effective Throughput",
        value=actual_throughput * good_rate,
        unit=f"units/{time_unit}",
        formula="Actual × (1 − Defect rate)",
        children=[
            KPINode(
                name="Actual Throughput",
                value=actual_throughput,
                unit=f"units/{time_unit}",
                formula="",
                children=[
                    KPINode(name="Capacity",    value=capacity,    unit=f"units/{time_unit}"),
                    KPINode(name="Utilization", value=utilization, unit="%", formula="Actual / Capacity"),
                ],
            ),
            KPINode(name="Good Rate", value=good_rate, unit="%", formula="1 − Defect rate"),
        ],
    )


def cost_kpi_tree(
    fixed_cost: float,
    variable_cost_per_unit: float,
    units_produced: float,
    *,
    currency: str = "$",
) -> KPINode:
    """Build a cost KPI tree rooted at unit cost.

    Parameters
    ----------
    fixed_cost : float
        Total fixed cost for the period.
    variable_cost_per_unit : float
        Variable cost per unit.
    units_produced : float
        Units produced in the period.
    currency : str
        Currency label for display.

    Returns
    -------
    KPINode
    """
    fc_unit  = fixed_cost / units_produced if units_produced > 0 else 0.0
    uc_total = fc_unit + variable_cost_per_unit
    return KPINode(
        name="Unit Cost",
        value=uc_total,
        unit=f"{currency}/unit",
        formula="Fixed/unit + Variable/unit",
        children=[
            KPINode(
                name="Fixed Cost / unit",
                value=fc_unit,
                unit=f"{currency}/unit",
                formula="Fixed cost / Units produced",
                children=[
                    KPINode(name="Fixed Cost",      value=fixed_cost,      unit=currency),
                    KPINode(name="Units Produced",  value=units_produced,  unit="units"),
                ],
            ),
            KPINode(name="Variable Cost / unit", value=variable_cost_per_unit, unit=f"{currency}/unit"),
        ],
    )
