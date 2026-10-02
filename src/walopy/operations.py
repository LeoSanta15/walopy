"""Análisis de OEE, eficiencia, utilización, throughput y costo unitario."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ._utils import as_fraction, as_nonneg, as_positive

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    import pandas as pd


@dataclass
class OEEResult:
    """Descomposición de la Eficiencia Global del Equipo (OEE).

    Attributes
    ----------
    availability : float
        A — fracción del tiempo planificado en que el activo estuvo funcionando.
    performance : float
        P — fracción de la velocidad real respecto de la ideal.
    quality : float
        Q — fracción de unidades buenas sobre el total producido.
    oee : float
        OEE = A × P × Q.
    params : dict
        Valores de entrada originales, conservados como referencia.
    """

    availability: float
    performance: float
    quality: float
    oee: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd

        return pd.DataFrame([{
            "Disponibilidad (A)": self.availability,
            "Rendimiento (P)": self.performance,
            "Calidad (Q)": self.quality,
            "OEE": self.oee,
            **self.params,
        }])

    def summary(self) -> str:
        lines = [
            f"Disponibilidad (A) : {self.availability:.2%}",
            f"Rendimiento    (P) : {self.performance:.2%}",
            f"Calidad        (Q) : {self.quality:.2%}",
            f"OEE                : {self.oee:.2%}",
        ]
        for k, v in self.params.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()

    def plot(self, **kwargs) -> plt.Figure:
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
    """Calcula la Eficiencia Global del Equipo (OEE).

    Se pueden indicar directamente los tres factores (A, P, Q, cada uno en [0, 1])
    o dejar que la función los derive de datos crudos.

    Parameters
    ----------
    availability : float
        Fracción del tiempo de producción planificado en que el equipo estuvo disponible [0, 1].
        Indique 0.0 si prefiere derivarla de ``planned_time`` y ``downtime``.
    performance : float
        Fracción de la tasa de producción real respecto de la ideal [0, 1].
        Indique 0.0 si prefiere derivarla de los tiempos de ciclo.
    quality : float
        Fracción de unidades buenas [0, 1].
        Indique 0.0 si prefiere derivarla de los conteos de unidades.
    planned_time : float, optional
        Tiempo de producción planificado total.
    downtime : float, optional
        Paradas no planificadas totales.
    ideal_cycle_time : float, optional
        Tiempo de ciclo ideal (mínimo) por unidad.
    actual_cycle_time : float, optional
        Tiempo de ciclo promedio real por unidad.
    total_units : float, optional
        Total de unidades producidas (buenas + defectuosas).
    defective_units : float, optional
        Unidades defectuosas o para retrabajo.

    Returns
    -------
    OEEResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
        Si algún factor no está en [0, 1].
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = oee(availability=0.9, performance=0.9, quality=0.9)
    >>> round(r.oee, 4)
    0.729
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
    """Métricas de utilización y eficiencia de un recurso.

    Attributes
    ----------
    utilization : float
        Fracción de la capacidad realmente consumida (λ/μ o similar).
    efficiency : float
        Salida realmente producida / salida máxima teórica.
    throughput : float
        Unidades (o trabajo) realmente completadas por unidad de tiempo.
    capacity : float
        Throughput máximo alcanzable.
    params : dict
    """

    utilization: float
    efficiency: float
    throughput: float
    capacity: float
    params: dict = field(default_factory=dict)

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd

        return pd.DataFrame([{
            "Utilización": self.utilization,
            "Eficiencia": self.efficiency,
            "Throughput": self.throughput,
            "Capacidad": self.capacity,
            **self.params,
        }])

    def summary(self) -> str:
        return (
            f"Utilización : {self.utilization:.2%}\n"
            f"Eficiencia  : {self.efficiency:.2%}\n"
            f"Throughput  : {self.throughput:.6g}\n"
            f"Capacidad   : {self.capacity:.6g}"
        )

    def __str__(self) -> str:
        return self.summary()


def utilization_efficiency(
    actual_output: float,
    capacity: float,
    *,
    standard_output: float | None = None,
) -> UtilizationResult:
    """Calcula la utilización y la eficiencia.

    Parameters
    ----------
    actual_output : float
        Unidades (o trabajo) realmente producidas por unidad de tiempo.
    capacity : float
        Máximo de unidades por unidad de tiempo (capacidad instalada).
    standard_output : float, optional
        Salida esperada o estándar por unidad de tiempo. Si se indica,
        eficiencia = actual_output / standard_output;
        de lo contrario eficiencia = actual_output / capacity.

    Returns
    -------
    UtilizationResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = utilization_efficiency(actual_output=75.0, capacity=100.0)
    >>> round(r.utilization, 4)
    0.75
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
    """Desglose del costo unitario.

    Attributes
    ----------
    unit_cost : float
        Costo total por unidad producida.
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

    def to_frame(self) -> pd.DataFrame:
        import pandas as pd

        return pd.DataFrame([{
            "Unidades producidas": self.units_produced,
            "Costo fijo / unidad": self.fixed_cost_per_unit,
            "Costo variable / unidad": self.variable_cost_per_unit,
            "Costo unitario total": self.unit_cost,
            "Costo total": self.total_cost,
            **self.params,
        }])

    def summary(self) -> str:
        return (
            f"Unidades producidas    : {self.units_produced:.6g}\n"
            f"Costo fijo / unidad    : {self.fixed_cost_per_unit:.6g}\n"
            f"Costo variable / unidad: {self.variable_cost_per_unit:.6g}\n"
            f"Costo unitario total   : {self.unit_cost:.6g}\n"
            f"Costo total            : {self.total_cost:.6g}"
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
    """Calcula el costo unitario con costos fijos, variables y gastos indirectos opcionales.

    Parameters
    ----------
    fixed_cost : float
        Costo fijo total del periodo.
    variable_cost_per_unit : float
        Costo variable por unidad producida.
    units_produced : float
        Número de unidades producidas.
    overhead_rate : float, optional
        Gastos indirectos como fracción del costo variable (por defecto 0).

    Returns
    -------
    UnitCostResult

    Raises
    ------
    ValueError
        Si algún argumento numérico no es finito o está fuera de su dominio (por ejemplo, no positivo).
    TypeError
        Si un argumento no es numérico o una secuencia contiene valores que no lo son.

    Examples
    --------
    >>> r = unit_cost(fixed_cost=1000.0, variable_cost_per_unit=5.0, units_produced=100.0)
    >>> round(r.unit_cost, 4)
    15.0
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
