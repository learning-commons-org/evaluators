# learning-commons-evaluators (Python)

Python SDK for Learning Commons educational text evaluators. Every evaluator is built from its shared contract under [`evals/`](../../evals) (prompts, models, schemas) and returns the same result envelope as the [TypeScript SDK](../typescript).

> **Under rebuild.** `main` carries the 1.0 rebuild in progress: five evaluators so far (`GradeLevelAppropriatenessEvaluator`, `PurposeClarityEvaluator`, `ToneAppropriatenessEvaluator`, `SentenceStructureEvaluator`, `VocabularyComplexityEvaluator`), with the rest following phase by phase. Nothing is published from this state; the last released version is [0.2.0 on PyPI](https://pypi.org/project/learning-commons-evaluators/0.2.0/), whose documentation remains on the [docs site](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview).

## Installation

```bash
pip install learning-commons-evaluators
```

Requires **Python 3.10+**. Provider API keys are passed in explicitly; the SDK never reads them from the environment.

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

Old evaluator ids still resolve: `get_evaluator("grade-level-appropriateness")` finds the evaluator now registered as `student_facing_text.ela_reading.grade_level_appropriateness`.

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

## More resources

- [Local development](./docs/local-development.md) – Local setup, testing, regenerating from `evals/`
- [Error handling](./docs/error-handling.md) — Exception hierarchy, retries, and how provider failures are classified
- [Evaluator contracts](../../evals/README.md) — The shared `evals/` registry every SDK is built from

## License

MIT
