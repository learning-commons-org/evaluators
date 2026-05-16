# learning-commons-evaluators (Python)

Python SDK for Learning Commons educational text evaluators.

## Package layout

- **`evaluators/`** – Evaluator classes: `BaseEvaluator`, `ConventionalityEvaluator`.
- **`schemas/`** – Pydantic schemas for inputs, outputs, config, metadata, and errors.
- **`providers/`** – LangChain-based LLM provider factory (OpenAI, Google, Anthropic).
- **`settings/`** – TOML settings loader for evaluator configuration.
- **`config.py`** – Re-exports config types (`EvaluatorConfig`, `LLMProviderConfig`, factory functions).
- **`errors.py`** – Re-exports error types.
- **`logger.py`** – Standard Python logging utilities.

## Installation

```bash
pip install learning-commons-evaluators
```

### Development setup

```bash
cd sdks/python

# Create and activate a virtual environment (Python 3.10+)
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate.bat  # Windows CMD
# .venv\Scripts\Activate.ps1  # Windows PowerShell

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Static checks + full test suite (unit + contract; same gate as CI for the Python SDK)
make verify

# Tests only (same pytest invocation as the verify step)
make test
```

Linting and typing use **Ruff** and **Mypy** (see `pyproject.toml`). From `sdks/python/`:

- `make lint` — Ruff lint on `src/`, `tests/`, and `scripts/generate_settings.py`
- `make format` / `make format-check` — Ruff formatter
- `make typecheck` — Mypy on the package and tests
- `make pip-check` — `pip check` for broken dependency metadata
- `make coverage` — unit tests with `pytest-cov` terminal report

### Regenerating settings after TOML changes

Evaluator settings (prompts, models, temperatures) live in `sdks/settings/` and are
baked into pre-generated Python modules at build time.  After editing any evaluator
settings TOML under `sdks/settings/`, regenerate those modules from `sdks/python/`:

```bash
make build   # regenerates _generated_*_settings.py and syncs contracts.toml
```

Commit both the updated TOML and the regenerated `.py` files together.  CI runs
`make check-build` to catch any drift between the TOML source and the generated files.

The repo root **`.gitattributes`** marks `_generated_*.py` and `contracts.toml`
(under `sdks/python/.../settings/` and `sdks/settings/`) with `linguist-generated=true`,
so GitHub treats them as generated in pull requests (diffs default to collapsed and
they are omitted from language statistics; you can still expand a file to review it).

### Running tests

```bash
# All tests (unit + contract, skipping unpopulated contract cases automatically)
pytest

# Unit tests only
pytest tests/ --ignore=tests/contract_tests

# Contract tests only
pytest tests/contract_tests/
```

### Contract tests

Contract tests verify that the Python SDK sends the same LLM request (fully formatted
prompts, model, temperature) as the Jupyter notebook, and produces the same structured
result from the same LLM response.

Each evaluator has a `contracts.toml` file that captures a real LLM interaction
from a notebook run.  Until that file is populated, contract tests are **automatically
skipped** — they do not fail.

**Populating the contract data** (once per evaluator, or after any prompt change):

1. Open `evals/Final ship - Conventionality Experimental Evaluator.ipynb` (or the
   relevant evaluator notebook) with a valid `GOOGLE_API_KEY` (or other provider key).
2. Run all cells.  The final "Contract test capture — TOML output" cell prints a TOML
   block.
3. Paste the printed block into
   `sdks/settings/conventionality/contracts.toml`, replacing the
   placeholder values in `[cases.turnip.prompt_steps.main]` and
   `[cases.turnip.expected_result]`.
4. Run `make sync-settings` to copy the updated file into the bundled package copy.
5. Run `pytest tests/contract_tests/` — the tests should now execute and pass.

### Keeping settings in sync

The canonical settings live in `sdks/settings/` (source of truth for all SDKs).
The Python package needs two things derived from them:

- **`_generated_*_settings.py`** — Python modules baked from the evaluator settings
  TOML at build time; evaluators import these at runtime (zero file I/O).
- **Bundled `contracts.toml`** — copied into the package so contract tests work
  after a plain `pip install`.

Run from `sdks/python/` after any change to `sdks/settings/`:

```bash
make build          # regenerate _generated_*_settings.py + sync contracts.toml
make check-build    # verify generated files match canonical TOML (used in CI)
```

Commit the updated canonical TOML together with the regenerated/synced files.

### Using the SDK before publishing

To use the SDK as source code in another project before publishing to PyPI:

```bash
pip install -e /path/to/evaluators/sdks/python
```

This installs the package in editable mode — changes to the SDK source are reflected
immediately without reinstalling.

## Quick start

```python
import logging
from learning_commons_evaluators import (
    ConventionalityEvaluator,
    ConventionalityEvaluationInput,
    GoogleLLMProviderConfig,
    create_config,
)

# Optional: app logging so SDK messages propagate (default logger is learning_commons_evaluators)
logging.basicConfig(level=logging.INFO)

# Create config with provider credentials
config = create_config(
    google_llm_provider_config=GoogleLLMProviderConfig(api_key="your-google-key"),
    telemetry_partner_id="your-telemetry-id",
)

# Create evaluator and run evaluation
evaluator = ConventionalityEvaluator(config)
result = evaluator.evaluate_sync(
    ConventionalityEvaluationInput(text="The cat's out of the bag now.", grade=5)
)

print(result.answer.score)        # e.g. "moderately_complex"
print(result.answer.label)        # e.g. "Moderately complex"
print(result.explanation.summary) # Reasoning for the score
```

## Evaluators

### Conventionality Evaluator

Evaluates text for conventionality of language (idioms, metaphors, implied meaning) relative to a grade level.

- **Input:** Text + grade level (0-12)
- **Output:** Complexity score, conventionality features, grade context, instructional insights

```python
from learning_commons_evaluators import (
    ConventionalityEvaluator,
    ConventionalityEvaluationInput,
    GoogleLLMProviderConfig,
    create_config,
)

config = create_config(
    google_llm_provider_config=GoogleLLMProviderConfig(api_key="..."),
    telemetry_partner_id="your-telemetry-id",
)
evaluator = ConventionalityEvaluator(config)

result = evaluator.evaluate_sync(
    ConventionalityEvaluationInput(text="Your text here.", grade=5)
)

# Result structure
result.answer.score           # "slightly_complex" | "moderately_complex" | "very_complex" | "exceedingly_complex"
result.answer.label           # Human-readable label
result.explanation.summary    # Reasoning
result.explanation.details    # {"conventionality_features": [...], "grade_context": "...", "instructional_insights": "..."}
result.metadata               # Timing, token usage, evaluator info
```

## Configuration

### Provider configs

Each LLM provider requires its own config with an API key:

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

### EvaluatorConfig

Use `create_config()` to create an `EvaluatorConfig`:

```python
from learning_commons_evaluators import create_config

config = create_config(
    google_llm_provider_config=google_config,
    openai_llm_provider_config=openai_config,
    telemetry_partner_id="your-telemetry-id",
    logger=my_logger,  # Optional: any standard logging.Logger (default: package logger)
)
```

### Per-instance default evaluation settings

Every `BaseEvaluator` subclass defines **class-level** `default_evaluation_settings`
(the bundled evaluators load these from generated settings). You can override that
default for a single evaluator instance by passing the same keyword to the
constructor:

```python
from learning_commons_evaluators import ConventionalityEvaluator, create_config

config = create_config(...)
# Start from the bundled defaults, then change what your deployment needs (models,
# temperatures, etc. live on nested PromptSettings).
settings = ConventionalityEvaluator.default_evaluation_settings.model_copy(deep=True)
settings.prompt_settings_step_conventionality_evaluation = (
    settings.prompt_settings_step_conventionality_evaluation.model_copy(
        update={"temperature": 0.2}
    )
)
evaluator = ConventionalityEvaluator(
    config,
    default_evaluation_settings=settings,
)

# Uses the instance default (a deep copy is taken inside evaluate / evaluate_sync)
result = evaluator.evaluate_sync(input)

# Per-call override still wins
result = evaluator.evaluate_sync(input, evaluation_settings=other_settings)
```

If you omit `default_evaluation_settings` at construction, attribute lookup uses the
subclass class attribute, same as before. Whenever you call `evaluate_sync()` or
`await evaluator.evaluate(...)` without `evaluation_settings`, the SDK uses
`model_copy(deep=True)` of the resolved default,
so the object you keep on the instance is not mutated by a run.

### Logging

The SDK uses Python's standard `logging` module. By default, `EvaluatorConfig` uses the
package logger `learning_commons_evaluators`, so log lines propagate to the root like
other libraries once your app configures handlers (for example `basicConfig` or
`dictConfig`).

```python
import logging

logging.basicConfig(level=logging.DEBUG)
# Optional: cap this library while the rest of the app stays DEBUG
logging.getLogger("learning_commons_evaluators").setLevel(logging.WARNING)

# Or route SDK logs through your own logger
my_logger = logging.getLogger("my_app.evaluators")
# create_config(..., logger=my_logger)

# Or use SDK helpers
from learning_commons_evaluators import (
    create_config_no_telemetry,
    create_logger,
    create_silent_logger,
    get_logger,
)

logger = create_logger(level=logging.DEBUG)  # stream handler on SDK subtree
sdk_logger = get_logger()  # same name as default config logger

# Discard evaluator log lines entirely
config = create_config_no_telemetry(logger=create_silent_logger())
```

## Error handling

Exceptions for evaluator failures, provider failures, and input validation inherit from `EvaluatorError`. Failures inside LLM prompt steps are wrapped at the boundary so callers see a predictable, sanitized hierarchy instead of raw LangChain, OpenAI, Anthropic, or HTTP-client exceptions. A few documented misuse paths still raise standard Python exceptions — for example `ValueError` from `execute_prompt_chain_step` when `json_dict_normalizer` is set without `parser_output_type`, and `RuntimeError` from `evaluate_sync()` when an asyncio event loop is already running on the current thread. Those are programmer errors, not evaluation failures.

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

- Retryable by default: `RateLimitError`, `NetworkError`, `RequestTimeoutError`, `OutputValidationError`, and any `APIError` with a 5xx status code.
- Not retryable: `ConfigurationError`, `InputValidationError`, `AuthenticationError`, and `APIError` with a 4xx status code.

`retryable` is also accepted as an `__init__` kwarg on `APIError` and `NetworkError` if you need to flag a specific instance differently (e.g. a permanently-bad hostname).

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

- `status_code` on `APIError` — HTTP status from the provider, when one was returned. Populated from the provider exception's `.status_code` attribute when present (preferred over message regex).
- `retry_after` on `RateLimitError` — suggested delay before retry, **in seconds**, or `None` if the provider didn't return a `Retry-After` header.
- `provider` on `APIError` — the `LLMProvider` being called when the failure occurred.
- `model` on `APIError` — the model ID requested.
- `response_body` on `APIError` — decoded response body. Opt-in for debugging; may contain echoed prompt content, so treat as sensitive.
- `request_id` on `APIError` — provider request ID, useful for support escalation.
- `validation_errors` on `OutputValidationError` — per-field details from Pydantic's `errors()` API with raw input values stripped (safe for logs).

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
    # Field-level errors are safe to log; raw LLM output is not in str(e).
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

On evaluation failure, `evaluation_metadata.status` is set to `failed` and `evaluation_metadata.error_details` is populated before `evaluate()` / `evaluate_sync()` re-raises (no result object is returned). `error_details` is itself sanitized:

- SDK errors record `"ClassName: <sanitized message>"`.
- Any other exception that escapes records only `"Unexpected error: ClassName"` — the message is omitted because arbitrary `ValueError`/`AttributeError`/etc. messages may contain user data or field values that aren't safe for telemetry.

The same policy applies to per-step `StepMetadata.error_details`. Both fields are emitted on the evaluation end log line.

## Creating custom evaluators

Extend `BaseEvaluator` to create custom evaluators. Set **class-level**
`default_evaluation_settings` for the usual defaults; callers may still construct
`MyEvaluator(config, default_evaluation_settings=...)` to pin different defaults on a
specific instance (see [Per-instance default evaluation settings](#per-instance-default-evaluation-settings)).

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
        maturity=EvaluatorMaturity.alpha,
    )
    default_evaluation_settings = MySettings(...)

    async def evaluate_impl(
        self,
        input: MyInput,
        evaluation_settings: MySettings,
        evaluation_metadata: EvaluationMetadata,
    ) -> EvaluationResult:
        # Use await self.execute_prompt_chain_step(...) for LLM calls
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

If you override `__init__` on the subclass, accept the same keyword-only argument and forward it: `super().__init__(config, default_evaluation_settings=default_evaluation_settings)`.

## License

MIT
