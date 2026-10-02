"""Árbol de KPI: descomposición jerárquica y cascada de KPI operativos."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    import plotly.graph_objects as go

from ._utils import as_finite_scalar, as_fraction, as_nonneg, as_positive


@dataclass
class KPINode:
    """Un nodo de un árbol de KPI.

    Parameters
    ----------
    name : str
        Nombre del KPI.
    value : float
        Valor calculado o proporcionado.
    unit : str
        Unidad de medida (p. ej. '%', 'unidades/h', '$').
    formula : str
        Fórmula legible (para mostrar).
    children : list[KPINode]
        Sub-KPI que alimentan a este nodo.
    """

    name: str
    value: float
    unit: str = ""
    formula: str = ""
    children: list[KPINode] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Tree navigation
    # ------------------------------------------------------------------ #

    def find(self, name: str) -> KPINode | None:
        """Búsqueda en profundidad por nombre."""
        if self.name == name:
            return self
        for child in self.children:
            result = child.find(name)
            if result is not None:
                return result
        return None

    def leaves(self) -> list[KPINode]:
        """Devuelve todos los nodos hoja (nodos sin hijos)."""
        if not self.children:
            return [self]
        result = []
        for child in self.children:
            result.extend(child.leaves())
        return result

    # ------------------------------------------------------------------ #
    # Display
    # ------------------------------------------------------------------ #

    def to_frame(self) -> pd.DataFrame:
        """Aplana el árbol en un DataFrame (en profundidad)."""
        import pandas as pd

        rows: list[dict] = []
        self._collect(rows, depth=0)
        return pd.DataFrame(rows).rename(
            columns={"depth": "nivel", "name": "nombre", "value": "valor", "unit": "unidad", "formula": "fórmula"}
        )

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

    def plot(self, **kwargs) -> go.Figure:
        """Genera un treemap interactivo de Plotly (o un sunburst con ``kind='sunburst'``)."""
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
    """Construye un árbol de KPI con raíz en el OEE.

    Parameters
    ----------
    availability : float
        Factor A [0, 1].
    performance : float
        Factor P [0, 1].
    quality : float
        Factor Q [0, 1].

    Returns
    -------
    KPINode
        Nodo raíz con el OEE y sus tres sub-KPI.

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = oee_kpi_tree(availability=0.9, performance=0.9, quality=0.9)
    >>> round(r.value, 4)
    0.729
    """
    availability = as_fraction(availability, "availability")
    performance  = as_fraction(performance, "performance")
    quality      = as_fraction(quality, "quality")
    oee_val = availability * performance * quality
    return KPINode(
        name="OEE",
        value=oee_val,
        unit="%",
        formula="A × P × Q",
        children=[
            KPINode(name="Disponibilidad", value=availability, unit="%", formula="(Planificado − Paradas) / Planificado"),
            KPINode(name="Rendimiento",  value=performance,  unit="%", formula="Ciclo ideal / Ciclo real"),
            KPINode(name="Calidad",      value=quality,      unit="%", formula="Unidades buenas / Unidades totales"),
        ],
    )


def throughput_kpi_tree(
    actual_throughput: float,
    capacity: float,
    defect_rate: float,
    *,
    time_unit: str = "h",
) -> KPINode:
    """Construye un árbol de KPI con raíz en el throughput efectivo.

    Parameters
    ----------
    actual_throughput : float
        Unidades buenas reales por ``time_unit``.
    capacity : float
        Capacidad instalada por ``time_unit``.
    defect_rate : float
        Fracción de unidades defectuosas [0, 1).
    time_unit : str
        Etiqueta de la unidad de tiempo (por defecto 'h').

    Returns
    -------
    KPINode

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si ``defect_rate`` no está en [0, 1].
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = throughput_kpi_tree(actual_throughput=80.0, capacity=100.0, defect_rate=0.05)
    >>> round(r.value, 4)
    76.0
    """
    actual_throughput = as_positive(actual_throughput, "actual_throughput")
    capacity          = as_positive(capacity, "capacity")
    defect_rate       = as_fraction(defect_rate, "defect_rate")
    utilization = actual_throughput / capacity
    good_rate   = 1.0 - defect_rate
    return KPINode(
        name="Throughput efectivo",
        value=actual_throughput * good_rate,
        unit=f"unidades/{time_unit}",
        formula="Real × (1 − Tasa de defectos)",
        children=[
            KPINode(
                name="Throughput real",
                value=actual_throughput,
                unit=f"unidades/{time_unit}",
                formula="",
                children=[
                    KPINode(name="Capacidad",    value=capacity,    unit=f"unidades/{time_unit}"),
                    KPINode(name="Utilización", value=utilization, unit="%", formula="Real / Capacidad"),
                ],
            ),
            KPINode(name="Tasa de buenos", value=good_rate, unit="%", formula="1 − Tasa de defectos"),
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
    """Construye un árbol de KPI con raíz en el ROI (retorno sobre la inversión).

    ROI = Utilidad neta / Inversión,  donde
    Utilidad neta = Ingresos − Costo total,
    Costo total = Costo fijo + Costo variable por unidad × Unidades vendidas.

    Parameters
    ----------
    revenue : float
        Ingresos totales del periodo.
    fixed_cost : float
        Costo fijo total del periodo.
    variable_cost_per_unit : float
        Costo variable por unidad vendida.
    units_sold : float
        Unidades vendidas en el periodo.
    investment : float
        Capital total invertido.
    currency : str
        Etiqueta de la moneda para mostrar (por defecto '$').

    Returns
    -------
    KPINode
        Nodo raíz con el ROI y toda su descomposición.

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = roi_kpi_tree(
    ...     revenue=1000.0,
    ...     fixed_cost=200.0,
    ...     variable_cost_per_unit=3.0,
    ...     units_sold=100.0,
    ...     investment=500.0,
    ... )
    >>> round(r.value, 4)
    1.0
    """
    revenue                = as_finite_scalar(revenue, "revenue")
    fixed_cost             = as_nonneg(fixed_cost, "fixed_cost")
    variable_cost_per_unit = as_nonneg(variable_cost_per_unit, "variable_cost_per_unit")
    units_sold             = as_nonneg(units_sold, "units_sold")
    investment             = as_finite_scalar(investment, "investment")
    variable_cost = variable_cost_per_unit * units_sold
    total_cost    = fixed_cost + variable_cost
    net_profit    = revenue - total_cost
    roi_val       = net_profit / investment if investment != 0 else 0.0

    return KPINode(
        name="ROI",
        value=roi_val,
        unit=f"{currency}/{currency}",
        formula="Utilidad neta / Inversión",
        children=[
            KPINode(
                name="Utilidad neta",
                value=net_profit,
                unit=currency,
                formula="Ingresos − Costo total",
                children=[
                    KPINode(name="Ingresos", value=revenue, unit=currency),
                    KPINode(
                        name="Costo total",
                        value=total_cost,
                        unit=currency,
                        formula="Costo fijo + Costo variable",
                        children=[
                            KPINode(name="Costo fijo",     value=fixed_cost,     unit=currency),
                            KPINode(
                                name="Costo variable",
                                value=variable_cost,
                                unit=currency,
                                formula="Costo/unidad × Unidades vendidas",
                                children=[
                                    KPINode(name="Costo / unidad",  value=variable_cost_per_unit, unit=f"{currency}/unidad"),
                                    KPINode(name="Unidades vendidas",   value=units_sold,             unit="unidades"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            KPINode(name="Inversión", value=investment, unit=currency),
        ],
    )
