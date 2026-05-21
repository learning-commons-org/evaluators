# Configuration

## Provider configs

Each LLM provider needs its own config with an API key. Configure providers required by your evaluator’s [evaluation settings](#evaluation-settings-per-evaluator) (each prompt step’s `provider_type` in the bundled defaults, or in your overrides).

```python
from learning_commons_evaluators import (
    GoogleLLMProviderConfig,
    OpenAILLMProviderConfig,
    AnthropicLLMProviderConfig,
)

google_config = GoogleLLMProviderConfig(api_key="...")
openai_config = OpenAILLMProviderConfig(api_key="...")
anthropic_config = AnthropicLLMProviderConfig(api_key="...")
```

If a prompt step requires a provider that is missing from `EvaluatorConfig`, evaluation raises `ConfigurationError`.

## EvaluatorConfig factories

Telemetry is not yet wired up in the SDK. Use `create_config_no_telemetry()` in application code (all examples in these docs do).

```python
from learning_commons_evaluators import create_config_no_telemetry

config = create_config_no_telemetry(
    google_llm_provider_config=google_config,
    openai_llm_provider_config=openai_config,
    logger=my_logger,  # optional; default: package logger
)
```

When telemetry is available, `create_config()` and `create_config_telemetry_with_full_input()` will require a `telemetry_partner_id`. Pass the resulting `EvaluatorConfig` to any evaluator constructor: `MyEvaluator(config)`.

## Evaluation settings (per evaluator)

What you can tune at runtime—default models, providers, temperatures, and other prompt-step options—is defined **per evaluator** as a Pydantic model subclass of `EvaluationSettings`. Each field on that model is part of that evaluator’s contract; there is no shared global settings shape across evaluators. See **Inputs**, **Outputs**, and **Evaluation settings** under each [evaluator](./evaluators.md) for the concrete types and bundled defaults.

Bundled evaluators load defaults from generated settings TOML ([Adding a new evaluator](./development.md#adding-a-new-evaluator) covers how those files are produced). Use `SomeEvaluator.default_evaluation_settings` (class attribute) or `evaluator.default_evaluation_settings` (after construction) as the starting point for overrides. Fields are usually named `prompt_settings_step_*` and hold `PromptSettings` (`provider_type`, `model`, `temperature`).

## Per-instance default evaluation settings

Pass `default_evaluation_settings=` to the evaluator constructor to change the default for every call on that instance. The value must match that evaluator’s [evaluation settings type](#evaluation-settings-per-evaluator). Per-call `evaluation_settings=` still overrides for a single run ([Per-call settings override](./running-evaluations.md#per-call-settings-override)).

```python
from dataclasses import replace

from learning_commons_evaluators import ConventionalityEvaluator

settings = ConventionalityEvaluator.default_evaluation_settings.model_copy(deep=True)
settings.prompt_settings_step_conventionality_evaluation = replace(
    settings.prompt_settings_step_conventionality_evaluation,
    temperature=0.2,
    model="gemini-2.5-pro",
)
evaluator = ConventionalityEvaluator(config, default_evaluation_settings=settings)

result = evaluator.evaluate_sync(input)  # uses instance default
```

The SDK deep-copies defaults before each run so in-memory settings objects are not mutated by evaluation.

## Logging

The SDK uses Python's standard `logging` module. By default, `EvaluatorConfig` uses the package logger `learning_commons_evaluators`, which propagates to the root logger once your app configures handlers.

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("learning_commons_evaluators").setLevel(logging.WARNING)

from learning_commons_evaluators import (
    create_config_no_telemetry,
    create_logger,
    create_silent_logger,
    get_logger,
)

logger = create_logger(level=logging.DEBUG)
config = create_config_no_telemetry(logger=create_silent_logger())  # discard SDK logs
```
