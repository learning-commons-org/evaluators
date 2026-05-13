PYTHON  ?= python3
PYTEST  := $(PYTHON) -m pytest
RUFF    := $(PYTHON) -m ruff
MYPY    := $(PYTHON) -m mypy

# Bundled settings directory inside the package.  Two things are maintained here:
#   _generated_*_settings.py  — generated from settings.toml by `make generate-settings`
#   contracts.toml             — copied from sdks/settings/ by `make sync-settings`
#
# Tests always read contracts.toml from the bundled copy (via importlib.resources
# fallback in shared_settings_root()).  EVALUATORS_SETTINGS_DIR is intentionally NOT
# exported here so that dev and installed-package runs behave identically.
SETTINGS_DST := src/learning_commons_evaluators/settings

.PHONY: help build check-build test unit-test contract-test \
        generate-settings check-generated sync-settings check-sync \
        lint format format-check typecheck pip-check verify coverage

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  build              Prepare the package: generate settings + sync contracts TOML"
	@echo "  check-build        Verify build artifacts are up to date (use in CI)"
	@echo ""
	@echo "  lint               Ruff linter (src/, tests/, scripts/)"
	@echo "  format             Apply Ruff formatter"
	@echo "  format-check       Fail if Ruff would reformat any file"
	@echo "  typecheck          Mypy on src package + tests"
	@echo "  pip-check          pip dependency consistency check"
	@echo "  verify             check-build + lint + format-check + typecheck + pip-check + test (unit + contract)"
	@echo "  coverage           Unit tests with coverage report (requires dev install)"
	@echo ""
	@echo "  test               Run the full test suite (unit + contract)"
	@echo "  unit-test          Run unit tests only (skip contract tests)"
	@echo "  contract-test      Run contract tests only"
	@echo ""
	@echo "  generate-settings  Re-generate _generated_*_settings.py from sdks/settings/"
	@echo "  check-generated    Verify generated .py files match sdks/settings/ (exits 1 if stale)"
	@echo "  sync-settings      Copy contracts.toml from sdks/settings/ into the package"
	@echo "  check-sync         Verify bundled contracts.toml matches sdks/settings/"
	@echo ""
	@echo "Typical workflows:"
	@echo "  After editing evaluator settings TOML:  make generate-settings && make test"
	@echo "  After editing contracts TOML:           make sync-settings && make contract-test"
	@echo "  Fresh checkout / before release:        make build && make verify"
	@echo "  CI:                                     make verify && make contract-test"

# ── Build ─────────────────────────────────────────────────────────────────────
# Prepares all package build artifacts in one step.  Run after editing any
# file under sdks/settings/, or on a fresh checkout before running tests.

build: generate-settings sync-settings

check-build: check-generated check-sync

# ── Static checks (Ruff + Mypy) ───────────────────────────────────────────────

lint:
	$(RUFF) check src tests scripts

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
	$(PYTEST) tests/ -q --ignore=tests/contract_tests --cov=learning_commons_evaluators --cov-report=term-missing

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	$(PYTEST) tests/ -v

unit-test:
	$(PYTEST) tests/ -v --ignore=tests/contract_tests

contract-test:
	$(PYTEST) tests/contract_tests/ -v

# ── Code generation ───────────────────────────────────────────────────────────
# Re-run when an evaluator settings TOML under sdks/settings/ changes.
# The generator sets EVALUATORS_SETTINGS_DIR itself to point at sdks/settings/.

generate-settings:
	$(PYTHON) scripts/generate_settings.py

check-generated:
	$(PYTHON) scripts/generate_settings.py --check

# ── Contract test bundling ────────────────────────────────────────────────────
# contracts.toml is bundled so contract tests run consistently whether using
# a development checkout or a pip-installed package.  The sync command is
# handled by the Python generator script.

sync-settings:
	$(PYTHON) scripts/generate_settings.py --sync

check-sync:
	$(PYTHON) scripts/generate_settings.py --check-sync
