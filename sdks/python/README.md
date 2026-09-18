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

## Docs

For full implementation details, check out the [Python SDK docs](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview).

## More resources

- [Evaluators](https://docs.learningcommons.org/evaluators/understanding-evaluators/introduction) — Shipped evaluators and how they work
- [Configuration](https://docs.learningcommons.org/evaluators/sdk-api-reference/python/configuration) — Provider configs, `EvaluatorConfig`, evaluation settings, logging, and per-call overrides
- [Outputs](https://docs.learningcommons.org/evaluators/sdk-api-reference/python/outputs) — `EvaluationResult` shape and metadata
- [Error handling](https://docs.learningcommons.org/evaluators/sdk-api-reference/python/error-handling) — Exception hierarchy and retries
- [Local development](./docs/local-development.md) — Repo-only: local setup, testing, and adding evaluators

## License

MIT
