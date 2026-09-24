# Inicio rápido

## Modelos de colas

```python
import walopy as wl

# M/M/1
r = wl.mm1(lam=3.0, mu=5.0)
print(r)

# G/G/1 — ecuación de Kingman
r = wl.kingman(lam=3.0, mu=5.0, ca2=1.2, cs2=0.8)
print(r)

# Ley de Little
L = wl.littles_law(lam=5.0, W=0.4)
```

## OEE

```python
r = wl.oee(availability=0.90, performance=0.80, quality=0.95)
print(r)
fig = r.plot()
```

## Análisis de cuellos de botella

```python
r = wl.bottleneck_analysis(
    station_names=["Corte", "Soldadura", "Pintura"],
    capacities=[120, 80, 100],
    demand_rate=70,
)
print(r)
fig = r.plot()
```

## Árbol de KPIs

```python
tree = wl.oee_kpi_tree(availability=0.9, performance=0.8, quality=0.95)
print(tree)
df = tree.to_frame()
fig = tree.plot()
```

## Costo unitario

```python
r = wl.unit_cost(fixed_cost=10_000, variable_cost_per_unit=8, units_produced=500)
print(r)
```
