# Evaluators

| Name                                     | Description                                                                                                                  | Supported grades              | Uses                                                                                                     |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------- |
| Vocabulary Evaluator                     | Evaluates vocabulary complexity using the Qualitative Text Complexity rubric (SAP).                                          | 3-12                          | OpenAI GPT-4o (background knowledge) + Google Gemini 2.5 Pro (grades 3-4) / OpenAI GPT-4.1 (grades 5-12) |
| Sentence Structure Evaluator             | Evaluates sentence structure complexity based on grammatical features.                                                       | 3-12                          | OpenAI GPT-4o                                                                                            |
| Subject Matter Knowledge (SMK) Evaluator | Evaluates the background knowledge demands of educational texts relative to grade level.                                     | 3-12                          | Google Gemini 3 Flash Preview                                                                            |
| Conventionality Evaluator                | Evaluates how explicit/literal versus abstract/figurative a text is for the target grade level.                              | 3-12                          | Google Gemini 3 Flash Preview                                                                            |
| Text Complexity Evaluator                | Composite evaluator that analyzes vocabulary, sentence structure, subject matter knowledge, and conventionality in parallel. | 3-12                          | Google Gemini 2.5 Pro + Google Gemini 3 Flash Preview + OpenAI GPT-4o + OpenAI GPT-4.1 (composite)       |
| Grade Level Appropriateness Evaluator    | Determines the grade band a text is appropriate for.                                                                         | N/A (no grade input required) | Google Gemini 2.5 Pro                                                                                    |
| Purpose Evaluator                        | Evaluates how explicitly the text's purpose is stated versus implied for the target grade level.                             | 3-12                          | Google Gemini 3 Flash Preview                                                                            |

## 1. Vocabulary Evaluator

```typescript
const evaluator = new VocabularyEvaluator(constructorOptions);
await evaluator.evaluate(text: string, grade: string)
```

### Constructor options

| Field           | Value                                  | Description                                                |
| --------------- | -------------------------------------- | ---------------------------------------------------------- |
| `googleApiKey`  | `string`                               | Google API key used for evaluator requests.                |
| `openaiApiKey`  | `string`                               | OpenAI API key used for evaluator requests.                |
| `modelOverride` | `ModelOverride` (optional)             | Overrides the default provider and model selection.        |
| `maxRetries`    | `number` (optional, default: `2`)      | Maximum retry attempts for failed evaluator calls.         |
| `telemetry`     | `boolean \| TelemetryOptions`          | Enables telemetry or configures telemetry behavior.        |
| `logger`        | `Logger` (optional)                    | Custom logger implementation for evaluator logging output. |
| `logLevel`      | `LogLevel` (optional, default: `WARN`) | Sets the logging verbosity level.                          |

### Output fields

| Field                       | Value                                                                                   | Description                                                    |
| --------------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `score`                     | `"Slightly complex" \| "Moderately complex" \| "Very complex" \| "Exceedingly complex"` | Complexity classification returned by the evaluator.           |
| `reasoning`                 | `string`                                                                                | Explanation for the assigned complexity score.                 |
| `metadata.model`            | `string`                                                                                | Provider and model identifier used to generate the evaluation. |
| `metadata.processingTimeMs` | `number`                                                                                | Total evaluation processing time in milliseconds.              |
| `_internal`                 | `VocabularyInternal`                                                                    | Detailed internal analysis data for vocabulary evaluation.     |

---

## 2. Sentence Structure Evaluator

```typescript
const evaluator = new SentenceStructureEvaluator(constructorOptions);
await evaluator.evaluate(text: string, grade: string)
```

### Constructor options

| Field           | Value                                  | Description                                                |
| --------------- | -------------------------------------- | ---------------------------------------------------------- |
| `openaiApiKey`  | `string`                               | OpenAI API key used for evaluator requests.                |
| `modelOverride` | `ModelOverride` (optional)             | Overrides the default provider and model selection.        |
| `maxRetries`    | `number` (optional, default: `2`)      | Maximum retry attempts for failed evaluator calls.         |
| `telemetry`     | `boolean \| TelemetryOptions`          | Enables telemetry or configures telemetry behavior.        |
| `logger`        | `Logger` (optional)                    | Custom logger implementation for evaluator logging output. |
| `logLevel`      | `LogLevel` (optional, default: `WARN`) | Sets the logging verbosity level.                          |

### Output fields

| Field                       | Value                                                                                                      | Description                                                        |
| --------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `score`                     | `"Slightly complex" \| "Moderately complex" \| "Very complex" \| "Exceedingly complex"`                    | Complexity classification returned by the evaluator.               |
| `reasoning`                 | `string`                                                                                                   | Explanation for the assigned complexity score.                     |
| `metadata.model`            | `string`                                                                                                   | Provider and model identifier used to generate the evaluation.     |
| `metadata.processingTimeMs` | `number`                                                                                                   | Total evaluation processing time in milliseconds.                  |
| `_internal`                 | `{ sentenceAnalysis: SentenceAnalysis; features: SentenceFeatures; complexity: ComplexityClassification }` | Detailed internal analysis data for sentence structure evaluation. |

---

## 3. Subject Matter Knowledge (SMK) Evaluator

```typescript
const evaluator = new SmkEvaluator();
await evaluator.evaluate(text: string, grade: string)
```

### Constructor options

| Field           | Value                                  | Description                                                |
| --------------- | -------------------------------------- | ---------------------------------------------------------- |
| `googleApiKey`  | `string`                               | Google API key used for evaluator requests.                |
| `modelOverride` | `ModelOverride` (optional)             | Overrides the default provider and model selection.        |
| `maxRetries`    | `number` (optional, default: `2`)      | Maximum retry attempts for failed evaluator calls.         |
| `telemetry`     | `boolean \| TelemetryOptions`          | Enables telemetry or configures telemetry behavior.        |
| `logger`        | `Logger` (optional)                    | Custom logger implementation for evaluator logging output. |
| `logLevel`      | `LogLevel` (optional, default: `WARN`) | Sets the logging verbosity level.                          |

### Output fields

| Field                       | Value                                                                                                                                                                                                                                                   | Description                                                              |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| `score`                     | `"Slightly complex" \| "Moderately complex" \| "Very complex" \| "Exceedingly complex"`                                                                                                                                                                 | Complexity classification returned by the evaluator.                     |
| `reasoning`                 | `string`                                                                                                                                                                                                                                                | Explanation for the assigned complexity score.                           |
| `metadata.model`            | `string`                                                                                                                                                                                                                                                | Provider and model identifier used to generate the evaluation.           |
| `metadata.processingTimeMs` | `number`                                                                                                                                                                                                                                                | Total evaluation processing time in milliseconds.                        |
| `_internal`                 | `{ identified_topics: string[]; curriculum_check: string; assumptions_and_scaffolding: string; friction_analysis: string; complexity_score: "Slightly complex" \| "Moderately complex" \| "Very complex" \| "Exceedingly complex"; reasoning: string }` | Detailed internal analysis data for subject matter knowledge evaluation. |

### Example

```typescript
import { SmkEvaluator } from "@learning-commons/evaluators";

const evaluator = new SmkEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});

const result = await evaluator.evaluate(
  "Hydraulic propulsion works by sucking water at the bow and forcing it sternward.",
  "10",
);
console.log(result.score); // "Very complex"
console.log(result.reasoning);
console.log(result._internal.identified_topics); // ["hydraulics", "propulsion", "physics"]
```

---

## 4. Conventionality Evaluator

```typescript
const evaluator = new ConventionalityEvaluator(constructorOptions);
await evaluator.evaluate(text: string, grade: string)
```

### Constructor options

| Field           | Value                                  | Description                                                |
| --------------- | -------------------------------------- | ---------------------------------------------------------- |
| `googleApiKey`  | `string`                               | Google API key used for evaluator requests.                |
| `modelOverride` | `ModelOverride` (optional)             | Overrides the default provider and model selection.        |
| `maxRetries`    | `number` (optional, default: `2`)      | Maximum retry attempts for failed evaluator calls.         |
| `telemetry`     | `boolean \| TelemetryOptions`          | Enables telemetry or configures telemetry behavior.        |
| `logger`        | `Logger` (optional)                    | Custom logger implementation for evaluator logging output. |
| `logLevel`      | `LogLevel` (optional, default: `WARN`) | Sets the logging verbosity level.                          |

### Output fields

| Field                       | Value                                                                                                                                                                                                                       | Description                                                     |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `score`                     | `"Slightly complex" \| "Moderately complex" \| "Very complex" \| "Exceedingly complex"`                                                                                                                                     | Complexity classification returned by the evaluator.            |
| `reasoning`                 | `string`                                                                                                                                                                                                                    | Explanation for the assigned complexity score.                  |
| `metadata.model`            | `string`                                                                                                                                                                                                                    | Provider and model identifier used to generate the evaluation.  |
| `metadata.processingTimeMs` | `number`                                                                                                                                                                                                                    | Total evaluation processing time in milliseconds.               |
| `_internal`                 | `{ conventionality_features: string[]; grade_context: string; instructional_insights: string; complexity_score: "Slightly complex" \| "Moderately complex" \| "Very complex" \| "Exceedingly complex"; reasoning: string }` | Detailed internal analysis data for conventionality evaluation. |

### Example

```typescript
import { ConventionalityEvaluator } from "@learning-commons/evaluators";

const evaluator = new ConventionalityEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});

const result = await evaluator.evaluate(
  "The author uses sustained irony to critique societal norms throughout the passage.",
  "10",
);
console.log(result.score); // "Very complex"
console.log(result.reasoning);
console.log(result._internal.conventionality_features); // ["sustained irony", ...]
```

---

## 5. Text Complexity Evaluator

```typescript
const evaluator = new TextComplexityEvaluator(constructorOptions);
await evaluator.evaluate(text: string, grade: string)
```

### Constructor options

| Field           | Value                                  | Description                                                      |
| --------------- | -------------------------------------- | ---------------------------------------------------------------- |
| `googleApiKey`  | `string`                               | Google API key used for evaluator requests.                      |
| `openaiApiKey`  | `string`                               | OpenAI API key used for evaluator requests.                      |
| `modelOverride` | `ModelOverride` (optional)             | Overrides the default provider and model for all sub-evaluators. |
| `maxRetries`    | `number` (optional, default: `2`)      | Maximum retry attempts for failed evaluator calls.               |
| `telemetry`     | `boolean \| TelemetryOptions`          | Enables telemetry or configures telemetry behavior.              |
| `logger`        | `Logger` (optional)                    | Custom logger implementation for evaluator logging output.       |
| `logLevel`      | `LogLevel` (optional, default: `WARN`) | Sets the logging verbosity level.                                |

### Output fields

| Field                    | Value                                                       | Description                                                                                |
| ------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `vocabulary`             | `EvaluationResult<TextComplexityLevel> \| { error: Error }` | Vocabulary evaluator output, or an error object if that sub-evaluator fails.               |
| `sentenceStructure`      | `EvaluationResult<TextComplexityLevel> \| { error: Error }` | Sentence structure evaluator output, or an error object if that sub-evaluator fails.       |
| `subjectMatterKnowledge` | `EvaluationResult<TextComplexityLevel> \| { error: Error }` | Subject matter knowledge evaluator output, or an error object if that sub-evaluator fails. |
| `conventionality`        | `EvaluationResult<TextComplexityLevel> \| { error: Error }` | Conventionality evaluator output, or an error object if that sub-evaluator fails.          |

Each sub-evaluator result is either a full `EvaluationResult` or `{ error: Error }` if that evaluator failed. An error is only thrown if all four fail.

### Example

```typescript
import { TextComplexityEvaluator } from "@learning-commons/evaluators";

const evaluator = new TextComplexityEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
  openaiApiKey: process.env.OPENAI_API_KEY,
});

const result = await evaluator.evaluate("Your text here", "6");

if (!("error" in result.vocabulary)) {
  console.log("Vocabulary:", result.vocabulary.score);
}
if (!("error" in result.sentenceStructure)) {
  console.log("Sentence structure:", result.sentenceStructure.score);
}
if (!("error" in result.subjectMatterKnowledge)) {
  console.log("Subject matter knowledge:", result.subjectMatterKnowledge.score);
}
if (!("error" in result.conventionality)) {
  console.log("Conventionality:", result.conventionality.score);
}
```

---

## 6. Grade Level Appropriateness Evaluator

```typescript
const evaluator = new GradeLevelAppropriatenessEvaluator();
await evaluator.evaluate(text: string)
```

### Constructor options

| Field           | Value                                  | Description                                                |
| --------------- | -------------------------------------- | ---------------------------------------------------------- |
| `googleApiKey`  | `string`                               | Google API key used for evaluator requests.                |
| `modelOverride` | `ModelOverride` (optional)             | Overrides the default provider and model selection.        |
| `maxRetries`    | `number` (optional, default: `2`)      | Maximum retry attempts for failed evaluator calls.         |
| `telemetry`     | `boolean \| TelemetryOptions`          | Enables telemetry or configures telemetry behavior.        |
| `logger`        | `Logger` (optional)                    | Custom logger implementation for evaluator logging output. |
| `logLevel`      | `LogLevel` (optional, default: `WARN`) | Sets the logging verbosity level.                          |

### Output fields

| Field                       | Value                                                                                         | Description                                                                                        |
| --------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `score`                     | `string`                                                                                      | Grade-band classification (for example: `"K-1"`, `"2-3"`, `"4-5"`, `"6-8"`, `"9-10"`, `"11-CCR"`). |
| `reasoning`                 | `string`                                                                                      | Explanation for the assigned grade-level appropriateness.                                          |
| `metadata.model`            | `string`                                                                                      | Provider and model identifier used to generate the evaluation.                                     |
| `metadata.processingTimeMs` | `number`                                                                                      | Total evaluation processing time in milliseconds.                                                  |
| `_internal`                 | `{ grade: string; alternative_grade: string; scaffolding_needed: string; reasoning: string }` | Detailed internal analysis data for grade-level appropriateness evaluation.                        |

---

## 7. Purpose Evaluator

```typescript
const evaluator = new PurposeEvaluator(constructorOptions);
await evaluator.evaluate(text: string, grade: string)
```

### Constructor options

| Field           | Value                                  | Description                                                |
| --------------- | -------------------------------------- | ---------------------------------------------------------- |
| `googleApiKey`  | `string`                               | Google API key used for evaluator requests (required).     |
| `modelOverride` | `ModelOverride` (optional)             | Overrides the default provider and model selection.        |
| `maxRetries`    | `number` (optional, default: `2`)      | Maximum retry attempts for failed evaluator calls.         |
| `telemetry`     | `boolean \| TelemetryOptions`          | Enables telemetry or configures telemetry behavior.        |
| `logger`        | `Logger` (optional)                    | Custom logger implementation for evaluator logging output. |
| `logLevel`      | `LogLevel` (optional, default: `WARN`) | Sets the logging verbosity level.                          |

### Output fields

| Field                       | Value                                                                                                                                                                                                                                                                                                                                                                                                                                            | Description                                                    |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- |
| `score`                     | `"Slightly complex" \| "Moderately complex" \| "Very complex" \| "Exceedingly complex" \| "More context needed"`                                                                                                                                                                                                                                                                                                                                 | Complexity classification returned by the evaluator.           |
| `reasoning`                 | `string`                                                                                                                                                                                                                                                                                                                                                                                                                                         | Explanation for the assigned complexity score.                 |
| `metadata.model`            | `string`                                                                                                                                                                                                                                                                                                                                                                                                                                         | Provider and model identifier used to generate the evaluation. |
| `metadata.processingTimeMs` | `number`                                                                                                                                                                                                                                                                                                                                                                                                                                         | Total evaluation processing time in milliseconds.              |
| `_internal`                 | `{ complexity_score: "slightly_complex" \| "moderately_complex" \| "very_complex" \| "exceedingly_complex" \| "more_context_needed"; reasoning: string; details: { detailed_summary: Array<{ factor: string; description: string; effect_on_complexity_dimension: string }>; adjustment_and_scaffolding: Array<{ scaffolding_need: string; suggestion: string }>; recommended_use_cases: Array<{ opportunity: string; suggestion: string }> } }` | Detailed internal analysis data for purpose evaluation.        |

> **Note:** The `'More context needed'` score is used for cases where the text alone is insufficient to determine complexity.

### Example

```typescript
import { PurposeEvaluator } from "@learning-commons/evaluators";

const evaluator = new PurposeEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});

const result = await evaluator.evaluate(
  "The author argues that renewable energy is the only viable solution to climate change.",
  "9",
);
console.log(result.score); // "Moderately complex"
console.log(result.reasoning);
console.log(result._internal.details.adjustment_and_scaffolding);
```
