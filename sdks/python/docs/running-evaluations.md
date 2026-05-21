# Running evaluations

## Synchronous

Use `evaluate_sync()` from scripts, notebooks, or other synchronous code:

```python
result = evaluator.evaluate_sync(input)
```

## Asynchronous

Use `await evaluator.evaluate(input)` in async apps, or when an event loop is already running on the thread. If you call `evaluate_sync()` while a loop is active, the SDK raises `RuntimeError` with a message to use `evaluate()` instead.

Invalid inputs (grade out of range, text too short, and other constraints from evaluator settings) raise `InputValidationError` before any LLM call.

```python
import asyncio

async def main():
    result = await evaluator.evaluate(input)
    return result

asyncio.run(main())
```

## Per-call settings override

Pass `evaluation_settings=` to override models, temperatures, or other [configurable evaluator settings](./configuration.md#evaluation-settings-per-evaluator) for a single call. When omitted, the evaluator uses a deep copy of its default settings (class-level defaults, or the instance override from construction — see [Per-instance default evaluation settings](./configuration.md#per-instance-default-evaluation-settings)).

```python
from dataclasses import replace

from learning_commons_evaluators import ConventionalityEvaluator

evaluator = ConventionalityEvaluator(config)
settings = evaluator.default_evaluation_settings.model_copy(deep=True)
settings.prompt_settings_step_conventionality_evaluation = replace(
    settings.prompt_settings_step_conventionality_evaluation,
    temperature=0.2,
)
result = evaluator.evaluate_sync(input, evaluation_settings=settings)
```
