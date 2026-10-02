"""Proyectos: ruta crítica (CPM) y probabilidad de cumplir un plazo (PERT)."""
import walopy as wl

actividades = [
    {"name": "Diseño", "optimistic": 3, "most_likely": 5, "pessimistic": 9, "predecessors": []},
    {"name": "Compras", "optimistic": 2, "most_likely": 4, "pessimistic": 8, "predecessors": ["Diseño"]},
    {"name": "Montaje", "optimistic": 4, "most_likely": 6, "pessimistic": 10, "predecessors": ["Compras"]},
    {"name": "Software", "optimistic": 5, "most_likely": 7, "pessimistic": 12, "predecessors": ["Diseño"]},
    {"name": "Pruebas", "optimistic": 2, "most_likely": 3, "pessimistic": 6, "predecessors": ["Montaje", "Software"]},
]

pert = wl.pert(actividades)
print(pert)
print(pert.to_frame()[["Activity", "Duration", "ES", "EF", "TF", "Critical"]])
for plazo in (20, 22, 24):
    print(f"P(terminar en {plazo} semanas) = {pert.probability(plazo):.1%}")

# Con duraciones fijas (valores esperados) el mismo proyecto como CPM:
cpm = wl.cpm([
    {"name": a["name"], "duration": (a["optimistic"] + 4 * a["most_likely"] + a["pessimistic"]) / 6,
     "predecessors": a["predecessors"]}
    for a in actividades
])
print("Ruta crítica CPM:", " → ".join(cpm.critical_path))
