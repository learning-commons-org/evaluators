# learning-commons-evaluators (Python)

Python SDK for Learning Commons educational text evaluators. Evaluators call LLMs via LangChain, return structured Pydantic results, and share a common configuration and error-handling model.

## Installation

```bash
pip install learning-commons-evaluators
```

Requires **Python 3.10+**. Provider API keys are passed in at runtime (not bundled with the package).

## Quick start

```python
import logging
from learning_commons_evaluators import (
    ConventionalityEvaluator,
    ConventionalityEvaluationInput,
    GoogleLLMProviderConfig,
    create_config_no_telemetry,
)

logging.basicConfig(level=logging.INFO)

config = create_config_no_telemetry(
    google_llm_provider_config=GoogleLLMProviderConfig(api_key="your-google-key"),
)

evaluator = ConventionalityEvaluator(config)
result = evaluator.evaluate_sync(
    ConventionalityEvaluationInput(text="The cat's out of the bag now.", grade=5)
)

print(result.answer.label)        # e.g. "Moderately complex"
print(result.explanation.summary) # Reasoning for the score
```

## Local development

For local setup, testing, and development, check out the [Local development](./docs/local-development.md) instructions.

## More resources

- [Evaluators](./docs/evaluators.md) — Shipped evaluators with their inputs, outputs, and evaluation settings
- [Running evaluations](./docs/running-evaluations.md) — Sync / async usage and per-call settings overrides
- [Results](./docs/results.md) — `EvaluationResult` shape and metadata
- [Configuration](./docs/configuration.md) — Provider configs, `EvaluatorConfig`, evaluation settings, logging
- [Error handling](./docs/error-handling.md) — Exception hierarchy, retries, and sanitization

## License

MIT
