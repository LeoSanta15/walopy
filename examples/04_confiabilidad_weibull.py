"""Confiabilidad: ajuste Weibull de tiempos de falla y sistema redundante."""
import walopy as wl

horas_hasta_falla = [212, 340, 415, 520, 633, 710, 842, 960, 1105, 1290]

w = wl.weibull_analysis(horas_hasta_falla)
print(w)
tipo = "desgaste" if w.shape > 1 else "fallas aleatorias o mortalidad infantil"
print(f"β = {w.shape:.2f} → {tipo}")
print(f"Confiabilidad a 500 h: {w.R(500):.1%}   vida B10: {w.b10:.0f} h")

# Dos bombas en paralelo con la tasa de falla implícita de la Weibull (aprox. exponencial)
lam = 1 / w.mttf
sistema = wl.parallel_system([lam, lam], t=500)
print(f"R(500 h) con una bomba de respaldo: {sistema.R_t:.1%}")
