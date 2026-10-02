"""Programación: secuencia de trabajos en una línea de 3 máquinas (flow-shop) con NEH."""
import walopy as wl

tiempos = [  # filas = pedidos, columnas = máquinas (corte, soldadura, pintura), en horas
    [5, 9, 8],
    [9, 3, 10],
    [9, 4, 5],
    [4, 8, 8],
    [7, 6, 3],
]
nombres = ["P1", "P2", "P3", "P4", "P5"]

r = wl.neh_flowshop(tiempos, names=nombres)
print(r)
print(r.to_frame())

print(f"\nMakespan NEH = {r.makespan:g} h")
