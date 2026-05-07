# Evaluator SDK Specification

This document is the source of truth for both the TypeScript and Python SDKs. It defines **what** each SDK must do — not how to do it. Implementation details (retry libraries, async patterns, type systems) are left to each language's idioms.

When the spec and an SDK diverge, the spec wins.

---

## 1. Config

Every evaluator accepts a config object at construction time.

| Field | Type | Default | Description |
|---|---|---|---|
| `google_api_key` | string | none | Google API key — required by evaluators whose `default_providers` includes `google` |
| `openai_api_key` | string | none | OpenAI API key — required by evaluators whose `default_providers` includes `openai` |
| `anthropic_api_key` | string | none | Anthropic API key — required when `model_override.provider` is `anthropic` |
| `model_override` | object | none | Override the provider and model for all LLM calls (see below) |
| `partner_key` | string | none | Learning Commons partner key, forwarded as auth in telemetry requests |
| `max_retries` | int | `2` | Max retry attempts on transient LLM failures. Total attempts = 1 + max_retries. Set to 0 to disable |
| `telemetry.enabled` | bool | `true` | Whether to fire telemetry events |
| `telemetry.record_inputs` | bool | `false` | Whether to include raw input text in telemetry. Off by default to avoid PII exposure |
| `logger` | object | none | Custom logger conforming to the SDK's `Logger` interface (`debug`/`info`/`warn`/`error`, each accepting `(message, context?)`). When provided, replaces the default console logger. |
| `log_level` | enum | `WARN` | Minimum log level for the default console logger: `DEBUG`, `INFO`, `WARN`, `ERROR`, `SILENT`. Ignored when a custom `logger` is provided. |

> **Language naming:** TypeScript uses camelCase (`googleApiKey`, `openaiApiKey`, `anthropicApiKey`, `modelOverride`, `partnerKey`, `maxRetries`, `logLevel`). Python uses snake_case. The `telemetry` field may be `true`/`false` as a shorthand for fully enabled/disabled, or an object for granular control.

### `model_override`

Overrides the provider and model used for all LLM calls within the evaluator.

```
model_override: { provider: Provider, model: string }
```

- `provider` must be one of the supported `Provider` values (see below)
- `model` is any model ID supported by that provider — must be a pinned snapshot ID (see section 7)
- When `model_override` is set, **only the API key for the override provider is required** — default provider key requirements are bypassed
- A warning is logged when override is active, since evaluators are validated against their default models
- Telemetry records `model_override: true` to flag override usage separately in analytics

### Provider

The set of supported LLM providers. Used in `model_override.provider` and evaluator `default_providers` metadata.

| Value | Description |
|---|---|
| `openai` | OpenAI (GPT models) |
| `google` | Google (Gemini models) |
| `anthropic` | Anthropic (Claude models) |

> **TS:** exported as a `Provider` enum. **Python:** a string literal type or equivalent enum.

---

## 2. Text Validation

Runs before every LLM call. Must run inside the error-handling boundary so validation failures are captured in telemetry.

Strip leading/trailing whitespace before measuring length. Then validate in this order:

- Whitespace-only input → `ValidationError("Text cannot be empty or contain only whitespace")`
- Length < min chars (trimmed) → `ValidationError("Text is too short. Minimum length is X characters...")`
- Length > max chars (trimmed) → `ValidationError("Text is too long. Maximum length is X characters...")`

Default limits:

| Limit | Default |
|---|---|
| `min_text_length` | `10` |
| `max_text_length` | `10,000` |

Limits may be overridden per-evaluator. When overridden, the evaluator's values apply. Overrides must not be silently ignored.

---

## 3. Grade Validation

- Grade must be in the evaluator's declared supported range → otherwise `ValidationError`
- Current evaluators all support grades **3–12**. No K, no 0–2.
- Type representation is language-idiomatic: strings in TypeScript (`"3"`), integers in Python (`3`)
- Early-fail: if the evaluator requires an API key that is absent, raise `ConfigurationError` at construction time, not at evaluation time

---

## 4. Result Shape

Every `evaluate()` call returns a result with three top-level objects: `answer`, `explanation`, and `metadata`.

### `answer`

| Field | Type | Description |
|---|---|---|
| `score` | any | Raw score value returned by the model (e.g. a string label or numeric value) |
| `label` | string | Human-friendly display label (e.g. `"Moderately complex"`) |

### `explanation`

| Field | Type | Description |
|---|---|---|
| `summary` | string | Model's reasoning — full explanation of how the score was determined |
| `details` | object | Full structured LLM output — all fields returned by the model, for all grade paths. Must be populated for every evaluator and every grade path. Must never be an empty object or omitted. |

### `metadata`

| Field | Type | Description |
|---|---|---|
| `model` | string | Model(s) used. Single provider: `"provider:model-id"`. Multi-provider: `"provider1:model1+provider2:model2"` (no spaces around `+`). Reflects the actual model used, including any override. |
| `processing_time_ms` / `processingTimeMs` | int | Wall-clock time for the full evaluation in milliseconds |

> **Language naming:** TypeScript uses camelCase (`processingTimeMs`). Python uses snake_case (`processing_time_ms`).

> **Migration note:** The TypeScript SDK currently returns `score`, `reasoning`, and `_internal` as top-level fields. It should be updated to match this shape.

> **TS naming:** `processingTimeMs`, `_internal`

---

## 5. Telemetry

### Semantics

- Must fire on every evaluation — both success and failure
- Fire-and-forget: never raises, never delays the return value
- When `telemetry.enabled = false`, no event is sent and no client is initialised

### Event Fields

| Field | Description |
|---|---|
| `timestamp` | ISO 8601 UTC |
| `sdk_version` | Package version string |
| `evaluator_type` | Evaluator ID (e.g. `"vocabulary"`) |
| `grade` | Grade passed by the caller; null if evaluator takes no grade |
| `status` | `"success"` or `"error"` |
| `error_code` | Error class name on failure; null on success |
| `latency_ms` | Total wall-clock time in milliseconds |
| `text_length_chars` | Character length of the input text |
| `provider` | Provider string(s) used. Same format as `metadata.model`: `"provider:model-id"` or `"provider1:model1+provider2:model2"` (no spaces around `+`) |
| `model_override` | `true` if `model_override` was set by the caller; omitted otherwise |
| `token_usage` | `{ input_tokens, output_tokens }` aggregated across all phases |
| `phase_details` | Array of per-phase objects (see below) |
| `input_text` | Raw input text — only when `telemetry.record_inputs = true` |

`partner_key` is forwarded as an authentication header on the request, not included in the event body.

### Phase Detail Fields

Each object in `phase_details`:

| Field | Description |
|---|---|
| `phase` | Phase name (e.g. `"background_knowledge"`, `"complexity_evaluation"`) |
| `provider` | `"provider:model-id"` |
| `latency_ms` | Wall-clock time for this phase |
| `token_usage` | `{ input_tokens, output_tokens }` |

---

## 6. Error Taxonomy

### Naming principle

Error class names must match across SDKs exactly as specified below. This ensures that documentation, error handling guides, and support answers are portable between languages without translation.

The only permitted divergence is a **builtin conflict** — when a name shadows a language builtin, prefix it with `Evaluator` (e.g. `TimeoutError` is a Python 3 builtin, so Python uses `EvaluatorTimeoutError`). Any such divergence must be documented in the permitted divergences table below.

If an error pattern is useful in one SDK, it must be implemented in both.

### Error classes

| Class | Code | Trigger | Retryable |
|---|---|---|---|
| `EvaluatorError` | — | Base class for all SDK errors | — |
| `ConfigurationError` | `CONFIGURATION_ERROR` | Missing required API key at construction | No |
| `ValidationError` | `VALIDATION_ERROR` | Invalid text or unsupported grade | No |
| `APIError` | — | Base class for all LLM provider errors | — |
| `AuthenticationError` | `AUTHENTICATION_ERROR` | 401 / 403 from provider | No |
| `RateLimitError` | `RATE_LIMIT_ERROR` | 429 from provider | Yes |
| `NetworkError` | `NETWORK_ERROR` | Connection failure | Yes |
| `TimeoutError` | `TIMEOUT_ERROR` | Request timeout | Yes |

### Fields

`APIError` and all its subclasses expose:

| Field | Type | Description |
|---|---|---|
| `statusCode` / `status_code` | `int \| null` | HTTP status code from the provider, if available |
| `retryable` | `bool` | Whether the caller may retry this error |

`RateLimitError` additionally exposes:

| Field | Type | Description |
|---|---|---|
| `retryAfter` / `retry_after` | `int \| null` | Milliseconds to wait before retrying, if the provider returned a value |

### Permitted divergences

| Spec class | TypeScript | Python | Reason |
|---|---|---|---|
| `TimeoutError` | `TimeoutError` | `EvaluatorTimeoutError` | `TimeoutError` is a Python 3 builtin |

### Cross-language error name reference

| Spec class | TypeScript | Python | Status |
|---|---|---|---|
| `EvaluatorError` | `EvaluatorError` | `EvaluatorError` | ✓ Both |
| `RetryableError` | `RetryableError` | `RetryableError` | ⚠ Python: rename from `EvaluatorRetryableError`; TS: not yet implemented |
| `ConfigurationError` | `ConfigurationError` | `ConfigurationError` | ✓ Both |
| `ValidationError` | `ValidationError` | `ValidationError` | ✓ Both |
| `APIError` | `APIError` | `APIError` | ✓ Both |
| `AuthenticationError` | `AuthenticationError` | `AuthenticationError` | ✓ Both |
| `RateLimitError` | `RateLimitError` | `RateLimitError` | ✓ Both |
| `NetworkError` | `NetworkError` | `NetworkError` | ✓ Both |
| `TimeoutError` | `TimeoutError` | `EvaluatorTimeoutError` | ✓ Both (permitted divergence) |

---

## 7. Implementation Rules

### Model IDs must be pinned to dated snapshots

No floating aliases. If a dated snapshot is not available for a given model, use the most specific stable identifier available and document it.

| Correct | Wrong |
|---|---|
| `gpt-4.1-2025-04-14` | `gpt-4.1` |
| `gpt-4o-2024-11-20` | `gpt-4o` |

### Structured output is the SDK's responsibility

Prompts must not contain LLM framework artifacts (e.g. injected JSON schema descriptions from `JsonOutputParser.get_format_instructions()`). Structured output enforcement belongs at the provider/chain layer.

> **Transitional note:** During the current Python SDK development phase, `{format_instructions}` may remain in prompts as a temporary LangChain compatibility measure. This will be removed when prompts are unified across SDKs and the Python SDK migrates to `.with_structured_output()`.

### FK score
Where FK score is used (see evaluator specs below), it must be computed using the Flesch-Kincaid Grade Level formula, rounded to 2 decimal places.

---

## 8. Evaluator Catalog

### Conventionality

| Property | Value |
|---|---|
| ID | `conventionality` |
| Supported grades | 3–12 |
| Default providers | `google` |
| Phases | 1 |
| Temperature | 0 |

| Phase | Model | Prompt inputs |
|---|---|---|
| `conventionality_evaluation` | `gemini-3-flash-preview` | text, grade, FK score |

---

### Vocabulary

| Property | Value |
|---|---|
| ID | `vocabulary` |
| Supported grades | 3–12 |
| Default providers | `google`, `openai` |
| Phases | 2 |
| Temperature | 0 (both phases) |

| Phase | Model | Prompt inputs |
|---|---|---|
| `background_knowledge` | `gpt-4o-2024-11-20` | text, grade |
| `complexity_evaluation` (grades 3–4) | `gemini-2.5-pro` | text, grade, background knowledge, FK score |
| `complexity_evaluation` (grades 5–12) | `gpt-4.1-2025-04-14` | text, grade, background knowledge |

> FK score is passed to the grades 3–4 complexity prompt only. The grades 5–12 prompt template does not use it.

**`internal` fields (all grades):** `complexity_score`, `reasoning`, `tier_2_words`, `tier_3_words`, `archaic_words`, `other_complex_words`

---

### Subject Matter Knowledge (SMK)

| Property | Value |
|---|---|
| ID | `subject-matter-knowledge` |
| Supported grades | 3–12 |
| Default providers | `google` |
| Phases | 1 |
| Temperature | 0 |

| Phase | Model | Prompt inputs |
|---|---|---|
| `smk_evaluation` | `gemini-3-flash-preview` | text, grade, FK score |

---

### Sentence Structure

| Property | Value |
|---|---|
| ID | `sentence-structure` |
| Supported grades | 3–12 |
| Default providers | `openai` |
| Phases | 2 |
| Temperature | 0 |

*(Full model and prompt details to be confirmed when Python implementation begins)*

---

### Grade Level Appropriateness (GLA)

| Property | Value |
|---|---|
| ID | `grade-level-appropriateness` |
| Grade parameter | None — GLA determines grade appropriateness, it does not take a grade as input |
| Default providers | `google` |
| Phases | 1 |
| Temperature | 0.25 |

| Phase | Model | Prompt inputs |
|---|---|---|
| `grade_evaluation` | `gemini-2.5-pro` | text |

---

## 9. Adding a New Evaluator

Before any implementation begins, the evaluator's entry in section 8 must be written and agreed upon by both SDK authors. The entry must specify: ID, supported grades, required keys, phase names, model IDs (pinned snapshots), prompt inputs, temperature, and `internal` fields.
