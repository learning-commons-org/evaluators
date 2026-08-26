# Evaluator SDK Specification

**Spec version:** 0.1.0 · **Changelog:** [Appendix D](#appendix-d-spec-changelog)

This document is the normative blueprint for all Learning Commons Evaluator SDKs — current (TypeScript, Python) and future. It defines **what** every SDK must do, not how. Implementation details (retry libraries, async patterns, type systems) are left to each language's idioms.

The spec is prescriptive, not descriptive: SDKs are brought into conformance with it, never the reverse. When the spec and an SDK diverge, the spec wins and the SDK carries the bug ([Appendix A](#appendix-a-known-conformance-gaps)).

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are to be interpreted as described in RFC 2119.

### Stability levels

Every section and evaluator definition carries a stability level; unlabeled content is **Stable**.

| Level | Meaning |
|---|---|
| **Stable** | Contract-bound; changes follow the compatibility policy (§12.3) |
| **Experimental** | May change or be removed without a deprecation window; users are warned in SDK docs |

New surfaces enter as Experimental and are promoted by maintainer agreement (§12.1) once at least one SDK ships them and contract fixtures (§11.3) cover them. Speed lives in Experimental; stability lives in Stable.

---

## 1. Design Principles

Every rule in this spec derives from one of these. When the spec is silent, decide by principle, then codify the decision here.

1. **One canonical name.** Every public identifier has exactly one canonical name, identical in every SDK and all documentation. Casing (§2.1) is the only permitted transformation; names are chosen, where practical, to avoid collisions with builtins and pervasive ecosystem names in target languages (`RequestTimeoutError`, not `TimeoutError`; `InputValidationError`, not pydantic's `ValidationError`).

2. **Idiomatic at the surface, identical at the core.** Types, async model, and packaging follow each language's conventions; behavior, names, and contracts are identical everywhere. When idiom and contract conflict, the contract wins and the gap is raised as a spec issue (§12.1).

3. **Universal envelope, evaluator-scoped payload.** Every result shares one envelope; the domain payload is defined per evaluator in the registry (§10), under shared invariants (§5.2).

4. **Fail fast, fail loud, fail structured.** Configuration problems surface at construction. Evaluation failures are canonical errors (§6) carrying retryability as data. Every error MUST be diagnosable from the error alone — silent fallbacks, swallowed causes, and generic messages are defects.

5. **Observability never affects results.** Telemetry and logging MUST NOT throw, block, delay, or change an evaluation's outcome.

6. **No hidden state.** The full structured model output MUST be surfaced in every result — never empty, never omitted.

7. **Sensitive data is opt-in at process boundaries.** Raw user-supplied input text MUST NOT leave the process — in telemetry or logs — unless the caller explicitly opts in; credentials and key fragments MUST NOT appear on any surface, ever. In-process error objects carry full diagnostic detail (§6.4). Model outputs, scores, and reasoning are product data and MAY be logged and reported.

8. **Determinism is declared.** Models are pinned to dated snapshots and temperatures declared; behavior changes only through deliberate registry updates (§10).

9. **Every unit is in the name.** Quantity fields carry a unit suffix (`_ms`, `_chars`, `_tokens`). The default unit for durations is milliseconds (`_ms`); any other unit is an explicit, documented exception.

10. **Core is required; capabilities are contracts.** §§3–8 are required for conformance. Optional capabilities (§9) are built only where an SDK's users need them — but to the spec'd contract when built.

11. **The spec is executable where possible.** Rules expressible as data or test vectors live in the shared fixtures (§11.3); prose states the principle, fixtures enforce it in CI.

---

## 2. Naming & Canonical Forms

### 2.1 Casing

The spec writes canonical names in `snake_case`. Each SDK maps them mechanically:

| Language | Fields / parameters | Classes | Example |
|---|---|---|---|
| TypeScript | `camelCase` | `PascalCase` | `model_override` → `modelOverride` |
| Python | `snake_case` | `PascalCase` | `model_override` → `model_override` |

Casing conversion MUST be purely mechanical — no renames, abbreviations, or reorderings.

### 2.2 Divergence convention

A name divergence is permitted **only** when the canonical name collides with a builtin, standard-library, or pervasive ecosystem name in a target language; stylistic preference is never grounds. The diverging SDK prefixes the most specific domain noun that resolves the collision, keeping the name guessable from the canonical one, and documents the mapping in its own reference docs.

Divergences are expected to be rare to zero — canonical names are chosen to avoid known conflicts up front. The table below mirrors any that occur, updated in the normal course of spec maintenance (not as a release gate):

**Registered divergences:** *none.*

### 2.3 Canonical value forms

Any **value** that crosses the SDK boundary into shared systems — results, telemetry — has exactly one canonical wire form, so data from different SDKs aggregates cleanly. SDKs MAY accept idiomatic conveniences on *input* (e.g. `int` grades in Python) when the mapping is unambiguous, but the canonical form is what appears in results and telemetry.

| Value | Canonical form |
|---|---|
| Grade | String token: `"3"` … `"12"` (the set may grow, e.g. `"K"`). Field naming: `grade_level` for a single grade, `grade_band` for a range |
| Timestamp | ISO 8601 UTC |
| Model | Model string (§3.4) |
| Error code | Canonical error class name (§6.1) |
| Evaluator ID | Registry ID (§10.1) |
| Durations / counts | Integer, unit-suffixed field name (Principle 9) |

A new value type that crosses the boundary MUST register its canonical form here or in the section that introduces it.

---

## 3. Configuration

Every evaluator accepts a config object at construction time.

| Field | Type | Default | Description |
|---|---|---|---|
| `google_api_key` | string | none | Required when `default_providers` includes `google` or `model_override.provider` is `google` |
| `openai_api_key` | string | none | Required when `default_providers` includes `openai` or `model_override.provider` is `openai` |
| `anthropic_api_key` | string | none | Required when `default_providers` includes `anthropic` or `model_override.provider` is `anthropic` |
| `learning_commons_api_key` | string | none | Learning Commons–issued key, authorizing Learning Commons API calls (e.g. Knowledge Graph). Never used for telemetry (§3.1) |
| `model_override` | object | none | Override provider and model for all LLM calls (§3.2) |
| `model_override.provider` | enum | — | A `Provider` value (§3.3) |
| `model_override.model` | string | — | Model ID for that provider, passed through as-is — the SDK does not validate its format (pinning §10.2 is a registry rule; override quality is the caller's responsibility) |
| `max_retries` | int | `2` | Retry attempts on retryable errors (§6.3). Total attempts = 1 + `max_retries`; `0` disables |
| `telemetry` | bool \| object | `true` | `true`/`false` shorthand, or an object for granular control |
| `telemetry.enabled` | bool | `true` | Whether to emit telemetry events |
| `telemetry.record_raw_inputs` | bool | `false` | Include verbatim user-supplied inputs in telemetry (Principle 7) |
| `telemetry.learning_commons_api_key` | string | none | Explicit opt-in to **identified** telemetry: sent as auth on telemetry requests, which the gateway resolves to the partner's Learning Commons user for event attribution. Unset → events are anonymous |
| `llm_provider` | object | none | *(Experimental)* Bring-your-own-provider: a caller-supplied provider client used for all LLM calls. Conflicts with `model_override` → `ConfigurationError` |
| `logger` | object | none | Custom logger implementing `Logger` (§7): `debug`/`info`/`warn`/`error`, each `(message, context?)`. Replaces the default console logger |
| `log_level` | enum | `WARN` | Minimum level for the **default** logger: `DEBUG`, `INFO`, `WARN`, `ERROR`, `SILENT`. Ignored when a custom `logger` is provided |

### 3.1 Keys: resolution and validation

- Credentials are **purpose-scoped**: a key is used only for the purpose its config location declares. The top-level `learning_commons_api_key` authorizes Learning Commons API calls; identified telemetry requires the separate `telemetry.learning_commons_api_key` declaration — the same value may be passed to both, but each use is opted into explicitly. SDKs MUST NOT repurpose a key across scopes.
- SDKs MUST NOT read credentials from the environment implicitly. Keys are passed explicitly in config; reading env vars (or vaults, or files) is the calling application's responsibility.
- An SDK MAY offer an explicit opt-in helper (e.g. `Config.from_env()`) that reads the documented canonical variable names — the env read is then a visible call the application made, never a constructor side effect.
- A key is *missing* if not provided or provided as the language's null/empty value.
- If a required key (per the evaluator's `default_providers`, or the `model_override` provider) is missing, the constructor MUST raise `ConfigurationError` — before any I/O.
- When `model_override` is set, **only** the override provider's key is required.

### 3.2 `model_override`

- The SDK MUST log a warning once, at construction, when an override is configured — evaluators are validated against their default models only. Per-evaluation log lines carry the effective model (§3.4); the warning is not repeated per call.
- Telemetry MUST record `model_override: true` on every evaluation (§8.2).
- A model-not-found rejection from the provider raises `ConfigurationError`, not a retryable API error.

### 3.3 `Provider`

The closed set of supported LLM providers, used in `model_override.provider`, `default_providers`, and model strings (§3.4). Each SDK exposes it as its idiomatic closed enumeration.

| Value | Description |
|---|---|
| `openai` | OpenAI (GPT models) |
| `google` | Google (Gemini models) |
| `anthropic` | Anthropic (Claude models) |

### 3.4 Model strings

Wherever a result or event reports which model ran:

- Single provider: `"provider:model-id"`
- Multiple providers: `"provider1:model1+provider2:model2"` — no spaces around `+`, in phase execution order.

Model strings MUST reflect the model **actually used**, including any override.

---

## 4. Input Validation

Validation runs before every LLM call, inside the error-handling boundary, so failures are captured in telemetry as `error` events.

### 4.1 Text

Trim leading/trailing Unicode whitespace, then validate in order:

1. Empty or whitespace-only → `InputValidationError("Text cannot be empty or contain only whitespace")`
2. Trimmed length < min → `InputValidationError` stating the minimum
3. Trimmed length > max → `InputValidationError` stating the maximum

Messages MUST convey the same facts (which bound, what the bound is) and SHOULD match the canonical wording. `text_length_chars` in telemetry is the **trimmed** length.

| Limit | Default |
|---|---|
| `min_text_length` | `1` |
| `max_text_length` | `10000` |

The SDK defaults carry no product opinion — `min_text_length: 1` only excludes empty input. Meaningful limits are per-evaluator registry values (§10); overrides MUST NOT be silently ignored.

### 4.2 Grade

- `grade_level` MUST be within the evaluator's declared supported range (§10) → otherwise `InputValidationError`.
- Grade validation exists **iff** grade is an input: grade-free evaluators (e.g. GLA) have no grade restrictions and MUST NOT silently consume a supplied grade. Grade-ranged *outputs* (e.g. GLA's bands) are fine and declared in the payload shape.

---

## 5. Evaluation Results

### 5.1 The envelope

Every `evaluate()` call resolves to:

| Field | Type | Description |
|---|---|---|
| `evaluator` | string | The evaluator's current registry `id` (§10.1); renames are resolvable via `id_history` |
| `result` | object | Evaluator-scoped payload (§5.2) |
| `metadata` | object | Operational metadata (below) |

`metadata`:

| Field | Type | Description |
|---|---|---|
| `model` | string | Model string(s) actually used (§3.4) |
| `processing_time_ms` | int | Wall-clock time for the full evaluation |
| `token_usage` | object | `{ input_tokens, output_tokens }` summed across all phases, without deduplication |

The envelope is identical for every evaluator, in every SDK, forever. New universal facts go in `metadata`; domain facts go in `result`.

### 5.2 Payload rules

The shape of `result` is defined per evaluator in its registry definition (§10.1) and MUST be identical across SDKs. No cross-evaluator shape taxonomy is specified (Q-2). Every payload MUST satisfy:

- The full structured model output is surfaced (Principle 6) — never an empty object, never omitted, on any grade path or code path.
- Individual payload fields MAY be optional or null where the declared shape says so; what is prohibited is withholding data the model returned, or an empty payload.
- Field names follow §2 (canonical, casing-mapped).
- The shape is declared in the evaluator's registry definition and covered by its contract fixtures (§11.3).
- Evaluators producing a single ordinal/categorical judgment SHOULD use the established conventions: `score`, `label`, `reasoning`, `details` — keeping the scored evaluators consistent without mandating the shape for evaluators it doesn't fit.

---

## 6. Errors

### 6.1 Canonical taxonomy

Class names are canonical in every SDK (§2.2). An error pattern useful in one SDK MUST be added here and implemented in all. Errors classify by **fault domain** — who must act — not by mechanism.

| Class | Extends | Fault domain / trigger | Retryable |
|---|---|---|---|
| `EvaluatorError` | — | Abstract base for all SDK errors | — |
| `ConfigurationError` | `EvaluatorError` | Caller: missing/invalid key, unknown provider or model, malformed settings | No |
| `InputValidationError` | `EvaluatorError` | Caller: text or grade failed validation (§4) | No |
| `EvaluationError` | `EvaluatorError` | Abstract base: the SDK's own evaluation logic failed after the dependency call succeeded | per class |
| `LLMOutputProcessingError` | `EvaluationError` | Model response failed parsing, normalization, or the expected output schema | Yes — immediate |
| `DependencyError` | `EvaluatorError` | Abstract base: an external system failed | per instance |
| `AuthenticationError` | `DependencyError` | 401 / 403 from the dependency | No |
| `RateLimitError` | `DependencyError` | 429 from the dependency | Yes — backoff |
| `NetworkError` | `DependencyError` | Connection failure (DNS, refused, TLS) | Yes — backoff |
| `RequestTimeoutError` | `DependencyError` | Request to the dependency exceeded its timeout | Yes — backoff |
| `LLMProviderError` | `DependencyError` | Catch-all for LLM-provider failures not mapped above | iff 5xx |
| `KnowledgeGraphError` | `DependencyError` | Catch-all for Knowledge Graph service failures not mapped above | iff 5xx |

- Abstract bases (`EvaluatorError`, `EvaluationError`, `DependencyError`) MUST NOT be instantiated directly — they exist so callers can branch on category.
- `InputValidationError` (caller's fault, never retryable) and `LLMOutputProcessingError` (model's fault, retryable — LLMs are nondeterministic) MUST NOT be merged.
- Fault domain decides classification, not subsystem: a caller-supplied unknown standards code is `InputValidationError`, even though the Knowledge Graph reports it.

**Extending to a new dependency:** reuse the shared subclasses (auth, rate-limit, network, timeout) — which system failed is data (`dependency`, §6.2), not a class. A new external system MAY add exactly one catch-all leaf under `DependencyError`, registered in the table above before it ships. No deeper per-integration hierarchies.

### 6.2 Fields

`DependencyError` and all subclasses:

| Field | Type | Description |
|---|---|---|
| `dependency` | string | Canonical ID of the failed system: a `Provider` value (§3.3) or a service ID (e.g. `"knowledge-graph"`) |
| `status_code` | int \| null | HTTP status from the dependency, if available |
| `retryable` | bool | Whether the caller may retry (§6.3) |
| `request_id` | string \| null | Dependency's request ID, for support escalation |
| `model` | string \| null | Model ID in use, when the dependency is an LLM provider |

`RateLimitError` additionally: `retry_after_ms` (int | null) — milliseconds to wait, converted from the provider's `Retry-After` seconds.

`LLMOutputProcessingError` additionally: `validation_errors` (array | null) — per-field failures as schema locations and error types.

### 6.3 Retryability is data; strategy follows the category

- `retryable` on the instance is the single source of truth; callers never memorize the hierarchy.
- Resolution order: explicit per-instance override → `true` for any 5xx → class default.
- Strategy is category-bound: **external failures back off, internal failures resample.** Retryable `DependencyError`s use exponential backoff with jitter, honoring `retry_after_ms` — the dependency is constrained and immediate retry worsens contention. Retryable `EvaluationError`s retry immediately — the failure is sampling variance, and waiting only adds latency.
- The SDK's retry loop (`max_retries`, §3) retries **only** retryable errors, applying the category's strategy.

### 6.4 Trust boundaries

The SDK caller is a code owner who already holds the API keys and inputs; diagnostic detail is theirs. What is limited is what leaves the process by default.

| Surface | Policy |
|---|---|
| Exception attributes + cause chain | Full diagnostic detail MUST be preserved: original exception and stack trace via the language's cause chain, plus structured attributes (§6.2) and allowlisted upstream diagnostics (provider message/code/reason) when structured payloads carry them |
| Error message | MUST be diagnosable and actionable on its own; MAY include input-derived detail where it aids diagnosis; MUST NOT contain credentials or key fragments — messages propagate by default (app logs, error trackers, HTTP responses) |
| Logs | No raw input text above `DEBUG` (§7) |
| Telemetry | Error class name and sanitized schema facts (field paths, error types) only; raw input only via `telemetry.record_raw_inputs` (§8) |

### 6.5 Dependency error mapping

Classify by **structured signals only** — status code, typed exception, structured error payloads (codes/reasons, walking the cause chain). Free-text message matching MUST NOT reclassify an error: wording is not a contract, and a misclassification is worse than the catch-all. Text-only failures stay in the dependency's catch-all class.

| Signal | Maps to |
|---|---|
| 404, or 400 with structured model-not-found semantics | `ConfigurationError` |
| 401 / 403, or structured auth codes | `AuthenticationError` |
| 429 | `RateLimitError` |
| Connection-level failure (typed) | `NetworkError` |
| Timeout (typed or 408) | `RequestTimeoutError` |
| Schema-invalid or unparseable model output | `LLMOutputProcessingError` |
| Anything else | Dependency catch-all (`LLMProviderError`, `KnowledgeGraphError`, …), retryable iff 5xx |

---

## 7. Logging

The canonical `Logger` interface:

```
Logger:
  debug(message: string, context?: LogContext): void
  info(message: string, context?: LogContext): void
  warn(message: string, context?: LogContext): void
  error(message: string, context?: LogContext): void
```

`LogContext` is a string-keyed map. Reserved keys (always safe to emit): `evaluator`, `operation`, `error`. Model outputs and scores may be logged (Principle 7); raw user input text MUST NOT appear above `DEBUG`.

- With a custom `logger`, the SDK routes all output through it and MUST NOT apply `log_level` filtering — level policy belongs to the custom logger.
- A logger that throws MUST NOT fail the evaluation (Principle 5); the SDK swallows logger exceptions.
- `log_level: SILENT` disables the default logger entirely.

---

## 8. Telemetry

### 8.1 Semantics

- One event per evaluation — on success **and** failure, including validation failures.
- Fire-and-forget: emission MUST NOT throw or delay the return value, and is abandoned if the endpoint is unreachable. SDKs SHOULD bound in-flight telemetry with a timeout of a few seconds.
- When disabled: no event constructed, no client initialized.
- `telemetry.learning_commons_api_key` is sent as an authentication header on the request — never in the event body. When unset, events are anonymous. The top-level `learning_commons_api_key` MUST NOT be used for telemetry (§3.1). Telemetry auth failures are logged at `DEBUG` and otherwise ignored.

### 8.2 Event fields *(Experimental)*

| Field | Description |
|---|---|
| `timestamp` | ISO 8601 UTC |
| `sdk_version` | Package version string |
| `evaluator_type` | Evaluator ID (§10.1) |
| `grade` | Canonical grade token; null if the evaluator takes no grade |
| `status` | `"success"` or `"error"` |
| `error_code` | Canonical error class name on failure; null on success |
| `latency_ms` | Total wall-clock time |
| `text_length_chars` | Trimmed input length |
| `model` | Model string(s) used (§3.4) |
| `model_override` | `true` if an override was set; omitted otherwise |
| `token_usage` | `{ input_tokens, output_tokens }` aggregated across phases |
| `phase_details` | Array of per-phase objects (§8.3) |
| `input_text` | Raw input — **only** when `telemetry.record_raw_inputs = true` |

### 8.3 Phase details *(Experimental)*

Each entry: `phase` (name from the registry definition), `model` (`"provider:model-id"`), `latency_ms`, `token_usage` (`{ input_tokens, output_tokens }`).

---

## 9. Optional Capabilities

No SDK is required to build these — they exist where that SDK's users need them. Any SDK that ships one MUST implement the contract below (Principle 10). New capabilities are added here before the first SDK ships them.

### 9.1 Batch evaluation *(Experimental)*

- **Never throws for item failures.** Per-item failures are returned as structured entries alongside successes.
- **Order-aligned results.** Results align index-for-index with inputs; failed items occupy their slot with the canonical error information (§6).
- **Fail-fast only for batch-level faults.** Configuration errors and invalid batch arguments raise before any item is evaluated.
- **Summary stats:** `total`, `successful`, `failed`, `average_processing_time_ms`.
- **Per-item telemetry.** Each item fires its own event exactly as a single evaluation (§8); no batch-level rollup event.
- **Bounded concurrency.** MUST bound concurrent provider calls; SHOULD expose the bound as an option.
- **Naming:** `evaluate_items` (TS: `evaluateItems`).

---

## 10. Evaluator Registry

Evaluator definitions are shared, language-neutral data: one definition per evaluator, consumed by every SDK, so evaluation behavior cannot drift between languages. Registry home and format: Q-6.

### 10.1 Definition schema

A definition MUST specify:

| Field | Meaning |
|---|---|
| `id` | Human-readable dotted identifier (e.g. `student_facing_text.ela_reading.background_knowledge_demands`). Appears in results and telemetry. MAY be renamed — names are not the identity |
| `stable_id` | Immutable UUID assigned at creation. The identity that survives renames; consumers aggregating across time key on it |
| `id_history` | Ordered list of prior `id` values, mapping old names to the current one |
| Stability | Stable or Experimental |
| Payload shape | The `result` shape (§5.2), field by field |
| Supported grades | Range of canonical grade tokens, or none for grade-free evaluators |
| Default providers | Drives key requirements (§3.1) |
| Phases | Ordered phase names; per phase: pinned model ID (§10.2), prompt inputs, temperature |
| Text limits | Only when overriding the §4.1 defaults |

Grade-path variants (different model or prompt inputs per grade band) are expressed within the phase definitions.

### 10.2 Model IDs are pinned snapshots

No floating aliases (Principle 8): `gpt-4o-2024-11-20`, not `gpt-4o`. If no dated snapshot exists, use the most specific stable identifier and note it in the definition.

This is a **registry authoring rule**, enforced by registry-side validation (schema checks, fixtures) — SDKs consume definitions as-is and do not re-validate them at runtime. The SDK's only duty: if the provider rejects a model ID, fail fast with `ConfigurationError` — never silently substitute. Model migrations are deliberate registry updates.

### 10.3 Prompts and structured output

Prompts MUST NOT contain LLM-framework artifacts (e.g. injected JSON-schema text). Structured output enforcement belongs at the provider/chain layer; a schema-invalid response raises `LLMOutputProcessingError`.

### 10.4 Derived inputs

Computed prompt inputs are part of the contract. Where FK score is used, it MUST be the Flesch-Kincaid Grade Level formula, rounded to 2 decimal places. New derived inputs MUST define their computation here or in the registry definition.

---

## 11. Process

### 11.1 Adding a new evaluator

Before implementation begins, the evaluator's registry definition (§10.1) MUST be written and approved by maintainers of every SDK — the definition PR is the agreement artifact.

### 11.2 Adding a new SDK

A new SDK claims conformance by satisfying the checklist and passing the shared contract fixtures (§11.3). Optional capabilities are conformant if absent or implemented per contract. Per-SDK status is tracked in [Appendix B](#appendix-b-conformance-matrix).

| # | Criterion |
|---|---|
| C-1 | Config surface per §3, casing-mapped per §2.1; construction fails fast per §3.1 |
| C-2 | Full canonical error taxonomy (§6.1) with fields (§6.2), data-driven retryability (§6.3), safe messages (§6.4), provider mapping (§6.5) |
| C-3 | Input validation order, messages, and limits per §4 |
| C-4 | Result envelope (§5.1) and payload invariants (§5.2) for every implemented evaluator |
| C-5 | Logger interface and behavior per §7 |
| C-6 | Telemetry semantics and event schema per §8 |
| C-7 | Derived-input computation and structured-output enforcement per §10.3–10.4 (registry authoring rules in §10.2–10.3 are validated registry-side, not by SDKs) |
| C-8 | Every implemented evaluator matches its registry definition (§10.1) and passes its contract fixtures (§11.3) |
| C-9 | Any name divergence follows §2.2 (expected: none) |
| C-10 | SDK declares the spec version it implements (§12.2) |

### 11.3 Contract fixtures — the executable spec

Cross-SDK behavior is verified by shared, language-neutral fixture files (per-evaluator cases plus spec-level fixtures for cross-cutting rules), executed by a per-language harness in each SDK's CI. The fixture format lives with the registry (Q-6).

- Every SDK MUST run the fixtures for each evaluator and capability it implements; a fixture failure is a conformance failure.
- A spec change that alters observable behavior MUST land with fixtures expressing it. Prose without fixtures is a **SHOULD**, not a MUST, until fixtures exist.
- Minimum coverage: input-validation outcomes and messages (§4), error mapping (§6.5), model strings (§3.4), envelope and payload shapes (§5), telemetry event shape (§8.2).
- Fixtures MUST NOT require live provider calls; they run against recorded/stubbed provider behavior.

---

## 12. Spec Lifecycle

### 12.1 Governance

- The spec changes by pull request, approved by at least one maintainer of **each** SDK; small clarifications need one maintainer.
- Substantive proposals SHOULD start as a short design note in the PR: motivation, alternatives, migration impact per SDK.
- Every normative change adds a changelog line ([Appendix D](#appendix-d-spec-changelog)).
- Open design questions live in [Appendix C](#appendix-c-open-questions) — promoted into the spec or closed with a recorded rationale, never silently dropped.

### 12.2 Versioning

- The spec is SemVer-versioned, independent of SDK packages. Pre-1.0, minor bumps may break; post-1.0, breaking changes to Stable content require a major bump.
- Each SDK release declares the spec version it implements (README and package metadata), so users reason about cross-SDK equivalence by spec version.

### 12.3 Compatibility policy for Stable content

Breaking is judged from the **user's** point of view:

- **Non-breaking:** adding fields to results, events, or config; adding evaluators, error subclasses, or capabilities; widening accepted inputs; improving error messages within §4.1's same-facts rule.
- **Breaking (major bump + deprecation):** removing or renaming any public name; changing a field's type, unit, or semantics; narrowing accepted inputs; changing a registry definition's models, phases, or temperature in a way that changes evaluation results.
- Consumers of results, events, and registry data MUST treat unknown fields as forward-compatible (ignore, don't fail).

**Deprecation:** a renamed or removed surface keeps a working, warning-emitting alias for at least one minor release of every affected SDK.

**Evaluation-behavior changes** (model or prompt updates) are versioned in the registry and communicated in SDK changelogs even when the API is unchanged — users experience a score shift as a breaking change, whatever SemVer says.

---

## Appendix A: Known Conformance Gaps

Tracked deviations between this spec and the current SDKs — each a bug to fix on the road to 1.0, not a precedent.

> **Snapshot as of 2026-08-18.** Several SDK PRs are in flight; refresh this table (and Appendix B) as they land.

| # | Spec section | SDK | Gap | Required change |
|---|---|---|---|---|
| 1 | §6.1 | TypeScript | `TimeoutError` instead of `RequestTimeoutError` | Rename |
| 2 | §6.1 | TypeScript | Single `ValidationError`; no output-processing class | Split into `InputValidationError` / `LLMOutputProcessingError` |
| 3 | §6.2 | TypeScript | `retryAfter` unsuffixed | Rename to `retryAfterMs` |
| 4 | §6.2 | Python | `retry_after` in seconds | Rename to `retry_after_ms`, convert to milliseconds |
| 5 | §5.1 | TypeScript | Flat `score`/`reasoning`/`metadata`/`_internal`; flat `inputTokens`/`outputTokens` | Migrate to envelope; nest `token_usage` |
| 6 | §5.1 | Python | Bespoke Pydantic result shapes | Migrate to envelope |
| 7 | §8.3 | Python | `step_details` / `step` naming | Rename to `phase_details` / `phase` |
| 8 | §6.4–6.5 | TypeScript | `wrapProviderError` classifies via message regexes and lacks cause preservation | Structured-signal classification; preserve cause chain and structured attributes |
| 9 | §6.1 | Python | Legacy `EvaluatorRetryableError` references | Remove aliases not in the taxonomy |
| 10 | §9.1 | TypeScript | Math Standards Alignment batch unverified against contract | Audit per §9.1 |
| 11 | §3 | Both | `partner_key`/`platformApiKey` naming; TS falls back `partnerKey ?? platformApiKey`, silently repurposing the KG key for telemetry attribution | Rename to `learning_commons_api_key`; add `telemetry.learning_commons_api_key`; remove the cross-scope fallback |
| 12 | §10 | Both | No shared registry; evaluator definitions duplicated in each SDK's code | Establish the registry (Q-6) and migrate definitions |
| 13 | §10.1 | Both | Evaluator IDs are flat (`vocabulary`), not namespaced | Adopt hierarchical IDs once the taxonomy is finalized (Q-7) |
| 14 | §11.3 | Both | No shared fixture format or cross-SDK harness (Python has an early harness tied to a temporary layout) | Establish fixture format with the registry; build per-language harnesses |
| 15 | §10.3 | Python | `{format_instructions}` LangChain placeholders remain in prompts | Remove; enforce structured output at the chain layer |
| 16 | §8.2–8.3 | Both | Telemetry field `provider` carries model strings | Rename to `model` in events and phase details |
| 17 | §6.1–6.2 | Both | `APIError` shape: no `EvaluationError`/`DependencyError` categories, no catch-all leaves, no `dependency` field; TS `KnowledgeGraphError` sits outside the taxonomy | Restructure to the fault-domain taxonomy; re-parent `KnowledgeGraphError` under `DependencyError` |
| 18 | §4.1 | Both | `min_text_length` default is 10 | Change SDK default to 1; meaningful minimums move to registry definitions |
| 19 | §4.2 | Both | Grade parameter named `grade` | Rename to `grade_level` (SDK surfaces; several evaluators already standardized) |

---

## Appendix B: Conformance Matrix

Per-SDK status against §11.2, updated whenever a gap closes or a new SDK lands. ✓ conformant · ◐ partial · ✗ not yet.

> **Snapshot as of 2026-08-18** — refresh alongside Appendix A.

| Criterion | TypeScript | Python |
|---|---|---|
| C-1 Config | ◐ (gap 11) | ◐ (gap 11) |
| C-2 Errors | ✗ (gaps 1–3, 8) | ◐ (gaps 4, 9) |
| C-3 Input validation | ◐ | ◐ |
| C-4 Envelope & payload | ✗ (gap 5) | ✗ (gap 6) |
| C-5 Logging | ✓ | ◐ |
| C-6 Telemetry | ◐ | ✗ (gap 7) |
| C-7 Registry rules | ◐ | ◐ |
| C-8 Registry + fixtures | ✗ (gaps 12–14) | ✗ (gaps 12–14) |
| C-9 Divergences | ✓ | ✓ |
| C-10 Spec version declared | ✗ | ✗ |

---

## Appendix C: Open Questions

| # | Question | Notes |
|---|---|---|
| Q-1 | ~~Should SDKs read API keys from environment variables as a fallback to explicit config?~~ | **Resolved (§3.1):** never implicitly — env reads are the application's responsibility; SDKs MAY offer an explicit `from_env()` helper |
| Q-2 | Payload shape taxonomy — should evaluator families (QTC, feedback, standards alignment, …) share declared payload profiles? | Deliberately deferred (§5.2); revisit once feedback and math evaluator classes mature |
| Q-3 | Should registry definitions carry a version (prompt/model revision) surfaced in result `metadata`? | Would let users pin/detect evaluation-behavior changes (§12.3) programmatically |
| Q-4 | Per-rule requirement IDs (OpenFeature-style `[ERR-3]`) | Adopt if fixtures and docs need finer-grained references than section numbers |
| Q-5 | Timeout defaults and configurability (`timeout_ms` in config?) | `RequestTimeoutError` exists but no canonical timeout knob is specified |
| Q-6 | Registry home and format: where do shared evaluator definitions and contract fixtures live, and how do SDKs consume them? | Early Python settings/contract-file work is the design input; its temporary layout is not the answer |
| Q-7 | ~~Evaluator ID taxonomy~~ | **Resolved (§10.1):** identity is `stable_id` (UUID) + `id_history`; the readable dotted `id` may be renamed freely, so its segments carry no stability burden |
| Q-8 | ~~Telemetry tracking field semantics~~ | **Resolved (§3, §8.1):** identified telemetry via explicit `telemetry.learning_commons_api_key` (gateway resolves the LC user); no separate tracking field |
| Q-9 | Anonymous telemetry identity: should the spec define the SDK-generated `client_id`, and where does it travel (header vs event body)? | TS ships a persisted per-install UUID sent as `X-Client-ID`, but nothing downstream reads it — all anonymous events share one `anonymousId`. Needs the collector-side design before the spec commits |
| Q-10 | Finalize the telemetry event schema (§8.2–8.3, Experimental) and migrate spec + TypeScript SDK + collector in one coordinated change | Spec says `phase`, Python internals say `step`, the deployed collector says `stage` inside a `metadata` wrapper. Recorded recommendations: `step`/`step_details` top-level (registry vocabulary follows); per-input `inputs` map with gated `raw` replacing `input_text`/`text_length_chars`; adopt `sdk_language`; `evaluator_type` → `evaluator`; per-step `error_code` replacing `schema_validation_failed`; absent = omitted, never null; unify `latency_ms`/`processing_time_ms` |

---

## Appendix D: Spec Changelog

| Version | Date | Changes |
|---|---|---|
| 0.1.0 | 2026-08-18 | Initial formalization: principles, naming + canonical value forms, envelope + payload invariants, canonical error taxonomy, telemetry/logging contracts, optional-capability tier, evaluator registry direction, contract-fixture mechanism, lifecycle & governance |
