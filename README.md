# walopy

**Teoría de colas, análisis de operaciones, modelos de inventario, árboles de KPI y más para Python.**

[![PyPI version](https://img.shields.io/pypi/v/walopy.svg)](https://pypi.org/project/walopy/)
[![Python](https://img.shields.io/pypi/pyversions/walopy.svg)](https://pypi.org/project/walopy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/LeoSanta15/walopy/actions/workflows/ci.yml/badge.svg)](https://github.com/LeoSanta15/walopy/actions/workflows/ci.yml)

```bash
pip install walopy
```

---

## Tabla de contenidos

1. [Modelos de colas clásicos](#1-modelos-de-colas-clásicos)
2. [Modelos avanzados y de capacidad finita](#2-modelos-avanzados-y-de-capacidad-finita)
3. [Colas con prioridad](#3-colas-con-prioridad)
4. [Simulación Monte Carlo G/G/1](#4-simulación-monte-carlo-gg1)
5. [Ajuste de parámetros desde datos reales](#5-ajuste-de-parámetros-desde-datos-reales)
6. [Redes de Jackson](#6-redes-de-jackson)
7. [Inventarios](#7-inventarios)
8. [Análisis de operaciones](#8-análisis-de-operaciones)
9. [Análisis de cuellos de botella](#9-análisis-de-cuellos-de-botella)
10. [Balance de línea y tiempo takt](#10-balance-de-línea-y-tiempo-takt)
11. [Análisis de punto de equilibrio](#11-análisis-de-punto-de-equilibrio)
12. [Árboles de KPI](#12-árboles-de-kpi)
13. [Solvers y optimización](#13-solvers-y-optimización)
14. [Análisis de sensibilidad](#14-análisis-de-sensibilidad)
15. [Escenarios en lote (batch_model)](#15-escenarios-en-lote-batch_model)
16. [Comparar múltiples resultados](#16-comparar-múltiples-resultados)
17. [Gráficas](#17-gráficas)
18. [CLI](#18-cli)
19. [Referencia de módulos](#19-referencia-de-módulos)
20. [Requisitos](#20-requisitos)

---

## 1. Modelos de colas clásicos

Todos los modelos devuelven un `QueueResult` con los indicadores estándar de teoría de colas.

### `QueueResult` — atributos principales

| Atributo | Descripción |
|---|---|
| `model` | Nombre del modelo (ej. `"M/M/1"`) |
| `lam` | Tasa de llegada λ |
| `mu` | Tasa de servicio μ por servidor |
| `servers` | Número de servidores *c* |
| `rho` | Utilización por servidor ρ = λ/(c·μ) |
| `L` | Número promedio de unidades en el sistema |
| `Lq` | Número promedio de unidades en la cola |
| `W` | Tiempo promedio en el sistema |
| `Wq` | Tiempo promedio de espera en cola |
| `params` | Parámetros adicionales específicos del modelo |

Métodos disponibles en todos los resultados:
- `.summary()` / `print(r)` — tabla de indicadores
- `.to_frame()` — exporta a `pd.DataFrame` de una fila
- `.plot()` — gráfica interactiva de sensibilidad

---

### `mm1(lam, mu)` — M/M/1

Un servidor, llegadas Poisson, servicio exponencial. El modelo más simple de cola.

**Fórmulas clave:**
- ρ = λ/μ (debe ser < 1 para estabilidad)
- Lq = ρ² / (1 − ρ)
- L = ρ / (1 − ρ)
- Wq = Lq / λ,   W = L / λ

```python
import walopy as wl

r = wl.mm1(lam=3.0, mu=5.0)
print(r)
# Model : M/M/1
# λ     : 3.0   (arrival rate)
# μ     : 5.0   (service rate per server)
# ρ     : 0.6   (utilization)
# L     : 1.5   (avg units in system)
# Lq    : 0.9   (avg units in queue)
# W     : 0.5   (avg time in system)
# Wq    : 0.3   (avg wait time in queue)

df = r.to_frame()   # exportar a DataFrame
r.plot()            # gráfica Wq y Lq vs ρ
```

---

### `mmc(lam, mu, c)` — M/M/c

Multi-servidor con llegadas Poisson y servicio exponencial. Usa la fórmula de Erlang-C para calcular la probabilidad de espera C(c, a).

**Fórmulas:**
- ρ = λ/(c·μ) (utilización por servidor, debe ser < 1)
- a = λ/μ (carga ofrecida)
- C(c,a) = P(esperar) — fórmula de Erlang-C
- Lq = C(c,a) · ρ / (1 − ρ)

```python
r = wl.mmc(lam=8.0, mu=5.0, c=2)
print(r.params["C(c,a) Erlang-C"])  # probabilidad de espera

r_1 = wl.mmc(lam=4.0, mu=5.0, c=1)  # equivalente a mm1
r_3 = wl.mmc(lam=4.0, mu=5.0, c=3)
print(r_3.Wq < r_1.Wq)              # True: más servidores → menor espera
```

---

### `md1(lam, mu)` — M/D/1

Llegadas Poisson, servicio **determinístico** (tiempo de servicio constante = 1/μ). Produce exactamente la mitad de cola que M/M/1 bajo la misma carga.

**Fórmulas:**
- Lq = ρ² / (2·(1 − ρ))   ← mitad que M/M/1
- L = ρ + Lq

```python
r_mm1 = wl.mm1(lam=3.0, mu=5.0)
r_md1 = wl.md1(lam=3.0, mu=5.0)
print(r_md1.Lq / r_mm1.Lq)   # ≈ 0.5 — M/D/1 tiene la mitad de cola
```

---

### `kingman(lam, mu, ca2, cs2)` — G/G/1 (aproximación VUT)

Modelo general G/G/1 mediante la **aproximación de Kingman** (también llamada VUT o fórmula de Pollaczek). Acepta cualquier distribución de llegadas y servicio a través de sus coeficientes de variación al cuadrado.

**Fórmula:**
```
Wq ≈ (ρ / (1 − ρ)) · ((ca² + cs²) / 2) · (1/μ)
```

| Parámetro | Descripción |
|---|---|
| `ca2` | CV² de los tiempos entre llegadas (1.0 para Poisson) |
| `cs2` | CV² de los tiempos de servicio (1.0 exponencial, 0.0 determinístico) |

```python
# Proceso de llegada más regular que Poisson (ca2 < 1)
r = wl.kingman(lam=3.0, mu=5.0, ca2=0.5, cs2=1.0)

# Servicio muy variable (ca2 >> 1)
r = wl.kingman(lam=3.0, mu=5.0, ca2=1.0, cs2=3.0)

# Recuperar parámetros ajustados desde datos reales y usarlos directamente
fit = wl.fit_from_data(inter_arrivals=..., service_times=...)
r   = wl.kingman(**fit.to_model_kwargs())
```

> **Equivalencias:**  
> `ca2=1, cs2=1` → M/M/1  
> `ca2=1, cs2=0` → M/D/1 (aproximado)

---

### `littles_law(*, L, lam, W)` — Ley de Little

Resuelve L = λ · W para la variable que falte. Exactamente uno de los tres parámetros debe ser `None`.

```python
L   = wl.littles_law(lam=5.0, W=0.4)     # L = 2.0
W   = wl.littles_law(L=2.0, lam=5.0)     # W = 0.4
lam = wl.littles_law(L=3.0, W=0.6)       # λ = 5.0
```

---

## 2. Modelos avanzados y de capacidad finita

### `mm1k(lam, mu, K)` — M/M/1/K

Cola con **capacidad finita** K (servidor + sala de espera). Los clientes que llegan cuando el sistema está lleno se pierden. El sistema es siempre estable incluso si λ > μ.

**Parámetros adicionales en `result.params`:**
- `PK (blocking prob)` — probabilidad de rechazo (sistema lleno)
- `lam_eff` — tasa de llegada efectiva = λ · (1 − P_K)

```python
r = wl.mm1k(lam=5.0, mu=3.0, K=10)
print(r.params["PK (blocking prob)"])  # fracción de clientes rechazados
print(r.params["lam_eff"])             # tasa real de entrada al sistema
```

---

### `mmck(lam, mu, c, K)` — M/M/c/K

Multi-servidor con capacidad finita. Generaliza tanto M/M/c (K→∞) como M/M/1/K (c=1). Las probabilidades de estado se calculan en espacio logarítmico para evitar desbordamientos con K grande.

```python
r = wl.mmck(lam=8.0, mu=3.0, c=2, K=20)
print(r.params["PK (blocking prob)"])

# Verificación: con K muy grande se acerca a M/M/c
r_inf  = wl.mmc(lam=3.0, mu=5.0, c=2)
r_fin  = wl.mmck(lam=3.0, mu=5.0, c=2, K=500)
print(abs(r_fin.Lq - r_inf.Lq) < 0.01)  # True
```

**Restricción:** K debe ser ≥ c (la capacidad total no puede ser menor que el número de servidores).

---

### `erlang_b(lam, mu, c)` — Erlang B

Probabilidad de bloqueo para un **sistema de pérdidas M/M/c/c** (sin sala de espera: si todos los servidores están ocupados el cliente se va). Usado en dimensionamiento de líneas telefónicas y redes de comunicación.

```python
pb = wl.erlang_b(lam=5.0, mu=1.0, c=8)
print(f"Blocking probability: {pb:.2%}")  # ej. 1.3%

# Cuántos servidores para bloqueo < 2%?
for c in range(1, 20):
    if wl.erlang_b(5.0, 1.0, c) < 0.02:
        print(f"Need c = {c} servers")
        break
```

---

### `queue_length_pmf(lam, mu, n_max)` — PMF de longitud de cola

Distribución de probabilidad del número de clientes en el sistema para M/M/1.
Devuelve un `pd.DataFrame` con columnas `n`, `P(N=n)`, `P(N<=n)`.

```python
df = wl.queue_length_pmf(lam=3.0, mu=5.0, n_max=20)
print(df.head())
# n  P(N=n)  P(N<=n)
# 0  0.400   0.400
# 1  0.240   0.640
# 2  0.144   0.784
# ...

# ¿Probabilidad de tener más de 5 clientes en sistema?
prob_gt5 = 1 - df.loc[df["n"] == 5, "P(N<=n)"].iloc[0]
```

---

### `sojourn_cdf(lam, mu, t_max, n_points)` — CDF del tiempo de permanencia

Distribución acumulada del tiempo total en el sistema (sojourn time) para M/M/1.
Devuelve un `pd.DataFrame` con columnas `t`, `F(t)`, `f(t)`.

```python
df = wl.sojourn_cdf(lam=3.0, mu=5.0)
# ¿Cuánto tiempo cubre el 95% de los clientes?
t95 = df.loc[df["F(t)"] >= 0.95, "t"].iloc[0]
print(f"95% of customers leave before t = {t95:.3f}")
```

---

## 3. Colas con prioridad

### `mm1_priority(lam_list, mu, *, class_names)` — M/M/1 HOL no-preemptiva

Cola de un servidor con múltiples clases de prioridad. La clase 0 tiene la prioridad más alta. La disciplina es **Head-Of-Line (HOL) no-preemptiva**: un cliente de alta prioridad que llega no interrumpe al que está siendo atendido, pero sí pasa delante de todos los que esperan.

**Fórmula de Kleinrock:**
```
Wq_k = R / ((1 − σ_{k−1}) · (1 − σ_k))
```
donde R = ρ_total / μ es el tiempo residual de servicio y σ_k = Σ_{i=0}^{k} ρ_i.

```python
# 3 clases: alta (λ=2), media (λ=1.5), baja (λ=0.5), μ=5 compartido
pri = wl.mm1_priority([2.0, 1.5, 0.5], mu=5.0)
print(pri)

for cls in pri.classes:
    print(f"Clase {cls['class_id']}: Wq = {cls['Wq']:.4f}")

# Con nombres de clase personalizados
pri = wl.mm1_priority(
    [2.0, 1.0],
    mu=5.0,
    class_names=["VIP", "Estándar"],
)
print(pri.classes[0]["Wq"])   # VIP espera mucho menos
print(pri.classes[1]["Wq"])   # Estándar espera más que en cola FIFO

df = pri.to_frame()  # DataFrame con una fila por clase
```

**`PriorityQueueResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `classes` | Lista de dicts con `class_id`, `lam`, `rho`, `Wq`, `W`, `Lq`, `L` por clase |
| `rho_total` | Utilización total del servidor |
| `mu` | Tasa de servicio compartida |

**Restricción:** la suma de todas las tasas de llegada debe ser < μ (sistema estable).

---

## 4. Simulación Monte Carlo G/G/1

### `monte_carlo_gg1(lam, mu, ca2, cs2, n_customers, seed)` — Simulación event-driven

Simula una cola G/G/1 con distribuciones gamma calibradas para reproducir cualquier ca² y cs². Útil para validar aproximaciones analíticas y obtener percentiles que los modelos cerrados no dan.

```python
sim = wl.monte_carlo_gg1(
    lam=3.0, mu=5.0,
    ca2=1.0, cs2=0.5,    # ca2=1 → Poisson, cs2=0.5 → Erlang-2
    n_customers=50_000,
    seed=42,
)

print(sim.Wq_mean)   # promedio
print(sim.Wq_p50)    # mediana
print(sim.Wq_p90)    # percentil 90
print(sim.Wq_p95)    # percentil 95
print(sim.Wq_p99)    # percentil 99

sim.plot()           # histograma + CDF empírica con percentiles anotados
```

**`SimulationResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `Wq_mean` | Tiempo promedio de espera simulado |
| `Wq_p50/p90/p95/p99` | Percentiles de la distribución de espera |
| `L_mean`, `Lq_mean` | Longitudes de sistema y cola promedio |
| `model` | Descripción del modelo simulado |

---

## 5. Ajuste de parámetros desde datos reales

### `fit_from_data(inter_arrivals, service_times, *, arrival_timestamps)` — Estimación de parámetros

Estima λ, μ, ca², cs² directamente desde datos observados. Útil para calibrar modelos cuando los parámetros no se conocen teóricamente.

**Formas de uso:**

```python
import numpy as np
import walopy as wl

rng = np.random.default_rng(42)

# 1. Desde tiempos entre llegadas y tiempos de servicio
ia  = rng.exponential(scale=0.2, size=1000)   # media = 0.2 → λ ≈ 5
svc = rng.exponential(scale=0.1, size=1000)   # media = 0.1 → μ ≈ 10

fit = wl.fit_from_data(ia, svc)
print(fit)
# λ ≈ 5.0   ca² ≈ 1.0   (exponencial → CV² = 1)
# μ ≈ 10.0  cs² ≈ 1.0

# 2. Solo tiempos entre llegadas (sin datos de servicio)
fit_ia = wl.fit_from_data(ia)
print(fit_ia.lam, fit_ia.ca2)
print(fit_ia.mu)     # None

# 3. Desde timestamps crudos (no se tienen los intervalos directamente)
ts  = np.cumsum(rng.exponential(0.2, 1000))   # timestamps acumulados
fit = wl.fit_from_data(arrival_timestamps=ts)

# 4. Conectar directamente con un modelo
r = wl.kingman(**fit.to_model_kwargs())  # usa lam, mu, ca2, cs2
```

**`FitResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `lam` | Tasa de llegada estimada (None si no hay datos de llegada) |
| `mu` | Tasa de servicio estimada (None si no hay datos de servicio) |
| `ca2` | CV² de tiempos entre llegadas |
| `cs2` | CV² de tiempos de servicio |
| `n_arrivals` | Número de observaciones de llegada |
| `n_services` | Número de observaciones de servicio |
| `mean_ia` | Media de tiempos entre llegadas |
| `mean_svc` | Media de tiempos de servicio |

Métodos: `.to_model_kwargs()` → dict con `lam`, `mu`, `ca2`, `cs2` listos para `kingman()`. `.to_frame()` → DataFrame.

---

## 6. Redes de Jackson

### `jackson_network(station_names, mu, gamma, routing, *, servers)` — Red abierta de colas

Analiza una red de colas de Jackson abierta. Por el **Teorema de Jackson**, cada estación se comporta como una cola M/M/c independiente con una tasa de llegada efectiva que satisface las ecuaciones de tráfico:

```
(I − P^T) · λ = γ
```

donde γ_i es la tasa de llegada externa a la estación i y P_ij es la probabilidad de routing de i a j.

```python
# Red de 3 estaciones en serie con estación final de 2 servidores
net = wl.jackson_network(
    station_names=["Recepción", "Control de calidad", "Empaque"],
    mu=[10.0, 8.0, 12.0],                  # tasa de servicio por servidor
    gamma=[5.0, 0.0, 0.0],                 # solo llegan clientes externos a Recepción
    routing=[
        [0.0, 1.0, 0.0],   # Recepción → 100% a QC
        [0.0, 0.0, 1.0],   # QC → 100% a Empaque
        [0.0, 0.0, 0.0],   # Empaque → sale del sistema
    ],
    servers=[1, 1, 2],                     # servidores por estación
)

print(net)
print(net.to_frame())   # DataFrame con métricas por estación

# Acceder a métricas por estación
for st in net.stations:
    print(f"{st.name}: λ={st.lam_total:.2f}, Wq={st.Wq:.4f}, ρ={st.rho:.2f}")

# Indicadores del sistema completo
print(f"L_sistema = {net.L_system:.4f}")  # clientes totales en toda la red
print(f"W_sistema = {net.W_system:.4f}")  # tiempo total en la red

# Red con bifurcación
net2 = wl.jackson_network(
    station_names=["Entrada", "Ruta A", "Ruta B"],
    mu=[20.0, 8.0, 10.0],
    gamma=[10.0, 0.0, 0.0],
    routing=[
        [0.0, 0.6, 0.4],  # 60% va a Ruta A, 40% a Ruta B
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
    ],
)
```

**`JacksonResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `stations` | Lista de `StationMetrics` por estación |
| `L_system` | Número total promedio de clientes en toda la red |
| `W_system` | Tiempo total promedio en la red (Little: L = λ_ext · W) |

**`StationMetrics` — atributos:**

| Atributo | Descripción |
|---|---|
| `name` | Nombre de la estación |
| `lam_total` | Tasa de llegada total (externa + interna) |
| `lam_external` | Tasa de llegada externa γ_i |
| `mu` | Tasa de servicio por servidor |
| `servers` | Número de servidores |
| `rho` | Utilización ρ = λ / (c·μ) |
| `L`, `Lq`, `W`, `Wq` | Indicadores estándar de cola |

**Restricciones:** todas las estaciones deben ser estables (ρ < 1). La suma de probabilidades de routing por fila debe ser ≤ 1.

---

## 7. Inventarios

### `eoq(demand_rate, ordering_cost, holding_cost)` — Cantidad Económica de Pedido

Fórmula de Wilson/Harris: minimiza la suma de costo de ordenar y costo de almacenar.

**Fórmula:**
```
Q* = √(2 · D · K / h)
```

En el óptimo: costo de mantener = costo de ordenar (propiedad de cruce).

```python
r = wl.eoq(
    demand_rate=1000,    # D: unidades por período
    ordering_cost=50,    # K: costo fijo por orden
    holding_cost=2,      # h: costo por unidad por período
)
print(r)
# EOQ (order quantity): 223.6 units
# Order frequency     : 4.472 orders/period
# Cycle time          : 0.2236 periods
# Total cost          : 447.2
#   Holding cost      : 223.6
#   Ordering cost     : 223.6   ← iguales en el óptimo

r.plot()            # gráfica de curvas de costo
df = r.to_frame()
```

**`EOQResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `eoq` | Cantidad óptima Q* |
| `total_cost` | Costo total mínimo por período |
| `holding_cost_total` | Componente de almacenamiento en Q* |
| `ordering_cost_total` | Componente de pedido en Q* |
| `order_frequency` | Número de pedidos por período D/Q* |
| `cycle_time` | Tiempo entre pedidos 1/(D/Q*) |

---

### `reorder_point(demand_rate, lead_time, *, demand_std, lead_time_std, service_level)` — Punto de reorden

Calcula el nivel de inventario al que se debe lanzar una orden de reposición, incluyendo **stock de seguridad** para cubrir la variabilidad de la demanda y del tiempo de entrega.

**Fórmulas:**
```
σ_DLT = √(L̄ · σ_D² + D̄² · σ_L²)
ROP   = D̄ · L̄ + z · σ_DLT
```

```python
r = wl.reorder_point(
    demand_rate=50,      # demanda media por período
    lead_time=2,         # tiempo de entrega medio (en mismas unidades)
    demand_std=10,       # desviación estándar de la demanda
    lead_time_std=0.5,   # desviación estándar del lead time
    service_level=0.95,  # nivel de servicio deseado
)
print(r)
# Reorder point   : 132.4 units
# Safety stock    : 32.4 units
# Service level   : 95.00%
# z-score         : 1.645
# Mean demand LT  : 100.0
# Std demand LT   : 19.72

# Sin variabilidad → solo demanda esperada durante LT
r_det = wl.reorder_point(demand_rate=50, lead_time=2,
                          demand_std=0, lead_time_std=0)
print(r_det.safety_stock)   # 0.0 — no se necesita buffer

# Comparar niveles de servicio
r_90 = wl.reorder_point(50, 2, demand_std=10, service_level=0.90)
r_99 = wl.reorder_point(50, 2, demand_std=10, service_level=0.99)
print(r_99.safety_stock > r_90.safety_stock)  # True
```

**`ReorderResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `reorder_point` | Nivel ROP en unidades |
| `safety_stock` | Stock de seguridad = z · σ_DLT |
| `service_level` | Nivel de servicio de ciclo |
| `z_score` | Factor de seguridad z |
| `mean_demand_lt` | Demanda esperada durante el lead time |
| `std_demand_lt` | Desviación estándar de la demanda durante LT |

---

### `newsvendor(demand_mean, demand_std, price, cost, *, salvage)` — Modelo del vendedor de periódicos

Optimiza la cantidad a ordenar para un producto **perecedero o de temporada** bajo demanda incierta. Equilibra el costo de quedarse corto (Cu) con el costo de sobrar (Co).

**Fórmulas:**
```
Cu = precio − costo           (costo de substock: venta perdida)
Co = costo − salvage          (costo de sobrestock: unidad no vendida)
CR = Cu / (Cu + Co)           (ratio crítico)
Q* = F⁻¹(CR)                  (cuantil CR de la demanda)
```

```python
r = wl.newsvendor(
    demand_mean=100,
    demand_std=20,
    price=10,        # precio de venta
    cost=6,          # costo de compra
    salvage=2,       # valor residual de unidades no vendidas
)
print(r)
# Optimal quantity   : 100.0 units
# Critical ratio     : 0.5
# Expected profit    : 320.0
# Expected sales     : 100.0
# Expected leftover  : 0.0
# Expected stockout  : 0.0
# Underage cost Cu   : 4.0
# Overage cost  Co   : 4.0

# Producto con alto margen → pedir por encima de la media
r_alto = wl.newsvendor(demand_mean=100, demand_std=20,
                        price=50, cost=6, salvage=0)
print(r_alto.optimal_qty > 100)   # True

# Producto con bajo margen → pedir por debajo de la media
r_bajo = wl.newsvendor(demand_mean=100, demand_std=20,
                        price=7, cost=6, salvage=2)
print(r_bajo.optimal_qty < 100)   # True
```

**`NewsvendorResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `optimal_qty` | Q* óptimo |
| `critical_ratio` | CR = Cu/(Cu+Co) |
| `expected_profit` | Beneficio esperado en Q* |
| `expected_sales` | Ventas esperadas E[min(D, Q*)] |
| `expected_leftover` | Sobrante esperado E[max(Q*−D, 0)] |
| `expected_stockout` | Rotura esperada E[max(D−Q*, 0)] |
| `underage_cost` | Cu — costo de substock |
| `overage_cost` | Co — costo de sobrestock |

---

## 8. Análisis de operaciones

### `oee(availability, performance, quality)` — OEE

Calcula la **Eficiencia Global de los Equipos** (OEE = Availability × Performance × Quality).

```python
r = wl.oee(
    availability=0.90,   # tiempo disponible / tiempo planificado
    performance=0.80,    # producción real / producción teórica
    quality=0.95,        # unidades buenas / unidades totales
)
print(r)
# OEE = 68.4%
# Clase mundial: ≥ 85%

r.plot()    # gráfica horizontal con referencia world-class (85%)
```

### `utilization_efficiency(actual_output, max_output)` — Utilización

```python
r = wl.utilization_efficiency(actual_output=750, max_output=1000)
print(r.utilization)         # 0.75 — 75% de utilización
print(r.idle_fraction)       # 0.25 — 25% capacidad ociosa
```

### `unit_cost(fixed_cost, variable_cost, units)` — Costo unitario

```python
r = wl.unit_cost(fixed_cost=10_000, variable_cost=5_000, units=500)
print(r.unit_cost)           # 30.0 $/unidad
print(r.fixed_cost_per_unit) # 20.0
print(r.var_cost_per_unit)   # 10.0
```

---

## 9. Análisis de cuellos de botella

### `bottleneck_analysis(station_names, capacities, demand_rate)` — Teoría de restricciones

Identifica el cuello de botella de una línea de producción comparando la capacidad de cada estación con la demanda.

```python
r = wl.bottleneck_analysis(
    station_names=["Corte", "Soldadura", "Pintura"],
    capacities=[120.0, 80.0, 100.0],  # unidades/hora por estación
    demand_rate=70.0,                  # demanda requerida
)
print(r)
# Bottleneck: Soldadura  (capacidad 80 < demanda 70 con menor margen)
# Utilization: Corte=58.3%, Soldadura=87.5%, Pintura=70.0%

r.plot()   # barras de utilización con cuello de botella en rojo
```

---

## 10. Balance de línea y tiempo takt

### `takt_time(available_time, demand)` — Tiempo takt

Ritmo de producción requerido para satisfacer la demanda del cliente.

```python
takt = wl.takt_time(available_time=480, demand=60)
print(takt)   # 8.0 min/unidad
```

### `line_balance(names, cycle_times, takt)` — Balance de línea

Analiza si cada estación puede cumplir con el tiempo takt y calcula la eficiencia de balance.

```python
lb = wl.line_balance(
    names=["A", "B", "C"],
    cycle_times=[5.0, 9.0, 4.0],
    takt=10.0,
)
print(lb.bottleneck)           # "B" — estación más lenta
print(lb.balance_efficiency)   # 0.60 — 60% de eficiencia
print(lb.total_idle_time)      # tiempo ocioso total

lb.plot()  # barras de cycle time vs takt
```

---

## 11. Análisis de punto de equilibrio

### `break_even(fixed_cost, price_per_unit, variable_cost_per_unit, *, actual_units)` — Punto de equilibrio

```python
be = wl.break_even(
    fixed_cost=10_000,
    price_per_unit=25,
    variable_cost_per_unit=15,
    actual_units=1_500,
)
print(be.bep_units)              # 1000.0 — punto de equilibrio en unidades
print(be.bep_revenue)            # 25000.0 — ingresos en el punto de equilibrio
print(be.margin_of_safety_pct)   # 33.3% — margen de seguridad sobre ventas actuales
print(be.profit)                 # 5000.0 — beneficio con actual_units

be.plot()   # líneas de ingresos/costos con BEP y zona de beneficio
```

---

## 12. Árboles de KPI

Los árboles de KPI crean jerarquías interactivas visualizadas como **treemap** o **sunburst** con Plotly.

### `oee_kpi_tree(availability, performance, quality)`

```python
tree = wl.oee_kpi_tree(0.90, 0.80, 0.95)
tree.plot()                     # treemap (por defecto)
tree.plot(kind="sunburst")      # diagrama radial
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

### `KPINode` — árbol personalizado

```python
root = wl.KPINode("EBITDA", value=100_000, unit="€")
rev  = root.add_child("Revenue",        value=200_000, unit="€")
cost = root.add_child("Operating costs", value=100_000, unit="€")
rev.add_child("Product A", value=120_000, unit="€")
rev.add_child("Product B", value=80_000,  unit="€")

from walopy.plotting import plot_kpi_tree
fig = plot_kpi_tree(root, kind="treemap")
fig.show()
```

---

## 13. Solvers y optimización

### `solve_lam(metric, target, *, mu, model)` — Máxima tasa de llegada

Encuentra la mayor λ tal que una métrica no supere el objetivo.

```python
r = wl.solve_lam("Wq", target=0.5, mu=5.0, model="mm1")
print(r.value)          # λ máxima ≈ 3.33
print(r.achieved_value) # Wq ≈ 0.5
print(r.model_result)   # QueueResult completo en la solución
```

### `solve_mu(metric, target, *, lam, model)` — Mínima tasa de servicio

```python
r = wl.solve_mu("Wq", target=0.3, lam=3.0, model="mm1")
print(r.value)   # μ mínima necesaria ≈ 5.0
```

### `solve_servers(metric, target, *, lam, mu)` — Mínimo número de servidores

```python
r = wl.solve_servers("Wq", target=0.1, lam=8.0, mu=5.0)
print(r.value)         # c mínimo = 3
print(r.model_result)  # QueueResult para M/M/3
```

### `optimize_servers(lam, mu, cost_per_server, cost_per_wait)` — Optimización de costo total

Minimiza cost_per_server × c + cost_per_wait × λ × Wq evaluando todos los c viables.

```python
r = wl.optimize_servers(
    lam=6.0,
    mu=5.0,
    cost_per_server=10.0,   # costo fijo por servidor por unidad de tiempo
    cost_per_wait=5.0,      # costo por unidad de tiempo de espera de cada cliente
)
print(r.optimal_servers)   # c óptimo
print(r.optimal_cost)      # costo mínimo

r.plot()   # gráfica de costo vs número de servidores
```

---

## 14. Análisis de sensibilidad

### `sensitivity(model_fn, param, values, **fixed_kwargs)` — Barrido paramétrico

Evalúa un modelo sobre un rango de valores de un parámetro.

```python
import numpy as np

df = wl.sensitivity(
    wl.mm1,
    param="lam",
    values=np.linspace(0.5, 4.5, 20),
    mu=5.0,       # parámetros fijos
)
print(df.columns.tolist())  # ['lam', 'rho', 'L', 'Lq', 'W', 'Wq', ...]

# Barrido sobre μ
df2 = wl.sensitivity(wl.mm1, "mu", np.linspace(4.0, 10.0, 15), lam=3.0)

# Barrido sobre número de servidores en M/M/c
df3 = wl.sensitivity(wl.mmc, "c", range(1, 6), lam=8.0, mu=5.0)

# Visualizar
from walopy.plotting import plot_sensitivity
fig = plot_sensitivity(df, "lam", metrics=["Wq", "Lq"])
fig.show()
```

---

## 15. Escenarios en lote (batch_model)

### `batch_model(model_fn, df, **fixed_kwargs)` — Aplicar modelo a un DataFrame

Aplica cualquier función de walopy a cada fila de un DataFrame de escenarios.

```python
import pandas as pd

# Varios escenarios con distintas tasas de llegada
escenarios = pd.DataFrame({
    "lam": [1.0, 2.0, 3.0, 4.0]
})
resultado = wl.batch_model(wl.mm1, escenarios, mu=5.0)
print(resultado[["lam", "rho", "Wq", "L"]])

# Escenarios mixtos (lambda y mu variables)
escenarios2 = pd.DataFrame({
    "lam": [2.0, 3.0, 4.0],
    "mu":  [5.0, 6.0, 7.0],
})
resultado2 = wl.batch_model(wl.mm1, escenarios2)

# Con número de servidores variable (columna int)
escenarios3 = pd.DataFrame({
    "c": [1, 2, 3, 4],
})
resultado3 = wl.batch_model(wl.mmc, escenarios3, lam=8.0, mu=5.0)

# Las filas con error quedan marcadas en "_error"
print(resultado[resultado["_error"].notna()])  # filas fallidas
```

---

## 16. Comparar múltiples resultados

### `compare(*results, labels)` — DataFrame comparativo

Construye un DataFrame con una fila por resultado para facilitar la comparación.

```python
df = wl.compare(
    wl.mm1(3.0, 5.0),
    wl.mmc(3.0, 5.0, 2),
    wl.md1(3.0, 5.0),
    labels=["M/M/1", "M/M/2", "M/D/1"],
)
print(df[["label", "ρ (utilization)", "Wq (wait time)", "L (system)"]])
#    label  ρ (utilization)  Wq (wait time)  L (system)
# 0  M/M/1          0.6         0.3000         1.50
# 1  M/M/2          0.3         0.0302         1.02
# 2  M/D/1          0.6         0.1500         1.05

# Sin etiquetas → scenario_1, scenario_2, ...
df2 = wl.compare(wl.mm1(1, 5), wl.mm1(2, 5), wl.mm1(3, 5))
```

---

## 17. Gráficas

Todos los resultados exponen `.plot()` que devuelve una figura de Matplotlib o Plotly. También se pueden llamar directamente desde `walopy.plotting`.

| Función `.plot()` | Tipo | Descripción |
|---|---|---|
| `QueueResult.plot()` | Matplotlib | Curvas Wq y Lq vs ρ con punto operativo |
| `OEEResult.plot()` | Matplotlib | Barras horizontales OEE con referencia 85% |
| `BottleneckResult.plot()` | Matplotlib | Utilización por estación, cuello de botella en rojo |
| `EOQResult.plot()` | Matplotlib | Curvas de costo de mantener, ordenar y total |
| `LineBalanceResult.plot()` | Plotly | Cycle time vs takt por estación |
| `BreakEvenResult.plot()` | Plotly | Líneas ingreso/costo con BEP y zona de beneficio |
| `SimulationResult.plot()` | Plotly | Histograma de Wq + CDF empírica con percentiles |
| `OptimizeResult.plot()` | Plotly | Costo por servidor, costo de espera y total vs c |
| `KPINode.plot(kind=)` | Plotly | Treemap o sunburst interactivo |

```python
# Guardar como HTML interactivo (Plotly)
fig = r.plot()
fig.write_html("resultado.html")

# Guardar como imagen (Matplotlib)
fig = wl.oee(0.9, 0.8, 0.95).plot()
fig.savefig("oee.png", dpi=150)
```

Para la curva de sensibilidad:
```python
from walopy.plotting import plot_sensitivity
df = wl.sensitivity(wl.mm1, "lam", np.linspace(0.5, 4.5, 20), mu=5.0)
fig = plot_sensitivity(df, "lam", metrics=["Wq", "Lq", "L"])
fig.show()
```

---

## 18. CLI

walopy incluye una interfaz de línea de comandos para uso rápido sin escribir código.

```bash
# M/M/1
python -m walopy mm1 --lam 3 --mu 5

# M/M/c
python -m walopy mmc --lam 8 --mu 5 --c 2

# M/D/1
python -m walopy md1 --lam 3 --mu 5

# G/G/1 (Kingman)
python -m walopy gg1 --lam 3 --mu 5 --ca2 1.2 --cs2 0.8

# Ley de Little (resolver W)
python -m walopy littles --L 2.5 --lam 5.0

# EOQ
python -m walopy eoq --demand 1000 --ordering 50 --holding 2

# Versión
python -m walopy --version
```

Ejemplo de salida:
```
Model : M/M/1
λ     : 3.0   (arrival rate)
μ     : 5.0   (service rate per server)
ρ     : 0.6   (utilization)
L     : 1.5   (avg units in system)
Lq    : 0.9   (avg units in queue)
W     : 0.5   (avg time in system)
Wq    : 0.3   (avg wait time in queue)
  P0      : 0.4
```

---

## 19. Referencia de módulos

| Módulo | Funciones y clases principales |
|---|---|
| `queuing` | `mm1`, `mmc`, `md1`, `kingman`, `littles_law`, `QueueResult` |
| `advanced` | `mm1k`, `mmck`, `erlang_b`, `mm1_priority`, `monte_carlo_gg1`, `takt_time`, `line_balance`, `break_even`, `queue_length_pmf`, `sojourn_cdf`, `PriorityQueueResult`, `SimulationResult`, `LineBalanceResult`, `BreakEvenResult` |
| `fitting` | `fit_from_data`, `FitResult` |
| `inventory` | `eoq`, `reorder_point`, `newsvendor`, `EOQResult`, `ReorderResult`, `NewsvendorResult` |
| `network` | `jackson_network`, `JacksonResult`, `StationMetrics` |
| `operations` | `oee`, `utilization_efficiency`, `unit_cost`, `OEEResult`, `UtilizationResult`, `UnitCostResult` |
| `bottleneck` | `bottleneck_analysis`, `BottleneckResult`, `StationResult` |
| `kpi` | `KPINode`, `oee_kpi_tree`, `throughput_kpi_tree`, `roi_kpi_tree` |
| `solver` | `solve_lam`, `solve_mu`, `solve_servers`, `optimize_servers`, `sensitivity`, `batch_model`, `compare`, `SolverResult`, `OptimizeResult` |
| `plotting` | `plot_queue_sensitivity`, `plot_queue_metrics`, `plot_oee`, `plot_bottleneck`, `plot_eoq`, `plot_kpi_tree`, `plot_sensitivity`, `plot_optimize_servers`, `plot_simulation`, `plot_line_balance`, `plot_break_even`, `plot_queue_distribution` |

---

## 20. Requisitos

```
Python ≥ 3.9
numpy ≥ 1.22
pandas ≥ 1.4
matplotlib ≥ 3.5
plotly ≥ 5.0
```

No se requiere `scipy`. Los cálculos estadísticos usan `statistics.NormalDist` de la biblioteca estándar de Python.

## Licencia

MIT — ver [LICENSE](LICENSE).

## Contribuciones

Pull requests bienvenidas. Asegúrate de que `pytest tests/` pase antes de abrir un PR.
