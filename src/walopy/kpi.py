"""KPI tree — hierarchical decomposition and cascade of operational KPIs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Sequence

if TYPE_CHECKING:
    import plotly.graph_objects as go


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

    def plot(self, **kwargs) -> "go.Figure":
        """Render an interactive Plotly treemap (or sunburst with ``kind='sunburst'``)."""
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


def roi_kpi_tree(
    revenue: float,
    fixed_cost: float,
    variable_cost_per_unit: float,
    units_sold: float,
    investment: float,
    *,
    currency: str = "$",
) -> KPINode:
    """Build a KPI tree rooted at ROI (Return on Investment).

    ROI = Net Profit / Investment,  where
    Net Profit = Revenue − Total Cost,
    Total Cost = Fixed Cost + Variable Cost per unit × Units sold.

    Parameters
    ----------
    revenue : float
        Total revenue for the period.
    fixed_cost : float
        Total fixed cost for the period.
    variable_cost_per_unit : float
        Variable cost per unit sold.
    units_sold : float
        Units sold in the period.
    investment : float
        Total capital invested.
    currency : str
        Currency label for display (default '$').

    Returns
    -------
    KPINode
        Root node with ROI and its full decomposition.
    """
    variable_cost = variable_cost_per_unit * units_sold
    total_cost    = fixed_cost + variable_cost
    net_profit    = revenue - total_cost
    roi_val       = net_profit / investment if investment != 0 else 0.0

    return KPINode(
        name="ROI",
        value=roi_val,
        unit=f"{currency}/{currency}",
        formula="Net Profit / Investment",
        children=[
            KPINode(
                name="Net Profit",
                value=net_profit,
                unit=currency,
                formula="Revenue − Total Cost",
                children=[
                    KPINode(name="Revenue", value=revenue, unit=currency),
                    KPINode(
                        name="Total Cost",
                        value=total_cost,
                        unit=currency,
                        formula="Fixed Cost + Variable Cost",
                        children=[
                            KPINode(name="Fixed Cost",     value=fixed_cost,     unit=currency),
                            KPINode(
                                name="Variable Cost",
                                value=variable_cost,
                                unit=currency,
                                formula="Cost/unit × Units sold",
                                children=[
                                    KPINode(name="Cost / unit",  value=variable_cost_per_unit, unit=f"{currency}/unit"),
                                    KPINode(name="Units Sold",   value=units_sold,             unit="units"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            KPINode(name="Investment", value=investment, unit=currency),
        ],
    )
