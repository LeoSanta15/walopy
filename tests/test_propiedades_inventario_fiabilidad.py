"""Fiabilidad, ajuste de colas, políticas de inventario, redes y costos contra fórmulas y enumeraciones independientes.

Escenarios aleatorios con semilla fija (``N`` por familia). Hallaron W-28 (``solve_servers`` / ``optimize_servers``, ver ``test_servidores_minimos.py``).
"""
from __future__ import annotations

import math
import random
import statistics

import numpy as np

import walopy as wl

N = 100
SEMILLA = 20261009
ND = statistics.NormalDist()


def _cerca(a: float, b: float, rel: float = 1e-7) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


def _escenarios(familia: str):
    r = random.Random(f"{SEMILLA}-{familia}")
    return [random.Random(r.random()) for _ in range(N)]


def test_weibull_mle_cumple_la_ecuacion_de_verosimilitud():
    for r in _escenarios("weibull"):
        n, beta0, eta0 = r.randint(5, 40), r.uniform(0.6, 4), r.uniform(10, 1000)
        t = [eta0 * (-math.log(1 - r.random())) ** (1 / beta0) for _ in range(n)]
        w = wl.weibull_analysis(t)
        b, e = w.shape, w.scale
        score = sum(x**b * math.log(x) for x in t) / sum(x**b for x in t) - 1 / b - sum(math.log(x) for x in t) / n
        assert abs(score) < 1e-6, t
        assert _cerca(e, (sum(x**b for x in t) / n) ** (1 / b), 1e-6), t
        assert _cerca(w.mttf, e * math.gamma(1 + 1 / b), 1e-9) and _cerca(w.b10, e * (-math.log(0.9)) ** (1 / b), 1e-9), t
        tt = r.uniform(1, 2 * e)
        assert _cerca(w.R(tt) + w.F(tt), 1.0, 1e-12) and _cerca(w.R(tt), math.exp(-((tt / e) ** b)), 1e-9), t
        rry = wl.weibull_analysis(t, method="RRY")
        assert rry.shape > 0 and rry.scale > 0 and math.isfinite(rry.shape) and math.isfinite(rry.scale), t


def test_disponibilidad_y_confiabilidad_de_un_componente():
    for r in _escenarios("mtbf"):
        lam, mttr, t = r.uniform(1e-4, 1), r.uniform(0.01, 50), r.uniform(0.1, 100)
        res = wl.mtbf_analysis(lam, mttr=mttr, t=t)
        assert _cerca(res.availability, (1 / lam) / (1 / lam + mttr), 1e-9), (lam, mttr)
        assert _cerca(res.R_t, math.exp(-lam * t), 1e-9), (lam, t)


def test_ajuste_de_colas_coincide_con_los_estadisticos_muestrales():
    for r in _escenarios("fit"):
        ia = np.array([r.expovariate(r.uniform(0.5, 3)) + 1e-3 for _ in range(r.randint(5, 60))])
        sv = np.array([r.uniform(0.1, 2) for _ in range(r.randint(5, 60))])
        f = wl.fit_from_data(ia, sv)
        assert _cerca(f.lam, 1 / ia.mean(), 1e-9) and _cerca(f.mu, 1 / sv.mean(), 1e-9)
        assert any(_cerca(f.ca2, ia.var(ddof=d) / ia.mean() ** 2) for d in (0, 1))
        assert any(_cerca(f.cs2, sv.var(ddof=d) / sv.mean() ** 2) for d in (0, 1))
        marcas = np.cumsum(ia)
        assert _cerca(wl.fit_from_data(arrival_timestamps=marcas).lam, 1 / np.diff(marcas).mean(), 1e-9)


def test_politicas_de_inventario_siguen_sus_formulas():
    for r in _escenarios("politicas"):
        D, K, h, L = r.uniform(5, 500), r.uniform(5, 300), r.uniform(0.05, 5), r.uniform(0.1, 10)
        sd, sl, nivel, R = r.uniform(0, 0.4) * D, r.uniform(0, 0.5) * L, r.uniform(0.5, 0.995), r.uniform(0.2, 5)
        z = ND.inv_cdf(nivel)
        sdlt = math.sqrt(L * sd**2 + D**2 * sl**2)
        Q = math.sqrt(2 * D * K / h)
        rop = wl.reorder_point(D, L, demand_std=sd, lead_time_std=sl, service_level=nivel)
        assert _cerca(rop.safety_stock, z * sdlt, 1e-9) and _cerca(rop.reorder_point, D * L + z * sdlt, 1e-9)
        rq = wl.rq_policy(D, K, h, L, demand_std=sd, lead_time_std=sl, service_level=nivel)
        assert _cerca(rq.order_qty, Q) and _cerca(rq.reorder_point, D * L + z * sdlt, 1e-9)
        assert _cerca(rq.avg_inventory, Q / 2 + z * sdlt, 1e-9)
        assert _cerca(rq.total_cost, K * D / Q + h * (Q / 2 + z * sdlt), 1e-9)
        ss = z * math.sqrt((R + L) * sd**2 + D**2 * sl**2)
        rs = wl.rs_policy(D, K, h, L, R, demand_std=sd, lead_time_std=sl, service_level=nivel)
        assert _cerca(rs.safety_stock, ss, 1e-9) and _cerca(rs.order_up_to, D * (R + L) + ss, 1e-9)
        assert _cerca(rs.avg_inventory, D * R / 2 + ss, 1e-9) and _cerca(rs.total_cost, K / R + h * (D * R / 2 + ss), 1e-9)


def test_eoq_multiple_y_ebq_siguen_sus_formulas():
    for r in _escenarios("eoq_multi"):
        m = r.randint(1, 5)
        D = [r.uniform(5, 1000) for _ in range(m)]
        K = [r.uniform(5, 200) for _ in range(m)]
        h = [r.uniform(0.05, 5) for _ in range(m)]
        q = [math.sqrt(2 * d * k / x) for d, k, x in zip(D, K, h)]
        em = wl.eoq_multi(D, K, h)
        assert all(_cerca(it["EOQ"], x) for it, x in zip(em.items, q))
        assert _cerca(em.total_cost, sum(d / x * k + y * x / 2 for d, k, y, x in zip(D, K, h, q)))
        P = D[0] * r.uniform(1.2, 6)
        qb = math.sqrt(2 * D[0] * K[0] / (h[0] * (1 - D[0] / P)))
        eb = wl.ebq(D[0], K[0], h[0], P)
        assert _cerca(eb.ebq, qb) and _cerca(eb.total_cost, K[0] * D[0] / qb + h[0] * qb * (1 - D[0] / P) / 2)


def test_eoq_con_presupuesto_es_factible_y_localmente_optimo():
    for r in _escenarios("eoq_restringido"):
        m = r.randint(1, 5)
        D = [r.uniform(5, 1000) for _ in range(m)]
        K = [r.uniform(5, 200) for _ in range(m)]
        h = [r.uniform(0.05, 5) for _ in range(m)]
        c = [r.uniform(1, 20) for _ in range(m)]
        q0 = [math.sqrt(2 * d * k / x) for d, k, x in zip(D, K, h)]

        def costo(q, D=D, K=K, h=h):
            return sum(d / x * k + y * x / 2 for d, k, y, x in zip(D, K, h, q))

        presupuesto = sum(a * x / 2 for a, x in zip(c, q0)) * r.uniform(0.2, 1.3)
        res = wl.eoq_multi_constrained(D, K, h, budget=presupuesto, budget_unit_costs=c)
        q = [it["Q*"] for it in res.items]
        assert sum(a * x / 2 for a, x in zip(c, q)) <= presupuesto * (1 + 1e-6)
        assert _cerca(res.total_cost, costo(q), 1e-6) and res.total_cost >= costo(q0) - 1e-7
        for _ in range(40):
            cand = [x * (1 + r.uniform(-0.1, 0.1)) for x in q]
            exceso = sum(a * x / 2 for a, x in zip(c, cand)) / presupuesto
            if exceso > 1:
                cand = [x / exceso for x in cand]
            assert costo(cand) >= costo(q) - 1e-6 * max(1, costo(q))


def test_descuentos_por_cantidad_dan_el_minimo_de_las_candidatas():
    for r in _escenarios("descuentos"):
        tramos = r.randint(1, 4)
        minimos = [0] + (sorted(r.sample(range(1, 3000), tramos - 1)) if tramos > 1 else [])
        precios = sorted((r.uniform(5, 20) for _ in range(tramos)), reverse=True)
        cortes = list(zip(minimos, precios))
        tasa, D, K = r.uniform(0.05, 0.4), r.uniform(100, 5000), r.uniform(10, 300)

        def costo(q, cortes=cortes, tasa=tasa, D=D, K=K):
            p = [pr for mq, pr in cortes if q >= mq][-1]
            return D * p + D / q * K + tasa * p * q / 2

        candidatas = [max(math.sqrt(2 * D * K / (tasa * pr)), mq, 1e-9) for mq, pr in cortes] + [max(mq, 1e-9) for mq, _ in cortes]
        res = wl.eoq_quantity_discount(D, K, tasa, cortes)
        assert _cerca(res.total_cost, min(costo(q) for q in candidatas)), (D, K, tasa, cortes)


def test_curvas_de_intercambio():
    for r in _escenarios("intercambio"):
        m = r.randint(1, 5)
        D = [r.uniform(5, 1000) for _ in range(m)]
        K = [r.uniform(5, 200) for _ in range(m)]
        h = [r.uniform(0.05, 5) for _ in range(m)]
        v = [r.uniform(1, 20) for _ in range(m)]
        q = [math.sqrt(2 * d * k / x) for d, k, x in zip(D, K, h)]
        n_eoq, i_eoq = sum(d / x for d, x in zip(D, q)), sum(a * x / 2 for a, x in zip(v, q))
        meta = n_eoq * r.uniform(0.3, 3)
        items = [{"name": f"I{i}", "demand": D[i], "ordering_cost": K[i], "holding_cost": h[i], "unit_value": v[i]} for i in range(m)]
        ex = wl.exchange_curve(items, target_orders=meta)
        assert _cerca(ex.n_orders_optimal, meta) and _cerca(ex.investment_optimal, n_eoq * i_eoq / meta, 1e-6)
        assert all(_cerca(p["N"] * p["I"], n_eoq * i_eoq, 1e-4) for p in ex.curve_points)
        sitems = [
            {"name": f"I{i}", "demand_rate": D[i], "demand_std": r.uniform(0.5, 30), "lead_time": r.uniform(0.2, 6),
             "lead_time_std": r.uniform(0, 1), "unit_value": v[i]}
            for i in range(m)
        ]
        suma = sum(
            math.sqrt(it["lead_time"] * it["demand_std"] ** 2 + it["demand_rate"] ** 2 * it["lead_time_std"] ** 2) * it["unit_value"] for it in sitems
        )
        nivel = r.uniform(0.55, 0.995)
        sc = wl.safety_stock_curve(sitems, target_service_level=nivel)
        assert _cerca(sc.z, ND.inv_cdf(nivel), 1e-9) and _cerca(sc.ss_investment, ND.inv_cdf(nivel) * suma, 1e-6)


def test_red_de_jackson_cumple_trafico_y_little():
    for r in _escenarios("jackson"):
        ns = r.randint(1, 4)
        gamma = [r.uniform(0.1, 1.0) for _ in range(ns)]
        P = [[r.random() for _ in range(ns)] for _ in range(ns)]
        P = [[x / (sum(fila) + r.uniform(0.3, 1.5)) for x in fila] for fila in P]
        lam = np.linalg.solve(np.eye(ns) - np.array(P).T, np.array(gamma))
        mu = [x * r.uniform(1.2, 3) + 0.1 for x in lam]
        res = wl.jackson_network([f"S{i}" for i in range(ns)], mu, gamma, P)
        assert all(_cerca(s.lam_total, x, 1e-7) for s, x in zip(res.stations, lam))
        assert all(_cerca(s.L, (x / m) / (1 - x / m), 1e-6) for s, x, m in zip(res.stations, lam, mu))
        assert _cerca(res.L_system, sum(s.L for s in res.stations)) and _cerca(res.W_system, res.L_system / sum(gamma))


def test_equilibrio_multiproducto_abc_y_cuello_de_botella():
    for r in _escenarios("varios"):
        m = r.randint(1, 5)
        precios = [r.uniform(5, 50) for _ in range(m)]
        variables = [p * r.uniform(0.1, 0.8) for p in precios]
        mezcla = [r.random() + 0.1 for _ in range(m)]
        mezcla = [x / sum(mezcla) for x in mezcla]
        F = r.uniform(100, 50000)
        bm = wl.break_even_multi(F, precios, variables, mezcla)
        cm = sum(x * (p - v) for x, p, v in zip(mezcla, precios, variables))
        assert _cerca(bm.weighted_avg_cm, cm) and _cerca(bm.bep_units_total, F / cm)
        assert _cerca(bm.bep_revenue_total, F / cm * sum(x * p for x, p in zip(mezcla, precios)))
        arts = [{"name": f"P{i}", "demand": r.uniform(1, 500), "unit_value": r.uniform(0.5, 50)} for i in range(r.randint(2, 15))]
        items = sorted(wl.abc_analysis(arts).items, key=lambda x: x["rank"])
        valores = [x["annual_value"] for x in items]
        assert valores == sorted(valores, reverse=True) and _cerca(items[-1]["cumulative_pct"], 1.0, 1e-9)
        previo, clases = 0.0, []
        for v in valores:
            previo_pct = previo / sum(valores)
            clases.append("A" if previo_pct < 0.8 else ("B" if previo_pct < 0.95 else "C"))
            previo += v
        assert [x["class"] for x in items] == clases
        k = r.randint(1, 6)
        cap, demanda, fr = [r.uniform(1, 20) for _ in range(k)], r.uniform(0.5, 25), [r.uniform(0.2, 1) for _ in range(k)]
        bn = wl.bottleneck_analysis([f"S{i}" for i in range(k)], cap, demanda, routing_fractions=fr)
        util = [demanda * f / c for f, c in zip(fr, cap)]
        assert all(_cerca(s.utilization, u) for s, u in zip(bn.stations, util))
        assert bn.bottleneck in (None, f"S{util.index(max(util))}")


def test_costo_unitario_y_utilizacion():
    for r in _escenarios("costos"):
        F, v, q, oh = r.uniform(0, 1e5), r.uniform(0.1, 50), r.uniform(1, 1e4), r.uniform(0, 0.5)
        uc = wl.unit_cost(F, v, q, overhead_rate=oh)
        assert _cerca(uc.total_cost, F + v * q * (1 + oh), 1e-9) and _cerca(uc.unit_cost, (F + v * q * (1 + oh)) / q, 1e-9)
        real = r.uniform(1, 100)
        capacidad, estandar = real * r.uniform(1, 3), real * r.uniform(0.5, 1.5)
        ue = wl.utilization_efficiency(real, capacidad, standard_output=estandar)
        assert _cerca(ue.utilization, real / capacidad) and _cerca(ue.efficiency, real / estandar)
