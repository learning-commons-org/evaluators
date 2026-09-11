# Local development

## Package layout

- **`logger.py`** — Logging helpers following the stdlib library convention (`NullHandler`, no root configuration)
- **`version.py`** — Package version and description

The 0.2.0 evaluators, their settings machinery, and the LangChain provider have been removed. The package is being rebuilt on the shared evaluator contracts under `evals/` and the SDK specification; the contract loader, error taxonomy, provider adapters, and evaluators land in the following PRs.

## Development setup

```bash
cd sdks/python

python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate.bat  # Windows CMD
# .venv\Scripts\Activate.ps1  # Windows PowerShell

pip install -e ".[dev]"

make verify   # lint + format-check + typecheck + pip-check + test (same gate as CI)
make test     # pytest only
```

From `sdks/python/`:

- `make lint` — Ruff on `src/`, `tests/`, `scripts/`
- `make format` / `make format-check` — Ruff formatter
- `make typecheck` — Mypy
- `make pip-check` — `pip check`
- `make coverage` — tests with coverage report

## Using the SDK before publishing

```bash
pip install -e /path/to/evaluators/sdks/python
```

Editable install: changes to SDK source apply without reinstalling.
