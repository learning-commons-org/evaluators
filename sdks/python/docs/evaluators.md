# Evaluators

Both shipped evaluators target **grades 3–12**, return a four-point complexity scale, and produce an `EvaluationResult` (see [Results](./results.md)).

| Evaluator                  | Maturity     | LLM providers required[^providers] |
| -------------------------- | ------------ | ---------------------------------- |
| `VocabularyEvaluator`      | Early access | OpenAI **and** Google              |
| `ConventionalityEvaluator` | Early access | Google                             |

[^providers]: Default providers for the bundled [evaluation settings](./configuration.md#evaluation-settings-per-evaluator). Override provider and model (and other configurable fields) via `default_evaluation_settings` at construction or `evaluation_settings` per call — see [Per-instance default evaluation settings](./configuration.md#per-instance-default-evaluation-settings) and [Per-call settings override](./running-evaluations.md#per-call-settings-override). You must still supply API keys in `EvaluatorConfig` for every provider your overridden settings use.

## Vocabulary Evaluator

Estimates the background knowledge students at the target grade are likely to have, identifies complex vocabulary (Tier 2, Tier 3, archaic, and other complex words), and rates overall vocabulary complexity relative to that grade level.

**Documentation:** [About Vocabulary Evaluator](https://docs.learningcommons.org/evaluators/literacy-evaluators/vocabulary-evaluator/about-this-evaluator)

### Inputs

Type: `VocabularyEvaluationInput`

<details>
<summary>Fields</summary>

| Field   | Type  | Constraints                  |
| ------- | ----- | ---------------------------- |
| `text`  | `str` | Educational text to evaluate |
| `grade` | `int` | Target grade level; **3–12** |

</details>

```python
VocabularyEvaluationInput(text="Your text here.", grade=5)
```

### Outputs

Type: `TextComplexityResult` (subclass of `EvaluationResult`)

<details>
<summary>Fields</summary>

| Field                 | Description                                                               |
| --------------------- | ------------------------------------------------------------------------- |
| `answer`              | `TextComplexityAnswer` — four-point complexity scale (`.score`, `.label`) |
| `explanation.summary` | Reasoning for the rating                                                  |
| `explanation.details` | `tier_2_words`, `tier_3_words`, `archaic_words`, `other_complex_words`    |
| `metadata`            | Run timing, status, token usage, per-step details                         |

</details>

### Evaluation settings

Type: `VocabularyEvaluationSettings` — one `PromptSettings` field per LLM step (override `provider_type`, `model`, `temperature` per step).

<details>
<summary>Default prompt steps</summary>

| Field                                       | Default provider | Default model                 |
| ------------------------------------------- | ---------------- | ----------------------------- |
| `prompt_settings_step_background_knowledge` | OpenAI           | `gpt-4o-2024-11-20`           |
| `prompt_settings_step_vocab_grades_3_4`     | Google           | `gemini-2.5-pro` (grades 3–4) |
| `prompt_settings_step_vocab_other_grades`   | OpenAI           | `gpt-4.1` (grades 5–12)       |

</details>

<details>
<summary>Example usage</summary>

```python
from learning_commons_evaluators import (
    VocabularyEvaluator,
    VocabularyEvaluationInput,
    GoogleLLMProviderConfig,
    OpenAILLMProviderConfig,
    create_config_no_telemetry,
)

config = create_config_no_telemetry(
    google_llm_provider_config=GoogleLLMProviderConfig(api_key="..."),
    openai_llm_provider_config=OpenAILLMProviderConfig(api_key="..."),
)
evaluator = VocabularyEvaluator(config)

result = evaluator.evaluate_sync(
    VocabularyEvaluationInput(text="The quick brown fox jumps over the lazy dog.", grade=5)
)

result.answer.score    # "slightly_complex" | "moderately_complex" | "very_complex" | "exceedingly_complex"
result.answer.label    # "Slightly complex" | ...
result.explanation.summary
result.explanation.details  # tier_2_words, tier_3_words, archaic_words, other_complex_words
```

</details>

## Conventionality Evaluator

Assesses how directly a text communicates its meaning—whether language is literal and explicit or relies on figurative, abstract, or implied meaning that requires interpretation.

**Documentation:** [About Conventionality Evaluator](https://docs.learningcommons.org/evaluators/literacy-evaluators/conventionality/about-this-evaluator)

### Inputs

Type: `ConventionalityEvaluationInput`

<details>
<summary>Fields</summary>

| Field   | Type  | Constraints                  |
| ------- | ----- | ---------------------------- |
| `text`  | `str` | **10–10,000** characters     |
| `grade` | `int` | Target grade level; **3–12** |

</details>

```python
ConventionalityEvaluationInput(text="Your text here.", grade=5)
```

### Outputs

Type: `TextComplexityResult` (subclass of `EvaluationResult`)

<details>
<summary>Fields</summary>

| Field                 | Description                                                               |
| --------------------- | ------------------------------------------------------------------------- |
| `answer`              | `TextComplexityAnswer` — four-point complexity scale (`.score`, `.label`) |
| `explanation.summary` | Reasoning for the rating                                                  |
| `explanation.details` | `conventionality_features`, `grade_context`, `instructional_insights`     |
| `metadata`            | Run timing, status, token usage, per-step details                         |

</details>

### Evaluation settings

Type: `ConventionalityEvaluationSettings` — configurable via a single `PromptSettings` field.

<details>
<summary>Default prompt steps</summary>

| Field                                             | Default provider | Default model            |
| ------------------------------------------------- | ---------------- | ------------------------ |
| `prompt_settings_step_conventionality_evaluation` | Google           | `gemini-3-flash-preview` |

</details>

<details>
<summary>Example usage</summary>

```python
from learning_commons_evaluators import (
    ConventionalityEvaluator,
    ConventionalityEvaluationInput,
    GoogleLLMProviderConfig,
    create_config_no_telemetry,
)

config = create_config_no_telemetry(
    google_llm_provider_config=GoogleLLMProviderConfig(api_key="..."),
)
evaluator = ConventionalityEvaluator(config)

result = evaluator.evaluate_sync(
    ConventionalityEvaluationInput(text="Your text here.", grade=5)
)

result.answer.score
result.answer.label
result.explanation.summary
result.explanation.details  # conventionality_features, grade_context, instructional_insights
```

</details>
