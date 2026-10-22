"""Centro de contacto: dotación con clientes que abandonan (Erlang A).

Llegan 2 llamadas por minuto, cada una dura 4 minutos de media (μ = 0.25 por minuto) y quien espera abandona
con una paciencia media de 3 minutos (θ = 1/3). Con M/M/c no se puede ni calcular con 8 agentes (λ = c·μ:
cola inestable); con Erlang A sí, porque los abandonos compensan el exceso de carga.
"""
import walopy as wl

llegadas, servicio, abandono = 2.0, 0.25, 1 / 3
espera_meta = 20 / 60                         # 20 segundos, en minutos

print("agentes  abandono  espera  atendidas en ≤ 20 s")
for c in range(8, 13):
    r = wl.erlang_a(llegadas, servicio, abandono, c)
    nivel = wl.erlang_a_service_level(llegadas, servicio, abandono, c, t=espera_meta)
    print(f"{c:7d}  {r.params['P(abandono)']:8.1%}  {r.params['P(esperar)']:6.1%}  {nivel:8.1%}")

solo_abandono = wl.erlang_a_servers(llegadas, servicio, abandono, max_abandon=0.03)
solo_nivel = wl.erlang_a_servers(llegadas, servicio, abandono, min_service_level=0.8, t=espera_meta)
ambos = wl.erlang_a_servers(llegadas, servicio, abandono, max_abandon=0.03, min_service_level=0.8, t=espera_meta)
print(f"\nAbandono ≤ 3 %: {solo_abandono.servers} agentes; 80 % en ≤ 20 s: {solo_nivel.servers} agentes; ambos: {ambos.servers}")
print(f"Con {ambos.servers} agentes la ocupación es {ambos.rho:.1%} y quien se atiende espera {ambos.params['Wq atendidos'] * 60:.0f} s de media.")
