# walopy

**Teoría de colas, análisis de operaciones, modelos de inventario, árboles de KPI y más para Python.**

🇬🇧 [English version of this document](https://github.com/LeoSanta15/walopy/blob/main/README.en.md)

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
12. [Curvas de intercambio](#12-curvas-de-intercambio)
13. [Programación de producción (scheduling)](#13-programación-de-producción-scheduling)
14. [Confiabilidad](#14-confiabilidad--reliability)
15. [Proyectos: CPM y PERT](#15-proyectos-cpm-y-pert--project)
16. [Árboles de KPI](#16-árboles-de-kpi)
17. [Solvers y optimización](#17-solvers-y-optimización)
18. [Análisis de sensibilidad](#18-análisis-de-sensibilidad)
19. [Escenarios en lote (batch_model)](#19-escenarios-en-lote-batch_model)
20. [Comparar múltiples resultados](#20-comparar-múltiples-resultados)
21. [Gráficas](#21-gráficas)
22. [CLI](#22-cli)
23. [Referencia de módulos](#23-referencia-de-módulos)
24. [Idioma de los textos](#24-idioma-de-los-textos)
25. [Requisitos](#25-requisitos)

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
# Modelo : M/M/1
# λ      : 3.0   (tasa de llegada)
# μ      : 5.0   (tasa de servicio por servidor)
# ρ      : 0.6   (utilización por servidor)
# L      : 1.5   (unidades promedio en el sistema)
# Lq     : 0.9   (unidades promedio en cola)
# W      : 0.5   (tiempo promedio en el sistema)
# Wq     : 0.3   (tiempo promedio de espera en cola)

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
import numpy as np
rng = np.random.default_rng(42)
fit = wl.fit_from_data(inter_arrivals=rng.exponential(0.2, 500), service_times=rng.exponential(0.1, 500))
r   = wl.kingman(**fit.to_model_kwargs())
```

> **Equivalencias:**  
> `ca2=1, cs2=1` → M/M/1  
> `ca2=1, cs2=0` → M/D/1 (aproximado)

---

### `mg1(lam, mu, cs2)` — M/G/1 (Pollaczek-Khinchine exacto)

Llegadas Poisson, servicio de **distribución arbitraria** parametrizado por su media (1/μ) y su variabilidad (cs²). La fórmula P-K es **exacta**, no una aproximación.

**Fórmula P-K:**  
Wq = λ · E[S²] / (2 · (1 − ρ)),   donde E[S²] = (1 + cs²) / μ²

```python
# Servicio con distribución triangular: calcular cs² primero
cs2 = wl.cv2_triangular(a=2, m=5, b=10)   # a=mín, m=moda, b=máx
r   = wl.mg1(lam=0.15, mu=1/5, cs2=cs2)

# Equivalencia con M/M/1 (cs²=1) y M/D/1 (cs²=0)
r_mm1 = wl.mg1(lam=3.0, mu=5.0, cs2=1.0)  # idéntico a mm1(3, 5)
r_md1 = wl.mg1(lam=3.0, mu=5.0, cs2=0.0)  # idéntico a md1(3, 5)
```

#### Helpers `cv2_*` — CV² por distribución

El CV² (varianza / media²) es el único parámetro de distribución que M/G/1 necesita:

| Función | Distribución | CV² |
|---|---|---|
| `cv2_normal(mean, std)` | Normal | (σ/μ)² |
| `cv2_triangular(a, m, b)` | Triangular | fórmula exacta |
| `cv2_uniform(a, b)` | Uniforme | (b−a)² / (12·μ²) |
| `cv2_erlang(k)` | Erlang-k | 1/k |
| `cv2_gamma(shape)` | Gamma | 1/shape |
| `cv2_lognormal(mean, std)` | Lognormal | (σ/μ)² |
| `cv2_weibull(shape)` | Weibull | Γ(1+2/k)/Γ(1+1/k)²−1 |

```python
# Servicio con distribución Weibull de forma 2 (rayleigh)
cs2 = wl.cv2_weibull(shape=2.0)      # ≈ 0.273
r   = wl.mg1(lam=1.0, mu=2.0, cs2=cs2)
print(r.Wq)   # tiempo medio de espera en cola

# Servicio Erlang-3 (menos variable que exponencial)
r = wl.mg1(lam=3.0, mu=5.0, cs2=wl.cv2_erlang(3))
```

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
- `λ_eff (effective rate)` — tasa de llegada efectiva = λ · (1 − P_K)

```python
r = wl.mm1k(lam=5.0, mu=3.0, K=10)
print(r.params["PK (prob. de bloqueo)"])  # fracción de clientes rechazados
print(r.params["λ_eff (tasa efectiva)"])  # tasa real de entrada al sistema
```

---

### `mmck(lam, mu, c, K)` — M/M/c/K

Multi-servidor con capacidad finita. Generaliza tanto M/M/c (K→∞) como M/M/1/K (c=1). Las probabilidades de estado se calculan en espacio logarítmico para evitar desbordamientos con K grande.

```python
r = wl.mmck(lam=8.0, mu=3.0, c=2, K=20)
print(r.params["PK (prob. de bloqueo)"])

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

# 4. Conectar directamente con un modelo (necesita λ, μ, ca² y cs²: ajuste con ambas muestras)
fit_completo = wl.fit_from_data(ia, svc)
r = wl.kingman(**fit_completo.to_model_kwargs())  # usa lam, mu, ca2, cs2
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
# EOQ (cantidad de pedido): 223.6 unidades
# Frecuencia de pedidos   : 4.472 pedidos/periodo
# Tiempo de ciclo         : 0.2236 periodos
# Costo total             : 447.2
#   Costo de mantener     : 223.6
#   Costo de ordenar      : 223.6   ← iguales en el óptimo

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
# Punto de reorden    : 132.4 unidades
# Stock de seguridad  : 32.4 unidades
# Nivel de servicio   : 95.00%
# z                   : 1.645
# Demanda media en LT : 100.0
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
# Cantidad óptima     : 100.0 unidades
# Razón crítica       : 0.5
# Utilidad esperada   : 320.0
# Ventas esperadas    : 100.0
# Sobrante esperado   : 0.0
# Faltante esperado   : 0.0
# Costo de subestimar Cu: 4.0
# Costo de sobrestimar Co: 4.0

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

### `ebq(demand_rate, setup_cost, holding_cost, production_rate)` — Lote Económico de Producción (EBQ/EPQ)

Extiende el EOQ al caso en que la producción y el consumo ocurren **simultáneamente** (tasa de producción finita P > D).

**Fórmula:**
```
Q* = √(2 · D · S / (h · (1 − D/P)))
Inventario máximo = Q* · (1 − D/P)
Inventario medio  = Inventario máximo / 2
```

```python
r = wl.ebq(
    demand_rate=1000,       # D: unidades/período
    setup_cost=50,          # S: costo fijo de setup por lote
    holding_cost=2,         # h: costo/unidad/período
    production_rate=4000,   # P: tasa de producción (debe ser > D)
)
print(r)
# EBQ (tamaño de lote): 258.2 unidades
# Inventario máximo   : 193.6
# Inventario promedio : 96.82
# Frecuencia de lotes : 3.873 lotes/periodo
# Tiempo de ciclo     : 0.2582 periodos
# Tiempo de producción: 0.06455 periodos
# Costo total         : 193.6
#   Costo de mantener : 96.82
#   Costo de preparación: 96.82
```

**`EBQResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `ebq` | Lote óptimo Q* |
| `max_inventory` | Nivel máximo de inventario Q*(1−D/P) |
| `avg_inventory` | Inventario promedio = max/2 |
| `production_time` | Tiempo de producción por ciclo = Q*/P |
| `cycle_time` | Duración del ciclo = Q*/D |
| `total_cost` | Costo total mínimo |

---

### `eoq_multi(demand_rates, ordering_costs, holding_costs, *, names)` — EOQ multi-ítem independiente

Resuelve el EOQ para cada ítem por separado sin restricciones compartidas.

```python
r = wl.eoq_multi(
    demand_rates   = [1000, 500, 800],
    ordering_costs = [50,   30,  40 ],
    holding_costs  = [2,    1,   1.5],
    names          = ["A", "B", "C"],
)
print(r.total_cost)   # suma de costos óptimos individuales
df = r.to_frame()     # DataFrame con EOQ, costos y frecuencias por ítem
```

---

### `ebq_multi(demand_rates, setup_costs, holding_costs, production_rates, *, names)` — EBQ multi-ítem independiente

```python
r = wl.ebq_multi(
    demand_rates    = [1000, 500],
    setup_costs     = [50,   30 ],
    holding_costs   = [2,    1  ],
    production_rates= [4000, 2000],
)
df = r.to_frame()   # EBQ, inventario máximo/medio, costo por ítem
```

---

### `eoq_multi_constrained(demand_rates, ordering_costs, holding_costs, ...)` — EOQ multi-ítem con restricciones

Minimiza el costo total de inventario sujeto a **restricciones lineales** sobre las cantidades de pedido mediante **relajación Lagrangiana** (búsqueda binaria sobre el multiplicador).

**Restricciones soportadas:**

| Parámetro | Restricción |
|---|---|
| `budget`, `budget_unit_costs` | Σ(c_i · Q_i / 2) ≤ budget — valor promedio en inventario |
| `space`, `space_per_unit` | Σ(s_i · Q_i / 2) ≤ space — espacio promedio ocupado |
| `constraints` | Lista de `{"name", "weights", "bound"}` — Σ(a_i · Q_i) ≤ B |

```python
# Restricción de presupuesto
r = wl.eoq_multi_constrained(
    [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
    budget=5000,
    budget_unit_costs=[10, 8, 12],   # costo unitario de compra
)
print(r.binding_constraints)   # ["budget"] si la restricción está activa
print(r.lagrange_multipliers)  # {"budget": λ}
df = r.to_frame()              # Q*, holding cost, ordering cost por ítem

# Restricción de espacio
r2 = wl.eoq_multi_constrained(
    [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
    space=200,
    space_per_unit=[0.5, 0.3, 0.4],
)

# Restricción genérica: suma total de unidades pedidas ≤ 400
r3 = wl.eoq_multi_constrained(
    [1000, 500, 800], [50, 30, 40], [2, 1, 1.5],
    constraints=[{"name": "total_qty", "weights": [1, 1, 1], "bound": 400}],
)
```

**`ConstrainedMultiEOQResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `items` | Lista de dicts por ítem: nombre, Q*, costos |
| `total_cost` | Costo total bajo las restricciones |
| `unconstrained_total_cost` | Costo sin restricciones (cota inferior) |
| `lagrange_multipliers` | Diccionario {nombre_restricción: λ} |
| `binding_constraints` | Nombres de restricciones activas (λ > 0) |

---

### `lot_for_lot(demands, setup_cost, holding_cost)` — Lote por Lote

Heurística de dimensionado dinámico: ordena **exactamente la demanda de cada período**. Minimiza el costo de almacenamiento (cero inventario en tránsito) a cambio de un setup por período.

```python
demands = [100, 80, 0, 120, 60]   # demandas por período
r = wl.lot_for_lot(demands, setup_cost=200, holding_cost=1)
print(r.total_holding_cost)   # 0.0 — sin inventario residual
print(r.n_orders)             # 4 — un pedido por período con demanda > 0
print(r)
# Método               : Lote por lote
# Número de pedidos    : 4
# Costo total          : 800.0
```

---

### `silver_meal(demands, setup_cost, holding_cost)` — Silver-Meal

Heurística de dimensionado dinámico que **agrupa períodos** mientras el costo promedio por período decrece, reduciendo el número de setups.

```python
r = wl.silver_meal(demands, setup_cost=200, holding_cost=1)
print(r.total_cost <= wl.lot_for_lot(demands, 200, 1).total_cost)  # True
df = r.to_frame()   # pedidos: período, cantidad, períodos cubiertos
```

**`LotSizingResult` — atributos (Lot-for-Lot y Silver-Meal):**

| Atributo | Descripción |
|---|---|
| `orders` | Lista de pedidos: período, cantidad, períodos cubiertos |
| `total_cost` | Costo total (setup + almacenamiento) |
| `total_setup_cost` | Costo total de setups |
| `total_holding_cost` | Costo total de almacenamiento |
| `n_orders` | Número de pedidos emitidos |
| `method` | Nombre de la heurística usada |

---

### `eoq_quantity_discount(demand_rate, ordering_cost, holding_cost_rate, price_breaks)` — EOQ con descuentos por cantidad

Evalúa todos los tramos de precio (all-units) y selecciona la cantidad que **minimiza el costo total anual** (compra + pedido + almacenamiento), ajustando el EOQ al tramo válido cuando cae fuera de rango.

```python
r = wl.eoq_quantity_discount(
    demand_rate=1000,
    ordering_cost=50,
    holding_cost_rate=0.20,   # 20% del precio unitario por año
    price_breaks=[
        (0,    10.00),   # precio base
        (500,   9.50),   # ≥ 500 unidades → $9.50
        (1000,  9.00),   # ≥ 1000 unidades → $9.00
    ],
)
print(r.optimal_qty)    # cantidad óptima seleccionada
print(r.unit_price)     # precio en ese tramo
print(r.total_cost)     # costo anual mínimo
df = r.to_frame()       # todos los candidatos evaluados
```

**`QuantityDiscountResult` — atributos:**

| Atributo | Descripción |
|---|---|
| `optimal_qty` | Cantidad óptima ajustada al tramo |
| `unit_price` | Precio unitario en el tramo seleccionado |
| `total_cost` | Costo total anual (compra + pedido + almacenamiento) |
| `purchase_cost` | Costo de compra anual D · precio |
| `ordering_cost_total` | Costo de pedido anual (D/Q) · K |
| `holding_cost_total` | Costo de almacenamiento anual (Q/2) · h · precio |
| `candidates` | Lista de todos los tramos evaluados |

---

---

### ABC, XYZ y ABC-XYZ — clasificación de artículos

`abc_analysis` clasifica por **valor anual** (Pareto): un artículo es A mientras el acumulado *previo* a él sea
menor que `a_threshold` (80 %), B mientras sea menor que `b_threshold` (95 %) y C en el resto. Los artículos
sin demanda quedan en C. `xyz_analysis` clasifica por **variabilidad** (coeficiente de variación): X si
CV ≤ `x_threshold` (0.5), Y hasta `y_threshold` (1.0) y Z por encima. `abc_xyz` combina ambas y devuelve la
matriz 3×3.

```python
items = [
    {"name": "A", "demand": 500, "unit_value": 10.0, "demand_std": 120},
    {"name": "B", "demand": 300, "unit_value": 10.0, "demand_std": 60},
    {"name": "C", "demand": 100, "unit_value": 10.0, "demand_std": 150},
    {"name": "D", "demand": 700, "unit_value": 1.0,  "demand_std": 300},
    {"name": "E", "demand": 300, "unit_value": 1.0,  "demand_std": 10},
]

abc = wl.abc_analysis(items)
print(abc)                       # resumen por clase: A = 2 artículos (80 % del valor)
print(abc.to_frame()[["artículo", "valor_anual", "pct_acumulado", "clase"]])

# XYZ: cada artículo aporta 'cv' directamente o 'demand_std' + 'demand_mean' (o 'demand_rate')
xyz = wl.xyz_analysis([
    {"name": i["name"], "demand_std": i["demand_std"], "demand_mean": i["demand"]} for i in items
])
print(xyz.to_frame())            # columnas: artículo, cv, clase

# ABC-XYZ: matriz de conteos (filas ABC, columnas XYZ)
combo = wl.abc_xyz([{**i, "cv": i["demand_std"] / i["demand"]} for i in items])
print(combo.matrix_frame())
print(combo.items[0]["combined_class"])   # 'AX'
```

| Parámetro | Descripción |
|---|---|
| `items` | Lista de diccionarios. ABC: `demand` (≥ 0) y `unit_value` (> 0). XYZ: `cv` o `demand_std` + `demand_mean`/`demand_rate` |
| `a_threshold`, `b_threshold` | Límites acumulados de las clases A y B (0 < a < b < 1) |
| `x_threshold`, `y_threshold` | Límites de CV de las clases X e Y |

Errores: lista vacía, elementos que no son diccionarios, claves faltantes y valores no finitos lanzan `ValueError`/`TypeError`
con el elemento y la clave afectados; si todas las demandas son 0 no hay nada que clasificar y se lanza `ValueError`.

---

### MRP de un nivel — `mrp`

Plan de requerimientos de materiales para un artículo: necesidades netas, órdenes planificadas (recepción y
liberación) y existencias proyectadas. Admite lote por lote (`"LFL"`) o lote fijo, tiempo de entrega,
stock de seguridad y recepciones programadas.

```python
r = wl.mrp(
    gross_requirements=[0, 50, 0, 30, 60, 20],
    initial_on_hand=40,
    scheduled_receipts=[0, 0, 25, 0, 0, 0],
    lead_time=1,
    lot_size=40,          # "LFL" para lote por lote
    safety_stock=10,
    item_name="Eje",
)
print(r)                      # tabla por periodo: GR, SR, OH, NR, PR, PO
print(r.to_frame())           # el mismo plan como DataFrame
print(r.past_due_releases)    # 0.0
```

Si el `lead_time` es mayor que el periodo en que se necesita la orden, la liberación cae antes del periodo 1:
`mrp` emite un `UserWarning` y acumula esa cantidad en `past_due_releases` (no aparece en `planned_releases`).

---

## 8. Análisis de operaciones

### `oee(availability, performance, quality)` — OEE

Calcula la **Eficiencia Global de los Equipos** (OEE = Disponibilidad × Rendimiento × Calidad).

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

### `utilization_efficiency(actual_output, capacity)` — Utilización

```python
r = wl.utilization_efficiency(actual_output=750, capacity=1000)
print(r.utilization)         # 0.75 — 75% de utilización
print(1 - r.utilization)     # 0.25 — 25% de capacidad ociosa
```

### `unit_cost(fixed_cost, variable_cost_per_unit, units_produced)` — Costo unitario

```python
r = wl.unit_cost(fixed_cost=10_000, variable_cost_per_unit=10, units_produced=500)
print(r.unit_cost)               # 30.0 $/unidad
print(r.fixed_cost_per_unit)     # 20.0
print(r.variable_cost_per_unit)  # 10.0
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
# Cuello de botella: Soldadura  (capacidad 80 < demanda 70 con menor margen)
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

### `line_balance(station_names, cycle_times, takt)` — Balance de línea

Analiza si cada estación puede cumplir con el tiempo takt y calcula la eficiencia de balance.

```python
lb = wl.line_balance(
    station_names=["A", "B", "C"],
    cycle_times=[5.0, 9.0, 4.0],
    takt=10.0,
)
print(lb.bottleneck)           # "B" — estación más lenta
print(lb.balance_efficiency)   # eficiencia de balance de la línea
print(lb.theoretical_min_stations)  # número mínimo teórico de estaciones

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
print(be.margin_of_safety_pct)   # 0.333 — margen de seguridad (fracción) sobre ventas actuales
print(be.margin_of_safety_units) # 500.0 — unidades por encima del punto de equilibrio

be.plot()   # líneas de ingresos/costos con BEP y zona de beneficio
```

### `break_even_multi(fixed_cost, prices, variable_costs, sales_mix)` — Multi-producto

Calcula el punto de equilibrio para una mezcla de varios productos usando la **contribución marginal ponderada (WACM)**.

**Fórmula:** WACM = Σ(CMᵢ × mixᵢ) / Σmixᵢ, luego BEP_total = FC / WACM

```python
r = wl.break_even_multi(
    fixed_cost=120_000,
    prices=[50, 80, 120],
    variable_costs=[30, 50, 70],
    sales_mix=[3, 2, 1],          # proporción de ventas
)
print(r.weighted_avg_cm)          # WACM ≈ 36.67
print(r.bep_units_total)          # unidades totales en el punto de equilibrio
print(r.bep_revenue_total)        # ingresos totales en el punto de equilibrio

for item in r.items:
    print(item["Producto"], item["PE unidades"])

r.to_frame()    # DataFrame con una fila por producto
```

| Atributo | Descripción |
|---|---|
| `weighted_avg_cm` | Contribución marginal ponderada |
| `bep_units_total` | Unidades totales en el BEP |
| `bep_revenue_total` | Ingresos totales en el BEP |
| `items` | Lista de dicts por producto con `BEP units`, `BEP revenue` |

---

### `break_even_sales(fixed_cost, variable_cost_ratio, *, actual_revenue)` — Punto de equilibrio en ingresos

Calcula el BEP en términos de ingresos cuando los costos variables se expresan como porcentaje de las ventas.

**Fórmula:** BEP = FC / (1 − RCV)

```python
r = wl.break_even_sales(
    fixed_cost=50_000,
    variable_cost_ratio=0.60,     # 60% de los ingresos son costos variables
    actual_revenue=200_000,
)
print(r.bep_revenue)              # 125 000 — ingresos en el BEP
print(r.contribution_margin_ratio) # 0.40 — margen de contribución
print(r.margin_of_safety_units)   # 75 000 — margen de seguridad en ingresos
print(r.margin_of_safety_pct)     # 0.375 — porcentaje del margen de seguridad
```

---

## 12. Curvas de intercambio

Herramientas para tomar decisiones de política agregada en familias de artículos.

### Tipo 1 — ciclo: `exchange_curve`

Traza la hipérbola entre número de pedidos por año (N) e inversión promedio en inventario de ciclo (I):

```
N(k) = N* / k      I(k) = k · I*      →      N · I = N* · I*  (constante)
```

Dado un target de N o de I, resuelve el multiplicador k óptimo y recalcula Q para cada artículo.

```python
import walopy as wl

items = [
    {"name": "A", "demand": 1000, "ordering_cost": 50,  "holding_cost": 2,  "unit_value": 10},
    {"name": "B", "demand":  500, "ordering_cost": 30,  "holding_cost": 1,  "unit_value":  5},
    {"name": "C", "demand": 2000, "ordering_cost": 100, "holding_cost": 4,  "unit_value":  8},
]

# Sin target → punto EOQ (k = 1)
r = wl.exchange_curve(items)
print(r)
```

```
Objetivo                : eoq
Multiplicador k         : 1.0000
N pedidos/año (EOQ)     : 87.27
N pedidos/año (óptimo)  : 87.27
Inversión (EOQ)         : 5430
Inversión (óptimo)      : 5430
```

```python
# Reducir a 20 pedidos/año (k > 1 → Q más grandes → más inversión)
r = wl.exchange_curve(items, target_orders=20)

# Limitar inversión a 3 000 (k < 1 → Q más pequeños → más pedidos)
r = wl.exchange_curve(items, target_investment=3000)

# Tabla por artículo
df = r.to_frame()
# columnas: artículo | Q_eoq | Q_óptima | n_pedidos | inversión

# Hipérbola para graficar
curve = r.curve_to_frame()
# columnas: N | I
```

**Parámetros de cada artículo**

| Clave | Requerido | Descripción |
|-------|-----------|-------------|
| `demand` | ✓ | Demanda anual Di |
| `ordering_cost` | ✓ | Costo de pedido Ki |
| `holding_cost` | ✓ | Costo de mantenimiento hi |
| `unit_value` | — | Valor unitario vi (default 1) |
| `name` | — | Etiqueta (default I1, I2, …) |

---

### Tipo 2 — seguridad: `safety_stock_curve`

Traza la curva entre inversión en stock de seguridad e nivel de servicio por ciclo usando una **política z común** para toda la familia:

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

# Target: nivel de servicio 95%
r = wl.safety_stock_curve(items, target_service_level=0.95)
print(r)
```

```
Objetivo          : nivel_de_servicio=95.0000%
z                 : 1.6449
Nivel de servicio : 95.0000%
Inversión en SS   : 1 847
```

```python
# Target: presupuesto máximo de SS
r = wl.safety_stock_curve(items, target_ss_investment=1000)

# Tabla por artículo (incluye punto de reorden cuando se da demand_rate)
df = r.to_frame()
# columnas: artículo | sigma_dlt | stock_de_seguridad | inversión | punto_de_reorden

# Curva completa (z de −2 a 4)
curve = r.curve_to_frame()
# columnas: z | service_level | ss_investment
```

**Parámetros de cada artículo**

| Clave | Requerido | Descripción |
|-------|-----------|-------------|
| `demand_std` | ✓ | Desviación estándar de la demanda |
| `lead_time` | ✓ | Lead time medio |
| `demand_rate` | — | Demanda media; activa columna `reorder_point` |
| `lead_time_std` | — | Desviación estándar del lead time (default 0) |
| `unit_value` | — | Valor unitario (default 1) |
| `name` | — | Etiqueta (default I1, I2, …) |

---

### Relación entre ambas curvas

| | Tipo 1 (ciclo) | Tipo 2 (seguridad) |
|---|---|---|
| **Función** | `exchange_curve` | `safety_stock_curve` |
| **Decide** | Tamaño de lote Q | Punto de reorden r |
| **Tradeoff** | N pedidos/año ↔ Inversión ciclo | Nivel de servicio ↔ SS |
| **Resultado** | `ExchangeCurveResult` | `SafetyStockCurveResult` |
| **Parámetro** | Multiplicador k | Factor z |

Usadas juntas cubren la política completa `(Q, r)` para toda la familia.

---

## 13. Programación de producción (scheduling)

### Máquina única — `schedule_single`

Asigna *n* trabajos a una sola máquina según una regla de prioridad.

```python
import walopy as wl

p = [3, 1, 4, 1, 5]          # tiempos de proceso
d = [8, 3, 10, 4, 12]         # fechas de entrega
w = [2, 5, 1, 4, 1]           # pesos de importancia

r = wl.schedule_single(p, rule="SPT", due_dates=d, weights=w,
                        names=["A","B","C","D","E"])
print(r)
```

```
Regla                   : SPT
Secuencia               : B → D → A → C → E
Makespan (Cmax)         : 14
Finalización total ΣCj  : 37
Finalización pond. ΣwCj : 89
Retraso máximo          : 2
Tardanza total ΣTj      : 2
Trabajos con retraso    : 1
```

**Reglas disponibles**

| `rule` | Criterio minimizado | Datos requeridos |
|--------|---------------------|-----------------|
| `'SPT'` | ΣCj (tiempo total de completación) | — |
| `'EDD'` | Lmax (máxima tardanza) | `due_dates` |
| `'WSPT'` | ΣwjCj (completación ponderada) | `weights` |
| `'CR'` | Ratio crítico dj/pj | `due_dates` |
| `'FIFO'` | Orden de llegada (línea base) | — |

**Atributos de `ScheduleResult`**

| Atributo | Descripción |
|----------|-------------|
| `rule` | Regla utilizada |
| `sequence` | Lista de nombres en orden de procesamiento |
| `jobs` | Lista de `JobSchedule` (por trabajo) |
| `makespan` | Cmax = suma de tiempos de proceso |
| `total_completion_time` | ΣCj |
| `total_weighted_completion_time` | ΣwjCj |
| `max_lateness` | max(Lj) |
| `total_tardiness` | ΣTj |
| `n_tardy` | Número de trabajos tarde |

```python
df = r.to_frame()  # columnas: Trabajo, p, d, w, Inicio, C, L, T, Con retraso
```

---

### Flow-shop de 2 máquinas — `johnson_flowshop`

El algoritmo de Johnson encuentra la secuencia óptima que minimiza el makespan cuando todos los trabajos pasan primero por M1 y luego por M2.

```python
m1 = [3, 8, 5, 7, 2]   # tiempos en máquina 1
m2 = [5, 2, 8, 4, 6]   # tiempos en máquina 2

r = wl.johnson_flowshop(m1, m2)
print(r)
```

```
Secuencia : J1 → J5 → J4 → J3 → J2
Makespan  : 34
```

```python
df = r.to_frame()
# columnas: Job | M1 start | M1 end | M2 start | M2 end
```

---

### Flow-shop de m máquinas — `neh_flowshop`

Heurística de **Nawaz-Enscore-Ham** para el flow-shop de permutación con cualquier número de máquinas:
ordena los trabajos por tiempo total decreciente e inserta cada uno en la mejor posición (aceleración de
Taillard: O(n²·m)). Es una heurística: en casos pequeños el makespan queda típicamente a pocos puntos
porcentuales del óptimo.

```python
# filas = trabajos, columnas = máquinas
tiempos = [[5, 9, 8], [9, 3, 10], [9, 4, 5], [4, 8, 8]]
r = wl.neh_flowshop(tiempos, names=["P1", "P2", "P3", "P4"])
print(r)               # secuencia y makespan
print(r.to_frame())    # Gantt: columnas M1_inicio, M1_fin, M2_inicio, ...
print(r.sequence, r.makespan)
```

---

## 14. Confiabilidad — `reliability`

Modelos de confiabilidad con distribución exponencial (tasa de falla constante).

### Componente individual — `mtbf_analysis`

```python
r = wl.mtbf_analysis(failure_rate=0.01, mttr=5.0, t=100)
print(r)
```

```
Topología       : component
Componentes     : 1
Tasas de falla λ: ['0.01']
MTBF            : 100
R(t=100)        : 0.367879
Disponibilidad  : 95.2381%
```

### Sistema en serie — `series_system`

El sistema falla si **cualquier** componente falla. λ_sys = Σλi.

```python
r = wl.series_system([0.01, 0.02, 0.03], t=10)
print(r.mtbf)      # 1/0.06 ≈ 16.67
print(r.R_t)       # e^{-0.06·10} ≈ 0.549
```

### Sistema en paralelo — `parallel_system`

El sistema opera si **al menos uno** de los componentes opera.  
R_sys(t) = 1 − ∏(1 − e^{−λi·t}). MTBF calculado numéricamente.

```python
r = wl.parallel_system([0.01, 0.02], t=50)
print(r.R_t)        # mayor que el sistema en serie
print(r.mtbf)       # mayor que cualquier componente individual
```

### Sistema k-de-n — `koon_system`

Opera si al menos **k** de **n** componentes idénticos están en servicio.  
MTBF exacto = (1/λ) · Σ_{j=k}^{n} (1/j).

```python
# 2-de-3: requiere al menos 2 de 3 componentes idénticos
r = wl.koon_system(n=3, k=2, failure_rate=0.01, t=50)
print(r.mtbf)   # (1/0.01) * (1/2 + 1/3) ≈ 83.33
print(r.R_t)
```

**Casos especiales**
- `k=1` → equivale a `parallel_system` con n componentes idénticos.
- `k=n` → equivale a `series_system` con n componentes idénticos.

**Atributos de `ReliabilityResult`**

| Atributo | Descripción |
|----------|-------------|
| `topology` | `'component'`, `'series'`, `'parallel'`, `'k-of-n'` |
| `n_components` | Número de componentes |
| `failure_rates` | Lista de λi |
| `mtbf` | MTBF del sistema |
| `R_t` | Confiabilidad R(t) si se proporcionó `t` |
| `availability` | Disponibilidad estacionaria A si se proporcionó `mttr` |
| `mttr` | Tiempo medio de reparación (si se proporcionó) |

```python
df = r.to_frame()   # columnas: Topología, Componentes, MTBF[, R(t), Disponibilidad]
r.R(t=200)          # evalúa R(t) en cualquier tiempo posterior
```

---

### Distribución de Weibull — `weibull_analysis`

Ajusta una Weibull de dos parámetros (forma β, escala η) a tiempos de falla completos por **máxima
verosimilitud** (`method="MLE"`, bisección sobre la ecuación de verosimilitud) o por **regresión de rangos**
(`method="RRY"`, rangos medianos de Benard). β < 1 indica mortalidad infantil, β ≈ 1 fallas aleatorias y
β > 1 desgaste.

```python
tiempos = [12.5, 18.3, 24.1, 31.7, 38.2, 45.9, 52.4, 61.0, 70.8, 85.3]
w = wl.weibull_analysis(tiempos)
print(w)                       # β ≈ 2.10, η ≈ 49.86, MTTF ≈ 44.16
print(w.R(30), w.F(30))        # confiabilidad y probabilidad de falla a t = 30
print(w.h(30))                 # tasa de falla instantánea
print(w.b10, w.b50, w.b_life(5))   # vidas B10, B50 y B5
print(w.to_frame())

w_rry = wl.weibull_analysis(tiempos, method="RRY")
```

Se necesitan al menos 2 tiempos finitos y positivos; si todos son iguales la forma no es estimable
(`ValueError`) y, si casi no hay dispersión, se avisa (`UserWarning`) de que β alcanzó la cota superior de 100.

---

## 15. Proyectos: CPM y PERT — `project`

Programación de proyectos sobre una red de actividades. Cada actividad es un diccionario con `name`,
`predecessors` (lista de nombres, puede omitirse) y su duración. Los nombres deben ser únicos; los
ciclos y los predecesores desconocidos lanzan `ValueError`.

### CPM — duraciones determinísticas

Paso hacia adelante (ES, EF) y hacia atrás (LS, LF); holgura total HT = LS − ES, holgura libre HL y ruta crítica (HT = 0).

```python
acts = [
    {"name": "A", "duration": 3, "predecessors": []},
    {"name": "B", "duration": 4, "predecessors": ["A"]},
    {"name": "C", "duration": 2, "predecessors": ["A"]},
    {"name": "D", "duration": 1, "predecessors": ["B", "C"]},
]
r = wl.cpm(acts)
print(r)                    # duración 8, ruta crítica A → B → D
print(r.to_frame())         # ES, EF, LS, LF, HT, HL y si es crítica
print(r.critical_path)      # ['A', 'B', 'D']
```

### PERT — tres estimaciones por actividad

Duración esperada tₑ = (a + 4m + b)/6 y varianza ((b − a)/6)²; la varianza del proyecto es la suma de las
de la ruta crítica. `probability(T)` da P(duración ≤ T) con aproximación normal.

```python
acts = [
    {"name": "A", "optimistic": 1, "most_likely": 3, "pessimistic": 5, "predecessors": []},
    {"name": "B", "optimistic": 2, "most_likely": 4, "pessimistic": 9, "predecessors": ["A"]},
]
p = wl.pert(acts)
print(p)                    # duración esperada 7.5, σ ≈ 1.34
print(p.probability(9.0))   # ≈ 0.868: probabilidad de terminar en 9 unidades o menos
```

`probability` solo está disponible en resultados PERT con varianza distinta de cero.

---

## 16. Árboles de KPI

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

## 17. Solvers y optimización

### `solve_lam(target_metric, target_value, *, mu, model)` — Máxima tasa de llegada

Encuentra la mayor λ tal que una métrica no supere el objetivo.

```python
r = wl.solve_lam("Wq", 0.5, mu=5.0, model="mm1")
print(r.value)          # λ máxima ≈ 3.33
print(r.achieved_value) # Wq ≈ 0.5
print(r.model_result)   # QueueResult completo en la solución
```

### `solve_mu(target_metric, target_value, *, lam, model)` — Mínima tasa de servicio

```python
r = wl.solve_mu("Wq", 0.3, lam=3.0, model="mm1")
print(r.value)   # μ mínima necesaria ≈ 5.0
```

### `solve_servers(target_metric, target_value, *, lam, mu)` — Mínimo número de servidores

```python
r = wl.solve_servers("Wq", 0.1, lam=8.0, mu=5.0)
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
print(r.min_cost)          # costo mínimo

r.plot()   # gráfica de costo vs número de servidores
```

---

## 18. Análisis de sensibilidad

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

## 19. Escenarios en lote (batch_model)

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

# Las filas con error quedan marcadas en "_error" (la columna solo existe si alguna fila falla;
# aquí c=1 es inestable porque λ=8 > μ=5)
print(resultado3[resultado3["_error"].notna()])  # filas fallidas

# Para que la primera excepción se propague en lugar de recogerse:
# wl.batch_model(wl.mmc, escenarios3, errors="raise", lam=8.0, mu=5.0)
```

---

## 20. Comparar múltiples resultados

### `compare(*results, labels)` — DataFrame comparativo

Construye un DataFrame con una fila por resultado para facilitar la comparación.

```python
df = wl.compare(
    wl.mm1(3.0, 5.0),
    wl.mmc(3.0, 5.0, 2),
    wl.md1(3.0, 5.0),
    labels=["M/M/1", "M/M/2", "M/D/1"],
)
print(df[["label", "ρ (utilización)", "Wq (tiempo de espera)", "L (en el sistema)"]])
#    label  ρ (utilización)  Wq (tiempo de espera)  L (en el sistema)
# 0  M/M/1          0.6         0.3000         1.50
# 1  M/M/2          0.3         0.0302         1.02
# 2  M/D/1          0.6         0.1500         1.05

# Sin etiquetas → scenario_1, scenario_2, ...
df2 = wl.compare(wl.mm1(1, 5), wl.mm1(2, 5), wl.mm1(3, 5))
```

---

## 21. Gráficas

Todos los resultados exponen `.plot()` que devuelve una figura de Matplotlib o Plotly. También se pueden llamar directamente desde `walopy.plotting`.

| Función `.plot()` | Tipo | Descripción |
|---|---|---|
| `QueueResult.plot()` | Matplotlib | Curvas Wq y Lq vs ρ con punto operativo |
| `OEEResult.plot()` | Matplotlib | Barras horizontales OEE con referencia 85% |
| `BottleneckResult.plot()` | Matplotlib | Utilización por estación, cuello de botella en rojo |
| `EOQResult.plot()` | Matplotlib | Curvas de costo de mantener, ordenar y total |
| `LineBalanceResult.plot()` | Plotly | Tiempo de ciclo vs takt por estación |
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

## 22. CLI

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
Modelo : M/M/1
λ      : 3.0   (tasa de llegada)
μ      : 5.0   (tasa de servicio por servidor)
ρ      : 0.6   (utilización por servidor)
L      : 1.5   (unidades promedio en el sistema)
Lq     : 0.9   (unidades promedio en cola)
W      : 0.5   (tiempo promedio en el sistema)
Wq     : 0.3   (tiempo promedio de espera en cola)
  P0      : 0.4
```

---

## 23. Referencia de módulos

| Módulo | Funciones y clases principales |
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

## 24. Idioma de los textos

Los mensajes de error, avisos, etiquetas de `summary()`, cabeceras de `to_frame()`, títulos de gráficas y la ayuda del CLI se muestran en el
idioma activo: **español (`"es"`, por defecto) o inglés (`"en"`)**. Si algún texto no estuviera traducido, se muestra en español: nunca falla por eso.

El idioma se elige, de mayor a menor prioridad, con:

1. `with walopy.language("en"):` — solo dentro del bloque (seguro con hilos y `asyncio`).
2. `walopy.set_language("en")` — para todo el proceso.
3. La variable de entorno `WALOPY_LANG=en` (también para el CLI). Un valor desconocido se ignora y se usa el español.

```python
import walopy as wl

wl.get_language()                  # 'es' (por defecto)
with wl.language("en"):            # cambia el idioma solo dentro del bloque
    print(wl.mm1(2, 3).summary().splitlines()[1])      # λ      : 2  (arrival rate)
    print(list(wl.mm1(2, 3).to_frame().columns)[:3])
wl.set_language("es")              # fija el idioma para todo el proceso
try:
    wl.set_language("fr")          # un idioma no admitido lanza ValueError
except ValueError as e:
    print(e)
```

Qué **no** cambia con el idioma: los nombres de funciones y argumentos, las claves de `result.params` (por ejemplo `"P0 (prob. de sistema vacío)"`;
`summary()` sí muestra su etiqueta traducida) y los nombres de las claves de datos (`"Q*"`, `"name"`, las clases `"A"`/`"B"`/`"C"`). Los números
tampoco cambian. Sí cambian, porque se crean en el idioma activo en ese momento: los nombres de las **columnas** de los `DataFrame`
(`"Artículo"` → `"Item"`), las claves de texto de las tablas internas (`result.items[0]["Producto"]`), el texto de `result.model` o `result.method`
cuando es una frase (`"Lote por lote"` → `"Lot-for-lot"`) y los nombres por defecto (`Artículo-1` → `Item-1`). Si cambias de idioma entre crear
un resultado y mostrarlo o graficarlo, `walopy` sigue encontrando sus columnas; tu propio código debe usar el nombre que la tabla tenga.

Desde la línea de comandos: `WALOPY_LANG=en python -m walopy mm1 --lam 2 --mu 3`.

---

## 25. Requisitos

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
