# learning-commons-arize-scorers

[Arize/Phoenix](https://phoenix.arize.com/) OTel tracing adapter for the [Learning Commons evaluators](https://github.com/learning-commons-org/evaluators) SDK.

Wraps any `LLMGeneratorProtocol` adapter and emits [OpenInference](https://github.com/Arize-ai/openinference) spans compatible with Arize Phoenix and any OTel backend.

## Installation

```bash
pip install learning-commons-arize-scorers
```

## Usage

```python
from learning_commons_arize_scorers import PhoenixTracingAdapter
from learning_commons_inspect_scorers.adapter import InspectModelAdapter
from learning_commons_evaluators import GradeLevelAppropriatenessEvaluator
from learning_commons_evaluators.config import create_config_no_telemetry

adapter = PhoenixTracingAdapter(
    InspectModelAdapter("anthropic/claude-opus-4-8"),
    capture_message_content=False,  # False by default — K-12 privacy
)
evaluator = GradeLevelAppropriatenessEvaluator(
    config=create_config_no_telemetry(),
    llm_provider=adapter,
)
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `inner` | required | Any `LLMGeneratorProtocol` adapter to wrap. |
| `tracer` | auto | OTel `Tracer`. Defaults to `trace.get_tracer("learning_commons_arize_scorers")`. |
| `capture_message_content` | `False` | Set `True` to include prompt/response text in spans. Off by default — student data may be sensitive. |

## Development

```bash
pip install -e sdks/python
pip install -e "integrations/arize-python[dev]"
pytest integrations/arize-python/tests/
```
