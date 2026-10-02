"""Colas: dimensionar servidores para un centro de atención.

Una oficina recibe 40 clientes por hora y cada ventanilla atiende 12 por hora. ¿Cuántas ventanillas
hacen falta para que la espera media en cola sea menor a 2 minutos (0.0333 h)?
"""
import walopy as wl

llegadas, servicio = 40.0, 12.0

for c in range(4, 8):
    r = wl.mmc(llegadas, servicio, c)
    print(f"c={c}: ρ={r.rho:.2f}  Wq={r.Wq * 60:.1f} min  Lq={r.Lq:.2f}")

res = wl.solve_servers("Wq", 2 / 60, lam=llegadas, mu=servicio)
print(f"\nMínimo de ventanillas para Wq ≤ 2 min: {int(res.value)}")

costo = wl.optimize_servers(llegadas, servicio, cost_per_server=20.0, cost_per_wait=60.0)
print(f"Dotación de costo mínimo: {costo.optimal_servers} (costo {costo.min_cost:.1f} por hora)")
