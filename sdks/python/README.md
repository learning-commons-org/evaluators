# learning-commons-evaluators (Python)

[![PyPI version](https://img.shields.io/pypi/v/learning-commons-evaluators)](https://pypi.org/project/learning-commons-evaluators/)

Python SDK for [Learning Commons evaluators](https://docs.learningcommons.org/evaluators/understanding-evaluators/introduction) — sixteen LLM-backed evaluators for the complexity of text students read, the quality of feedback they receive, and the alignment of math items to standards.

Every evaluator is built from its shared contract under [`evals/`](../../evals) (prompts, models, schemas) and returns the same result envelope as the [TypeScript SDK](../typescript), so a payload is identical whichever SDK produced it.

## Installation

```bash
pip install learning-commons-evaluators
```

Requires **Python 3.11+**. Provider API keys are passed in explicitly; the SDK never reads
them from the environment, so setting `GOOGLE_API_KEY` in your shell does not satisfy
`google_api_key`. Omitting a key an evaluator needs raises `ConfigurationError` at
construction, before any I/O.

## Quick start

```python
from learning_commons_evaluators import PurposeClarityEvaluator, read_outcome

evaluator = PurposeClarityEvaluator(google_api_key="your-google-key")

evaluation = evaluator.evaluate_sync(
    text="Trees are important plants that grow in many parts of the world. ...",
    grade_level=5,
)

print(evaluation.result.complexity_score)   # e.g. "slightly_complex"
print(evaluation.result.reasoning)
print(evaluation.metadata.model)            # "google:gemini-3-flash-preview"

outcome = read_outcome(evaluation, PurposeClarityEvaluator.metadata.outcome)
print(outcome.score)                        # the same verdict, as one comparable string
```

`await evaluator.evaluate(...)` is the primary form; `evaluate_sync` wraps it for
synchronous code. Inputs are the contract's names (`text`, `grade_level`, `student_text`,
`feedback_text`), passed as keywords or as the evaluator's typed input model
(`PurposeClarityInput`).

Every evaluator resolves to the same three-part envelope, so generic code works across all
sixteen:

```python
class EvaluationResult(BaseModel):
    evaluator: str                     # registry id, e.g. "text_complexity.ela_reading.vocabulary_complexity"
    result: ResultT                    # the evaluator's own payload, exactly as its output schema declares it
    metadata: EvaluationMetadata


class EvaluationMetadata(BaseModel):
    model: str                         # "provider:model" that ran; "a+b" when several did
    processing_time_ms: int
    token_usage: EvaluationTokenUsage  # .input_tokens, .output_tokens
```

`result` is the model's structured output with keys and values unaltered. An evaluator whose
contract declares several steps sums the token usage across them, and `model` names every
model that ran, joined with `+`. Which models run can depend on the input: Vocabulary
Complexity takes a different branch for grades 3–4 than for 5–12, but construction validates
the union of keys it could need, so it demands both keys at any grade.

When you want one comparable value per evaluation regardless of evaluator, use
`read_outcome`. `score` is always a string, or `None` for an evaluator that declares no
single verdict — which today means Math Standards Alignment.

## Evaluators

**Text complexity** — how demanding a text is for a given grade. Each takes
`{ text, grade_level }` and returns a `complexity_score` on a four-level scale —
`slightly_complex`, `moderately_complex`, `very_complex`, `exceedingly_complex` — with
`reasoning`. Purpose Clarity has a fifth value, `more_context_needed`, so a match over the
four above is not exhaustive for it. Payloads carry more than the verdict, and how much
varies: Vocabulary Complexity adds `tier_2_words`, `tier_3_words`, `archaic_words` and
`other_complex_words`; only Sentence Structure returns just the score and reasoning. Each
evaluator's payload model (`VocabularyComplexityOutput` and so on) is the authoritative shape.

| Evaluator | Grades | Default provider | Docs |
| --- | --- | --- | --- |
| `BackgroundKnowledgeDemandsEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/background-knowledge-demands) |
| `MeaningDirectnessEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/meaning-directness) |
| `OrganizationalStructureEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/organizational-structure) |
| `PurposeClarityEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/purpose-clarity) |
| `ReferenceKnowledgeDemandsEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/reference-knowledge-demands) |
| `SentenceStructureEvaluator` | 3–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/sentence-structure) |
| `VocabularyComplexityEvaluator` | 3–12 | OpenAI + Google | [Link](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/vocabulary-complexity) |

**Grade band** — takes `{ text }` only, and determines the grade rather than judging against
one. Returns `grade_band`, `alternative_grade_band`, `scaffolding_needed`, `reasoning`. Bands
are `K-1`, `2-3`, `4-5`, `6-8`, `9-10`, `11-12` — spans on the CCSS text-complexity scale, not
single grades.

| Evaluator | Grades | Default provider | Docs |
| --- | --- | --- | --- |
| `GradeLevelAppropriatenessEvaluator` | K–12 | Google | [Link](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/grade-level-appropriateness) |

**Feedback quality** — judges a teacher comment on a student's writing. Each takes
`{ student_text, feedback_text }` and returns a binary `quality_score` (the integer `0` or
`1`, not a bool) with `reasoning`, `key_features` and `proposed_adjustment`. `key_features` is
a model, not a dict, and **its criterion keys differ per evaluator** — Tone Appropriateness
declares `neutral_professional_language`, `targets_work_not_student` and
`praise_proportionate_to_work`. Read them with
`list(ToneAppropriatenessOutput.model_fields["key_features"].annotation.model_fields)`.

| Evaluator | Grades | Default provider | Docs |
| --- | --- | --- | --- |
| `RevisionAccuracyEvaluator` | 6–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/feedback-evaluators/revision-accuracy) |
| `RevisionActionabilityEvaluator` | 6–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/feedback-evaluators/revision-actionability) |
| `RevisionManageabilityEvaluator` | 6–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/feedback-evaluators/revision-manageability) |
| `StrengthAcknowledgmentEvaluator` | 6–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/feedback-evaluators/strength-acknowledgment) |
| `StudentResponseSpecificityEvaluator` | 6–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/feedback-evaluators/student-response-specificity) |
| `ToneAppropriatenessEvaluator` | 6–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/feedback-evaluators/tone-appropriateness) |
| `WithholdingAnswersEvaluator` | 6–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/feedback-evaluators/withholding-answers) |

**Standards alignment** — checks a math item against a standard, component by component.
See [Math Standards Alignment](#math-standards-alignment) below, which has two entry points.

| Evaluator | Grades | Default provider | Also needs | Docs |
| --- | --- | --- | --- | --- |
| `MathStandardsAlignmentEvaluator` | K–12 | Anthropic | `learning_commons_api_key` (Knowledge Graph) | [Link](https://docs.learningcommons.org/evaluators/academic-standards-evaluators/math-standards-alignment) |

## Discovering evaluators

Every evaluator is listed in a registry, keyed by the registry id that appears on each result:

```python
from learning_commons_evaluators import get_evaluator, get_evaluators

for m in get_evaluators():
    print(f"{m.name} ({m.id}) — grades {', '.join(m.supported_grades)}")

# Renamed ids still resolve, so a stored result stays identifiable.
get_evaluator("conventionality").name          # "Meaning Directness Evaluator"
get_evaluator("grade-level-appropriateness").id  # "text_complexity.ela_reading.grade_level_appropriateness"
```

Both return `EvaluatorMetadata` — `id`, `stable_id`, `id_history`, `name`, `description`,
`supported_grades`, `default_providers`, `required_credentials`, and `outcome` where the
evaluator declares a single verdict. `required_credentials` lists only **non-LLM** services —
it is `("learning_commons_api_key",)` for math standards alignment and empty for the other
fifteen, so it is not the answer to "which keys does this need". Provider keys follow
`default_providers`: `(Provider.GOOGLE,)` means supply `google_api_key`. To *run* an
evaluator, import it by name — the metadata does not say which named inputs it takes, and
each evaluator's are different.

## Configuration

Pass an `EvaluatorConfig` or its fields as keyword arguments:

| Field | Default | Purpose |
| --- | --- | --- |
| `google_api_key`, `openai_api_key`, `anthropic_api_key` | none | Required for the provider(s) the evaluator's contract declares. A missing one raises `ConfigurationError` at construction. |
| `learning_commons_api_key` | none | Learning Commons API calls (Knowledge Graph); only evaluators that declare it need it. |
| `model_override` | none | `ModelOverride(provider, model)`: run every LLM step on this model instead. Logged once as a warning; evaluators are validated against their default models only. |
| `max_retries` | `2` | Retries on retryable errors; total attempts are `1 + max_retries`. |
| `telemetry` | `True` | `True` / `False`, or `TelemetryOptions(enabled, learning_commons_api_key)`. |

Old evaluator ids still resolve: `get_evaluator("grade-level-appropriateness")` finds the evaluator now registered as `text_complexity.ela_reading.grade_level_appropriateness`.

### Telemetry

One event per evaluation, on success and on failure. Telemetry never includes the text you
evaluate: the event carries its length, the evaluator, the grade level you passed, the provider
and model, latency, status, any error class name, token counts, and the SDK version. There is no
option to send the text itself.

Events are anonymous, attributed to a client id kept in `~/.config/learning-commons/config.json`
(`%APPDATA%\learning-commons\config.json` on Windows), which is the same file the TypeScript SDK
uses. Setting `TelemetryOptions(learning_commons_api_key=...)` attributes them to your Learning
Commons user instead.

Sending is fire-and-forget on a background thread: it never blocks an evaluation, never changes a
result, and never raises. Failures are logged at `warning`, so a restricted-egress environment
sees a warning per evaluation at the default level; `telemetry=False` silences it, and builds no
telemetry client at all.

### Knowledge Graph

Evaluators that align to academic standards read them from the
[Learning Commons Knowledge Graph](https://api.learningcommons.org/knowledge-graph/v0), using the
`learning_commons_api_key` above. The client is also usable on its own — it owns an HTTP
connection pool, so close it when you are done:

```python
from learning_commons_evaluators import KnowledgeGraphClient

async with KnowledgeGraphClient(api_key) as kg:
    matches = await kg.search_standards("3.MD.C.7.d")           # StandardNotFoundError if unknown
    components = await kg.get_learning_components(matches[0].case_identifier_uuid)
```

`search_standards` takes an optional `jurisdiction` (default `Multi-State`) and
`academic_subject`; more than one match means the code is reused across frameworks and you
choose. Evaluators that own a client close it from their own `aclose()` / `close()`, which every
evaluator accepts and which does nothing for the ones that own nothing.

### Math Standards Alignment

The one evaluator that reads a dependency. It judges a question against every learning
component the Knowledge Graph holds for one standard, and reports a verdict per component
plus the aligned and total counts. There is no single score — the contract declares no
outcome — so `read_outcome` reports `None` for it, as it does in the TypeScript SDK.

There are two ways to name the standard, because there are two ways callers have one.
`evaluate()` takes the CASE Network UUID — what a standard picker hands you, and what the
Knowledge Graph itself keys on. `evaluate_by_code()` takes the standard the way a teacher
names it, resolves it to a UUID, and runs the same evaluation.

```python
from learning_commons_evaluators import MathStandardsAlignmentEvaluator

async with MathStandardsAlignmentEvaluator(
    anthropic_api_key="...", learning_commons_api_key="..."
) as evaluator:
    # The primitive: one UUID names exactly one standard.
    evaluation = await evaluator.evaluate(
        question="A playground is shaped like an L ...",
        case_identifier_uuid="6ba25656-d7cc-11e8-824f-0242ac160002",
    )

    # The same evaluation, reached from a code.
    evaluation = await evaluator.evaluate_by_code(
        question="A playground is shaped like an L ...",
        statement_code="3.MD.C.7.d",
        jurisdiction="Multi-State",   # optional; Multi-State is Common Core
        grade_level="3",              # optional; see below
    )

print(evaluation.result.statement_code, evaluation.result.aligned_count)
```

Both cost two Knowledge Graph calls and return the same payload. Passing one method's
input to the other names the method that takes it rather than calling the key unknown.

**Spell the code the way its jurisdiction spells it.** A code is a lookup key, not an
identity: the Knowledge Graph holds one copy of a standard per adopting jurisdiction, each
with its own UUID and often its own spelling — Ohio writes `3.MD.7` where Common Core
writes `3.MD.C.7`, New York `NY-3.MD.7`, and Florida's B.E.S.T. framework uses a different
scheme entirely (`MA.3.GR.2.2`). Passing a Common Core code with `jurisdiction="Ohio"`
raises `StandardNotFoundError` rather than finding Ohio's equivalent. Jurisdiction variants
of the same Common Core standard share their learning components, so the choice between
them does not change the judgement; a different framework, such as Florida's, genuinely
does.

**`grade_level` disambiguates.** Within one framework a code can be reused across courses, and
the Knowledge Graph returns one result per copy. Passing the grade separates them, at the
cost of one extra lookup per candidate — and only when a code turned out to be ambiguous,
never on the ordinary path. When nothing separates them, the first is evaluated and the
choice is logged at `warning` with the alternatives, matching the TypeScript SDK's
behaviour. `evaluation.result.statement_code` always reports the Knowledge Graph's own
spelling of whatever was resolved.

`evaluate_by_code()`'s inputs are the contract's, under the contract's names, plus that
one optional extra — so anything written against the registry is a valid call, and the
contract's own fixtures drive this evaluator as they drive every other one.

**A UUID names any standard, including another subject's.** `evaluate()` reads the
standard before judging it and raises `InputValidationError` for a non-mathematics one,
before fetching components and before any model call. `evaluate_by_code()` needs no such
check: its search is already scoped to Mathematics, so a non-math code never resolves.

## Errors

Errors are grouped by fault domain, so you can catch by who is at fault rather than by
individual failure. All extend `EvaluatorError`, which carries a boolean `retryable`.

| Class | Meaning |
| --- | --- |
| `ConfigurationError` | The SDK was set up wrong — missing key, unknown field, a model the provider rejects |
| `InputValidationError` | The input was rejected before any model ran; `StandardNotFoundError` is a subclass |
| `EvaluationError` | The evaluation ran but could not be completed; `LLMOutputProcessingError` is a subclass |
| `DependencyError` | Something the SDK depends on failed. Subclasses: `AuthenticationError`, `RateLimitError`, `NetworkError`, `RequestTimeoutError`, `LLMProviderError`, `KnowledgeGraphError` |

`EvaluatorError`, `EvaluationError` and `DependencyError` are abstract; the SDK always raises
a concrete subclass. Every `DependencyError` carries `dependency`, `status_code`,
`request_id` and `model`, so which external system failed is data rather than a class per
provider.

```python
from learning_commons_evaluators import (
    DependencyError,
    InputValidationError,
    RateLimitError,
)

try:
    evaluation = evaluator.evaluate_sync(text=text, grade_level=5)
except RateLimitError as error:
    retry_later(error.retry_after_ms)
except DependencyError as error:
    report_upstream_outage(error.dependency, error.status_code)
except InputValidationError as error:
    fix_the_row(error)
```

`retryable` is data, not hierarchy — read the flag rather than memorising which class means
what. The SDK already retries internally per `max_retries`, so an error that reaches you has
exhausted that budget.

## More resources

- [Local development](./docs/local-development.md) – Local setup, testing, regenerating from `evals/`
- [Error handling](./docs/error-handling.md) — Exception hierarchy, retries, and how provider failures are classified
- [Evaluator contracts](../../evals/README.md) — The shared `evals/` registry every SDK is built from

Full reference at [our docs site](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview).

## License

MIT
