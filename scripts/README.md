# scripts/ — repo check harness

Repo-wide checks that keep contributions consistent. The **same checks run
locally and in CI**, so what you run here is exactly what gates a PR.

## Setup

```bash
pip install -r scripts/requirements.txt   # one-time; pinned tools the checks use
```

## Usage

```bash
python3 scripts/check.py          # check everything (what CI runs)
python3 scripts/check.py --fix    # auto-fix what's safe, report the rest
python3 scripts/check.py --list   # list available checks
python3 scripts/check.py strip-notebooks   # run a single check
```

**Run `python3 scripts/check.py --fix` before you commit.** It catches issues
early with clear messages and fixes what it can. CI runs the same harness and
fails the PR (it never auto-fixes) — so fixing locally saves a round-trip.

## How it works

- One check per concern, two modes: **check** (the default — non-zero exit on
  problems) and **`--fix`** (repair in place where safe).
- The orchestrator runs **every** check and reports **all** failures at once —
  no stop-at-first, no whack-a-mole.
- Tools the checks rely on are pinned in `requirements.txt` so local and CI
  behave identically.

## Checks

| Check | What it does |
|-------|--------------|
| `strip-notebooks` | Clears outputs, execution counts, and cell metadata from `.ipynb` files |
| `eval-config` | Validates each evaluator `config.json` against the shared schema (`evals/_schemas/config.schema.json`, referenced by the config's own `$schema`), plus cross-file rules: referenced files exist, prompt `sha256` matches, placeholders ⇄ template `{vars}` are in sync, system prompts carry no placeholders, and no obsolete `format_instructions` survive |
| `eval-schemas` | Meta-validates each `input_schema.json` / `output_schema.json` is a well-formed JSON Schema document |
| `eval-fixtures` | Validates `fixtures.json` against the shared `evals/_schemas/fixtures.schema.json`, and binds each case's `input`/`expected` to that evaluator's own input/output schema |
| `eval-notebook` | Where an evaluator ships an example notebook, confirms it loads the config + prompt files from disk rather than hardcoding them |

## Coming next

This is the seed of a broader self-service harness. Planned additions:

- **delegation to the SDK suites** (`sdks/typescript` lint/type/test,
  `sdks/python` Makefile) so one local command covers everything. CI keeps the
  per-SDK workflows separate for parallelism and path-filtered signal.

## Running before every commit

`scripts/setup.sh` (once per clone) installs `pre-commit` + the harness deps and
enables a hook that runs `python3 scripts/check.py --fix` on each commit (the hook
runs in pre-commit's own pinned, isolated env). Because setup also installs the
deps, you can run it directly too: `python3 scripts/check.py --fix`. It's opt-in
convenience — `git commit --no-verify` bypasses it, and CI runs the same checks
regardless. See [`CONTRIBUTING.md`](../CONTRIBUTING.md).

## Adding a check

Add a `Check` subclass in `scripts/checks/` (see `strip_notebooks.py`) and
register it in `scripts/checks/__init__.py`. It's automatically picked up by
the orchestrator and CI.

## `scripts/notebook_ci/` — live notebook execution (separate from the harness above)

`find_affected.py` computes which evaluator notebooks a PR's changed files
affect, by reading each evaluator's own `config.json` dependency closure
(prompt `source_path`s, schema `$ref`s, `fixtures.path`) — not a hand-maintained
map. Used by
[`.github/workflows/eval-notebooks.yml`](../.github/workflows/eval-notebooks.yml)
to run only the affected notebooks against real LLM APIs on each PR.

This is intentionally **not** part of `scripts/check.py`: it makes real,
billed API calls and is advisory (never blocks a PR), whereas the checks above
are deterministic, free, and gate merges. Scope is also narrower — only
evaluators with a `config.json` are covered, same as every check above.

```bash
python3 scripts/notebook_ci/find_affected.py --changed-files-from <(git diff --name-only main)
```
