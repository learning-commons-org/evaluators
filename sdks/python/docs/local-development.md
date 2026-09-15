# Local development

## Package layout

- **`contracts/`** — The `evals/` registry as the package ships it. `contracts/_generated/<family>/<subject>/<evaluator>/` holds each contract's `config.json`, input and output schemas, and prompt files, copied verbatim by `make generate-contracts`; `contracts/loader.py` reads one back as a typed `Contract`.
- **`schemas/<family>/<subject>/<evaluator>.py`** — Generated from each contract's schemas: pydantic `<Class>Input` and `<Class>Output` models.
- **`providers/`** — The `LLMProvider` protocol and one adapter per native SDK (`openai_sdk.py`, `anthropic_sdk.py`, `google_genai.py`), `create_provider()`, and the resampling half of the retry split (`retry.py`).
- **`errors.py`** — The canonical error taxonomy (SDK spec §6) and `wrap_provider_error()`.
- **`logger.py`** — Logging helpers following the stdlib library convention (`NullHandler`, no root configuration)
- **`version.py`** — Package version and description

The evaluators themselves (contract-driven single-step and multi-step factories, the registry, result envelope, and flat config) land in the following PRs.

## Development setup

```bash
cd sdks/python

python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate.bat  # Windows CMD
# .venv\Scripts\Activate.ps1  # Windows PowerShell

pip install -e ".[dev]"

make verify   # check-build + lint + format-check + typecheck + pip-check + test (same gate as CI)
make test     # pytest only
```

From `sdks/python/`:

- `make lint` — Ruff on `src/` and `tests/`
- `make format` / `make format-check` — Ruff formatter
- `make typecheck` — Mypy
- `make pip-check` — `pip check`
- `make coverage` — tests with coverage report

## Using the SDK before publishing

```bash
pip install -e /path/to/evaluators/sdks/python
```

Editable install: changes to SDK source apply without reinstalling.

## Regenerating after a change under `evals/`

The registry at `evals/<family>/<subject>/<evaluator>/` is the source of truth for every evaluator's id, prompts, models, preprocessing, and schemas. The package bundles it and generates pydantic models from it, so after editing anything there:

```bash
make generate-contracts  # bundle contracts into contracts/_generated/ and regenerate schemas/<family>/<subject>/*.py
make check-generated     # verify the committed files match evals/ (CI runs this; stale or orphaned files fail)
```

The generator (`scripts/generate_contracts.py`) checks each prompt and rubric file against the `sha256` its `config.json` declares and refuses to bundle one that drifted. Commit the registry change together with the regenerated files; `.gitattributes` marks them `linguist-generated=true` so GitHub collapses them in review.

Generated schema modules start with `# GENERATED — do not edit directly.` and are excluded from Ruff; edit the `output_schema.json` or `input_schema.json` they come from instead. Bundled files are byte-for-byte copies.

## Tests

- `tests/unit/errors/` — the taxonomy's rules and the error mapping check: every signal row of SDK spec §6.5 maps to the expected class, using the native SDKs' real exception types.
- `tests/unit/providers/` — each adapter against a fake client, the factory, and the resampling loop.
- `tests/unit/contracts/` — every bundled contract read back and cross-checked against `evals/` (sha256, placeholder sources, outcome fields), plus the generator's emitter on synthetic schemas.
- `tests/unit/schemas/` — parser tests: hand-written payloads per `output_schema.json` against the generated `<Class>Output` models.
