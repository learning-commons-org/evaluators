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
| `eval-config` | Validates each evaluator `config.json` against the shared schema (`evals/_schemas/config.schema.json`, referenced by the config's own `$schema`), plus cross-file rules: referenced files exist, prompt `sha256` matches, placeholders ⇄ template `{vars}` are in sync, system prompts carry no placeholders, no obsolete `format_instructions` survive, and `stable_id`/`id`/`id_history` values are never reused across evaluators |
| `eval-schemas` | Meta-validates each `input_schema.json` / `output_schema.json` is a well-formed JSON Schema document |
| `eval-fixtures` | Validates `fixtures.json` against the shared `evals/_schemas/fixtures.schema.json`, and binds each case's `input`/`expected` to that evaluator's own input/output schema |
| `eval-notebook` | Where an evaluator ships an example notebook, confirms it loads the config + prompt files from disk rather than hardcoding them |
| `eval-requirements` | Cross-checks `evals/requirements.txt` against imports actually used in `evals/`, in both directions: something imported with no matching entry (a missing dependency), and something listed but never imported (a stale one) |

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

## `scripts/prompt_diff.py` — review what actually changed in a prompt

A plain `git diff` is a poor review tool for prompt changes, for two reasons:
files move (so everything reads as delete + add), and content moves *between*
files (rubric text relocated from a user prompt to a system prompt reads as a
large deletion plus a large addition, when nothing the model sees changed).

This renders each side into one normalized blob — every message concatenated in
the order `config.json` declares — and word-diffs that. A pure restructure
produces an empty diff; only real wording changes surface. Word granularity
matters for prose: a reflowed paragraph is a whole-line change to a line
differ but a no-op to a word differ.

Diffs are **per LLM call** (one `steps[]` entry in `config.json`) by default —
the unit that maps to an actual API request.

```bash
python3 scripts/prompt_diff.py --list                   # evaluators + calls
python3 scripts/prompt_diff.py --all                    # verdict per LLM call
python3 scripts/prompt_diff.py vocabulary-complexity    # one diff per call
python3 scripts/prompt_diff.py --all --emit /tmp/pd     # dump every pair to disk
```

It runs `git fetch origin` first, because both sides are read from refs rather
than the working tree. Skipping that would mean a prompt you just pushed to a
PR is invisible, and the tool would report a confident verdict on stale
content. Pass `--no-fetch` when offline.

That same fetch also pulls each PR head from `refs/pull/<N>/head` into
`refs/prompt-diff/pr-<N>`, so **the tool works on any clone** — the person
running it needs no local branches, no worktrees, and no knowledge of branch
names. It's been verified against a `--single-branch` clone that only knew
`origin/main`. GitHub keeps those refs after a PR merges and its branch is
deleted, so old comparisons stay reproducible.

### Seeing what changed

```bash
python3 scripts/prompt_diff.py --all --changed-only     # terminal, only what moved
python3 scripts/prompt_diff.py <evaluator> --difftool   # your configured diff tool
python3 scripts/prompt_diff.py <evaluator> --difftool=opendiff   # pick one explicitly
```

`--difftool` renders each side to a file and hands the pair to
`git difftool --no-index`, so it uses whatever you've set as `diff.tool` and
supports everything git does — `git difftool --tool-help` lists what's
installed. No bespoke launcher and no extra config of its own. Only calls that
actually changed are opened.

`--emit DIR` writes the pairs without opening anything, if you'd rather drive
the comparison yourself:

```bash
python3 scripts/prompt_diff.py --all --changed-only --emit /tmp/pd
git difftool --no-index /tmp/pd/<call>.BEFORE.txt /tmp/pd/<call>.AFTER.txt
```

| Flag | Purpose |
|------|---------|
| `--changed-only` | Skip calls whose prompt is unchanged. |
| `--difftool [TOOL]` | Open each changed call via `git difftool --no-index`, using your configured `diff.tool` unless you name one. |
| `--combined` | Concatenate all of an evaluator's calls into one diff. Off by default: condition-gated branches (Vocabulary Complexity's grade bands) can cancel out when flattened, so a real change to one branch could read as `IDENTICAL`. |
| `--no-fetch` | Skip the automatic `git fetch origin`. |
| `--emit DIR` | Write each rendered `BEFORE`/`AFTER` pair to `DIR` and print a `code --diff` line for each, instead of printing the diff inline. Use this to review in VS Code, Meld, Beyond Compare, or any visual difftool. |
| `--mode content` | *(default)* Ignore role and file boundaries. Answers "did the instruction set change at all?" |
| `--mode roles` | Keep `===== SYSTEM =====` markers. Answers "what moved between the system and user prompts?" |
| `--mode files` | File inventory per call, no diff. Answers "which files went where?" |
| `--normalize` | Canonicalize already-agreed renames (`{grade}`→`{grade_level}`, drop `{format_instructions}`) so only *unexpected* changes remain. Reports which substitutions fired, so nothing hides silently. |
| `--base` / `--head` | Diff any two refs. Defaults: `origin/main` → the evaluator's PR branch. |

Both sides are read with `git show`, so no checkout or worktree is needed. You
can run it without checking out the branch it lives on:

```bash
git fetch origin worktree-prompt-diff-tool
git show FETCH_HEAD:scripts/prompt_diff.py > /tmp/prompt_diff.py
python3 /tmp/prompt_diff.py --all      # from anywhere in the repo, any branch
```

To hand it to someone else while it's still unmerged, that snippet is the
whole handoff — it needs only clone access, and bootstraps every ref it
compares.

It survives the migration merging. When a PR branch is deleted the head falls
back to `--fallback-head` (default `origin/main`); and because the base-side
files are *also* gone from `main` by then — they were `git mv`d away — each
base path is resolved back to the last commit where it still existed, rather
than erroring out.

`EVALUATORS` in the script maps each LLM call (a `steps[]` entry in
`config.json`) to the base-side files it came from, before the
`evals/prompts/` → `evals/student-facing-text/ela-reading/` migration. That
mapping is inherently historical — `git` can't infer it once files move and
merge — so it's maintained by hand as new evaluators land.

A step's `head_extra` lists files that call depends on but `config.json`
cannot name: Sentence Structure's grade-band rubrics are `preprocessing`
entries interpolated into `{rubric}`, and `config.schema.json` has no
`source_path` field for preprocessing entries. Worth fixing at the schema
level — `notebook_ci/find_affected.py` derives its dependency closure from
the same data, so those rubrics are currently outside it too.
