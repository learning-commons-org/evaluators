# Error handling

During a normal `evaluate()` / `evaluate_sync()` run, failures from evaluator input checks, configuration, LLM prompt steps, and output validation typically surface as subclasses of `EvaluatorError`. Failures inside LLM prompt steps are wrapped at the boundary so callers see a predictable, sanitized hierarchy instead of raw LangChain, OpenAI, Anthropic, or HTTP-client exceptions. **Programmer errors** (such as misusing the API, passing the wrong types, or violating invariants) may still raise standard Python exceptions (e.g., `ValueError`, `TypeError`, `RuntimeError`). Only evaluation failures are wrapped; not all exceptions are guaranteed to be subclasses of `EvaluatorError`.

## Hierarchy

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

## Knowing when to retry

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

## Sanitization and debugging context

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

## Metadata and telemetry

On evaluation failure, the run metadata object (the same `EvaluationMetadata` attached as `result.metadata` on success) has `status` set to `failed` and `error_details` populated before `evaluate()` / `evaluate_sync()` re-raises. `error_details` is itself sanitized:

- SDK errors record only the class name (for example `"RateLimitError"`).
- Any other exception that escapes records only `"Unexpected error: ClassName"` — the message is omitted because arbitrary exception text may contain user data or field values that aren't safe for telemetry.

The same policy applies to per-step `StepMetadata.error_details`. Both fields are emitted on the evaluation end log line.

For custom code that calls LLM providers outside `execute_prompt_chain_step`, the package exports `wrap_provider_error()` to apply the same routing and sanitization rules.
