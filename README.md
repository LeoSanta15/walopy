# walopy

**Queuing theory, operations analysis, inventory models, KPI trees and more for Python.**

```bash
pip install walopy
```

---

## Quick start

```python
import walopy as wl

# --- Queuing models ---
r = wl.mm1(lam=3.0, mu=5.0)
print(r)                         # ρ=0.6  L=1.5  Lq=0.9  W=0.5  Wq=0.3
r.plot()                         # interactive Wq sensitivity chart

r = wl.mmc(lam=8.0, mu=5.0, c=2)
r = wl.md1(lam=3.0, mu=5.0)
r = wl.kingman(lam=3.0, mu=5.0, ca2=1.2, cs2=0.8)

L = wl.littles_law(lam=5.0, W=0.4)    # → 2.0

# --- Finite-capacity and priority queues ---
r = wl.mm1k(lam=5.0, mu=3.0, K=10)        # M/M/1/K
r = wl.mmck(lam=8.0, mu=3.0, c=2, K=20)  # M/M/c/K
r = wl.erlang_b(lam=5.0, mu=1.0, c=8)    # Erlang B blocking probability

# Non-preemptive HOL priority (class 0 = highest priority)
pri = wl.mm1_priority([2.0, 1.5, 0.5], mu=5.0)
print(pri)

# --- Fit parameters from real data ---
import numpy as np
rng = np.random.default_rng(42)
fit = wl.fit_from_data(
    inter_arrivals=rng.exponential(0.2, 1000),   # true λ = 5
    service_times=rng.exponential(0.1, 1000),    # true μ = 10
)
print(fit)                                        # λ ≈ 5, μ ≈ 10, ca² ≈ 1, cs² ≈ 1
r = wl.kingman(**fit.to_model_kwargs())          # plug estimates directly into model

# From raw timestamps
ts  = np.cumsum(rng.exponential(0.2, 1000))
fit = wl.fit_from_data(arrival_timestamps=ts)

# --- Jackson network of queues ---
net = wl.jackson_network(
    station_names=["Intake", "QC", "Packaging"],
    mu=[10.0, 8.0, 12.0],
    gamma=[5.0, 0.0, 0.0],
    routing=[[0.0, 1.0, 0.0],   # Intake → QC
             [0.0, 0.0, 1.0],   # QC → Packaging
             [0.0, 0.0, 0.0]],  # Packaging → exit
    servers=[1, 1, 2],
)
print(net)
print(net.to_frame())

# --- Solvers ---
r = wl.solve_lam("Wq", 0.5, mu=5.0, model="mm1")   # max λ for Wq ≤ 0.5
r = wl.solve_mu("Wq", 0.3, lam=3.0, model="mm1")   # min μ for Wq ≤ 0.3
r = wl.solve_servers("Wq", 0.1, lam=8.0, mu=5.0)   # min c for Wq ≤ 0.1
r = wl.optimize_servers(lam=6.0, mu=5.0,
                         cost_per_server=10.0,
                         cost_per_wait=5.0)

# --- Sensitivity sweep ---
import numpy as np
df = wl.sensitivity(wl.mm1, "lam", np.linspace(0.5, 4.5, 20), mu=5.0)

# --- Batch: apply model to a DataFrame of scenarios ---
import pandas as pd
scenarios = pd.DataFrame({"lam": [1.0, 2.0, 3.0, 4.0]})
df = wl.batch_model(wl.mm1, scenarios, mu=5.0)

# --- Compare multiple results ---
df = wl.compare(
    wl.mm1(3.0, 5.0),
    wl.mmc(3.0, 5.0, 2),
    wl.md1(3.0, 5.0),
    labels=["M/M/1", "M/M/2", "M/D/1"],
)

# --- Simulation ---
sim = wl.monte_carlo_gg1(lam=3.0, mu=5.0, ca2=1.0, cs2=0.5,
                          n_customers=50_000, seed=42)
print(sim.Wq_p95)   # 95th-percentile waiting time

# --- OEE ---
r = wl.oee(availability=0.90, performance=0.80, quality=0.95)
print(r)            # OEE = 68.4%
r.plot()

# --- Bottleneck analysis ---
r = wl.bottleneck_analysis(
    station_names=["Corte", "Soldadura", "Pintura"],
    capacities=[120.0, 80.0, 100.0],
    demand_rate=70.0,
)
print(r)            # Bottleneck: Soldadura
r.plot()

# --- KPI trees (interactive Plotly) ---
tree = wl.oee_kpi_tree(0.9, 0.8, 0.95)
tree.plot()                              # treemap or sunburst

tree = wl.roi_kpi_tree(
    revenue=50_000, fixed_cost=10_000,
    variable_cost_per_unit=8, units_sold=2_000,
    investment=20_000,
)
print(tree)         # ROI = 1.20  (120%)

# --- Line balance and takt time ---
takt = wl.takt_time(available_time=480, demand=60)     # 8 min/unit
lb   = wl.line_balance(["A", "B", "C"], [5.0, 9.0, 4.0], takt=10.0)
print(lb.bottleneck, lb.balance_efficiency)

# --- Break-even ---
be = wl.break_even(fixed_cost=10_000, price_per_unit=25,
                    variable_cost_per_unit=15, actual_units=1_500)
print(be.bep_units, be.margin_of_safety_pct)

# --- Inventory ---
r = wl.eoq(demand_rate=1000, ordering_cost=50, holding_cost=2)
print(r)            # EOQ ≈ 223.6 units

r = wl.reorder_point(
    demand_rate=50, lead_time=2,
    demand_std=10, lead_time_std=0.5,
    service_level=0.95,
)
print(r.reorder_point, r.safety_stock)

r = wl.newsvendor(
    demand_mean=100, demand_std=20,
    price=10, cost=6, salvage=2,
)
print(r.optimal_qty, r.critical_ratio)

# --- CLI ---
# python -m walopy mm1 --lam 3 --mu 5
# python -m walopy mmc --lam 8 --mu 5 --c 2
# python -m walopy eoq --demand 1000 --ordering 50 --holding 2
# python -m walopy --version
```

---

## Modules

| Module | Key functions |
|---|---|
| `queuing` | `mm1`, `mmc`, `md1`, `kingman`, `littles_law` |
| `advanced` | `mm1k`, `mmck`, `erlang_b`, `mm1_priority`, `monte_carlo_gg1`, `takt_time`, `line_balance`, `break_even`, `queue_length_pmf`, `sojourn_cdf` |
| `fitting` | `fit_from_data` — estimate λ, μ, ca², cs² from observed data |
| `inventory` | `eoq`, `reorder_point`, `newsvendor` |
| `network` | `jackson_network` — open Jackson networks |
| `operations` | `oee`, `utilization_efficiency`, `unit_cost` |
| `bottleneck` | `bottleneck_analysis` |
| `kpi` | `KPINode`, `oee_kpi_tree`, `throughput_kpi_tree`, `roi_kpi_tree` |
| `solver` | `solve_lam`, `solve_mu`, `solve_servers`, `optimize_servers`, `sensitivity`, `batch_model`, `compare` |
| `plotting` | All `.plot()` back-ends (Matplotlib + Plotly) |

---

## Requirements

Python ≥ 3.9 · numpy ≥ 1.22 · pandas ≥ 1.4 · matplotlib ≥ 3.5 · plotly ≥ 5.0

## License

MIT
