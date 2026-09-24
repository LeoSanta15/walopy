# walopy

**Queuing theory, operations analysis, OEE, bottleneck analysis and KPI trees for Python.**

```bash
pip install walopy
```

## Quick start

```python
import walopy as wl

# --- Queuing ---
r = wl.mm1(lam=3.0, mu=5.0)
print(r)           # ρ=0.6, L=1.5, Lq=0.9, W=0.5, Wq=0.3
r.plot()           # Wq sensitivity curve

r = wl.kingman(lam=3.0, mu=5.0, ca2=1.2, cs2=0.8)
print(r)

L = wl.littles_law(lam=5.0, W=0.4)   # → 2.0

# --- OEE ---
r = wl.oee(availability=0.90, performance=0.80, quality=0.95)
print(r)   # OEE = 68.4%
r.plot()

# --- Bottleneck ---
r = wl.bottleneck_analysis(
    station_names=["Corte", "Soldadura", "Pintura"],
    capacities=[120, 80, 100],
    demand_rate=70,
)
print(r)   # Bottleneck: Soldadura
r.plot()

# --- KPI tree ---
tree = wl.oee_kpi_tree(0.9, 0.8, 0.95)
print(tree)
tree.to_frame()

# ROI tree
tree = wl.roi_kpi_tree(
    revenue=50_000, fixed_cost=10_000,
    variable_cost_per_unit=8, units_sold=2_000,
    investment=20_000,
)
print(tree)   # ROI = 1.2  (120%)

# --- Unit cost ---
r = wl.unit_cost(fixed_cost=10_000, variable_cost_per_unit=8, units_produced=500)
print(r)
```

## Modules

| Module | Contents |
|---|---|
| `walopy.queuing` | `mm1`, `mmc`, `md1`, `kingman`, `littles_law`, `QueueResult` |
| `walopy.operations` | `oee`, `utilization_efficiency`, `unit_cost` |
| `walopy.bottleneck` | `bottleneck_analysis`, `BottleneckResult` |
| `walopy.kpi` | `KPINode`, `oee_kpi_tree`, `throughput_kpi_tree`, `roi_kpi_tree` |
| `walopy.plotting` | All `.plot()` back-ends |

## Requirements

Python ≥ 3.9 · numpy · pandas · matplotlib

## License

MIT
