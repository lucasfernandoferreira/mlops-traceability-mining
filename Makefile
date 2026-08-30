PYTHON_VERSION := 3.12
PYTHON_SYSTEM ?= python$(PYTHON_VERSION)
VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP_COMPILE := $(VENV)/bin/pip-compile
PIP_COMPILE_FLAGS := --quiet --allow-unsafe --strip-extras --generate-hashes --newline=lf
PROD_LOCK_COMMAND = $(PIP_COMPILE) $(PIP_COMPILE_FLAGS) pyproject.toml -o requirements.txt
DEV_LOCK_COMMAND = $(PIP_COMPILE) $(PIP_COMPILE_FLAGS) --extra dev pyproject.toml -o requirements-dev.txt

.PHONY: help bootstrap lock setup lint format-check typecheck test smoke smoke-dev search screen check clean

help:
	@echo "make bootstrap    Cria ou repara o ambiente Python 3.12"
	@echo "make lock         Gera requirements com versões e hashes fixados"
	@echo "make setup        Instala o ambiente de desenvolvimento"
	@echo "make lint         Executa análise estática"
	@echo "make format-check Verifica formatação"
	@echo "make typecheck    Executa verificação de tipos"
	@echo "make test         Executa testes"
	@echo "make smoke        Valida a fundação e exige worktree limpo"
	@echo "make smoke-dev    Valida a fundação permitindo alterações locais"
	@echo "make search       Executa a coleta paginada da Fase 1"
	@echo "make screen       Executa a triagem automática da Fase 2"
	@echo "make check        Executa todos os gates da Fase 0"

bootstrap:
	@command -v $(PYTHON_SYSTEM) >/dev/null 2>&1 || { \
		echo "Erro: $(PYTHON_SYSTEM) não foi encontrado no PATH."; \
		echo "Instale-o com: uv python install $(PYTHON_VERSION)"; \
		exit 1; \
	}
	@$(PYTHON_SYSTEM) -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))' || { \
		echo "Erro: $(PYTHON_SYSTEM) precisa apontar para Python $(PYTHON_VERSION)."; \
		exit 1; \
	}
	@if ! test -x $(PYTHON) \
		|| ! $(PYTHON) -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))' >/dev/null 2>&1 \
		|| ! $(PYTHON) -m pip --version >/dev/null 2>&1; then \
		echo "Criando ambiente virtual Python $(PYTHON_VERSION) em $(VENV)..."; \
		$(PYTHON_SYSTEM) -m venv --clear $(VENV); \
	fi
lock: bootstrap
	$(PYTHON) -m pip install --require-hashes -r requirements-dev.txt
	CUSTOM_COMPILE_COMMAND='make lock' $(PROD_LOCK_COMMAND)
	CUSTOM_COMPILE_COMMAND='make lock' $(DEV_LOCK_COMMAND)

setup: bootstrap
	$(PYTHON) -m pip install --require-hashes -r requirements-dev.txt
	$(PYTHON) -m pip install --no-build-isolation --no-deps --editable .

lint:
	$(PYTHON) -m ruff check .

format-check:
	$(PYTHON) -m ruff format --check .

typecheck:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest

smoke:
	$(PYTHON) scripts/00_smoke.py

smoke-dev:
	$(PYTHON) scripts/00_smoke.py --allow-dirty

search:
	@set -a; \
	if test -f .env; then . ./.env; fi; \
	if test -f .env.local; then . ./.env.local; fi; \
	set +a; \
	$(PYTHON) scripts/01_search_candidates.py

screen:
	$(PYTHON) scripts/02_screen_sample.py

check: lint format-check typecheck test smoke

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov tmp
	rm -f .coverage coverage.xml
