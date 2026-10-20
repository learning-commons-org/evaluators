---
name: new-evaluator
description: >
  Wire an existing evals/ contract into both SDKs: generate the contract mirrors,
  implement and register the evaluator in the Python and TypeScript SDKs, and
  verify it with unit tests and live integration tests. Use when adding a new
  evaluator whose contract directory already exists under evals/.
argument-hint: "<family>/<subject>/<evaluator> (e.g. durable-skills/ela-writing/critical-thinking)"
---

# New evaluator: wire a contract into both SDKs

Takes an evaluator whose **contract already exists** under `evals/` and ships it in
both SDKs. This skill does not author contracts; it implements them.

## Step 0 — Precondition: the contract must exist. Error out if it doesn't.

Resolve the argument to `evals/<family>/<subject>/<evaluator>/` (kebab-case path
segments; the canonical dotted id is the same path with `_` instead of `-`, e.g.
`durable_skills.ela_writing.critical_thinking`).

**Stop immediately with an error** — do not scaffold anything, do not create the
directory — unless the directory exists and contains all of: `config.json`,
`input_schema.json`, `output_schema.json`, `system.txt`, `user.txt`,
`fixtures.json`. Report exactly which files are missing and tell the user to add
the contract first (see `evals/_schemas/` for the config and fixtures schemas).

While there, read `config.json` to learn what you are implementing: single-step
vs multi-step, the providers it declares (which decide the integration-test API
keys), and any dependencies (e.g. the Knowledge Graph) or `x-image` input bounds.

## Step 1 — Python SDK (`sdks/python/`)

1. **Regenerate the mirrors**: `make generate-contracts`. This bundles the
   contract into `src/learning_commons_evaluators/contracts/_generated/...` and
   emits the schema module under `src/.../schemas/<family>/<subject>/`. Never
   hand-edit either; `make check-generated` must pass afterwards.
2. **Implement** `src/.../evaluators/<family>/<subject>/<evaluator>.py`, modeled
   on the nearest sibling (e.g. `durable_skills/ela_writing/critical_thinking.py`
   for single-step). Add any missing `__init__.py` files in the package chain.
3. **Register and export**: add it to `evaluators/registry.py` and thread the
   public name through `evaluators/__init__.py` and the package `__init__.py`.
   The registry-conformance tests (`tests/unit/evaluators/test_registry*.py`)
   will tell you if wiring is incomplete.
4. **Unit tests**: add `tests/unit/evaluators/<family>/<subject>/test_<evaluator>.py`
   (construction, input validation, score/judgment mapping), mirroring the
   sibling evaluator's tests. Update registry/conformance and cross-SDK prompt
   tests where they enumerate evaluators (`test_cross_sdk_prompts.py`).
5. **Integration test**: add `tests/integration/test_<evaluator>.py` driven by
   the contract's `fixtures.json` via the existing `conftest.py` helpers
   (`fixtures_for` / `keys_for`); it must skip cleanly when keys are absent.
6. **Verify**: `make verify` (runs check-generated, lint, format-check,
   typecheck, pip-check, and the unit suite).

## Step 2 — TypeScript SDK (`sdks/typescript/`)

1. **Regenerate schemas**: `npm run generate:schemas`, which writes
   `src/schemas/<family>/<subject>/<evaluator>.ts`. Then add that exact path to
   the root `.gitattributes` generated-file list — the TS schema modules are
   listed one by one, and a unit test fails if the list and the GENERATED
   markers disagree.
2. **Implement** `src/evaluators/<family>/<subject>/<evaluator>.ts`, modeled on
   the nearest sibling.
3. **Register and export**: wire `src/evaluators/registry.ts`,
   `src/evaluators/index.ts`, and `src/index.ts`.
4. **Unit tests**: dedicated tests under `tests/unit/evaluators/` plus the
   suites that enumerate evaluators — `registry-conformance.test.ts`,
   `functional-api.test.ts`, `declarations.test.ts`,
   `scripts/generate-schema.test.ts` — and `tests/utils/test-helpers.ts` if it
   carries per-evaluator fixtures.
5. **Integration test**: `tests/integration/<evaluator>.integration.test.ts`,
   following the skip-without-keys pattern in `tests/README.md`.
6. **Verify**: `npm run lint && npm run typecheck && npm run test:unit`. If you
   touched the entry points, also `npm run verify:dist && npm run verify:package`.

## Step 3 — Live integration tests (required before calling it done)

Keys live in `evals/.env` (`OPENAI_API_KEY`, `GOOGLE_API_KEY`,
`ANTHROPIC_API_KEY`, `LEARNING_COMMONS_API_KEY`) — neither SDK loads that file
itself, so export it into the environment:

```shell
set -a; source evals/.env; set +a
```

Then, scoped to the new evaluator:

```shell
# Python (from sdks/python/)
RUN_INTEGRATION_TESTS=1 pytest tests/integration -v -k <evaluator>

# TypeScript (from sdks/typescript/)
RUN_INTEGRATION_TESTS=true npm run test:integration -- <evaluator>
```

If the evaluator depends on the Knowledge Graph, also set
`NO_PROXY=api.learningcommons.org` (a local system proxy re-signs KG TLS and
breaks the calls). Run the live tests on **both** sides and report the actual
results — a skipped suite is not a pass; if a key is missing from `evals/.env`,
say so rather than skipping silently.

## Step 4 — Repo harness and PRs

- Run `python3 scripts/check.py --fix` from the repo root before committing
  (use the interpreter `scripts/setup.sh` provisioned if bare `python3` lacks
  the harness deps).
- Ship as **two draft PRs** matching repo history: `feat(ts-sdk): add the <Name>
  evaluator` and `feat(python-sdk): add the <Name> evaluator`. Conventional
  commits are CI-enforced; releases are release-please — never touch versions
  or CHANGELOGs.
- Do not update the demos as part of this skill; offer it as a follow-up.
