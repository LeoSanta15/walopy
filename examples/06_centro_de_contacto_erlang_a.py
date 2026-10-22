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

# Dos tipos de cliente: el 25 % son VIP (paciencia media de 10 min) y pasan delante en la fila; el resto (3 min de paciencia) espera su turno.
vip, estandar = 0.5, 1.5                       # llamadas por minuto de cada clase
print("\nagentes  abandono VIP  abandono estándar  atendidas en ≤ 20 s (VIP / estándar)")
for c in range(9, 13):
    r = wl.erlang_a_priority(vip, estandar, servicio, 0.1, abandono, c)
    alto, bajo = wl.erlang_a_priority_service_level(vip, estandar, servicio, 0.1, abandono, c, t=espera_meta)
    a, b = r.classes
    print(f"{c:7d}  {a['p_abandon']:12.1%}  {b['p_abandon']:16.1%}  {alto:10.1%} / {bajo:.1%}")

# Tres niveles de cliente (platino, oro, estándar), cada uno con su paciencia: K clases con prioridad.
lam3, theta3 = [0.2, 0.5, 1.3], [0.05, 0.1, abandono]
print("\nagentes  abandono platino / oro / estándar   atendidas en ≤ 20 s (platino / oro / estándar)")
for c in range(9, 12):
    r3 = wl.erlang_a_classes(lam3, servicio, theta3, c)
    n3 = wl.erlang_a_classes_service_level(lam3, servicio, theta3, c, t=espera_meta)
    ab = " / ".join(f"{x['p_abandon']:.1%}" for x in r3.classes)
    print(f"{c:7d}  {ab:>31}   {n3[0]:.1%} / {n3[1]:.1%} / {n3[2]:.1%}")

# Agentes senior para los VIP: se atiende a los VIP en 2.5 min (μ = 0.4) y a los estándar en 4 min (μ = 0.25).
r_rapido = wl.erlang_a_classes([vip, estandar], mu=[0.4, servicio], theta=[0.1, abandono], c=10)
r_igual = wl.erlang_a_classes([vip, estandar], mu=servicio, theta=[0.1, abandono], c=10)
print("\nCon 10 agentes, abandono VIP / estándar:")
print(f"  mismo tiempo de servicio (4 min)       : {r_igual.classes[0]['p_abandon']:.1%} / {r_igual.classes[1]['p_abandon']:.1%}")
print(f"  VIP en 2.5 min, estándar en 4 min       : {r_rapido.classes[0]['p_abandon']:.1%} / {r_rapido.classes[1]['p_abandon']:.1%}")

# Centro grande (80 agentes) con tiempos de servicio distintos: el modelo exacto ya no llega (c ≥ 40), se simula con intervalos de confianza.
sim = wl.monte_carlo_erlang_a([5.5, 16.5], mu=[0.4, servicio], theta=[0.1, abandono], c=80,
                              n_customers=100_000, n_replications=6, t=espera_meta, seed=2026)
vip_s, est_s = sim.classes
print(f"\n80 agentes (simulación, IC 95 %): abandono VIP {vip_s['p_abandon']:.2%} ± {vip_s['p_abandon_halfwidth']:.2%}, "
      f"estándar {est_s['p_abandon']:.2%} ± {est_s['p_abandon_halfwidth']:.2%}")
print(f"  atendidas en ≤ 20 s: VIP {vip_s['service_level']:.1%}, estándar {est_s['service_level']:.1%}")
