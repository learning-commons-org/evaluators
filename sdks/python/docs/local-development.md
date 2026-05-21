# Local development

## Package layout

- **`evaluators/`** — `BaseEvaluator`, `VocabularyEvaluator`, `ConventionalityEvaluator`
- **`schemas/`** — Pydantic types for inputs, outputs, config, metadata, errors
- **`providers/`** — LangChain LLM provider factory (OpenAI, Google, Anthropic)
- **`settings/`** — Generated settings modules from `sdks/settings/` TOML
- **`config.py`** / **`errors.py`** / **`logger.py`** — Re-exports for top-level imports

## Development setup

```bash
cd sdks/python

python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate.bat  # Windows CMD
# .venv\Scripts\Activate.ps1  # Windows PowerShell

pip install -e ".[dev]"

make verify   # lint + typecheck + full test suite (same gate as CI)
make test     # pytest only
```

From `sdks/python/`:

- `make lint` — Ruff on `src/`, `tests/`, `scripts/generate_settings.py`
- `make format` / `make format-check` — Ruff formatter
- `make typecheck` — Mypy
- `make pip-check` — `pip check`
- `make coverage` — unit tests with coverage report

## Using the SDK before publishing

```bash
pip install -e /path/to/evaluators/sdks/python
```

Editable install: changes to SDK source apply without reinstalling.

## Running tests

```bash
pytest                                    # unit + contract (unpopulated contracts skipped)
pytest tests/ --ignore=tests/contract_tests   # unit only
pytest tests/contract_tests/                  # contract only
```

Or use `make test`, `make unit-test`, and `make contract-test` from `sdks/python/`.

## Regenerating settings after TOML changes

Evaluator settings (prompts, models, temperatures) live in `sdks/settings/` and are baked into `_generated_*_settings.py` at build time. After editing any evaluator TOML:

```bash
make build               # generate-settings + sync-settings
make check-build         # verify generated files match canonical TOML (CI)
```

Commit the updated TOML together with regenerated/synced files. Repo `.gitattributes` marks `_generated_*.py` and `contracts.toml` as `linguist-generated=true`. See [Adding a new evaluator](#adding-a-new-evaluator) for the full checklist when introducing a new evaluator directory.

## Contract tests

Contract tests verify that the Python SDK sends the same LLM request (prompts, model, temperature) as the reference Jupyter notebook and parses the same structured result from a captured LLM response.

Each evaluator has a `contracts.toml` under `sdks/settings/<evaluator>/`. Until populated, contract tests are **skipped**, not failed.

**Populating contract data** (once per evaluator, or after prompt changes):

1. Open the evaluator notebook under `evals/` with a valid provider API key.
2. Run all cells; the final "Contract test capture — TOML output" cell prints a TOML block.
3. Paste into `sdks/settings/<evaluator>/contracts.toml` (replace placeholder `prompt_steps` / `expected_result`).
4. Run `make build` to sync the bundled package copy.
5. Run `pytest tests/contract_tests/` — tests should execute and pass.

## Keeping settings in sync

Canonical settings: `sdks/settings/`. The Python package needs:

- **`_generated_*_settings.py`** — imported at runtime (no TOML file I/O in production)
- **Bundled `contracts.toml`** — for contract tests after `pip install`

After any change under `sdks/settings/`:

```bash
make build
make check-build
```

## Adding a new evaluator

Contributor workflow for shipping an evaluator in this package. Use `ConventionalityEvaluator` (single LLM step) and `VocabularyEvaluator` (multi-step) as references.

**1. Canonical settings** — Add `sdks/settings/<evaluator_id>/settings.toml` (snake_case folder name). Include:

- `[evaluator_metadata]` — `id`, `version`, `name`, `description`, `maturity` (`early_access` is the only value defined today)
- `[[evaluator_metadata.inputs]]` — `TextInputField` and/or `GradeInputField` constraints (see `schemas/input_specs.py` for the input-spec checklist if you need a new field type)
- `[prompts]` — system/human template strings (`{format_instructions}` where using `JsonOutputParser`)
- `[evaluation_settings.prompt_settings_step_*]` — default `provider_type`, `model`, `temperature` per LLM step

Optionally add `sdks/settings/<evaluator_id>/contracts.toml` (placeholders are fine until you capture real notebook output).

**2. Schemas** — Add `src/learning_commons_evaluators/schemas/<evaluator_id>.py`:

- `<PascalCase>EvaluationSettings` subclass of `EvaluationSettings` (generator expects this name: `conventionality` → `ConventionalityEvaluationSettings`)
- Pydantic output model(s) for `JsonOutputParser`
- Avoid class docstrings on models used with `JsonOutputParser` if they would change `model_json_schema()` and break contract-test prompt snapshots (see `VocabularyComplexityOutput` in `schemas/vocabulary.py`)

**3. Generate settings** — From `sdks/python/`:

```bash
make generate-settings   # writes settings/_generated_<evaluator_id>_settings.py
make check-generated     # CI staleness check
```

The generator picks up any `sdks/settings/*/settings.toml` automatically.

**4. Evaluator module** — Add `src/learning_commons_evaluators/evaluators/<evaluator_id>.py`:

- `EvaluationInput` subclass with `_input_settings` pointing at `CONFIG.evaluator_metadata.inputs` and a caller-facing `__init__(self, *, text: str, grade: int, **kwargs)` (raw values are coerced to `TextInputField` / `GradeInputField` automatically)
- `BaseEvaluator` subclass wired to generated `CONFIG`:

```python
from typing import ClassVar

from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.schemas.common_inputs import GradeInputField, TextInputField
from learning_commons_evaluators.schemas.evaluator import EvaluationInput, EvaluationExplanation, EvaluationResult
from learning_commons_evaluators.schemas.metadata import EvaluationMetadata, EvaluatorMetadata
from learning_commons_evaluators.settings._generated_my_evaluator_settings import CONFIG

# MyEvaluationSettings, MyOutputSchema, and prompt templates live in schemas/<evaluator_id>.py

_INPUT_SETTINGS = CONFIG.evaluator_metadata.inputs


class MyEvaluationInput(EvaluationInput):
    _input_settings: ClassVar[dict] = _INPUT_SETTINGS

    text: TextInputField
    grade: GradeInputField

    def __init__(self, *, text: str, grade: int, **kwargs):
        super().__init__(text=text, grade=grade, **kwargs)


class MyEvaluator(BaseEvaluator[MyEvaluationInput, EvaluationResult, MyEvaluationSettings]):
    metadata: EvaluatorMetadata = CONFIG.evaluator_metadata
    default_evaluation_settings: MyEvaluationSettings = CONFIG.evaluation_settings

    async def evaluate_impl(
        self,
        input: MyEvaluationInput,
        evaluation_settings: MyEvaluationSettings,
        evaluation_metadata: EvaluationMetadata,
    ) -> EvaluationResult:
        prompts = CONFIG.prompts
        output = await self.execute_prompt_chain_step(
            step_name="main",
            prompt_settings=evaluation_settings.prompt_settings_step_main,
            evaluation_metadata=evaluation_metadata,
            template=my_chat_prompt_template,  # built from prompts[...]
            chain_inputs=input.input_values(),
            parser_output_type=MyOutputSchema,
        )
        return EvaluationResult(
            answer=...,
            explanation=EvaluationExplanation(summary=output.reasoning, details={...}),
            metadata=evaluation_metadata,
        )
```

If you override `__init__`, forward `default_evaluation_settings=` to `super().__init__(config, default_evaluation_settings=...)`.

**5. Public exports** — Register the evaluator and input types in `evaluators/__init__.py` and, when ready to ship, in the root `learning_commons_evaluators/__init__.py` `__all__`.

**6. Unit tests** — Add `tests/evaluators/test_<evaluator_id>.py`. Mock `execute_prompt_chain_step` (see `test_conventionality.py`) to avoid live LLM calls; include cases for `InputValidationError` and `ConfigurationError` where relevant.

**7. Contract tests** — Add `tests/contract_tests/<evaluator_id>.py`, a loader module, and `tests/contract_tests/test_<evaluator_id>.py` following the conventionality pattern. Populate `contracts.toml` from the evaluator notebook under `evals/` (see [Contract tests](#contract-tests)), then `make sync-settings`.

**8. Verify** — `make verify` before opening a PR. Commit canonical TOML, generated `_generated_*.py`, and synced bundled `contracts.toml` together.

Runtime overrides (`default_evaluation_settings` at construction, `evaluation_settings` per call) work the same as for bundled evaluators — see [Evaluation settings (per evaluator)](./configuration.md#evaluation-settings-per-evaluator).
