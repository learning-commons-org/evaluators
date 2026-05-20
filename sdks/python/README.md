# learning-commons-evaluators (Python)

Python SDK for Learning Commons educational text evaluators. Evaluators call LLMs via LangChain, return structured Pydantic results, and share a common configuration and error-handling model.

## Installation

```bash
pip install learning-commons-evaluators
```

Requires **Python 3.10+**. Provider API keys are passed in at runtime (not bundled with the package).

## Quick start

```python
import logging
from learning_commons_evaluators import (
    ConventionalityEvaluator,
    ConventionalityEvaluationInput,
    GoogleLLMProviderConfig,
    create_config_no_telemetry,
)

logging.basicConfig(level=logging.INFO)

config = create_config_no_telemetry(
    google_llm_provider_config=GoogleLLMProviderConfig(api_key="your-google-key"),
)

evaluator = ConventionalityEvaluator(config)
result = evaluator.evaluate_sync(
    ConventionalityEvaluationInput(text="The cat's out of the bag now.", grade=5)
)

print(result.answer.label)        # e.g. "Moderately complex"
print(result.explanation.summary) # Reasoning for the score
```

## Evaluators

Both shipped evaluators target **grades 3–12**, return a four-point complexity scale, and produce an `EvaluationResult` (see [Results](#results)).

| Evaluator | Maturity | LLM providers required[^providers] |
|-----------|----------|--------------------------------------|
| `VocabularyEvaluator` | Early access | OpenAI **and** Google |
| `ConventionalityEvaluator` | Early access | Google |

[^providers]: Default providers for the bundled [evaluation settings](#evaluation-settings-per-evaluator). Override provider and model (and other configurable fields) via `default_evaluation_settings` at construction or `evaluation_settings` per call — see [Per-instance default evaluation settings](#per-instance-default-evaluation-settings) and [Per-call settings override](#per-call-settings-override). You must still supply API keys in `EvaluatorConfig` for every provider your overridden settings use.

### Vocabulary Evaluator

Estimates the background knowledge students at the target grade are likely to have, identifies complex vocabulary (Tier 2, Tier 3, archaic, and other complex words), and rates overall vocabulary complexity relative to that grade level.

**Documentation:** [About Vocabulary Evaluator](https://docs.learningcommons.org/evaluators/literacy-evaluators/vocabulary-evaluator/about-this-evaluator)

#### Inputs

Type: `VocabularyEvaluationInput`

<details>
<summary>Fields</summary>

| Field | Type | Constraints |
|-------|------|-------------|
| `text` | `str` | Educational text to evaluate |
| `grade` | `int` | Target grade level; **3–12** |

</details>

```python
VocabularyEvaluationInput(text="Your text here.", grade=5)
```

#### Outputs

Type: `TextComplexityResult` (subclass of `EvaluationResult`)

<details>
<summary>Fields</summary>

| Field | Description |
|-------|-------------|
| `answer` | `TextComplexityAnswer` — four-point complexity scale (`.score`, `.label`) |
| `explanation.summary` | Reasoning for the rating |
| `explanation.details` | `tier_2_words`, `tier_3_words`, `archaic_words`, `other_complex_words` |
| `metadata` | Run timing, status, token usage, per-step details |

</details>

#### Evaluation settings

Type: `VocabularyEvaluationSettings` — one `PromptSettings` field per LLM step (override `provider_type`, `model`, `temperature` per step).

<details>
<summary>Default prompt steps</summary>

| Field | Default provider | Default model |
|-------|------------------|---------------|
| `prompt_settings_step_background_knowledge` | OpenAI | `gpt-4o-2024-11-20` |
| `prompt_settings_step_vocab_grades_3_4` | Google | `gemini-2.5-pro` (grades 3–4) |
| `prompt_settings_step_vocab_other_grades` | OpenAI | `gpt-4.1` (grades 5–12) |

</details>

<details>
<summary>Example usage</summary>

```python
from learning_commons_evaluators import (
    VocabularyEvaluator,
    VocabularyEvaluationInput,
    GoogleLLMProviderConfig,
    OpenAILLMProviderConfig,
    create_config_no_telemetry,
)

config = create_config_no_telemetry(
    google_llm_provider_config=GoogleLLMProviderConfig(api_key="..."),
    openai_llm_provider_config=OpenAILLMProviderConfig(api_key="..."),
)
evaluator = VocabularyEvaluator(config)

result = evaluator.evaluate_sync(
    VocabularyEvaluationInput(text="The quick brown fox jumps over the lazy dog.", grade=5)
)

result.answer.score    # "slightly_complex" | "moderately_complex" | "very_complex" | "exceedingly_complex"
result.answer.label    # "Slightly complex" | ...
result.explanation.summary
result.explanation.details  # tier_2_words, tier_3_words, archaic_words, other_complex_words
```

</details>

### Conventionality Evaluator

Assesses how directly a text communicates its meaning—whether language is literal and explicit or relies on figurative, abstract, or implied meaning that requires interpretation.

**Documentation:** [About Conventionality Evaluator](https://docs.learningcommons.org/evaluators/literacy-evaluators/conventionality/about-this-evaluator)

#### Inputs

Type: `ConventionalityEvaluationInput`

<details>
<summary>Fields</summary>

| Field | Type | Constraints |
|-------|------|-------------|
| `text` | `str` | **10–10,000** characters |
| `grade` | `int` | Target grade level; **3–12** |

</details>

```python
ConventionalityEvaluationInput(text="Your text here.", grade=5)
```

#### Outputs

Type: `TextComplexityResult` (subclass of `EvaluationResult`)

<details>
<summary>Fields</summary>

| Field | Description |
|-------|-------------|
| `answer` | `TextComplexityAnswer` — four-point complexity scale (`.score`, `.label`) |
| `explanation.summary` | Reasoning for the rating |
| `explanation.details` | `conventionality_features`, `grade_context`, `instructional_insights` |
| `metadata` | Run timing, status, token usage, per-step details |

</details>

#### Evaluation settings

Type: `ConventionalityEvaluationSettings` — configurable via a single `PromptSettings` field.

<details>
<summary>Default prompt steps</summary>

| Field | Default provider | Default model |
|-------|------------------|---------------|
| `prompt_settings_step_conventionality_evaluation` | Google | `gemini-3-flash-preview` |

</details>

<details>
<summary>Example usage</summary>

```python
from learning_commons_evaluators import (
    ConventionalityEvaluator,
    ConventionalityEvaluationInput,
    GoogleLLMProviderConfig,
    create_config_no_telemetry,
)

config = create_config_no_telemetry(
    google_llm_provider_config=GoogleLLMProviderConfig(api_key="..."),
)
evaluator = ConventionalityEvaluator(config)

result = evaluator.evaluate_sync(
    ConventionalityEvaluationInput(text="Your text here.", grade=5)
)

result.answer.score
result.answer.label
result.explanation.summary
result.explanation.details  # conventionality_features, grade_context, instructional_insights
```

</details>

## Running evaluations

### Synchronous

Use `evaluate_sync()` from scripts, notebooks, or other synchronous code:

```python
result = evaluator.evaluate_sync(input)
```

### Asynchronous

Use `await evaluator.evaluate(input)` in async apps, or when an event loop is already running on the thread. If you call `evaluate_sync()` while a loop is active, the SDK raises `RuntimeError` with a message to use `evaluate()` instead.

Invalid inputs (grade out of range, text too short, and other constraints from evaluator settings) raise `InputValidationError` before any LLM call.

```python
import asyncio

async def main():
    result = await evaluator.evaluate(input)
    return result

asyncio.run(main())
```

### Per-call settings override

Pass `evaluation_settings=` to override models, temperatures, or other [configurable evaluator settings](#evaluation-settings-per-evaluator) for a single call. When omitted, the evaluator uses a deep copy of its default settings (class-level defaults, or the instance override from construction — see [Per-instance default evaluation settings](#per-instance-default-evaluation-settings)).

```python
from dataclasses import replace

from learning_commons_evaluators import ConventionalityEvaluator

evaluator = ConventionalityEvaluator(config)
settings = evaluator.default_evaluation_settings.model_copy(deep=True)
settings.prompt_settings_step_conventionality_evaluation = replace(
    settings.prompt_settings_step_conventionality_evaluation,
    temperature=0.2,
)
result = evaluator.evaluate_sync(input, evaluation_settings=settings)
```

## Results

Successful evaluations return an `EvaluationResult` with three top-level fields (`answer`, `explanation`, `metadata`):

| Field | Description |
|-------|-------------|
| `answer` | The evaluation score and label |
| `explanation.summary` | Main reasoning string from the model |
| `explanation.details` | Evaluator-specific structured fields (dict) |
| `metadata` | Run metadata: timing, status, token usage, per-step details |

```python
result.metadata.status              # Status.succeeded on success
result.metadata.processing_time_ms
result.metadata.total_token_usage   # dict[LLMProvider, TokenUsage]
result.metadata.step_details        # per prompt step: timing, token usage, prompt settings
```

On failure, the same metadata object (`result.metadata` on success) is updated with `status=failed` and a sanitized `error_details`, emitted on the evaluation end log line, then `evaluate` / `evaluate_sync` **re-raise** without returning a result.

## Configuration

### Provider configs

Each LLM provider needs its own config with an API key. Configure providers required by your evaluator’s [evaluation settings](#evaluation-settings-per-evaluator) (each prompt step’s `provider_type` in the bundled defaults, or in your overrides).

```python
from learning_commons_evaluators import (
    GoogleLLMProviderConfig,
    OpenAILLMProviderConfig,
    AnthropicLLMProviderConfig,
)

google_config = GoogleLLMProviderConfig(api_key="...")
openai_config = OpenAILLMProviderConfig(api_key="...")
anthropic_config = AnthropicLLMProviderConfig(api_key="...")
```

If a prompt step requires a provider that is missing from `EvaluatorConfig`, evaluation raises `ConfigurationError`.

### EvaluatorConfig factories

Telemetry is not yet wired up in the SDK. Use `create_config_no_telemetry()` in application code (all examples in this README do).

```python
from learning_commons_evaluators import create_config_no_telemetry

config = create_config_no_telemetry(
    google_llm_provider_config=google_config,
    openai_llm_provider_config=openai_config,
    logger=my_logger,  # optional; default: package logger
)
```

When telemetry is available, `create_config()` and `create_config_telemetry_with_full_input()` will require a `telemetry_partner_id`. Pass the resulting `EvaluatorConfig` to any evaluator constructor: `MyEvaluator(config)`.

### Evaluation settings (per evaluator)

What you can tune at runtime—default models, providers, temperatures, and other prompt-step options—is defined **per evaluator** as a Pydantic model subclass of `EvaluationSettings`. Each field on that model is part of that evaluator’s contract; there is no shared global settings shape across evaluators. See **Inputs**, **Outputs**, and **Evaluation settings** under each [evaluator](#evaluators) for the concrete types and bundled defaults.

Bundled evaluators load defaults from generated settings TOML ([Adding a new evaluator](#adding-a-new-evaluator) covers how those files are produced). Use `SomeEvaluator.default_evaluation_settings` (class attribute) or `evaluator.default_evaluation_settings` (after construction) as the starting point for overrides. Fields are usually named `prompt_settings_step_*` and hold `PromptSettings` (`provider_type`, `model`, `temperature`).

### Per-instance default evaluation settings

Pass `default_evaluation_settings=` to the evaluator constructor to change the default for every call on that instance. The value must match that evaluator’s [evaluation settings type](#evaluation-settings-per-evaluator). Per-call `evaluation_settings=` still overrides for a single run ([Per-call settings override](#per-call-settings-override)).

```python
from dataclasses import replace

from learning_commons_evaluators import ConventionalityEvaluator

settings = ConventionalityEvaluator.default_evaluation_settings.model_copy(deep=True)
settings.prompt_settings_step_conventionality_evaluation = replace(
    settings.prompt_settings_step_conventionality_evaluation,
    temperature=0.2,
    model="gemini-2.5-pro",
)
evaluator = ConventionalityEvaluator(config, default_evaluation_settings=settings)

result = evaluator.evaluate_sync(input)  # uses instance default
```

The SDK deep-copies defaults before each run so in-memory settings objects are not mutated by evaluation.

### Logging

The SDK uses Python's standard `logging` module. By default, `EvaluatorConfig` uses the package logger `learning_commons_evaluators`, which propagates to the root logger once your app configures handlers.

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("learning_commons_evaluators").setLevel(logging.WARNING)

from learning_commons_evaluators import (
    create_config_no_telemetry,
    create_logger,
    create_silent_logger,
    get_logger,
)

logger = create_logger(level=logging.DEBUG)
config = create_config_no_telemetry(logger=create_silent_logger())  # discard SDK logs
```

## Error handling

During a normal `evaluate()` / `evaluate_sync()` run, failures from evaluator input checks, configuration, LLM prompt steps, and output validation typically surface as subclasses of `EvaluatorError`. Failures inside LLM prompt steps are wrapped at the boundary so callers see a predictable, sanitized hierarchy instead of raw LangChain, OpenAI, Anthropic, or HTTP-client exceptions. **Programmer errors** (such as misusing the API, passing the wrong types, or violating invariants) may still raise standard Python exceptions (e.g., `ValueError`, `TypeError`, `RuntimeError`). Only evaluation failures are wrapped; not all exceptions are guaranteed to be subclasses of `EvaluatorError`.

### Hierarchy

```
EvaluatorError
├── ConfigurationError       — bad config (missing provider, unknown model, malformed settings)
├── InputValidationError     — caller-supplied input failed validation
└── APIError                 — failures originating in the LLM provider call
    ├── AuthenticationError  — 401 / 403
    ├── RateLimitError       — 429; carries `retry_after` (seconds)
    ├── NetworkError         — connection refused, DNS failure, broken TLS
    ├── RequestTimeoutError  — request exceeded the configured timeout
    └── OutputValidationError — LLM response failed to parse or didn't match the expected schema
```

`InputValidationError` is named that way deliberately to avoid collision with `pydantic.ValidationError`. `RequestTimeoutError` is named that way to avoid shadowing the builtin `TimeoutError`. There is **no** `ValidationError` or `EvaluatorTimeoutError` in the public API.

### Knowing when to retry

Every `EvaluatorError` exposes a boolean `retryable` attribute. This is the single signal callers should consult when wrapping `evaluate()` in retry logic — there is no separate marker class to check. Subclasses set sensible defaults:

- Retryable by default: `RateLimitError`, `NetworkError`, `RequestTimeoutError`, `OutputValidationError`, and any `APIError` with a 5xx status code (retryable is inferred automatically if not explicitly set).
- Not retryable: `ConfigurationError`, `InputValidationError`, `AuthenticationError`, and `APIError` with a 4xx status code.

`retryable` is also accepted as an `__init__` kwarg on `APIError` and `NetworkError` if you need to flag a specific instance differently (e.g. a permanently-bad hostname). If you construct an `APIError` with a status code >= 500 and do not specify `retryable`, it will default to `True`.

```python
import time
from learning_commons_evaluators import EvaluatorError, RateLimitError

for attempt in range(3):
    try:
        result = evaluator.evaluate_sync(input)
        break
    except EvaluatorError as e:
        if not e.retryable or attempt == 2:
            raise
        delay = e.retry_after if isinstance(e, RateLimitError) and e.retry_after else 2 ** attempt
        time.sleep(delay)  # retry_after is in seconds
```

### Sanitization and debugging context

Error **messages** (the value returned by `str(err)`) are short and controlled. Raw provider strings — which may contain prompt echoes, user text, or fragments of API keys — are **not** interpolated into the SDK exception's message. Structured detail lives on attributes instead:

- `status_code` on `APIError` — HTTP status from the provider, when one was returned. Populated from the provider exception's `.status_code` or `.response.status_code`/`.response.status` attribute when present (preferred over message regex).
- `retry_after` on `RateLimitError` — suggested delay before retry, **in seconds**, or `None` if the provider didn't return a `Retry-After` header.
- `provider` on `APIError` — the `LLMProvider` being called when the failure occurred.
- `model` on `APIError` — the model ID requested.
- `response_body` on `APIError` — decoded response body. Opt-in for debugging; may contain echoed prompt content, so treat as sensitive.
- `request_id` on `APIError` — provider request ID, useful for support escalation.
- `validation_errors` on `OutputValidationError` — per-field entries from Pydantic's `errors()` API after `sanitize_pydantic_errors` (only `loc`, `type`, optional `url`, and numeric/boolean `ctx` values are retained — all `input`, `msg`, string or mapping `ctx` values are dropped, which can echo model output).

The original provider exception is preserved on `__cause__` (via `raise … from e`), so debuggers, tracebacks, and `logging.exception()` retain full detail even though `str(err)` is sanitized.

```python
import logging
import time

from learning_commons_evaluators import APIError, OutputValidationError, RateLimitError

log = logging.getLogger(__name__)
try:
    result = evaluator.evaluate_sync(input)
except RateLimitError as e:
    time.sleep(e.retry_after or 30)  # seconds
except OutputValidationError as e:
    # Structured entries omit Pydantic msg/input (may echo LLM text); use __cause__ for full detail.
    log.warning("Bad LLM output: %s", e.validation_errors)
    # Original pydantic.ValidationError / OutputParserException available as e.__cause__
except APIError as e:
    log.error(
        "Provider call failed",
        extra={
            "provider": e.provider,
            "model": e.model,
            "status": e.status_code,
            "request_id": e.request_id,
        },
    )
    raise
```

### Metadata and telemetry

On evaluation failure, the run metadata object (the same `EvaluationMetadata` attached as `result.metadata` on success) has `status` set to `failed` and `error_details` populated before `evaluate()` / `evaluate_sync()` re-raises. `error_details` is itself sanitized:

- SDK errors record only the class name (for example `"RateLimitError"`).
- Any other exception that escapes records only `"Unexpected error: ClassName"` — the message is omitted because arbitrary exception text may contain user data or field values that aren't safe for telemetry.

The same policy applies to per-step `StepMetadata.error_details`. Both fields are emitted on the evaluation end log line.

For custom code that calls LLM providers outside `execute_prompt_chain_step`, the package exports `wrap_provider_error()` to apply the same routing and sanitization rules.

## Development

### Package layout

- **`evaluators/`** — `BaseEvaluator`, `VocabularyEvaluator`, `ConventionalityEvaluator`
- **`schemas/`** — Pydantic types for inputs, outputs, config, metadata, errors
- **`providers/`** — LangChain LLM provider factory (OpenAI, Google, Anthropic)
- **`settings/`** — Generated settings modules from `sdks/settings/` TOML
- **`config.py`** / **`errors.py`** / **`logger.py`** — Re-exports for top-level imports

### Development setup

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

### Using the SDK before publishing

```bash
pip install -e /path/to/evaluators/sdks/python
```

Editable install: changes to SDK source apply without reinstalling.

### Running tests

```bash
pytest                                    # unit + contract (unpopulated contracts skipped)
pytest tests/ --ignore=tests/contract_tests   # unit only
pytest tests/contract_tests/                  # contract only
```

Or use `make test`, `make unit-test`, and `make contract-test` from `sdks/python/`.

### Regenerating settings after TOML changes

Evaluator settings (prompts, models, temperatures) live in `sdks/settings/` and are baked into `_generated_*_settings.py` at build time. After editing any evaluator TOML:

```bash
make build               # generate-settings + sync-settings
make check-build         # verify generated files match canonical TOML (CI)
```

Commit the updated TOML together with regenerated/synced files. Repo `.gitattributes` marks `_generated_*.py` and `contracts.toml` as `linguist-generated=true`. See [Adding a new evaluator](#adding-a-new-evaluator) for the full checklist when introducing a new evaluator directory.

### Contract tests

Contract tests verify that the Python SDK sends the same LLM request (prompts, model, temperature) as the reference Jupyter notebook and parses the same structured result from a captured LLM response.

Each evaluator has a `contracts.toml` under `sdks/settings/<evaluator>/`. Until populated, contract tests are **skipped**, not failed.

**Populating contract data** (once per evaluator, or after prompt changes):

1. Open the evaluator notebook under `evals/` with a valid provider API key.
2. Run all cells; the final "Contract test capture — TOML output" cell prints a TOML block.
3. Paste into `sdks/settings/<evaluator>/contracts.toml` (replace placeholder `prompt_steps` / `expected_result`).
4. Run `make build` to sync the bundled package copy.
5. Run `pytest tests/contract_tests/` — tests should execute and pass.

### Keeping settings in sync

Canonical settings: `sdks/settings/`. The Python package needs:

- **`_generated_*_settings.py`** — imported at runtime (no TOML file I/O in production)
- **Bundled `contracts.toml`** — for contract tests after `pip install`

After any change under `sdks/settings/`:

```bash
make build
make check-build
```

### Adding a new evaluator

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

Runtime overrides (`default_evaluation_settings` at construction, `evaluation_settings` per call) work the same as for bundled evaluators — see [Evaluation settings (per evaluator)](#evaluation-settings-per-evaluator).

## License

MIT
