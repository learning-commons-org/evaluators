# learning-commons-evaluators (Python)

Python SDK for Learning Commons educational text evaluators. Every evaluator is built from its shared contract under [`evals/`](../../evals) (prompts, models, schemas) and returns the same result envelope as the [TypeScript SDK](../typescript).

> **Under rebuild.** `main` carries the 1.0 rebuild in progress: sixteen of the seventeen evaluators, being the whole Text Complexity family (`BackgroundKnowledgeDemandsEvaluator`, `GradeLevelAppropriatenessEvaluator`, `MeaningDirectnessEvaluator`, `OrganizationalStructureEvaluator`, `PurposeClarityEvaluator`, `ReferenceKnowledgeDemandsEvaluator`, `SentenceStructureEvaluator`, `VocabularyComplexityEvaluator`), the whole Feedback family (`RevisionAccuracyEvaluator`, `RevisionActionabilityEvaluator`, `RevisionManageabilityEvaluator`, `StrengthAcknowledgmentEvaluator`, `StudentResponseSpecificityEvaluator`, `ToneAppropriatenessEvaluator`, `WithholdingAnswersEvaluator`), and `MathStandardsAlignmentEvaluator`, with Critical Thinking still to come. Nothing is published from this state; the last released version is [0.2.0 on PyPI](https://pypi.org/project/learning-commons-evaluators/0.2.0/), whose documentation remains on the [docs site](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview).

## Installation

```bash
pip install learning-commons-evaluators
```

Requires **Python 3.11+**. Provider API keys are passed in explicitly; the SDK never reads them from the environment.

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

`await evaluator.evaluate(...)` is the primary form; `evaluate_sync` wraps it for synchronous code. Inputs are the contract's names (`text`, `grade_level`, `student_text`, `feedback_text`), passed as keywords or as the evaluator's typed input model (`PurposeClarityInput`).

Every `evaluate()` returns the same three-field envelope: `evaluator` (the registry id), `result` (the full structured output, as the contract's `output_schema.json` declares it), and `metadata` (`model`, `processing_time_ms`, `token_usage`). An evaluator whose contract declares several steps sums the token usage across them, and `model` names every model that ran, joined with `+`.

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

```python
from learning_commons_evaluators import MathStandardsAlignmentEvaluator

async with MathStandardsAlignmentEvaluator(
    anthropic_api_key="...", learning_commons_api_key="..."
) as evaluator:
    evaluation = await evaluator.evaluate(
        question="A playground is shaped like an L ...",
        statement_code="3.MD.C.7.d",
        jurisdiction="Multi-State",   # optional; Multi-State is Common Core
        grade="3",                    # optional; see below
    )

print(evaluation.result.statement_code, evaluation.result.aligned_count)
```

**Spell the code the way its jurisdiction spells it.** A code is a lookup key, not an
identity: the Knowledge Graph holds one copy of a standard per adopting jurisdiction, each
with its own UUID and often its own spelling — Ohio writes `3.MD.7` where Common Core
writes `3.MD.C.7`, New York `NY-3.MD.7`, and Florida's B.E.S.T. framework uses a different
scheme entirely (`MA.3.GR.2.2`). Passing a Common Core code with `jurisdiction="Ohio"`
raises `StandardNotFoundError` rather than finding Ohio's equivalent. Jurisdiction variants
of the same Common Core standard share their learning components, so the choice between
them does not change the judgement; a different framework, such as Florida's, genuinely
does.

**`grade` disambiguates.** Within one framework a code can be reused across courses, and
the Knowledge Graph returns one result per copy. Passing the grade separates them, at the
cost of one extra lookup per candidate — and only when a code turned out to be ambiguous,
never on the ordinary path. When nothing separates them, the first is evaluated and the
choice is logged at `warning` with the alternatives, matching the TypeScript SDK's
behaviour. `evaluation.result.statement_code` always reports the Knowledge Graph's own
spelling of whatever was resolved.

The inputs are the contract's, under the contract's names, plus that one optional extra —
so anything written against the registry is a valid call, and the contract's own fixtures
drive this evaluator as they drive every other one.

## More resources

- [Local development](./docs/local-development.md) – Local setup, testing, regenerating from `evals/`
- [Error handling](./docs/error-handling.md) — Exception hierarchy, retries, and how provider failures are classified
- [Evaluator contracts](../../evals/README.md) — The shared `evals/` registry every SDK is built from

## License

MIT
