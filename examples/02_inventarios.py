"""Inventarios: EOQ, clasificación ABC-XYZ y plan MRP."""
import walopy as wl

# 1. Cantidad económica de pedido
eoq = wl.eoq(demand_rate=12_000, ordering_cost=150.0, holding_cost=3.0)
print(f"EOQ = {eoq.eoq:.0f} unidades, {eoq.order_frequency:.1f} pedidos por periodo")

# 2. Clasificación ABC-XYZ de un catálogo pequeño
catalogo = [
    {"name": "Tornillo", "demand": 9000, "unit_value": 0.10, "cv": 0.2},
    {"name": "Motor", "demand": 120, "unit_value": 450.0, "cv": 0.4},
    {"name": "Cable", "demand": 3000, "unit_value": 1.20, "cv": 0.9},
    {"name": "Sensor", "demand": 60, "unit_value": 80.0, "cv": 1.6},
    {"name": "Etiqueta", "demand": 20000, "unit_value": 0.01, "cv": 0.3},
]
clasificacion = wl.abc_xyz(catalogo)
print(clasificacion.matrix_frame())
for e in clasificacion.items:
    print(f"  {e['name']:9s} {e['combined_class']}")

# 3. MRP de un nivel para el Motor
plan = wl.mrp(
    gross_requirements=[0, 30, 0, 45, 60, 20],
    initial_on_hand=50,
    lead_time=1,
    lot_size=40,
    safety_stock=10,
    item_name="Motor",
)
print(plan)
