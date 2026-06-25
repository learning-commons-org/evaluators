# scripts/ — repo check harness

Repo-wide checks that keep contributions consistent. The **same checks run
locally and in CI**, so what you run here is exactly what gates a PR.

## Setup

```bash
pip install -r scripts/requirements.txt   # one-time; pinned tools the checks use
```

## Usage

```bash
python scripts/check.py          # check everything (what CI runs)
python scripts/check.py --fix    # auto-fix what's safe, report the rest
python scripts/check.py --list   # list available checks
python scripts/check.py strip-notebooks   # run a single check
```

**Run `python scripts/check.py --fix` before you commit.** It catches issues
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

## Coming next

This is the seed of a broader self-service harness. Planned additions:

- **eval-config validation** — parser kind, prompt `sha256` drift, no dangling
  placeholders, fixture labels within the output schema enum.
- **naming / structure conventions** for `evals/`.
- **delegation to the SDK suites** (`sdks/typescript` lint/type/test,
  `sdks/python` Makefile) so one local command covers everything. CI keeps the
  per-SDK workflows separate for parallelism and path-filtered signal.

> **TODO** (once there are more checks): surface this from the root `README.md`
> / `CONTRIBUTING.md` so newcomers discover it — e.g. "Before committing, run
> `python scripts/check.py --fix` (see `scripts/README.md`)."

## Adding a check

Add a `Check` subclass in `scripts/checks/` (see `strip_notebooks.py`) and
register it in `scripts/checks/__init__.py`. It's automatically picked up by
the orchestrator and CI.
