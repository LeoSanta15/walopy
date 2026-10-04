# walopy — comandos de verificación (los mismos que ejecuta el CI).
# `make check-fast` para iterar; `make check` antes de abrir un PR; `make release-check TAG=vX.Y.Z` antes de crear un tag.
PYTHON ?= python
MINIMO_COBERTURA_MODULO ?= 70

.PHONY: help install test cov lint types build docs examples obsoletas regresion mutaciones inventario-i18n notas-release check-fast check release-check clean

help:
	@echo "Objetivos: install test cov lint types build docs examples obsoletas regresion mutaciones inventario-i18n notas-release VERSION=X.Y.Z check-fast check release-check TAG=vX.Y.Z clean"

install:
	$(PYTHON) -m pip install -e ".[dev,release,docs]"

test:
	$(PYTHON) -m pytest

cov:
	$(PYTHON) -m pytest --cov=walopy --cov-report=term-missing --cov-report=json
	$(PYTHON) scripts/comprobar_cobertura_modulos.py $(MINIMO_COBERTURA_MODULO)

lint:
	$(PYTHON) -m ruff check src/ tests/ benchmarks/ scripts/ examples/

types:
	$(PYTHON) -m mypy src/walopy --ignore-missing-imports

build:
	rm -rf dist build
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*

docs:
	$(PYTHON) -m sphinx -b html -W docs/source docs/build

examples:
	@for f in examples/*.py; do echo "== $$f"; MPLBACKEND=Agg PYTHONWARNINGS=error $(PYTHON) $$f > /dev/null || exit 1; done

obsoletas:
	@if grep -rn "PLACEHOLDER\|TU_USUARIO\|cost_kpi_tree" . --include="*.py" --include="*.md" --include="*.toml" --include="*.yml" --exclude=CLAUDE.md --exclude=AGENTS.md --exclude-dir=.git --exclude-dir=.github --exclude-dir=auditoria --exclude-dir=referencia --exclude-dir=retrospectiva --exclude-dir=.claude --exclude-dir=build --exclude-dir=dist --exclude-dir=.venv; then echo "Se encontraron referencias obsoletas"; exit 1; else echo "Sin referencias obsoletas"; fi

# Los tests de regresión deben FALLAR en el tag anterior (necesita los tags de git).
regresion:
	@if git describe --tags --abbrev=0 > /dev/null 2>&1; then $(PYTHON) scripts/verificar_regresion.py --manifiesto tests/regresiones.json; else echo "OMITIDO: no hay tags de git (git fetch --tags)"; fi

# Internacionalización: falla si quedan textos visibles escritos directamente en src/ (deben ir en _catalogo_es.py y usarse con _t("clave")).
inventario-i18n:
	$(PYTHON) scripts/inventario_i18n.py

# Mutación de una línea: cada test de regresión debe fallar si el bug vuelve.
mutaciones:
	$(PYTHON) scripts/verificar_mutaciones.py

check-fast: lint types test

check: lint types cov build docs examples obsoletas regresion

# Cuerpo del release a partir del CHANGELOG: make notas-release VERSION=0.3.0
notas-release:
	@test -n "$(VERSION)" || { echo "Uso: make notas-release VERSION=X.Y.Z"; exit 2; }
	@$(PYTHON) scripts/notas_release.py $(VERSION)

# El wheel construido debe tener la versión del tag: make release-check TAG=v0.3.0
release-check:
	@test -n "$(TAG)" || { echo "Uso: make release-check TAG=vX.Y.Z"; exit 2; }
	rm -rf dist build
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*
	$(PYTHON) scripts/comprobar_version_release.py $(TAG) dist

clean:
	rm -rf dist build docs/build .coverage coverage.json .pytest_cache .mypy_cache .ruff_cache
