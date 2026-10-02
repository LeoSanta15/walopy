# Rendimiento

Línea base de las operaciones más costosas, medida con `benchmarks/bench_core.py` (semillas fijas;
mediana de 3 ejecuciones).

| Operación | Mediana de 3 ejecuciones (s) |
|---|---|
| neh_flowshop n=100, m=10 | 0.031 |
| neh_flowshop n=200, m=10 | 0.119 |
| wagner_whitin n=1000 | 0.063 |
| wagner_whitin n=2000 | 0.228 |
| mmc c=1000 (ρ=0.95) | 0.000 |
| monte_carlo_gg1 n=1e6 | 0.555 |
| abc_xyz n=2000 | 0.011 |
| cpm n=1000 | 0.007 |
| weibull_analysis n=5000 (MLE) | 0.140 |

Entorno de referencia: Python 3.11.15, x86_64, walopy 0.2.8.

## Complejidad

| Algoritmo | Complejidad | Verificación |
|---|---|---|
| `wagner_whitin` | O(n²) | `tests/test_complejidad.py` (equivalente a fuerza bruta; n=1000 en < 2 s) |
| `neh_flowshop` | O(n²·m) (aceleración de Taillard) | `tests/test_complejidad.py` (equivalente a la versión directa; n=200, m=10 en < 2 s) |
| `mmc` | O(c) (recurrencia de Erlang-B) | `tests/test_mmc_estable.py` (contraste con balance de nacimiento-muerte hasta c = 1000) |

## Cotas de tamaño

Para evitar cálculos de duración prácticamente infinita, algunos parámetros de tamaño tienen un máximo:
número de servidores (`c`, 10⁶), capacidad del sistema y puntos de las tablas (`K`, `n_max`, `n_points`, 10⁶) y
clientes simulados (`n_customers`, 10⁷). Superarlos lanza `ValueError`.

## Reproducir

```bash
python benchmarks/bench_core.py             # texto
python benchmarks/bench_core.py --markdown  # tabla para esta página
```
