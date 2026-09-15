PYTHON  ?= python3
PYTEST  := $(PYTHON) -m pytest
RUFF    := $(PYTHON) -m ruff
MYPY    := $(PYTHON) -m mypy

# Generated from the evals/ registry by scripts/generate_contracts.py:
#   src/learning_commons_evaluators/contracts/_generated/**   — bundled contracts (package data)
#   src/learning_commons_evaluators/schemas/<family>/<subject>/*.py — pydantic Input/Output models
# Both are committed; `make check-generated` fails CI when they drift from evals/.

.PHONY: help build check-build test integration-test generate-contracts check-generated \
        lint lint-fix format format-check typecheck pip-check verify coverage

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  build              Prepare the package: bundle evals/ contracts + generate schema modules"
	@echo "  check-build        Verify generated files are up to date (use in CI)"
	@echo ""
	@echo "  lint               Ruff linter (src/, tests/, scripts/)"
	@echo "  lint-fix           Ruff linter with --fix (safe auto-fixes)"
	@echo "  format             Apply Ruff formatter"
	@echo "  format-check       Fail if Ruff would reformat any file"
	@echo "  typecheck          Mypy on src package + tests"
	@echo "  pip-check          pip dependency consistency check"
	@echo "  verify             check-build + lint + format-check + typecheck + pip-check + test"
	@echo "  coverage           Tests with coverage report (requires dev install)"
	@echo ""
	@echo "  test               Run the test suite (live integration tests skip without keys)"
	@echo "  integration-test   Live provider tests: needs RUN_INTEGRATION_TESTS=1 and GOOGLE_API_KEY / OPENAI_API_KEY"
	@echo ""
	@echo "  generate-contracts Re-bundle evals/ contracts and regenerate schema modules"
	@echo "  check-generated    Verify generated files match evals/ (exits 1 if stale or orphaned)"
	@echo ""
	@echo "Typical workflows:"
	@echo "  After editing anything under evals/:    make generate-contracts && make test"
	@echo "  Fresh checkout / before release:        make build && make verify"
	@echo "  CI:                                     make verify"

# ── Build ─────────────────────────────────────────────────────────────────────
# Prepares all package build artifacts in one step.  Run after editing any
# file under evals/, or on a fresh checkout before running tests.

build: generate-contracts

check-build: check-generated

# ── Static checks (Ruff + Mypy) ───────────────────────────────────────────────

lint:
	$(RUFF) check src tests scripts

lint-fix:
	$(RUFF) check --fix src tests scripts

format:
	$(RUFF) format src tests scripts

format-check:
	$(RUFF) format --check src tests scripts

typecheck:
	$(MYPY) src/learning_commons_evaluators tests

pip-check:
	$(PYTHON) -m pip check

verify: check-build lint format-check typecheck pip-check test

coverage:
	$(PYTEST) tests/ -q --cov=learning_commons_evaluators --cov-report=term-missing

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	$(PYTEST) tests/ -v

integration-test:
	RUN_INTEGRATION_TESTS=1 $(PYTEST) tests/integration -v

# ── Code generation ───────────────────────────────────────────────────────────
# Re-run when anything under evals/ changes. The generator verifies each prompt
# file against the sha256 its config.json declares before bundling it.

generate-contracts:
	$(PYTHON) scripts/generate_contracts.py

check-generated:
	$(PYTHON) scripts/generate_contracts.py --check
