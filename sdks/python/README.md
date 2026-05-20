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
| `answer` | The evaluation score and label. Bundled text-complexity evaluators use `TextComplexityResult`, whose `answer` is a `TextComplexityAnswer` enum member (`SLIGHTLY_COMPLEX`, `MODERATELY_COMPLEX`, `VERY_COMPLEX`, `EXCEEDINGLY_COMPLEX`) with `.score` (snake_case string) and `.label` (human-readable) |
| `explanation.summary` | Main reasoning string from the model |
| `explanation.details` | Evaluator-specific structured fields (dict) |
| `metadata` | Run metadata: timing, status, token usage, per-step details |

```python
result.metadata.status              # Status.succeeded on success
result.metadata.processing_time_ms
result.metadata.total_token_usage   # dict[LLMProvider, TokenUsage]
result.metadata.step_details        # per prompt step: timing, token usage, prompt settings
```

On failure, `metadata.status` and `error_details` are set on the in-memory metadata object and included in the evaluation end log line; `evaluate` / `evaluate_sync` still **re-raise** and do not return a result object.

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

Bundled evaluators load defaults from generated settings TOML. Use `SomeEvaluator.default_evaluation_settings` (class attribute) or `evaluator.default_evaluation_settings` (after construction) as the starting point for overrides. Fields are usually named `prompt_settings_step_*` and hold `PromptSettings` (`provider_type`, `model`, `temperature`).

Custom evaluators declare their own settings type and set `default_evaluation_settings` on the class (see [Creating custom evaluators](#creating-custom-evaluators)).

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

```python
from learning_commons_evaluators import (
    ConfigurationError,  # Missing/invalid config
    ValidationError,     # Invalid input (grade, text length, etc.)
    AuthenticationError, # Invalid API keys (401/403)
    RateLimitError,      # Rate limit exceeded (429); has retry_after
    NetworkError,        # Network failures
    EvaluatorTimeoutError,
    APIError,            # Other API errors; check retryable
)

try:
    result = evaluator.evaluate_sync(input)
except ConfigurationError as e:
    ...
except ValidationError as e:
    ...
except RateLimitError as e:
    print(f"Retry after {e.retry_after}ms")
except APIError as e:
    print(f"retryable={e.retryable}: {e}")
```

Failures inside LLM prompt steps are normalized via `wrap_provider_error()` so you typically see `APIError` subclasses rather than raw LangChain or HTTP exceptions. The package does not export a `TimeoutError` alias (to avoid shadowing the Python builtin); use `EvaluatorTimeoutError` for timeouts.

## Creating custom evaluators

Extend `BaseEvaluator` to add new evaluators. Define a dedicated `MySettings` model (subclass of `EvaluationSettings`) for [configurable settings on that evaluator](#evaluation-settings-per-evaluator), set class-level `default_evaluation_settings`, and implement `evaluate_impl`. Callers may pass `default_evaluation_settings=` at construction (same pattern as bundled evaluators).

```python
from learning_commons_evaluators import BaseEvaluator, EvaluatorConfig
from learning_commons_evaluators.schemas.evaluator import EvaluationInput, EvaluationResult
from learning_commons_evaluators.schemas.metadata import EvaluatorMetadata, EvaluatorMaturity, EvaluationMetadata

class MyEvaluator(BaseEvaluator[MyInput, EvaluationResult, MySettings]):
    metadata = EvaluatorMetadata(
        id="my-evaluator",
        version="0.1.0",
        name="My Evaluator",
        description="Evaluates something custom",
        maturity=EvaluatorMaturity.early_access,
    )
    default_evaluation_settings = MySettings(...)

    async def evaluate_impl(
        self,
        input: MyInput,
        evaluation_settings: MySettings,
        evaluation_metadata: EvaluationMetadata,
    ) -> EvaluationResult:
        output = await self.execute_prompt_chain_step(
            step_name="main",
            prompt_settings=evaluation_settings.prompt_settings,
            evaluation_metadata=evaluation_metadata,
            template=my_prompt_template,
            chain_inputs={"text": input.text.value},
            parser_output_type=MyOutputSchema,
        )
        return EvaluationResult(answer=..., explanation=..., metadata=evaluation_metadata)
```

If you override `__init__` on the subclass, forward the keyword: `super().__init__(config, default_evaluation_settings=default_evaluation_settings)`.

Input constraints (allowed grades, text length) can be declared in evaluator settings TOML under `[[evaluator_metadata.inputs]]` and are enforced automatically on `EvaluationInput` subclasses.

---

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

### Regenerating settings after TOML changes

Evaluator settings (prompts, models, temperatures) live in `sdks/settings/` and are baked into `_generated_*_settings.py` at build time. After editing any evaluator TOML:

```bash
make build          # regenerate _generated_*_settings.py + sync contracts.toml
make check-build    # verify generated files match canonical TOML (CI)
```

Commit the updated TOML together with regenerated/synced files. Repo `.gitattributes` marks `_generated_*.py` and `contracts.toml` as `linguist-generated=true`.

### Running tests

```bash
pytest                                    # unit + contract (unpopulated contracts skipped)
pytest tests/ --ignore=tests/contract_tests   # unit only
pytest tests/contract_tests/                  # contract only
```

### Contract tests

Contract tests verify that the Python SDK sends the same LLM request (prompts, model, temperature) as the Jupyter notebook and parses the same structured result from a captured LLM response.

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

## License

MIT
