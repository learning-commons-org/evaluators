VENV    := ../../.venv
PYTHON  := $(VENV)/bin/python
PYTEST  := $(VENV)/bin/pytest
RUFF    := $(VENV)/bin/ruff
MYPY    := $(VENV)/bin/mypy

.PHONY: help test unit-test lint format format-check typecheck pip-check verify coverage

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  lint               Ruff linter (src, tests)"
	@echo "  format             Apply Ruff formatter"
	@echo "  format-check       Fail if Ruff would reformat any file"
	@echo "  typecheck          Mypy on src package + tests"
	@echo "  pip-check          pip dependency consistency check"
	@echo "  verify             lint + format-check + typecheck + pip-check + unit-test"
	@echo "  coverage           Unit tests with coverage report (requires dev install)"
	@echo ""
	@echo "  test               Run the full test suite"
	@echo "  unit-test          Run unit tests only"

# ── Static checks (Ruff + Mypy) ───────────────────────────────────────────────

lint:
	$(RUFF) check src tests

format:
	$(RUFF) format src tests

format-check:
	$(RUFF) format --check src tests

typecheck:
	$(MYPY) src/learning_commons_evaluators tests

pip-check:
	$(PYTHON) -m pip check

verify: lint format-check typecheck pip-check unit-test

coverage:
	$(PYTEST) tests/ -q --ignore=tests/contract_tests --cov=learning_commons_evaluators --cov-report=term-missing

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	$(PYTEST) tests/ -v

unit-test:
	$(PYTEST) tests/ -v --ignore=tests/contract_tests
