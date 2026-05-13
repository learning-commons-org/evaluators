PYTHON  ?= python3
PYTEST  := $(PYTHON) -m pytest
RUFF    := $(PYTHON) -m ruff
MYPY    := $(PYTHON) -m mypy

.PHONY: help test unit-test generate-settings check-generated \
        lint format format-check typecheck pip-check verify coverage

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  lint               Ruff linter (src, tests, settings generator script)"
	@echo "  format             Apply Ruff formatter"
	@echo "  format-check       Fail if Ruff would reformat any file"
	@echo "  typecheck          Mypy on src package + tests"
	@echo "  pip-check          pip dependency consistency check"
	@echo "  verify             check-generated + lint + format-check + typecheck + pip-check + test (unit + contract)"
	@echo "  coverage           Unit tests with coverage report (requires dev install)"
	@echo ""
	@echo "  test               Run the full test suite"
	@echo "  unit-test          Run unit tests only"
	@echo ""
	@echo "  generate-settings  Re-generate _generated_*_settings.py from sdks/settings/"
	@echo "  check-generated    Verify generated .py files match sdks/settings/ (exits 1 if stale)"
	@echo ""
	@echo "Typical workflows:"
	@echo "  After editing evaluator settings TOML:  make generate-settings && make test"
	@echo "  CI:                                     make verify"

# ── Static checks (Ruff + Mypy) ───────────────────────────────────────────────

lint:
	$(RUFF) check src tests scripts/generate_settings.py

format:
	$(RUFF) format src tests scripts/generate_settings.py

format-check:
	$(RUFF) format --check src tests scripts/generate_settings.py

typecheck:
	$(MYPY) src/learning_commons_evaluators tests

pip-check:
	$(PYTHON) -m pip check

verify: check-generated lint format-check typecheck pip-check test

coverage:
	$(PYTEST) tests/ -q --ignore=tests/contract_tests --cov=learning_commons_evaluators --cov-report=term-missing

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	$(PYTEST) tests/ -v

unit-test:
	$(PYTEST) tests/ -v --ignore=tests/contract_tests

# ── Code generation ───────────────────────────────────────────────────────────
# Re-run when an evaluator settings TOML under sdks/settings/ changes.

generate-settings:
	$(PYTHON) scripts/generate_settings.py

check-generated:
	$(PYTHON) scripts/generate_settings.py --check
