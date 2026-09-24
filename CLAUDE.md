# CLAUDE.md — walopy

## Overview
Python library for queuing theory, operations analysis, OEE, bottleneck analysis and KPI trees.

## Structure
- `src/walopy/queuing.py`   — M/M/1, M/M/c, M/D/1, G/G/1 (Kingman), Little's Law
- `src/walopy/operations.py` — OEE, utilization_efficiency, unit_cost
- `src/walopy/bottleneck.py` — bottleneck_analysis
- `src/walopy/kpi.py`        — KPINode, oee_kpi_tree, throughput_kpi_tree, cost_kpi_tree
- `src/walopy/plotting.py`   — all plot functions (matplotlib, lazy import)
- `src/walopy/_utils.py`     — shared validators

## Rules
- Python ≥ 3.9, `from __future__ import annotations` in every file.
- All public functions have NumPy-style docstrings and type hints.
- Internal imports are relative (`from .module import X`).
- `__version__` in `__init__.py` must match `version` in `pyproject.toml`.
- Validate only at system boundaries (`_utils.py` helpers).
- Calculation functions never import matplotlib; plotting functions do it lazily.

## Tests
```bash
pytest --cov=walopy
```

## Release checklist
- [ ] Bump version in `pyproject.toml` and `src/walopy/__init__.py`
- [ ] Add entry in `CHANGELOG.md`
- [ ] `pytest` passes
- [ ] `ruff check src/` clean
- [ ] `mypy src/walopy` clean
- [ ] Push to `main`, create GitHub release with tag `vX.Y.Z`
