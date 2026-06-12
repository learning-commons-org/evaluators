# learning-commons-langfuse-scorers

[Langfuse](https://langfuse.com/) tracing adapter for the [Learning Commons evaluators](https://github.com/learning-commons-org/evaluators) SDK.

Wraps any `LLMGeneratorProtocol` adapter and records generations in Langfuse v2.

> **Note:** Requires `langfuse>=2.0.0,<3.0.0`. Langfuse v3+ replaced the `trace()`/`generation()` API with an OTel-based pattern — migration is tracked as a TODO.

## Installation

```bash
pip install learning-commons-langfuse-scorers
```

## Usage

```python
from learning_commons_langfuse_scorers import LangfuseTracingAdapter
from learning_commons_inspect_scorers.adapter import InspectModelAdapter
from learning_commons_evaluators import GradeLevelAppropriatenessEvaluator
from learning_commons_evaluators.config import create_config_no_telemetry

adapter = LangfuseTracingAdapter(
    InspectModelAdapter("anthropic/claude-opus-4-8"),
    trace_name="gla-eval",
)
evaluator = GradeLevelAppropriatenessEvaluator(
    config=create_config_no_telemetry(),
    llm_provider=adapter,
)
```

> **Note:** Each `generate()` call creates a new Langfuse trace. For multi-step evaluators,
> pass a per-run unique `trace_name` (e.g. a UUID) to group calls by name in the UI.

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `inner` | required | Any `LLMGeneratorProtocol` adapter to wrap. |
| `langfuse` | auto | `Langfuse()` client. Reads `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` from env. |
| `trace_name` | `"lc_eval"` | Langfuse trace name. |

## Development

```bash
pip install -e sdks/python
pip install -e "integrations/langfuse-python[dev]"
pytest integrations/langfuse-python/tests/
```
