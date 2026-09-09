PYTHON_VERSION := 3.12
PYTHON_SYSTEM ?= python$(PYTHON_VERSION)
VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP_COMPILE := $(VENV)/bin/pip-compile
PIP_COMPILE_FLAGS := --quiet --allow-unsafe --strip-extras --generate-hashes --newline=lf
PROD_LOCK_COMMAND = $(PIP_COMPILE) $(PIP_COMPILE_FLAGS) pyproject.toml -o requirements.txt
DEV_LOCK_COMMAND = $(PIP_COMPILE) $(PIP_COMPILE_FLAGS) --extra dev pyproject.toml -o requirements-dev.txt

.PHONY: help bootstrap lock setup lint format-check typecheck test smoke smoke-dev search screen screen-retry-errors preserve-runs pipeline check clean

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
	@echo "make screen-retry-errors Reutiliza a última Fase 2 e processa apenas erros"
	@echo "make preserve-runs Preserva artefatos legados em diretórios por run_id"
	@echo "make pipeline     Executa check, search e screen nesta ordem"
	@echo "make check        Executa todos os gates da Fase 0"
	@echo "make test-evidence Executa contratos e fixtures de verificação offline"
	@echo "make test-counterexamples Executa mutações sintéticas com motivo de falha esperado"
	@echo "make import-reviews Preserva e valida revisões de um índice explícito"
	@echo "make verify-study Confere Git, métricas e estatísticas de um índice explícito"

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
	@set -a; \
	if test -f .env; then . ./.env; fi; \
	if test -f .env.local; then . ./.env.local; fi; \
	set +a; \
	$(PYTHON) scripts/02_screen_sample.py

screen-retry-errors:
	@set -a; \
	if test -f .env; then . ./.env; fi; \
	if test -f .env.local; then . ./.env.local; fi; \
	set +a; \
	SCREEN_RETRY_ERRORS_ONLY=1 $(PYTHON) scripts/02_screen_sample.py

preserve-runs:
	$(PYTHON) scripts/preserve_current_run.py

pipeline:
	@$(MAKE) --no-print-directory check
	@$(MAKE) --no-print-directory search
	@$(MAKE) --no-print-directory screen

check: lint format-check typecheck test smoke

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov tmp
	rm -f .coverage coverage.xml

# Study stages require explicit inputs; ALLOW_DIRTY=1 only produces development runs.
DEV_FLAG = $(if $(filter 1,$(ALLOW_DIRTY)),--allow-dirty,)
.PHONY: clone mine metrics study-index validate-taxonomy collect-pr-map qualitative report finalize-study
clone:
	@test -n "$(REPO)" || { echo "REPO is required"; exit 2; }
	$(PYTHON) scripts/03_clone_repos.py --repository "$(REPO)" $(DEV_FLAG)
mine:
	@test -n "$(REPO)" -a -n "$(SOURCE_RUN_ID)" || { echo "REPO and SOURCE_RUN_ID are required"; exit 2; }
	$(PYTHON) scripts/04_mine_commits.py --repository "$(REPO)" --source-run-id "$(SOURCE_RUN_ID)" $(DEV_FLAG)
metrics:
	@test -n "$(REPO)" -a -n "$(SOURCE_RUN_ID)" || { echo "REPO and SOURCE_RUN_ID are required"; exit 2; }
	$(PYTHON) scripts/05_compute_metrics.py --repository "$(REPO)" --source-run-id "$(SOURCE_RUN_ID)" $(DEV_FLAG)
study-index:
	@test -n "$(RUNS_FILE)" || { echo "RUNS_FILE is required"; exit 2; }
	$(PYTHON) scripts/build_study_index.py --runs-file "$(RUNS_FILE)" $(DEV_FLAG)
validate-taxonomy:
	@test -n "$(SAMPLE)" -a -n "$(INVENTORY)" -a -n "$(STUDY_INDEX)" || { echo "SAMPLE, INVENTORY and STUDY_INDEX are required"; exit 2; }
	$(PYTHON) scripts/06_validate_taxonomy.py --sample "$(SAMPLE)" --inventory "$(INVENTORY)" --study-index "$(STUDY_INDEX)" $(DEV_FLAG)
qualitative:
	@test -n "$(STUDY_INDEX)" || { echo "STUDY_INDEX is required"; exit 2; }
	$(PYTHON) scripts/07_select_qualitative.py --study-index "$(STUDY_INDEX)" $(if $(PR_MAP),--pr-map "$(PR_MAP)",) $(DEV_FLAG)
collect-pr-map:
	@test -n "$(STUDY_INDEX)" -a -n "$(OUTPUT_DIR)" || { echo "STUDY_INDEX and OUTPUT_DIR are required"; exit 2; }
	@set -a; \
	if test -f .env; then . ./.env; fi; \
	if test -f .env.local; then . ./.env.local; fi; \
	set +a; \
	$(PYTHON) scripts/collect_pr_map.py --study-index "$(STUDY_INDEX)" --output-dir "$(OUTPUT_DIR)"
report:
	@test -n "$(STUDY_INDEX)" || { echo "STUDY_INDEX is required"; exit 2; }
	$(PYTHON) scripts/08_report.py --study-index "$(STUDY_INDEX)" $(DEV_FLAG)
finalize-study:
	@test -n "$(STUDY_INDEX)" -a -n "$(VALIDATION_RUN_ID)" || { echo "STUDY_INDEX and VALIDATION_RUN_ID are required"; exit 2; }
	$(PYTHON) scripts/09_finalize_study.py --study-index "$(STUDY_INDEX)" --validation-run-id "$(VALIDATION_RUN_ID)" $(if $(QUALITATIVE_RUN_ID),--qualitative-run-id "$(QUALITATIVE_RUN_ID)",) $(if $(REPORT_RUN_ID),--report-run-id "$(REPORT_RUN_ID)",) $(if $(CASE_REVIEW),--case-review "$(CASE_REVIEW)",) $(if $(ACADEMIC_REVIEW),--academic-review "$(ACADEMIC_REVIEW)",) $(if $(QUALITATIVE_REVIEW),--qualitative-review "$(QUALITATIVE_REVIEW)",) $(DEV_FLAG)

.PHONY: test-evidence test-counterexamples import-reviews
test-evidence:
	$(PYTHON) -m pytest tests/verification -m 'not counterexample' --no-cov

test-counterexamples:
	$(PYTHON) -m pytest tests/verification -m counterexample --no-cov

import-reviews:
	@test -n "$(STUDY_INDEX)" -a -n "$(REVIEW_DIR)" -a -n "$(OUTPUT_DIR)" || { echo "STUDY_INDEX, REVIEW_DIR and OUTPUT_DIR are required"; exit 2; }
	$(PYTHON) scripts/import_reviews.py --study-index "$(STUDY_INDEX)" --review-dir "$(REVIEW_DIR)" --output-dir "$(OUTPUT_DIR)"

.PHONY: verify-study
verify-study:
	@test -n "$(STUDY_INDEX)" -a -n "$(REVIEW_DIR)" || { echo "STUDY_INDEX and REVIEW_DIR are required"; exit 2; }
	$(PYTHON) scripts/verify_study.py --study-index "$(STUDY_INDEX)" --review-dir "$(REVIEW_DIR)" $(if $(OUTPUT_DIR),--output-dir "$(OUTPUT_DIR)",)
