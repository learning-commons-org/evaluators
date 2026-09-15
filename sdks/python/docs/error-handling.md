# Error handling

Every failure the SDK raises during `evaluate()` / `evaluate_sync()` is a subclass of `EvaluatorError`. Failures inside LLM calls are classified at the evaluator boundary by `wrap_provider_error()`, so callers see one predictable hierarchy instead of raw OpenAI, Anthropic, Google, or `httpx` exceptions. **Programmer errors** (misusing the API, passing the wrong types) may still raise standard Python exceptions such as `TypeError`; only evaluation failures are wrapped.

The hierarchy, field names, and classification rules are the [SDK specification's](../../SPEC.md) §6 and are identical in the TypeScript SDK: an error caught in one SDK has the same class name and the same fields in the other.

## Hierarchy

Errors classify by **fault domain** — who must act — not by mechanism.

```
EvaluatorError                      (abstract; carries `retryable`)
├── ConfigurationError              caller: missing or invalid key, unknown provider or model, malformed settings
├── InputValidationError            caller: text or grade failed validation
│   └── StandardNotFoundError       caller: an academic-standard code the Knowledge Graph does not know (`statement_code`)
├── EvaluationError                 (abstract) the SDK's own logic failed after the dependency call succeeded
│   └── LLMOutputProcessingError    model output failed parsing or its output schema (`validation_errors`)
└── DependencyError                 (abstract) an external system failed (`dependency`, `status_code`, `request_id`, `model`)
    ├── AuthenticationError         401 / 403
    ├── RateLimitError              429 (`retry_after_ms`)
    ├── NetworkError                connection failure: DNS, refused, reset, TLS
    ├── RequestTimeoutError         the request exceeded its timeout, or a 408
    ├── LLMProviderError            catch-all for LLM-provider failures not mapped above
    └── KnowledgeGraphError         catch-all for Knowledge Graph failures not mapped above
```

The three abstract classes cannot be instantiated; they exist so you can catch a whole category. `InputValidationError` is named to avoid the collision with `pydantic.ValidationError`, and `RequestTimeoutError` to avoid shadowing the builtin `TimeoutError`.

## Knowing when to retry

`retryable` on the instance is the single signal to consult. It resolves as: an explicit per-instance override, else `True` for any 5xx status, else the class default.

| Class | Retryable | Strategy |
| --- | --- | --- |
| `ConfigurationError`, `InputValidationError`, `StandardNotFoundError` | No | Fix the call |
| `LLMOutputProcessingError` | Yes | Resample immediately: the failure is sampling variance, so waiting only adds latency |
| `AuthenticationError` | No | Fix the credential |
| `RateLimitError`, `NetworkError`, `RequestTimeoutError` | Yes | Back off, honouring `retry_after_ms` when present |
| `LLMProviderError`, `KnowledgeGraphError` | Only on 5xx | Back off |

Strategy follows the category: **external failures back off, internal failures resample.** The SDK applies both itself. The `max_retries` setting is handed to the native provider SDKs, which back off on their own retryable statuses and connection failures, and the evaluator resamples an `LLMOutputProcessingError` up to the same number of times. A retryable error that still reaches you has exhausted that budget.

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
        delay_ms = e.retry_after_ms if isinstance(e, RateLimitError) and e.retry_after_ms else 500 * 2**attempt
        time.sleep(delay_ms / 1000)
```

## Fields

Every `EvaluatorError` exposes `retryable`. `DependencyError` and its subclasses add:

- `dependency` — which service failed: `"openai"`, `"google"`, `"anthropic"`, `"knowledge-graph"`, or `"custom"` for a caller-injected provider.
- `status_code` — the HTTP status, or `None`.
- `request_id` — the dependency's request id for support escalation, read from `x-request-id`, `request-id`, or `x-amzn-requestid`, or `None`.
- `model` — the model id in use when the dependency is an LLM provider, or `None`.

`RateLimitError` adds `retry_after_ms`: the provider's `Retry-After` converted to milliseconds, `None` when absent, unusable (zero, negative, an HTTP-date), or implausible (capped at one hour). `LLMOutputProcessingError` adds `validation_errors`: pydantic's per-field failures reduced to `loc`, `type`, and numeric constraint context, with the rejected values and messages stripped so the list is safe to log.

`str(err)` is the message, which carries the provider's own wording for diagnosis. The original exception is always on `__cause__`, so tracebacks and `logging.exception()` keep full detail.

## How dependency failures are classified

`wrap_provider_error(error, dependency=..., model=...)` classifies by **structured signals only**: HTTP status codes, typed exceptions from the native SDKs, `httpx`, and the standard library, structured error payloads, and errnos, each searched along the exception's cause chain. Message text is never matched — wording is not a contract, and the catch-all is safer than a wrong class.

| Signal | Maps to |
| --- | --- |
| 404, or 400 whose body blames the model (`param: "model"` or `code: "model_not_found"`) | `ConfigurationError` |
| 401 / 403 | `AuthenticationError` |
| 429 | `RateLimitError`, with `retry_after_ms` |
| Typed connection failure (`httpx.NetworkError`, `ConnectionError`, `socket.gaierror`, `ssl.SSLError`, the SDKs' `APIConnectionError`, host/network-unreachable errnos) | `NetworkError` |
| Typed timeout (`httpx.TimeoutException`, `TimeoutError`, the SDKs' `APITimeoutError`, `ETIMEDOUT`) or 408 | `RequestTimeoutError` |
| `pydantic.ValidationError` or `json.JSONDecodeError` on a *successful* response | `LLMOutputProcessingError` |
| Anything else | `LLMProviderError`, retryable iff 5xx |

Two refinements: an unparseable body that arrived with an HTTP error status is the dependency's fault (the body is an error page, not a malformed completion), so it stays in the catch-all rather than being resampled against a failing service; and a provider's own retryability hint (`x-should-retry`) can only widen the catch-all's verdict, never make an `AuthenticationError` retryable or stop a `RateLimitError` from retrying.

```python
import logging

from learning_commons_evaluators import (
    DependencyError,
    LLMOutputProcessingError,
    RateLimitError,
)

log = logging.getLogger(__name__)
try:
    result = evaluator.evaluate_sync(input)
except RateLimitError as e:
    time.sleep((e.retry_after_ms or 30_000) / 1000)
except LLMOutputProcessingError as e:
    log.warning("Bad model output: %s", e.validation_errors)  # loc/type only, no model text
except DependencyError as e:
    log.error(
        "Dependency call failed",
        extra={"dependency": e.dependency, "model": e.model, "status": e.status_code, "request_id": e.request_id},
    )
    raise
```

For custom code that calls a provider outside the evaluators, `wrap_provider_error()` is exported so the same classification applies.
