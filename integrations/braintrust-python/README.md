# learning-commons-braintrust-scorers

[Braintrust](https://braintrust.dev/) adapters for the [Learning Commons evaluators](https://github.com/learning-commons-org/evaluators) SDK.

Two adapters are provided:

- **`BraintrustAnthropicAdapter`** — uses `braintrust.auto_instrument()` to intercept Anthropic SDK calls. Requires the `[braintrust]` optional dependency.
- **`BraintrustProxyAdapter`** — routes calls through the Braintrust AI Proxy. No Braintrust SDK required.

## Installation

```bash
# Proxy adapter only (no Braintrust SDK needed)
pip install learning-commons-braintrust-scorers

# Auto-instrument adapter
pip install "learning-commons-braintrust-scorers[braintrust]"
```

## Usage

```python
from learning_commons_braintrust_scorers import BraintrustProxyAdapter
from learning_commons_evaluators import GradeLevelAppropriatenessEvaluator
from learning_commons_evaluators.config import create_config_no_telemetry

adapter = BraintrustProxyAdapter(
    model="claude-opus-4-8-20250514",
    api_key="bt-...",
    project="my-project",
)
evaluator = GradeLevelAppropriatenessEvaluator(
    config=create_config_no_telemetry(),
    llm_provider=adapter,
)
```

## Configuration

### `BraintrustAnthropicAdapter`

| Parameter | Default | Description |
|---|---|---|
| `model` | `"claude-opus-4-8-20250514"` | Anthropic model ID. |
| `project` | `None` | Braintrust project name. When set, calls `braintrust.init(project=...)`. |

### `BraintrustProxyAdapter`

| Parameter | Default | Description |
|---|---|---|
| `model` | `"claude-opus-4-8-20250514"` | Anthropic model ID. |
| `api_key` | env `BRAINTRUST_API_KEY` | Braintrust API key. Raises `ValueError` if absent. |
| `project` | `None` | Braintrust project name (passed as `x-bt-parent` header). |

## Development

```bash
pip install -e sdks/python
pip install -e "integrations/braintrust-python[dev]"
pytest integrations/braintrust-python/tests/
```
