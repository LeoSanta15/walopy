# walopy

**Queueing theory, operations analysis, inventory models, KPI trees and more for Python.**

🇪🇸 [Versión en español](https://github.com/LeoSanta15/walopy/blob/main/README.md)

[![PyPI version](https://img.shields.io/pypi/v/walopy.svg)](https://pypi.org/project/walopy/)
[![Python](https://img.shields.io/pypi/pyversions/walopy.svg)](https://pypi.org/project/walopy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/LeoSanta15/walopy/actions/workflows/ci.yml/badge.svg)](https://github.com/LeoSanta15/walopy/actions/workflows/ci.yml)

```bash
pip install walopy
```

> **Language.** The texts you see (error messages, `summary()` labels, `to_frame()` column names, plot titles, CLI help) are in **Spanish by
> default**. All examples in this document assume English: start your program with `walopy.set_language("en")`
> (see [section 24](#24-language-of-the-texts)). The examples print their results as comments, as they look in English.

```python
import walopy as wl

wl.set_language("en")
```

---

## Table of contents

1. [Classic queueing models](#1-classic-queueing-models)
2. [Advanced and finite-capacity models](#2-advanced-and-finite-capacity-models)
3. [Priority queues](#3-priority-queues)
4. [Monte Carlo simulation G/G/1](#4-monte-carlo-simulation-gg1)
5. [Fitting parameters from real data](#5-fitting-parameters-from-real-data)
6. [Jackson networks](#6-jackson-networks)
7. [Inventory](#7-inventory)
8. [Operations analysis](#8-operations-analysis)
9. [Bottleneck analysis](#9-bottleneck-analysis)
10. [Line balancing and takt time](#10-line-balancing-and-takt-time)
11. [Break-even analysis](#11-break-even-analysis)
12. [Exchange curves](#12-exchange-curves)
13. [Production scheduling](#13-production-scheduling)
14. [Reliability](#14-reliability--reliability)
15. [Projects: CPM and PERT](#15-projects-cpm-and-pert--project)
16. [KPI trees](#16-kpi-trees)
17. [Solvers and optimization](#17-solvers-and-optimization)
18. [Sensitivity analysis](#18-sensitivity-analysis)
19. [Batch scenarios (batch_model)](#19-batch-scenarios-batch_model)
20. [Comparing multiple results](#20-comparing-multiple-results)
21. [Plots](#21-plots)
22. [CLI](#22-cli)
23. [Module reference](#23-module-reference)
24. [Language of the texts](#24-language-of-the-texts)
25. [Requirements](#25-requirements)

---

## 1. Classic queueing models

All models return a `QueueResult` with the standard queueing-theory indicators.

### `QueueResult` — main attributes

| Attribute | Description |
|---|---|
| `model` | Model name (e.g. `"M/M/1"`) |
| `lam` | Arrival rate λ |
| `mu` | Service rate μ per server |
| `servers` | Number of servers *c* |
| `rho` | Utilization per server ρ = λ/(c·μ) |
| `L` | Average number of units in the system |
| `Lq` | Average number of units in the queue |
| `W` | Average time in the system |
| `Wq` | Average waiting time in the queue |
| `params` | Additional model-specific parameters |

Methods available on every result:
- `.summary()` / `print(r)` — table of indicators
- `.to_frame()` — exports to a one-row `pd.DataFrame`
- `.plot()` — interactive sensitivity plot

---

### `mm1(lam, mu)` — M/M/1

One server, Poisson arrivals, exponential service. The simplest queue model.

**Key formulas:**
- ρ = λ/μ (must be < 1 for stability)
- Lq = ρ² / (1 − ρ)
- L = ρ / (1 − ρ)
- Wq = Lq / λ,   W = L / λ

```python
import walopy as wl

r = wl.mm1(lam=3.0, mu=5.0)
print(r)
# Model  : M/M/1
# λ      : 3.0   (arrival rate)
# μ      : 5.0   (service rate per server)
# ρ      : 0.6   (utilization per server)
# L      : 1.5   (average units in the system)
# Lq     : 0.9   (average units in queue)
# W      : 0.5   (average time in the system)
# Wq     : 0.3   (average waiting time in queue)

df = r.to_frame()   # export to a DataFrame
r.plot()            # Wq and Lq vs ρ plot
```

---

### `mmc(lam, mu, c)` — M/M/c

Multi-server with Poisson arrivals and exponential service. It uses the Erlang-C formula to compute the probability of waiting C(c, a).

**Formulas:**
- ρ = λ/(c·μ) (utilization per server, must be < 1)
- a = λ/μ (offered load)
- C(c,a) = P(wait) — Erlang-C formula
- Lq = C(c,a) · ρ / (1 − ρ)

```python
r = wl.mmc(lam=8.0, mu=5.0, c=2)
print(r.params["C(c,a) Erlang-C"])  # probability of waiting

r_1 = wl.mmc(lam=4.0, mu=5.0, c=1)  # equivalent to mm1
r_3 = wl.mmc(lam=4.0, mu=5.0, c=3)
print(r_3.Wq < r_1.Wq)              # True: more servers → shorter wait
```

---

### `md1(lam, mu)` — M/D/1

Poisson arrivals, **deterministic** service (constant service time = 1/μ). It produces exactly half the queue of M/M/1 under the same load.

**Formulas:**
- Lq = ρ² / (2·(1 − ρ))   ← half of M/M/1
- L = ρ + Lq

```python
r_mm1 = wl.mm1(lam=3.0, mu=5.0)
r_md1 = wl.md1(lam=3.0, mu=5.0)
print(r_md1.Lq / r_mm1.Lq)   # ≈ 0.5 — M/D/1 has half the queue
```

---

### `kingman(lam, mu, ca2, cs2)` — G/G/1 (VUT approximation)

General G/G/1 model using the **Kingman approximation** (also called VUT or Pollaczek formula). It accepts any arrival and service distribution through their squared coefficients of variation.

**Formula:**
```
Wq ≈ (ρ / (1 − ρ)) · ((ca² + cs²) / 2) · (1/μ)
```

| Parameter | Description |
|---|---|
| `ca2` | CV² of the interarrival times (1.0 for Poisson) |
| `cs2` | CV² of the service times (1.0 exponential, 0.0 deterministic) |

```python
# Arrival process more regular than Poisson (ca2 < 1)
r = wl.kingman(lam=3.0, mu=5.0, ca2=0.5, cs2=1.0)

# Highly variable service (cs2 >> 1)
r = wl.kingman(lam=3.0, mu=5.0, ca2=1.0, cs2=3.0)

# Recover parameters fitted from real data and use them directly
import numpy as np
rng = np.random.default_rng(42)
fit = wl.fit_from_data(inter_arrivals=rng.exponential(0.2, 500), service_times=rng.exponential(0.1, 500))
r   = wl.kingman(**fit.to_model_kwargs())
```

> **Equivalences:**  
> `ca2=1, cs2=1` → M/M/1  
> `ca2=1, cs2=0` → M/D/1 (approximate)

---

### `mg1(lam, mu, cs2)` — M/G/1 (exact Pollaczek-Khinchine)

Poisson arrivals, service with an **arbitrary distribution** parameterized by its mean (1/μ) and its variability (cs²). The P-K formula is **exact**, not an approximation.

**P-K formula:**  
Wq = λ · E[S²] / (2 · (1 − ρ)),   where E[S²] = (1 + cs²) / μ²

```python
# Service with a triangular distribution: compute cs² first
cs2 = wl.cv2_triangular(a=2, m=5, b=10)   # a=min, m=mode, b=max
r   = wl.mg1(lam=0.15, mu=1/5, cs2=cs2)

# Equivalence with M/M/1 (cs²=1) and M/D/1 (cs²=0)
r_mm1 = wl.mg1(lam=3.0, mu=5.0, cs2=1.0)  # identical to mm1(3, 5)
r_md1 = wl.mg1(lam=3.0, mu=5.0, cs2=0.0)  # identical to md1(3, 5)
```

#### `cv2_*` helpers — CV² by distribution

The CV² (variance / mean²) is the only distribution parameter that M/G/1 needs:

| Function | Distribution | CV² |
|---|---|---|
| `cv2_normal(mean, std)` | Normal | (σ/μ)² |
| `cv2_triangular(a, m, b)` | Triangular | exact formula |
| `cv2_uniform(a, b)` | Uniform | (b−a)² / (12·μ²) |
| `cv2_erlang(k)` | Erlang-k | 1/k |
| `cv2_gamma(shape)` | Gamma | 1/shape |
| `cv2_lognormal(mean, std)` | Lognormal | (σ/μ)² |
| `cv2_weibull(shape)` | Weibull | Γ(1+2/k)/Γ(1+1/k)²−1 |

```python
# Service with a Weibull distribution of shape 2 (Rayleigh)
cs2 = wl.cv2_weibull(shape=2.0)      # ≈ 0.273
r   = wl.mg1(lam=1.0, mu=2.0, cs2=cs2)
print(r.Wq)   # mean waiting time in queue

# Erlang-3 service (less variable than exponential)
r = wl.mg1(lam=3.0, mu=5.0, cs2=wl.cv2_erlang(3))
```

---

### `littles_law(*, L, lam, W)` — Little's law

Solves L = λ · W for the missing variable. Exactly one of the three parameters must be `None`.

```python
L   = wl.littles_law(lam=5.0, W=0.4)     # L = 2.0
W   = wl.littles_law(L=2.0, lam=5.0)     # W = 0.4
lam = wl.littles_law(L=3.0, W=0.6)       # λ = 5.0
```

---

## 2. Advanced and finite-capacity models

### `mm1k(lam, mu, K)` — M/M/1/K

Queue with **finite capacity** K (server + waiting room). Customers who arrive when the system is full are lost. The system is always stable even if λ > μ.

**Additional parameters in `result.params`:**
- `PK (prob. de bloqueo)` — rejection probability (system full)
- `λ_eff (tasa efectiva)` — effective arrival rate = λ · (1 − P_K)

> **Note.** The keys of `result.params` are fixed identifiers and do **not** change with the language
> (they are the ones shown in the examples); `summary()` does show their translated label.

```python
r = wl.mm1k(lam=5.0, mu=3.0, K=10)
print(r.params["PK (prob. de bloqueo)"])  # fraction of rejected customers
print(r.params["λ_eff (tasa efectiva)"])  # actual rate of entry into the system
```

---

### `mmck(lam, mu, c, K)` — M/M/c/K

Multi-server with finite capacity. It generalizes both M/M/c (K→∞) and M/M/1/K (c=1). The state probabilities are computed in log space to avoid overflow with large K.

```python
r = wl.mmck(lam=8.0, mu=3.0, c=2, K=20)
print(r.params["PK (prob. de bloqueo)"])

# Check: with a very large K it approaches M/M/c
r_inf  = wl.mmc(lam=3.0, mu=5.0, c=2)
r_fin  = wl.mmck(lam=3.0, mu=5.0, c=2, K=500)
print(abs(r_fin.Lq - r_inf.Lq) < 0.01)  # True
```

**Restriction:** K must be ≥ c (the total capacity cannot be smaller than the number of servers).

---

### `erlang_b(lam, mu, c)` — Erlang B

Blocking probability for an **M/M/c/c loss system** (no waiting room: if all servers are busy the customer leaves). Used to dimension telephone lines and communication networks.

```python
pb = wl.erlang_b(lam=5.0, mu=1.0, c=8)
print(f"Blocking probability: {pb:.2%}")  # e.g. 1.3%

# How many servers for blocking < 2%?
for c in range(1, 20):
    if wl.erlang_b(5.0, 1.0, c) < 0.02:
        print(f"Need c = {c} servers")
        break
```

---

### `queue_length_pmf(lam, mu, n_max)` — Queue length PMF

Probability distribution of the number of customers in the system for M/M/1.
Returns a `pd.DataFrame` with columns `n`, `P(N=n)`, `P(N<=n)`.

```python
df = wl.queue_length_pmf(lam=3.0, mu=5.0, n_max=20)
print(df.head())
# n  P(N=n)  P(N<=n)
# 0  0.400   0.400
# 1  0.240   0.640
# 2  0.144   0.784
# ...

# Probability of having more than 5 customers in the system?
prob_gt5 = 1 - df.loc[df["n"] == 5, "P(N<=n)"].iloc[0]
```

---

### `sojourn_cdf(lam, mu, t_max, n_points)` — Sojourn time CDF

Cumulative distribution of the total time in the system (sojourn time) for M/M/1.
Returns a `pd.DataFrame` with columns `t`, `F(t)`, `f(t)`.

```python
df = wl.sojourn_cdf(lam=3.0, mu=5.0)
# How much time covers 95% of the customers?
t95 = df.loc[df["F(t)"] >= 0.95, "t"].iloc[0]
print(f"95% of customers leave before t = {t95:.3f}")
```

---

## 3. Priority queues

### `mm1_priority(lam_list, mu, *, class_names)` — M/M/1 non-preemptive HOL

Single-server queue with multiple priority classes. Class 0 has the highest priority. The discipline is **non-preemptive Head-Of-Line (HOL)**: a high-priority customer who arrives does not interrupt the one being served, but does move ahead of everyone who is waiting.

**Kleinrock formula:**
```
Wq_k = R / ((1 − σ_{k−1}) · (1 − σ_k))
```
where R = ρ_total / μ is the residual service time and σ_k = Σ_{i=0}^{k} ρ_i.

```python
# 3 classes: high (λ=2), medium (λ=1.5), low (λ=0.5), shared μ=5
pri = wl.mm1_priority([2.0, 1.5, 0.5], mu=5.0)
print(pri)

for cls in pri.classes:
    print(f"Class {cls['class_id']}: Wq = {cls['Wq']:.4f}")

# With custom class names
pri = wl.mm1_priority(
    [2.0, 1.0],
    mu=5.0,
    class_names=["VIP", "Standard"],
)
print(pri.classes[0]["Wq"])   # VIP waits much less
print(pri.classes[1]["Wq"])   # Standard waits longer than in a FIFO queue

df = pri.to_frame()  # DataFrame with one row per class
```

**`PriorityQueueResult` — attributes:**

| Attribute | Description |
|---|---|
| `classes` | List of dicts with `class_id`, `lam`, `rho`, `Wq`, `W`, `Lq`, `L` per class |
| `rho_total` | Total server utilization |
| `mu` | Shared service rate |

**Restriction:** the sum of all arrival rates must be < μ (stable system).

---

## 4. Monte Carlo simulation G/G/1

### `monte_carlo_gg1(lam, mu, ca2, cs2, n_customers, seed)` — Event-driven simulation

Simulates a G/G/1 queue with gamma distributions calibrated to reproduce any ca² and cs². Useful to validate analytical approximations and to get percentiles that closed-form models do not give.

```python
sim = wl.monte_carlo_gg1(
    lam=3.0, mu=5.0,
    ca2=1.0, cs2=0.5,    # ca2=1 → Poisson, cs2=0.5 → Erlang-2
    n_customers=50_000,
    seed=42,
)

print(sim.Wq_mean)   # mean
print(sim.Wq_p50)    # median
print(sim.Wq_p90)    # 90th percentile
print(sim.Wq_p95)    # 95th percentile
print(sim.Wq_p99)    # 99th percentile

sim.plot()           # histogram + empirical CDF with annotated percentiles
```

**`SimulationResult` — attributes:**

| Attribute | Description |
|---|---|
| `Wq_mean` | Simulated mean waiting time |
| `Wq_p50/p90/p95/p99` | Percentiles of the waiting-time distribution |
| `L_mean`, `Lq_mean` | Mean system and queue lengths |
| `model` | Description of the simulated model |

---

## 5. Fitting parameters from real data

### `fit_from_data(inter_arrivals, service_times, *, arrival_timestamps)` — Parameter estimation

Estimates λ, μ, ca², cs² directly from observed data. Useful to calibrate models when the parameters are not known theoretically.

**Ways to use it:**

```python
import numpy as np
import walopy as wl

rng = np.random.default_rng(42)

# 1. From interarrival times and service times
ia  = rng.exponential(scale=0.2, size=1000)   # mean = 0.2 → λ ≈ 5
svc = rng.exponential(scale=0.1, size=1000)   # mean = 0.1 → μ ≈ 10

fit = wl.fit_from_data(ia, svc)
print(fit)
# λ ≈ 5.0   ca² ≈ 1.0   (exponential → CV² = 1)
# μ ≈ 10.0  cs² ≈ 1.0

# 2. Interarrival times only (no service data)
fit_ia = wl.fit_from_data(ia)
print(fit_ia.lam, fit_ia.ca2)
print(fit_ia.mu)     # None

# 3. From raw timestamps (the intervals are not available directly)
ts  = np.cumsum(rng.exponential(0.2, 1000))   # cumulative timestamps
fit = wl.fit_from_data(arrival_timestamps=ts)

# 4. Connect directly to a model (needs λ, μ, ca² and cs²: fit with both samples)
fit_full = wl.fit_from_data(ia, svc)
r = wl.kingman(**fit_full.to_model_kwargs())  # uses lam, mu, ca2, cs2
```

**`FitResult` — attributes:**

| Attribute | Description |
|---|---|
| `lam` | Estimated arrival rate (None if there is no arrival data) |
| `mu` | Estimated service rate (None if there is no service data) |
| `ca2` | CV² of the interarrival times |
| `cs2` | CV² of the service times |
| `n_arrivals` | Number of arrival observations |
| `n_services` | Number of service observations |
| `mean_ia` | Mean of the interarrival times |
| `mean_svc` | Mean of the service times |

Methods: `.to_model_kwargs()` → dict with `lam`, `mu`, `ca2`, `cs2` ready for `kingman()`. `.to_frame()` → DataFrame.

---

## 6. Jackson networks

### `jackson_network(station_names, mu, gamma, routing, *, servers)` — Open queueing network

Analyzes an open Jackson queueing network. By **Jackson's theorem**, each station behaves as an independent M/M/c queue with an effective arrival rate that satisfies the traffic equations:

```
(I − P^T) · λ = γ
```

where γ_i is the external arrival rate to station i and P_ij is the routing probability from i to j.

```python
# 3-station serial network with a 2-server final station
net = wl.jackson_network(
    station_names=["Reception", "Quality control", "Packing"],
    mu=[10.0, 8.0, 12.0],                  # service rate per server
    gamma=[5.0, 0.0, 0.0],                 # only external customers arrive at Reception
    routing=[
        [0.0, 1.0, 0.0],   # Reception → 100% to QC
        [0.0, 0.0, 1.0],   # QC → 100% to Packing
        [0.0, 0.0, 0.0],   # Packing → leaves the system
    ],
    servers=[1, 1, 2],                     # servers per station
)

print(net)
print(net.to_frame())   # DataFrame with per-station metrics

# Access per-station metrics
for st in net.stations:
    print(f"{st.name}: λ={st.lam_total:.2f}, Wq={st.Wq:.4f}, ρ={st.rho:.2f}")

# Whole-system indicators
print(f"L_system = {net.L_system:.4f}")  # total customers in the whole network
print(f"W_system = {net.W_system:.4f}")  # total time in the network

# Network with branching
net2 = wl.jackson_network(
    station_names=["Entry", "Route A", "Route B"],
    mu=[20.0, 8.0, 10.0],
    gamma=[10.0, 0.0, 0.0],
    routing=[
        [0.0, 0.6, 0.4],  # 60% goes to Route A, 40% to Route B
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
    ],
)
```

**`JacksonResult` — attributes:**

| Attribute | Description |
|---|---|
| `stations` | List of `StationMetrics`, one per station |
| `L_system` | Average total number of customers in the whole network |
| `W_system` | Average total time in the network (Little: L = λ_ext · W) |

**`StationMetrics` — attributes:**

| Attribute | Description |
|---|---|
| `name` | Station name |
| `lam_total` | Total arrival rate (external + internal) |
| `lam_external` | External arrival rate γ_i |
| `mu` | Service rate per server |
| `servers` | Number of servers |
| `rho` | Utilization ρ = λ / (c·μ) |
| `L`, `Lq`, `W`, `Wq` | Standard queue indicators |

**Restrictions:** all stations must be stable (ρ < 1). The sum of the routing probabilities in each row must be ≤ 1.

---

## 7. Inventory

### `eoq(demand_rate, ordering_cost, holding_cost)` — Economic Order Quantity

Wilson/Harris formula: minimizes the sum of ordering cost and holding cost.

**Formula:**
```
Q* = √(2 · D · K / h)
```

At the optimum: holding cost = ordering cost (crossing property).

```python
r = wl.eoq(
    demand_rate=1000,    # D: units per period
    ordering_cost=50,    # K: fixed cost per order
    holding_cost=2,      # h: cost per unit per period
)
print(r)
# EOQ (order quantity): 223.6 units
# Order frequency     : 4.472 orders/period
# Cycle time          : 0.2236 periods
# Total cost          : 447.2
#   Holding cost      : 223.6
#   Ordering cost     : 223.6   ← equal at the optimum

r.plot()            # cost curves plot
df = r.to_frame()
```

**`EOQResult` — attributes:**

| Attribute | Description |
|---|---|
| `eoq` | Optimal quantity Q* |
| `total_cost` | Minimum total cost per period |
| `holding_cost_total` | Holding component at Q* |
| `ordering_cost_total` | Ordering component at Q* |
| `order_frequency` | Number of orders per period D/Q* |
| `cycle_time` | Time between orders 1/(D/Q*) |

---

### `reorder_point(demand_rate, lead_time, *, demand_std, lead_time_std, service_level)` — Reorder point

Computes the inventory level at which a replenishment order must be placed, including **safety stock** to cover the variability of demand and lead time.

**Formulas:**
```
σ_DLT = √(L̄ · σ_D² + D̄² · σ_L²)
ROP   = D̄ · L̄ + z · σ_DLT
```

```python
r = wl.reorder_point(
    demand_rate=50,      # mean demand per period
    lead_time=2,         # mean lead time (in the same units)
    demand_std=10,       # standard deviation of demand
    lead_time_std=0.5,   # standard deviation of the lead time
    service_level=0.95,  # desired service level
)
print(r)
# Reorder point       : 132.4 units
# Safety stock        : 32.4 units
# Service level       : 95.00%
# z                   : 1.645
# Mean demand over LT : 100.0
# Demand std over LT  : 19.72

# No variability → only the expected demand during LT
r_det = wl.reorder_point(demand_rate=50, lead_time=2,
                          demand_std=0, lead_time_std=0)
print(r_det.safety_stock)   # 0.0 — no buffer needed

# Compare service levels
r_90 = wl.reorder_point(50, 2, demand_std=10, service_level=0.90)
r_99 = wl.reorder_point(50, 2, demand_std=10, service_level=0.99)
print(r_99.safety_stock > r_90.safety_stock)  # True
```

**`ReorderResult` — attributes:**

| Attribute | Description |
|---|---|
| `reorder_point` | ROP level in units |
| `safety_stock` | Safety stock = z · σ_DLT |
| `service_level` | Cycle service level |
| `z_score` | Safety factor z |
| `mean_demand_lt` | Expected demand during the lead time |
| `std_demand_lt` | Standard deviation of demand during LT |

---

### `newsvendor(demand_mean, demand_std, price, cost, *, salvage)` — Newsvendor model

Optimizes the order quantity for a **perishable or seasonal** product under uncertain demand. It balances the cost of falling short (Cu) with the cost of having leftovers (Co).

**Formulas:**
```
Cu = price − cost             (understock cost: lost sale)
Co = cost − salvage           (overstock cost: unsold unit)
CR = Cu / (Cu + Co)           (critical ratio)
Q* = F⁻¹(CR)                  (CR quantile of the demand)
```

```python
r = wl.newsvendor(
    demand_mean=100,
    demand_std=20,
    price=10,        # selling price
    cost=6,          # purchase cost
    salvage=2,       # salvage value of unsold units
)
print(r)
# Optimal quantity       : 100.0 units
# Critical ratio         : 0.5
# Expected profit        : 320.0
# Expected sales         : 100.0
# Expected leftover      : 0.0
# Expected shortage      : 0.0
# Underage cost Cu       : 4.0
# Overage cost Co        : 4.0

# High-margin product → order above the mean
r_high = wl.newsvendor(demand_mean=100, demand_std=20,
                        price=50, cost=6, salvage=0)
print(r_high.optimal_qty > 100)   # True

# Low-margin product → order below the mean
r_low = wl.newsvendor(demand_mean=100, demand_std=20,
                       price=7, cost=6, salvage=2)
print(r_low.optimal_qty < 100)   # True
```

**`NewsvendorResult` — attributes:**

| Attribute | Description |
|---|---|
| `optimal_qty` | Optimal Q* |
| `critical_ratio` | CR = Cu/(Cu+Co) |
| `expected_profit` | Expected profit at Q* |
| `expected_sales` | Expected sales E[min(D, Q*)] |
| `expected_leftover` | Expected leftover E[max(Q*−D, 0)] |
| `expected_stockout` | Expected stockout E[max(D−Q*, 0)] |
| `underage_cost` | Cu — understock cost |
| `overage_cost` | Co — overstock cost |

---

### `ebq(demand_rate, setup_cost, holding_cost, production_rate)` — Economic Batch Quantity (EBQ/EPQ)

Extends the EOQ to the case where production and consumption occur **simultaneously** (finite production rate P > D).

**Formula:**
```
Q* = √(2 · D · S / (h · (1 − D/P)))
Maximum inventory = Q* · (1 − D/P)
Average inventory = Maximum inventory / 2
```

```python
r = wl.ebq(
    demand_rate=1000,       # D: units/period
    setup_cost=50,          # S: fixed setup cost per batch
    holding_cost=2,         # h: cost/unit/period
    production_rate=4000,   # P: production rate (must be > D)
)
print(r)
# EBQ (batch size)   : 258.2 units
# Maximum inventory  : 193.6
# Average inventory  : 96.82
# Batch frequency    : 3.873 batches/period
# Cycle time         : 0.2582 periods
# Production time    : 0.06455 periods
# Total cost         : 193.6
#   Holding cost     : 96.82
#   Setup cost       : 96.82
```

**`EBQResult` — attributes:**

| Attribute | Description |
|---|---|
| `ebq` | Optimal batch Q* |
| `max_inventory` | Maximum inventory level Q*(1−D/P) |
| `avg_inventory` | Average inventory = max/2 |
| `production_time` | Production time per cycle = Q*/P |
| `cycle_time` | Cycle length = Q*/D |
| `total_cost` | Minimum total cost |

---

### `eoq_multi(demand_rates, ordering_costs, holding_costs, *, names)` — Independent multi-item EOQ

Solves the EOQ for each item separately, with no shared constraints.

```python
r = wl.eoq_multi(
    demand_rates   = [1000, 500, 800],
    ordering_costs = [50,   30,  40 ],
    holding_costs  = [2,    1,   1.5],
    names          = ["A", "B", "C"],
)
print(r.total_cost)   # sum of the individual optimal costs
df = r.to_frame()     # DataFrame with EOQ, costs and frequencies per item
```

---

### `ebq_multi(demand_rates, setup_costs, holding_costs, production_rates, *, names)` — Independent multi-item EBQ

```python
r = wl.ebq_multi(
    demand_rates    = [1000, 500],
    setup_costs     = [50,   30 ],
    holding_costs   = [2,    1  ],
    production_rates= [4000, 2000],
)
df = r.to_frame()   # EBQ, maximum/average inventory, cost per item
```

---

### `eoq_multi_constrained(demand_rates, ordering_costs, holding_costs, ...)` — Multi-item EOQ with constraints

Minimizes the total inventory cost subject to **linear constraints** on the order quantities using **Lagrangian relaxation** (bisection on the multiplier).

**Supported constraints:**

| Parameter | Constraint |
|---|---|
| `budget`, `budget_unit_costs` | Σ(c_i · Q_i / 2) ≤ budget — average value held in inventory |
| `space`, `space_per_unit` | Σ(s_i · Q_i / 2) ≤ space — average space occupied |
| `constraints` | List of `{"name", "weights", "bound"}` — Σ(a_i · Q_i) ≤ B |

```python
# Budget constraint
r = wl.eoq_multi_constrained(
    [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
    budget=5000,
    budget_unit_costs=[10, 8, 12],   # unit purchase cost
)
print(r.binding_constraints)   # ["budget"] if the constraint is active
print(r.lagrange_multipliers)  # {"budget": λ}
df = r.to_frame()              # Q*, holding cost, ordering cost per item

# Space constraint
r2 = wl.eoq_multi_constrained(
    [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
    space=200,
    space_per_unit=[0.5, 0.3, 0.4],
)

# Generic constraint: total ordered units ≤ 400
r3 = wl.eoq_multi_constrained(
    [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
    constraints=[{"name": "total_qty", "weights": [1, 1, 1], "bound": 400}],
)
```

**`ConstrainedMultiEOQResult` — attributes:**

| Attribute | Description |
|---|---|
| `items` | List of dicts per item: name, Q*, costs |
| `total_cost` | Total cost under the constraints |
| `unconstrained_total_cost` | Cost without constraints (lower bound) |
| `lagrange_multipliers` | Dictionary {constraint_name: λ} |
| `binding_constraints` | Names of the active constraints (λ > 0) |

---

### `lot_for_lot(demands, setup_cost, holding_cost)` — Lot-for-Lot

Dynamic lot-sizing heuristic: orders **exactly the demand of each period**. It minimizes the holding cost (zero inventory carried) in exchange for one setup per period.

```python
demands = [100, 80, 0, 120, 60]   # demands per period
r = wl.lot_for_lot(demands, setup_cost=200, holding_cost=1)
print(r.total_holding_cost)   # 0.0 — no leftover inventory
print(r.n_orders)             # 4 — one order per period with demand > 0
print(r)
# Method               : Lot-for-lot
# Number of orders     : 4
# Total cost           : 800.0
```

---

### `silver_meal(demands, setup_cost, holding_cost)` — Silver-Meal

Dynamic lot-sizing heuristic that **groups periods** as long as the average cost per period decreases, reducing the number of setups.

```python
r = wl.silver_meal(demands, setup_cost=200, holding_cost=1)
print(r.total_cost <= wl.lot_for_lot(demands, 200, 1).total_cost)  # True
df = r.to_frame()   # orders: period, quantity, periods covered
```

**`LotSizingResult` — attributes (Lot-for-Lot and Silver-Meal):**

| Attribute | Description |
|---|---|
| `orders` | List of orders: period, quantity, periods covered |
| `total_cost` | Total cost (setup + holding) |
| `total_setup_cost` | Total setup cost |
| `total_holding_cost` | Total holding cost |
| `n_orders` | Number of orders placed |
| `method` | Name of the heuristic used |

---

### `eoq_quantity_discount(demand_rate, ordering_cost, holding_cost_rate, price_breaks)` — EOQ with quantity discounts

Evaluates all the price breaks (all-units) and selects the quantity that **minimizes the total annual cost** (purchase + ordering + holding), adjusting the EOQ to the valid break when it falls outside the range.

```python
r = wl.eoq_quantity_discount(
    demand_rate=1000,
    ordering_cost=50,
    holding_cost_rate=0.20,   # 20% of the unit price per year
    price_breaks=[
        (0,    10.00),   # base price
        (500,   9.50),   # ≥ 500 units → $9.50
        (1000,  9.00),   # ≥ 1000 units → $9.00
    ],
)
print(r.optimal_qty)    # selected optimal quantity
print(r.unit_price)     # price in that break
print(r.total_cost)     # minimum annual cost
df = r.to_frame()       # all the candidates evaluated
```

**`QuantityDiscountResult` — attributes:**

| Attribute | Description |
|---|---|
| `optimal_qty` | Optimal quantity adjusted to the break |
| `unit_price` | Unit price in the selected break |
| `total_cost` | Total annual cost (purchase + ordering + holding) |
| `purchase_cost` | Annual purchase cost D · price |
| `ordering_cost_total` | Annual ordering cost (D/Q) · K |
| `holding_cost_total` | Annual holding cost (Q/2) · h · price |
| `candidates` | List of all the breaks evaluated |

---

---

### ABC, XYZ and ABC-XYZ — item classification

`abc_analysis` classifies by **annual value** (Pareto): an item is A while the cumulative value *before* it is
below `a_threshold` (80 %), B while it is below `b_threshold` (95 %) and C otherwise. Items
with no demand end up in C. `xyz_analysis` classifies by **variability** (coefficient of variation): X if
CV ≤ `x_threshold` (0.5), Y up to `y_threshold` (1.0) and Z above that. `abc_xyz` combines both and returns the
3×3 matrix.

```python
items = [
    {"name": "A", "demand": 500, "unit_value": 10.0, "demand_std": 120},
    {"name": "B", "demand": 300, "unit_value": 10.0, "demand_std": 60},
    {"name": "C", "demand": 100, "unit_value": 10.0, "demand_std": 150},
    {"name": "D", "demand": 700, "unit_value": 1.0,  "demand_std": 300},
    {"name": "E", "demand": 300, "unit_value": 1.0,  "demand_std": 10},
]

abc = wl.abc_analysis(items)
print(abc)                       # summary per class: A = 2 items (80 % of the value)
print(abc.to_frame()[["item", "annual_value", "cumulative_pct", "class"]])

# XYZ: each item provides 'cv' directly or 'demand_std' + 'demand_mean' (or 'demand_rate')
xyz = wl.xyz_analysis([
    {"name": i["name"], "demand_std": i["demand_std"], "demand_mean": i["demand"]} for i in items
])
print(xyz.to_frame())            # columns: item, cv, class

# ABC-XYZ: matrix of counts (ABC rows, XYZ columns)
combo = wl.abc_xyz([{**i, "cv": i["demand_std"] / i["demand"]} for i in items])
print(combo.matrix_frame())
print(combo.items[0]["combined_class"])   # 'AX'
```

| Parameter | Description |
|---|---|
| `items` | List of dictionaries. ABC: `demand` (≥ 0) and `unit_value` (> 0). XYZ: `cv` or `demand_std` + `demand_mean`/`demand_rate` |
| `a_threshold`, `b_threshold` | Cumulative limits of classes A and B (0 < a < b < 1) |
| `x_threshold`, `y_threshold` | CV limits of classes X and Y |

Errors: an empty list, elements that are not dictionaries, missing keys and non-finite values raise `ValueError`/`TypeError`
naming the element and the key concerned; if all the demands are 0 there is nothing to classify and a `ValueError` is raised.

---

### Single-level MRP — `mrp`

Material requirements plan for one item: net requirements, planned orders (receipt and
release) and projected on-hand inventory. It supports lot-for-lot (`"LFL"`) or fixed lot size, lead time,
safety stock and scheduled receipts.

```python
r = wl.mrp(
    gross_requirements=[0, 50, 0, 30, 60, 20],
    initial_on_hand=40,
    scheduled_receipts=[0, 0, 25, 0, 0, 0],
    lead_time=1,
    lot_size=40,          # "LFL" for lot-for-lot
    safety_stock=10,
    item_name="Shaft",
)
print(r)                      # table per period: GR, SR, POH, NR, PR, PRel
print(r.to_frame())           # the same plan as a DataFrame
print(r.past_due_releases)    # 0.0
```

If the `lead_time` is greater than the period in which the order is needed, the release falls before period 1:
`mrp` issues a `UserWarning` and accumulates that quantity in `past_due_releases` (it does not appear in `planned_releases`).

---

## 8. Operations analysis

### `oee(availability, performance, quality)` — OEE

Computes the **Overall Equipment Effectiveness** (OEE = Availability × Performance × Quality).

```python
r = wl.oee(
    availability=0.90,   # available time / planned time
    performance=0.80,    # actual output / theoretical output
    quality=0.95,        # good units / total units
)
print(r)
# OEE = 68.4%
# World class: ≥ 85%

r.plot()    # horizontal plot with the world-class reference (85%)
```

### `utilization_efficiency(actual_output, capacity)` — Utilization

```python
r = wl.utilization_efficiency(actual_output=750, capacity=1000)
print(r.utilization)         # 0.75 — 75% utilization
print(1 - r.utilization)     # 0.25 — 25% idle capacity
```

### `unit_cost(fixed_cost, variable_cost_per_unit, units_produced)` — Unit cost

```python
r = wl.unit_cost(fixed_cost=10_000, variable_cost_per_unit=10, units_produced=500)
print(r.unit_cost)               # 30.0 $/unit
print(r.fixed_cost_per_unit)     # 20.0
print(r.variable_cost_per_unit)  # 10.0
```

---

## 9. Bottleneck analysis

### `bottleneck_analysis(station_names, capacities, demand_rate)` — Theory of constraints

Identifies the bottleneck of a production line by comparing the capacity of each station with the demand.

```python
r = wl.bottleneck_analysis(
    station_names=["Cutting", "Welding", "Painting"],
    capacities=[120.0, 80.0, 100.0],  # units/hour per station
    demand_rate=70.0,                  # required demand
)
print(r)
# Bottleneck station: Welding  (highest utilization)
# Utilization: Cutting=58.3%, Welding=87.5%, Painting=70.0%

r.plot()   # utilization bars with the bottleneck in red
```

---

## 10. Line balancing and takt time

### `takt_time(available_time, demand)` — Takt time

Production pace required to satisfy customer demand.

```python
takt = wl.takt_time(available_time=480, demand=60)
print(takt)   # 8.0 min/unit
```

### `line_balance(station_names, cycle_times, takt)` — Line balance

Analyzes whether each station can meet the takt time and computes the balance efficiency.

```python
lb = wl.line_balance(
    station_names=["A", "B", "C"],
    cycle_times=[5.0, 9.0, 4.0],
    takt=10.0,
)
print(lb.bottleneck)           # "B" — slowest station
print(lb.balance_efficiency)   # line balance efficiency
print(lb.theoretical_min_stations)  # theoretical minimum number of stations

lb.plot()  # cycle time vs takt bars
```

---

## 11. Break-even analysis

### `break_even(fixed_cost, price_per_unit, variable_cost_per_unit, *, actual_units)` — Break-even point

```python
be = wl.break_even(
    fixed_cost=10_000,
    price_per_unit=25,
    variable_cost_per_unit=15,
    actual_units=1_500,
)
print(be.bep_units)              # 1000.0 — break-even point in units
print(be.bep_revenue)            # 25000.0 — revenue at the break-even point
print(be.margin_of_safety_pct)   # 0.333 — margin of safety (fraction) over actual sales
print(be.margin_of_safety_units) # 500.0 — units above the break-even point

be.plot()   # revenue/cost lines with the BEP and the profit zone
```

### `break_even_multi(fixed_cost, prices, variable_costs, sales_mix)` — Multi-product

Computes the break-even point for a mix of several products using the **weighted average contribution margin (WACM)**.

**Formula:** WACM = Σ(CMᵢ × mixᵢ) / Σmixᵢ, then BEP_total = FC / WACM

```python
r = wl.break_even_multi(
    fixed_cost=120_000,
    prices=[50, 80, 120],
    variable_costs=[30, 50, 70],
    sales_mix=[3, 2, 1],          # sales proportion
)
print(r.weighted_avg_cm)          # WACM ≈ 36.67
print(r.bep_units_total)          # total units at the break-even point
print(r.bep_revenue_total)        # total revenue at the break-even point

for item in r.items:
    print(item["Product"], item["BEP units"])

r.to_frame()    # DataFrame with one row per product
```

| Attribute | Description |
|---|---|
| `weighted_avg_cm` | Weighted average contribution margin |
| `bep_units_total` | Total units at the BEP |
| `bep_revenue_total` | Total revenue at the BEP |
| `items` | List of dicts per product with `BEP units`, `BEP revenue` |

---

### `break_even_sales(fixed_cost, variable_cost_ratio, *, actual_revenue)` — Break-even point in revenue

Computes the BEP in terms of revenue when the variable costs are expressed as a percentage of sales.

**Formula:** BEP = FC / (1 − VCR)

```python
r = wl.break_even_sales(
    fixed_cost=50_000,
    variable_cost_ratio=0.60,     # 60% of revenue is variable cost
    actual_revenue=200_000,
)
print(r.bep_revenue)              # 125 000 — revenue at the BEP
print(r.contribution_margin_ratio) # 0.40 — contribution margin
print(r.margin_of_safety_units)   # 75 000 — margin of safety in revenue
print(r.margin_of_safety_pct)     # 0.375 — margin of safety percentage
```

---

## 12. Exchange curves

Tools for making aggregate policy decisions on families of items.

### Type 1 — cycle: `exchange_curve`

Traces the hyperbola between the number of orders per year (N) and the average cycle-stock investment (I):

```
N(k) = N* / k      I(k) = k · I*      →      N · I = N* · I*  (constant)
```

Given a target for N or I, it solves the optimal multiplier k and recomputes Q for each item.

```python
import walopy as wl

items = [
    {"name": "A", "demand": 1000, "ordering_cost": 50,  "holding_cost": 2,  "unit_value": 10},
    {"name": "B", "demand":  500, "ordering_cost": 30,  "holding_cost": 1,  "unit_value":  5},
    {"name": "C", "demand": 2000, "ordering_cost": 100, "holding_cost": 4,  "unit_value":  8},
]

# No target → EOQ point (k = 1)
r = wl.exchange_curve(items)
print(r)
```

```
Target                  : eoq
Multiplier k            : 1.0000
Orders/year (EOQ)       : 87.27
Orders/year (optimal)   : 87.27
Investment (EOQ)        : 5430
Investment (optimal)    : 5430
```

```python
# Reduce to 20 orders/year (k > 1 → larger Q → more investment)
r = wl.exchange_curve(items, target_orders=20)

# Limit the investment to 3 000 (k < 1 → smaller Q → more orders)
r = wl.exchange_curve(items, target_investment=3000)

# Table per item
df = r.to_frame()
# columns: item | Q_eoq | Q_optimal | n_orders | investment

# Hyperbola for plotting
curve = r.curve_to_frame()
# columns: N (orders/year) | I (investment)
```

**Parameters of each item**

| Key | Required | Description |
|-------|-----------|-------------|
| `demand` | ✓ | Annual demand Di |
| `ordering_cost` | ✓ | Ordering cost Ki |
| `holding_cost` | ✓ | Holding cost hi |
| `unit_value` | — | Unit value vi (default 1) |
| `name` | — | Label (default I1, I2, …) |

---

### Type 2 — safety: `safety_stock_curve`

Traces the curve between safety-stock investment and cycle service level using a **common z policy** for the whole family:

```
SS_i(z) = z · σᵢ_DLT · vᵢ          σᵢ_DLT = √(Lᵢ·σ²_Di + D²ᵢ·σ²_Li)
SS_total(z) = z · Σ σᵢ_DLT · vᵢ     SL(z) = Φ(z)
```

```python
items = [
    {"name": "A", "demand_rate": 100, "demand_std": 10, "lead_time": 2, "unit_value": 10},
    {"name": "B", "demand_rate":  50, "demand_std":  5, "lead_time": 1, "unit_value":  5},
    {"name": "C", "demand_rate": 200, "demand_std": 20, "lead_time": 3, "unit_value":  8},
]

# Target: 95% service level
r = wl.safety_stock_curve(items, target_service_level=0.95)
print(r)
```

```
Target            : service_level=95.0000%
z                 : 1.6449
Service level     : 95.0000%
SS investment     : 1 847
```

```python
# Target: maximum SS budget
r = wl.safety_stock_curve(items, target_ss_investment=1000)

# Table per item (includes the reorder point when demand_rate is given)
df = r.to_frame()
# columns: item | sigma_dlt | safety_stock | investment | reorder_point

# Full curve (z from −2 to 4)
curve = r.curve_to_frame()
# columns: z | service_level | ss_investment
```

**Parameters of each item**

| Key | Required | Description |
|-------|-----------|-------------|
| `demand_std` | ✓ | Standard deviation of demand |
| `lead_time` | ✓ | Mean lead time |
| `demand_rate` | — | Mean demand; enables the `reorder_point` column |
| `lead_time_std` | — | Standard deviation of the lead time (default 0) |
| `unit_value` | — | Unit value (default 1) |
| `name` | — | Label (default I1, I2, …) |

---

### Relationship between the two curves

| | Type 1 (cycle) | Type 2 (safety) |
|---|---|---|
| **Function** | `exchange_curve` | `safety_stock_curve` |
| **Decides** | Lot size Q | Reorder point r |
| **Tradeoff** | N orders/year ↔ Cycle investment | Service level ↔ SS |
| **Result** | `ExchangeCurveResult` | `SafetyStockCurveResult` |
| **Parameter** | Multiplier k | Factor z |

Used together they cover the complete `(Q, r)` policy for the whole family.

---

## 13. Production scheduling

### Single machine — `schedule_single`

Assigns *n* jobs to a single machine according to a priority rule.

```python
import walopy as wl

p = [3, 1, 4, 1, 5]          # processing times
d = [8, 3, 10, 4, 12]         # due dates
w = [2, 5, 1, 4, 1]           # importance weights

r = wl.schedule_single(p, rule="SPT", due_dates=d, weights=w,
                        names=["A","B","C","D","E"])
print(r)
```

```
Rule                     : SPT
Sequence                 : B → D → A → C → E
Makespan (Cmax)          : 14
Total completion ΣCj     : 37
Weighted completion ΣwCj : 89
Maximum lateness         : 2
Total tardiness ΣTj      : 2
Tardy jobs               : 1
```

**Available rules**

| `rule` | Criterion minimized | Required data |
|--------|---------------------|-----------------|
| `'SPT'` | ΣCj (total completion time) | — |
| `'EDD'` | Lmax (maximum lateness) | `due_dates` |
| `'WSPT'` | ΣwjCj (weighted completion) | `weights` |
| `'CR'` | Critical ratio dj/pj | `due_dates` |
| `'FIFO'` | Arrival order (baseline) | — |

**`ScheduleResult` attributes**

| Attribute | Description |
|----------|-------------|
| `rule` | Rule used |
| `sequence` | List of names in processing order |
| `jobs` | List of `JobSchedule` (one per job) |
| `makespan` | Cmax = sum of processing times |
| `total_completion_time` | ΣCj |
| `total_weighted_completion_time` | ΣwjCj |
| `max_lateness` | max(Lj) |
| `total_tardiness` | ΣTj |
| `n_tardy` | Number of tardy jobs |

```python
df = r.to_frame()  # columns: Job, p, d, w, Start, C, L, T, Tardy
```

---

### 2-machine flow shop — `johnson_flowshop`

Johnson's algorithm finds the optimal sequence that minimizes the makespan when all jobs go first through M1 and then through M2.

```python
m1 = [3, 8, 5, 7, 2]   # times on machine 1
m2 = [5, 2, 8, 4, 6]   # times on machine 2

r = wl.johnson_flowshop(m1, m2)
print(r)
```

```
Sequence  : J1 → J5 → J4 → J3 → J2
Makespan  : 34
```

```python
df = r.to_frame()
# columns: Job | M1 start | M1 end | M2 start | M2 end
```

---

### m-machine flow shop — `neh_flowshop`

**Nawaz-Enscore-Ham** heuristic for the permutation flow shop with any number of machines:
it sorts the jobs by decreasing total time and inserts each one in the best position (Taillard's
acceleration: O(n²·m)). It is a heuristic: in small cases the makespan is typically within a few percentage
points of the optimum.

```python
# rows = jobs, columns = machines
times = [[5, 9, 8], [9, 3, 10], [9, 4, 5], [4, 8, 8]]
r = wl.neh_flowshop(times, names=["P1", "P2", "P3", "P4"])
print(r)               # sequence and makespan
print(r.to_frame())    # Gantt: columns M1_start, M1_end, M2_start, ...
print(r.sequence, r.makespan)
```

---

## 14. Reliability — `reliability`

Reliability models with exponential distribution (constant failure rate).

### Single component — `mtbf_analysis`

```python
r = wl.mtbf_analysis(failure_rate=0.01, mttr=5.0, t=100)
print(r)
```

```
Topology        : component
Components      : 1
Failure rates λ : ['0.01']
MTBF            : 100
R(t=100)        : 0.367879
Availability    : 95.2381%
```

### Series system — `series_system`

The system fails if **any** component fails. λ_sys = Σλi.

```python
r = wl.series_system([0.01, 0.02, 0.03], t=10)
print(r.mtbf)      # 1/0.06 ≈ 16.67
print(r.R_t)       # e^{-0.06·10} ≈ 0.549
```

### Parallel system — `parallel_system`

The system operates if **at least one** of the components operates.  
R_sys(t) = 1 − ∏(1 − e^{−λi·t}). MTBF computed numerically.

```python
r = wl.parallel_system([0.01, 0.02], t=50)
print(r.R_t)        # greater than the series system
print(r.mtbf)       # greater than any individual component
```

### k-out-of-n system — `koon_system`

It operates if at least **k** of **n** identical components are in service.  
Exact MTBF = (1/λ) · Σ_{j=k}^{n} (1/j).

```python
# 2-out-of-3: requires at least 2 of 3 identical components
r = wl.koon_system(n=3, k=2, failure_rate=0.01, t=50)
print(r.mtbf)   # (1/0.01) * (1/2 + 1/3) ≈ 83.33
print(r.R_t)
```

**Special cases**
- `k=1` → equivalent to `parallel_system` with n identical components.
- `k=n` → equivalent to `series_system` with n identical components.

**`ReliabilityResult` attributes**

| Attribute | Description |
|----------|-------------|
| `topology` | `'component'`, `'series'`, `'parallel'`, `'k-of-n'` |
| `n_components` | Number of components |
| `failure_rates` | List of λi |
| `mtbf` | System MTBF |
| `R_t` | Reliability R(t) if `t` was provided |
| `availability` | Steady-state availability A if `mttr` was provided |
| `mttr` | Mean time to repair (if provided) |

```python
df = r.to_frame()   # columns: Topology, Components, MTBF[, R(t), Availability]
r.R(t=200)          # evaluates R(t) at any later time
```

---

### Weibull distribution — `weibull_analysis`

Fits a two-parameter Weibull (shape β, scale η) to complete failure times by **maximum
likelihood** (`method="MLE"`, bisection on the likelihood equation) or by **rank regression**
(`method="RRY"`, Benard's median ranks). β < 1 indicates infant mortality, β ≈ 1 random failures and
β > 1 wear-out.

```python
times = [12.5, 18.3, 24.1, 31.7, 38.2, 45.9, 52.4, 61.0, 70.8, 85.3]
w = wl.weibull_analysis(times)
print(w)                       # β ≈ 2.10, η ≈ 49.86, MTTF ≈ 44.16
print(w.R(30), w.F(30))        # reliability and failure probability at t = 30
print(w.h(30))                 # instantaneous failure rate
print(w.b10, w.b50, w.b_life(5))   # B10, B50 and B5 lives
print(w.to_frame())

w_rry = wl.weibull_analysis(times, method="RRY")
```

At least 2 finite, positive times are needed; if all of them are equal the shape cannot be estimated
(`ValueError`) and, if there is almost no dispersion, a warning (`UserWarning`) says that β reached the upper bound of 100.

---

## 15. Projects: CPM and PERT — `project`

Project scheduling on a network of activities. Each activity is a dictionary with `name`,
`predecessors` (list of names, may be omitted) and its duration. Names must be unique; cycles and
unknown predecessors raise `ValueError`.

### CPM — deterministic durations

Forward pass (ES, EF) and backward pass (LS, LF); total float TF = LS − ES, free float FF and critical path (TF = 0).

```python
acts = [
    {"name": "A", "duration": 3, "predecessors": []},
    {"name": "B", "duration": 4, "predecessors": ["A"]},
    {"name": "C", "duration": 2, "predecessors": ["A"]},
    {"name": "D", "duration": 1, "predecessors": ["B", "C"]},
]
r = wl.cpm(acts)
print(r)                    # duration 8, critical path A → B → D
print(r.to_frame())         # ES, EF, LS, LF, TF, FF and whether it is critical
print(r.critical_path)      # ['A', 'B', 'D']
```

### PERT — three estimates per activity

Expected duration tₑ = (a + 4m + b)/6 and variance ((b − a)/6)²; the project variance is the sum of those
along the critical path. `probability(T)` gives P(duration ≤ T) with a normal approximation.

```python
acts = [
    {"name": "A", "optimistic": 1, "most_likely": 3, "pessimistic": 5, "predecessors": []},
    {"name": "B", "optimistic": 2, "most_likely": 4, "pessimistic": 9, "predecessors": ["A"]},
]
p = wl.pert(acts)
print(p)                    # expected duration 7.5, σ ≈ 1.34
print(p.probability(9.0))   # ≈ 0.868: probability of finishing in 9 units or less
```

`probability` is only available on PERT results with nonzero variance.

---

## 16. KPI trees

KPI trees create interactive hierarchies visualized as a **treemap** or **sunburst** with Plotly.

### `oee_kpi_tree(availability, performance, quality)`

```python
tree = wl.oee_kpi_tree(0.90, 0.80, 0.95)
tree.plot()                     # treemap (default)
tree.plot(kind="sunburst")      # radial diagram
```

### `throughput_kpi_tree(actual_throughput, capacity, defect_rate)`

```python
tree = wl.throughput_kpi_tree(
    actual_throughput=750,
    capacity=1000,
    defect_rate=0.05,
)
tree.plot()
```

### `roi_kpi_tree(revenue, fixed_cost, variable_cost_per_unit, units_sold, investment)`

```python
tree = wl.roi_kpi_tree(
    revenue=50_000,
    fixed_cost=10_000,
    variable_cost_per_unit=8,
    units_sold=2_000,
    investment=20_000,
)
print(tree.value)   # ROI = 0.2 (20%)
tree.plot()
```

### `KPINode` — custom tree

The label of each rectangle is the node's actual value; its **size** is the larger of that value and the sum of its children (a KPI such as EBITDA = Revenue − Costs
is not the sum of its children, and Plotly draws a blank figure when a parent is smaller than they are).

```python
rev = wl.KPINode("Revenue", value=200_000, unit="€", children=[
    wl.KPINode("Product A", value=120_000, unit="€"),
    wl.KPINode("Product B", value=80_000, unit="€"),
])
cost = wl.KPINode("Operating costs", value=100_000, unit="€")
root = wl.KPINode("EBITDA", value=100_000, unit="€", formula="Revenue − Operating costs",
                  children=[rev, cost])

from walopy.plotting import plot_kpi_tree
fig = plot_kpi_tree(root, kind="treemap")
fig.show()
```

---

## 17. Solvers and optimization

### `solve_lam(target_metric, target_value, *, mu, model)` — Maximum arrival rate

Finds the largest λ such that a metric does not exceed the target.

```python
r = wl.solve_lam("Wq", 0.5, mu=5.0, model="mm1")
print(r.value)          # maximum λ ≈ 3.33
print(r.achieved_value) # Wq ≈ 0.5
print(r.model_result)   # complete QueueResult at the solution
```

### `solve_mu(target_metric, target_value, *, lam, model)` — Minimum service rate

```python
r = wl.solve_mu("Wq", 0.3, lam=3.0, model="mm1")
print(r.value)   # minimum μ needed ≈ 5.0
```

### `solve_servers(target_metric, target_value, *, lam, mu)` — Minimum number of servers

```python
r = wl.solve_servers("Wq", 0.1, lam=8.0, mu=5.0)
print(r.value)         # minimum c = 3
print(r.model_result)  # QueueResult for M/M/3
```

### `optimize_servers(lam, mu, cost_per_server, cost_per_wait)` — Total cost optimization

Minimizes cost_per_server × c + cost_per_wait × λ × Wq by evaluating all the feasible c.

```python
r = wl.optimize_servers(
    lam=6.0,
    mu=5.0,
    cost_per_server=10.0,   # fixed cost per server per unit of time
    cost_per_wait=5.0,      # cost per unit of waiting time of each customer
)
print(r.optimal_servers)   # optimal c
print(r.min_cost)          # minimum cost

r.plot()   # cost vs number of servers plot
```

---

## 18. Sensitivity analysis

### `sensitivity(model_fn, param, values, **fixed_kwargs)` — Parametric sweep

Evaluates a model over a range of values of a parameter.

```python
import numpy as np

df = wl.sensitivity(
    wl.mm1,
    param="lam",
    values=np.linspace(0.5, 4.5, 20),
    mu=5.0,       # fixed parameters
)
print(df.columns.tolist())  # ['lam', 'rho', 'L', 'Lq', 'W', 'Wq', ...]

# Sweep over μ
df2 = wl.sensitivity(wl.mm1, "mu", np.linspace(4.0, 10.0, 15), lam=3.0)

# Sweep over the number of servers in M/M/c
df3 = wl.sensitivity(wl.mmc, "c", range(1, 6), lam=8.0, mu=5.0)

# Visualize
from walopy.plotting import plot_sensitivity
fig = plot_sensitivity(df, "lam", metrics=["Wq", "Lq"])
fig.show()
```

---

## 19. Batch scenarios (batch_model)

### `batch_model(model_fn, df, **fixed_kwargs)` — Apply a model to a DataFrame

Applies any walopy function to each row of a scenarios DataFrame.

```python
import pandas as pd

# Several scenarios with different arrival rates
scenarios = pd.DataFrame({
    "lam": [1.0, 2.0, 3.0, 4.0]
})
result = wl.batch_model(wl.mm1, scenarios, mu=5.0)
print(result[["lam", "rho", "Wq", "L"]])

# Mixed scenarios (variable lambda and mu)
scenarios2 = pd.DataFrame({
    "lam": [2.0, 3.0, 4.0],
    "mu":  [5.0, 6.0, 7.0],
})
result2 = wl.batch_model(wl.mm1, scenarios2)

# With a variable number of servers (int column)
scenarios3 = pd.DataFrame({
    "c": [1, 2, 3, 4],
})
result3 = wl.batch_model(wl.mmc, scenarios3, lam=8.0, mu=5.0)

# Rows with an error are flagged in "_error" (the column only exists if some row fails;
# here c=1 is unstable because λ=8 > μ=5)
print(result3[result3["_error"].notna()])  # failed rows

# To make the first exception propagate instead of being collected:
# wl.batch_model(wl.mmc, scenarios3, errors="raise", lam=8.0, mu=5.0)
```

---

## 20. Comparing multiple results

### `compare(*results, labels)` — Comparison DataFrame

Builds a DataFrame with one row per result to make comparison easier.

```python
df = wl.compare(
    wl.mm1(3.0, 5.0),
    wl.mmc(3.0, 5.0, 2),
    wl.md1(3.0, 5.0),
    labels=["M/M/1", "M/M/2", "M/D/1"],
)
print(df[["label", "ρ (utilization)", "Wq (waiting time)", "L (in the system)"]])
#    label  ρ (utilization)  Wq (waiting time)  L (in the system)
# 0  M/M/1          0.6         0.3000         1.50
# 1  M/M/2          0.3         0.0302         1.02
# 2  M/D/1          0.6         0.1500         1.05

# Without labels → scenario_1, scenario_2, ...
df2 = wl.compare(wl.mm1(1, 5), wl.mm1(2, 5), wl.mm1(3, 5))
```

---

## 21. Plots

All results expose `.plot()`, which returns a Matplotlib or Plotly figure. They can also be called directly from `walopy.plotting`.

| `.plot()` function | Type | Description |
|---|---|---|
| `QueueResult.plot()` | Matplotlib | Wq and Lq curves vs ρ with the operating point |
| `OEEResult.plot()` | Matplotlib | Horizontal OEE bars with an 85% reference |
| `BottleneckResult.plot()` | Matplotlib | Utilization per station, bottleneck in red |
| `EOQResult.plot()` | Matplotlib | Holding, ordering and total cost curves |
| `LineBalanceResult.plot()` | Plotly | Cycle time vs takt per station |
| `BreakEvenResult.plot()` | Plotly | Revenue/cost lines with the BEP and the profit zone |
| `SimulationResult.plot()` | Plotly | Wq histogram + empirical CDF with percentiles |
| `OptimizeResult.plot()` | Plotly | Server cost, waiting cost and total vs c |
| `KPINode.plot(kind=)` | Plotly | Interactive treemap or sunburst |

```python
# Save as interactive HTML (Plotly)
fig = r.plot()
fig.write_html("result.html")

# Save as an image (Matplotlib)
fig = wl.oee(0.9, 0.8, 0.95).plot()
fig.savefig("oee.png", dpi=150)
```

For the sensitivity curve:
```python
from walopy.plotting import plot_sensitivity
df = wl.sensitivity(wl.mm1, "lam", np.linspace(0.5, 4.5, 20), mu=5.0)
fig = plot_sensitivity(df, "lam", metrics=["Wq", "Lq", "L"])
fig.show()
```

---

## 22. CLI

walopy includes a command-line interface for quick use without writing code.

```bash
# M/M/1
python -m walopy mm1 --lam 3 --mu 5

# M/M/c
python -m walopy mmc --lam 8 --mu 5 --c 2

# M/D/1
python -m walopy md1 --lam 3 --mu 5

# G/G/1 (Kingman)
python -m walopy gg1 --lam 3 --mu 5 --ca2 1.2 --cs2 0.8

# Little's law (solve for W)
python -m walopy littles --L 2.5 --lam 5.0

# EOQ
python -m walopy eoq --demand 1000 --ordering 50 --holding 2

# Version
python -m walopy --version
```

The CLI also follows `WALOPY_LANG` (see [section 24](#24-language-of-the-texts)); for example,
`WALOPY_LANG=en python -m walopy mm1 --lam 3 --mu 5` prints:
```
Model  : M/M/1
λ      : 3.0   (arrival rate)
μ      : 5.0   (service rate per server)
ρ      : 0.6   (utilization per server)
L      : 1.5   (average units in the system)
Lq     : 0.9   (average units in queue)
W      : 0.5   (average time in the system)
Wq     : 0.3   (average waiting time in queue)
  P0 (empty-system prob.): 0.4
```

---

## 23. Module reference

| Module | Main functions and classes |
|---|---|
| `queuing` | `mm1`, `mmc`, `md1`, `kingman`, `mg1`, `littles_law`, `QueueResult`, `cv2_normal`, `cv2_triangular`, `cv2_uniform`, `cv2_erlang`, `cv2_gamma`, `cv2_lognormal`, `cv2_weibull` |
| `advanced` | `mm1k`, `mmck`, `erlang_b`, `mm1_priority`, `monte_carlo_gg1`, `takt_time`, `line_balance`, `break_even`, `break_even_multi`, `break_even_sales`, `queue_length_pmf`, `sojourn_cdf`, `PriorityQueueResult`, `SimulationResult`, `LineBalanceResult`, `BreakEvenResult`, `BreakEvenMultiResult` |
| `fitting` | `fit_from_data`, `FitResult` |
| `inventory` | `eoq`, `ebq`, `eoq_multi`, `ebq_multi`, `eoq_multi_constrained`, `lot_for_lot`, `silver_meal`, `eoq_quantity_discount`, `wagner_whitin`, `rq_policy`, `rs_policy`, `exchange_curve`, `safety_stock_curve`, `abc_analysis`, `xyz_analysis`, `abc_xyz`, `mrp`, `reorder_point`, `newsvendor`, `EOQResult`, `EBQResult`, `MultiItemResult`, `ConstrainedMultiEOQResult`, `LotSizingResult`, `QuantityDiscountResult`, `ReorderResult`, `NewsvendorResult`, `RQPolicyResult`, `RSPolicyResult`, `ExchangeCurveResult`, `SafetyStockCurveResult`, `ABCResult`, `XYZResult`, `ABCXYZResult`, `MRPResult` |
| `scheduling` | `schedule_single`, `johnson_flowshop`, `neh_flowshop`, `ScheduleResult`, `JobSchedule`, `FlowShopResult`, `NEHResult` |
| `project` | `cpm`, `pert`, `ProjectResult`, `ActivityResult` |
| `reliability` | `mtbf_analysis`, `series_system`, `parallel_system`, `koon_system`, `weibull_analysis`, `ReliabilityResult`, `WeibullResult` |
| `network` | `jackson_network`, `JacksonResult`, `StationMetrics` |
| `operations` | `oee`, `utilization_efficiency`, `unit_cost`, `OEEResult`, `UtilizationResult`, `UnitCostResult` |
| `bottleneck` | `bottleneck_analysis`, `BottleneckResult`, `StationResult` |
| `kpi` | `KPINode`, `oee_kpi_tree`, `throughput_kpi_tree`, `roi_kpi_tree` |
| `solver` | `solve_lam`, `solve_mu`, `solve_servers`, `optimize_servers`, `sensitivity`, `batch_model`, `compare`, `SolverResult`, `OptimizeResult` |
| `plotting` | `plot_queue_sensitivity`, `plot_queue_metrics`, `plot_oee`, `plot_bottleneck`, `plot_eoq`, `plot_kpi_tree`, `plot_sensitivity`, `plot_optimize_servers`, `plot_simulation`, `plot_line_balance`, `plot_break_even`, `plot_queue_distribution` |

---

## 24. Language of the texts

The error messages, warnings, `summary()` labels, `to_frame()` headers, plot titles and the CLI help are shown in the
active language: **Spanish (`"es"`, the default) or English (`"en"`)**. If a text were not translated, it is shown in Spanish: it never fails because of that.

The language is chosen, from highest to lowest priority, with:

1. `with walopy.language("en"):` — only inside the block (safe with threads and `asyncio`).
2. `walopy.set_language("en")` — for the whole process.
3. The `WALOPY_LANG=en` environment variable (also for the CLI). An unknown value is ignored and Spanish is used.

```python
import walopy as wl

print(wl.get_language())           # 'en' (set at the top of this document; the default is 'es')
with wl.language("es"):            # change the language only inside the block
    print(wl.mm1(2, 3).summary().splitlines()[1])      # λ      : 2  (tasa de llegada)
    print(list(wl.mm1(2, 3).to_frame().columns)[:3])
wl.set_language("en")              # set the language for the whole process
try:
    wl.set_language("fr")          # an unsupported language raises ValueError
except ValueError as e:
    print(e)
```

What does **not** change with the language: function and argument names, the keys of `result.params` (for example `"P0 (prob. de sistema vacío)"`;
`summary()` does show their translated label) and the names of the data keys (`"Q*"`, `"name"`, the classes `"A"`/`"B"`/`"C"`). The numbers
do not change either. What does change, because they are created in the language that is active at that moment: the names of the **columns** of the `DataFrame`s
(`"Artículo"` → `"Item"`), the text keys of the internal tables (`result.items[0]["Producto"]`), the text of `result.model` or `result.method`
when it is a phrase (`"Lote por lote"` → `"Lot-for-lot"`) and the default names (`Artículo-1` → `Item-1`). If you change the language between creating
a result and displaying or plotting it, `walopy` still finds its columns; your own code must use the name the table has.

From the command line: `WALOPY_LANG=en python -m walopy mm1 --lam 2 --mu 3`.

---

## 25. Requirements

```
Python ≥ 3.9
numpy ≥ 1.22
pandas ≥ 1.4
matplotlib ≥ 3.5
plotly ≥ 5.0
```

`scipy` is not required. The statistical calculations use `statistics.NormalDist` from the Python standard library.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Pull requests are welcome. Make sure `pytest tests/` passes before opening a PR.
