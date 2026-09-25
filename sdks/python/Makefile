PYTHON  ?= python3
PYTEST  := $(PYTHON) -m pytest
RUFF    := $(PYTHON) -m ruff
MYPY    := $(PYTHON) -m mypy

# Floor for line coverage. The suite sits at 98%; the gap is headroom so a single
# uncovered line does not block an otherwise good PR. Raise it, never lower it.
COV_MIN ?= 95

# Generated from the evals/ registry by scripts/generate_contracts.py:
#   src/learning_commons_evaluators/contracts/_generated/**   — bundled contracts (package data)
#   src/learning_commons_evaluators/schemas/<family>/<subject>/*.py — pydantic Input/Output models
# Both are committed; `make check-generated` fails CI when they drift from evals/.
#
# Generated from openapi/knowledge-graph.yaml by scripts/generate_kg_client.py:
#   src/learning_commons_evaluators/dependencies/_generated/knowledge_graph/**
# Also committed; `make check-kg-client` fails CI when it drifts from the vendored spec.
# The spec itself is refreshed by `make fetch-kg-openapi`, which is the only network step
# and so is deliberately outside `verify`.

.PHONY: help build check-build test integration-test generate-contracts check-generated \
        fetch-kg-openapi generate-kg-client check-kg-client \
        lint lint-fix format format-check typecheck pip-check verify coverage

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  build              Prepare the package: bundle evals/ contracts + generate schema modules"
	@echo "  check-build        Verify every generated tree is up to date (use in CI)"
	@echo ""
	@echo "  lint               Ruff linter (src/, tests/, scripts/)"
	@echo "  lint-fix           Ruff linter with --fix (safe auto-fixes)"
	@echo "  format             Apply Ruff formatter"
	@echo "  format-check       Fail if Ruff would reformat any file"
	@echo "  typecheck          Mypy on src package + tests"
	@echo "  pip-check          pip dependency consistency check"
	@echo "  verify             check-build + lint + format-check + typecheck + pip-check + test"
	@echo "  coverage           Tests with coverage; fails under COV_MIN ($(COV_MIN)%)"
	@echo ""
	@echo "  test               Run the test suite (live integration tests skip without keys)"
	@echo "  integration-test   Live tests: needs RUN_INTEGRATION_TESTS=1 plus GOOGLE_API_KEY / OPENAI_API_KEY"
	@echo ""
	@echo "  generate-contracts Re-bundle evals/ contracts and regenerate schema modules"
	@echo "  check-generated    Verify generated files match evals/ (exits 1 if stale or orphaned)"
	@echo "  fetch-kg-openapi   Download the Knowledge Graph OpenAPI spec (network; not in verify)"
	@echo "  generate-kg-client Re-generate the Knowledge Graph client from the vendored spec"
	@echo "  check-kg-client    Verify the generated Knowledge Graph client matches the spec"
	@echo ""
	@echo "Typical workflows:"
	@echo "  After editing anything under evals/:    make generate-contracts && make test"
	@echo "  After a Knowledge Graph API change:     make fetch-kg-openapi && make generate-kg-client"
	@echo "  Fresh checkout / before release:        make build && make verify"
	@echo "  CI:                                     make verify"

# ── Build ─────────────────────────────────────────────────────────────────────
# Prepares the evals/-derived artifacts in one step.  Run after editing any
# file under evals/, or on a fresh checkout before running tests.

# The Knowledge Graph client is deliberately not here. It is generated from openapi/,
# not evals/, changes only when the published spec does, and its generator cannot be
# installed on every interpreter the package supports — so regenerating it is its own
# explicit step. The committed tree is the build artifact; `check-build` still verifies it.
build: generate-contracts

check-build: check-generated check-kg-client

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
	$(PYTEST) tests/ -q --cov=learning_commons_evaluators \
	  --cov-report=term-missing --cov-report=xml --cov-fail-under=$(COV_MIN)

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	$(PYTEST) tests/ -v

# Each case also needs its own credential in the environment and skips without it:
# GOOGLE_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY per the evaluator's contract, and
# LEARNING_COMMONS_API_KEY for the live Knowledge Graph checks.
integration-test:
	RUN_INTEGRATION_TESTS=1 $(PYTEST) tests/integration -v

# ── Code generation ───────────────────────────────────────────────────────────
# Re-run when anything under evals/ changes. The generator verifies each prompt
# file against the sha256 its config.json declares before bundling it.

generate-contracts:
	$(PYTHON) scripts/generate_contracts.py

check-generated:
	$(PYTHON) scripts/generate_contracts.py --check

# ── Knowledge Graph OpenAPI client ────────────────────────────────────────────
# Two steps on purpose. Fetching the published spec is the network step and is not part
# of `verify`, so a change to the live API arrives as a reviewed commit to
# openapi/knowledge-graph.yaml. Generation is offline from that vendored file, so CI and
# a laptop produce the same client.

fetch-kg-openapi:
	$(PYTHON) scripts/fetch_kg_openapi.py

generate-kg-client:
	$(PYTHON) scripts/generate_kg_client.py

check-kg-client:
	$(PYTHON) scripts/generate_kg_client.py --check
