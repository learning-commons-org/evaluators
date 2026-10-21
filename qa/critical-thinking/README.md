# Critical Thinking SDK QA

QA harness for the Critical Thinking evaluator in both SDKs. It lives on the `qa/critical-thinking` branch only and is never merged. The full plan, scenarios and bug template are in the QA guide.

## Setup (once)

```bash
git clone https://github.com/learning-commons-org/evaluators.git
cd evaluators && git checkout qa/critical-thinking
cd qa/critical-thinking
./setup.sh              # both SDKs; or --python / --ts for one
echo 'ANTHROPIC_API_KEY=<shared QA key>' > .env   # or: export ANTHROPIC_API_KEY=<shared QA key>
```

`run.sh` reads the key from your shell or from a `.env` file. A key exported in the shell wins, then `qa/critical-thinking/.env`, then the repo root `.env`. Both `.env` files are git-ignored. Each run prints which keys it loaded from a file (names only, never values).

You need Python 3.11+ and/or Node ^20.19 or >=22.12. `setup.sh` builds both SDKs from this checkout the way users will get them:

- **Python:** a regular, non-editable `pip install` of `sdks/python` into `.venv`, so the contracts and prompts come from the built package, not the source folder.
- **TypeScript:** `npm run build` + `npm pack` of `sdks/typescript`, then that tarball is installed into `ts/` with fresh peer dependencies (`ai`, `zod`, `@ai-sdk/anthropic`).

When the branch is updated, `git pull` and run `./setup.sh` again.

## Running

| Command | Scenario | Cost |
|---|---|---|
| `./run.sh py inputs/B-one-passage.json` | Smoke test, D2, D3, C* | 1 call |
| `./run.sh ts inputs/B-one-passage.json` | Same, TypeScript | 1 call |
| `./run.sh py inputs/A-three-passages-mixed.json --spy-telemetry` | D8: print telemetry events | 1 call |
| `./run.sh py inputs/A-three-passages-mixed.json --no-telemetry` | D8: nothing sent | 1 call |
| `./run.sh py validate` / `./run.sh ts validate` | D5: 22 validation cases | free |
| `./run.sh py errors` / `./run.sh ts errors` | D6: config and provider errors | free |
| `./run.sh py async inputs/B-one-passage.json` | D7: three concurrent calls | 3 calls |
| `./run.sh fixtures` | Writes the eval's fixtures to `inputs/fixtures/` (C1) | free |
| `./run.sh --no-env py errors` | Any command, ignoring both `.env` files (here: case 3 SKIPs) | free |

`validate` and `errors` cases 1–2 use built-in fake keys, so they behave the same with or without your key; only `errors` case 3 and the paid runs use it. `--no-env` ignores the `.env` files but not a key exported in your shell; to drop that too, run `env -u ANTHROPIC_API_KEY ./run.sh --no-env ...`.

A call costs about $0.03 for the samples and up to about $0.19 for the three-passage fixture. Every run prints the full result envelope, then a summary: indicators rated, whether `synthesizing_sources` is present, whether the score equals the median, tokens and time.

Your own inputs: put JSON files in `inputs/local/` (git-ignored) with `assignment_text`, `source_passages` and `essay_text`. Don't commit real student essays.

## Inputs

| File | What it exercises |
|---|---|
| `A-three-passages-mixed.json` | Title only, title + author, text only. `synthesizing_sources` present. |
| `B-one-passage.json` | One passage, so `synthesizing_sources` should be absent (not null). |
| `C-fabricated-citations-one-passage.json` | Cites sources that weren't given. Known issue: record the score, don't refile. |
| `D-four-passage-shapes-with-null.json` | Every passage shape, including `author: null`. |
| `E-no-sources-cited.json` | An opinion essay that ignores the sources. |
| `F-cite-by-number-untitled.json` | Untitled passages cited as "Source 1" and "Source 2". |
| `validation_cases.json` | 22 validation cases with the exact expected messages. |
