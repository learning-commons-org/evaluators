# @learning-commons/evaluators

[![npm version](https://img.shields.io/npm/v/@learning-commons/evaluators)](https://www.npmjs.com/package/@learning-commons/evaluators)

TypeScript SDK for Learning Commons educational text complexity evaluators.

## Installation

```bash
npm install @learning-commons/evaluators ai
```

The SDK uses the [Vercel AI SDK](https://sdk.vercel.ai) (`ai`) as its LLM interface. You also need to install the provider adapter(s) for the LLM(s) you use:

```bash
npm install @ai-sdk/openai   # for OpenAI
npm install @ai-sdk/google   # for Google Gemini
npm install @ai-sdk/anthropic  # for Anthropic
```

## Quick Start

```typescript
import { VocabularyEvaluator } from '@learning-commons/evaluators';

const evaluator = new VocabularyEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
  openaiApiKey: process.env.OPENAI_API_KEY
});

const result = await evaluator.evaluate("Your text here", "5");
console.log(result.score); // "Moderately complex"
```

---

## Evaluators

### 1. Vocabulary Evaluator

Evaluates vocabulary complexity using the Qualitative Text Complexity rubric (SAP).

**Supported Grades:** 3-12

**Uses:** OpenAI GPT-4o (background knowledge) + Google Gemini 2.5 Pro (grades 3–4) / OpenAI GPT-4.1 (grades 5–12)

**Constructor:**
```typescript
const evaluator = new VocabularyEvaluator({
  googleApiKey: string;                   // Google API key
  openaiApiKey: string;                   // OpenAI API key
  modelOverride?: ModelOverride;          // Override the default provider and model
  maxRetries?: number;                    // Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry settings (default: enabled)
  logger?: Logger;                        // Custom logger
  logLevel?: LogLevel;                    // Log verbosity (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string, grade: string)
```

**Returns:**
```typescript
{
  score: 'Slightly complex' | 'Moderately complex' | 'Very complex' | 'Exceedingly complex';
  reasoning: string;
  metadata: {
    model: string;
    processingTimeMs: number;
  };
  _internal: VocabularyInternal; // Detailed analysis
}
```

---

### 2. Sentence Structure Evaluator

Evaluates sentence structure complexity based on grammatical features.

**Supported Grades:** 3-12

**Uses:** OpenAI GPT-4o

**Constructor:**
```typescript
const evaluator = new SentenceStructureEvaluator({
  openaiApiKey: string;                   // OpenAI API key
  modelOverride?: ModelOverride;          // Override the default provider and model
  maxRetries?: number;                    // Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry settings (default: enabled)
  logger?: Logger;                        // Custom logger
  logLevel?: LogLevel;                    // Log verbosity (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string, grade: string)
```

**Returns:**
```typescript
{
  score: 'Slightly complex' | 'Moderately complex' | 'Very complex' | 'Exceedingly complex';
  reasoning: string;
  metadata: {
    model: string;
    processingTimeMs: number;
  };
  _internal: {
    sentenceAnalysis: SentenceAnalysis;
    features: SentenceFeatures;
    complexity: ComplexityClassification;
  };
}
```

---

### 3. Subject Matter Knowledge (SMK) Evaluator

Evaluates the background knowledge demands of educational texts relative to grade level. Determines how much prior subject knowledge a student needs to comprehend the text, based on the Common Core Qualitative Text Complexity Rubric.

**Supported Grades:** 3-12

**Uses:** Google Gemini 3 Flash Preview

**Constructor:**
```typescript
const evaluator = new SmkEvaluator({
  googleApiKey: string;                   // Google API key
  modelOverride?: ModelOverride;          // Override the default provider and model
  maxRetries?: number;                    // Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry settings (default: enabled)
  logger?: Logger;                        // Custom logger
  logLevel?: LogLevel;                    // Log verbosity (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string, grade: string)
```

**Returns:**
```typescript
{
  score: 'Slightly complex' | 'Moderately complex' | 'Very complex' | 'Exceedingly complex';
  reasoning: string;
  metadata: {
    model: string;
    processingTimeMs: number;
  };
  _internal: {
    identified_topics: string[];
    curriculum_check: string;
    assumptions_and_scaffolding: string;
    friction_analysis: string;
    complexity_score: 'Slightly complex' | 'Moderately complex' | 'Very complex' | 'Exceedingly complex';
    reasoning: string;
  };
}
```

**Example:**
```typescript
import { SmkEvaluator } from '@learning-commons/evaluators';

const evaluator = new SmkEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});

const result = await evaluator.evaluate(
  "Hydraulic propulsion works by sucking water at the bow and forcing it sternward.",
  "10"
);
console.log(result.score);          // "Very complex"
console.log(result.reasoning);
console.log(result._internal.identified_topics); // ["hydraulics", "propulsion", "physics"]
```

---

### 4. Conventionality Evaluator

Evaluates how explicit, literal, and straightforward a text's meaning is versus how abstract, ironic, figurative, or archaic it is for the target grade level. Based on the Common Core Qualitative Text Complexity Rubric.

**Supported Grades:** 3-12

**Uses:** Google Gemini 3 Flash Preview

**Constructor:**
```typescript
const evaluator = new ConventionalityEvaluator({
  googleApiKey: string;                   // Google API key
  modelOverride?: ModelOverride;          // Override the default provider and model
  maxRetries?: number;                    // Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry settings (default: enabled)
  logger?: Logger;                        // Custom logger
  logLevel?: LogLevel;                    // Log verbosity (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string, grade: string)
```

**Returns:**
```typescript
{
  score: 'Slightly complex' | 'Moderately complex' | 'Very complex' | 'Exceedingly complex';
  reasoning: string;
  metadata: {
    model: string;
    processingTimeMs: number;
  };
  _internal: {
    conventionality_features: string[];
    grade_context: string;
    instructional_insights: string;
    complexity_score: 'Slightly complex' | 'Moderately complex' | 'Very complex' | 'Exceedingly complex';
    reasoning: string;
  };
}
```

**Example:**
```typescript
import { ConventionalityEvaluator } from '@learning-commons/evaluators';

const evaluator = new ConventionalityEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});

const result = await evaluator.evaluate(
  "The author uses sustained irony to critique societal norms throughout the passage.",
  "10"
);
console.log(result.score);          // "Very complex"
console.log(result.reasoning);
console.log(result._internal.conventionality_features); // ["sustained irony", ...]
```

---

### 5. Text Complexity Evaluator

Composite evaluator that analyzes vocabulary, sentence structure, subject matter knowledge, and conventionality complexity in parallel.

**Supported Grades:** 3-12

**Uses:** Google Gemini 2.5 Pro + Google Gemini 3 Flash Preview + OpenAI GPT-4o + OpenAI GPT-4.1 (composite)

**Constructor:**
```typescript
const evaluator = new TextComplexityEvaluator({
  googleApiKey: string;                   // Google API key
  openaiApiKey: string;                   // OpenAI API key
  modelOverride?: ModelOverride;          // Override the default provider and model for all sub-evaluators
  maxRetries?: number;                    // Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry settings (default: enabled)
  logger?: Logger;                        // Custom logger
  logLevel?: LogLevel;                    // Log verbosity (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string, grade: string)
```

**Returns:**
```typescript
{
  vocabulary: EvaluationResult<TextComplexityLevel> | { error: Error };
  sentenceStructure: EvaluationResult<TextComplexityLevel> | { error: Error };
  subjectMatterKnowledge: EvaluationResult<TextComplexityLevel> | { error: Error };
  conventionality: EvaluationResult<TextComplexityLevel> | { error: Error };
}
```

Each sub-evaluator result is either a full `EvaluationResult` or `{ error: Error }` if that evaluator failed. An error is only thrown if all four fail.

**Example:**
```typescript
import { TextComplexityEvaluator } from '@learning-commons/evaluators';

const evaluator = new TextComplexityEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
  openaiApiKey: process.env.OPENAI_API_KEY,
});

const result = await evaluator.evaluate("Your text here", "6");

if (!('error' in result.vocabulary)) {
  console.log('Vocabulary:', result.vocabulary.score);
}
if (!('error' in result.sentenceStructure)) {
  console.log('Sentence structure:', result.sentenceStructure.score);
}
if (!('error' in result.subjectMatterKnowledge)) {
  console.log('Subject matter knowledge:', result.subjectMatterKnowledge.score);
}
if (!('error' in result.conventionality)) {
  console.log('Conventionality:', result.conventionality.score);
}
```

---

### 6. Grade Level Appropriateness Evaluator

Determines appropriate grade level for text.

**No grade parameter required** - evaluates what grade the text is appropriate for.

**Uses:** Google Gemini 2.5 Pro

**Constructor:**
```typescript
const evaluator = new GradeLevelAppropriatenessEvaluator({
  googleApiKey: string;                   // Google API key
  modelOverride?: ModelOverride;          // Override the default provider and model
  maxRetries?: number;                    // Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry settings (default: enabled)
  logger?: Logger;                        // Custom logger
  logLevel?: LogLevel;                    // Log verbosity (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string)
```

**Returns:**
```typescript
{
  score: string; // e.g., 'K-1', '2-3', '4-5', '6-8', '9-10', '11-CCR'
  reasoning: string;
  metadata: {
    model: string;
    processingTimeMs: number;
  };
  _internal: {
    grade: string;
    alternative_grade: string;
    scaffolding_needed: string;
    reasoning: string;
  };
}
```

---

### 7. Purpose Evaluator

Evaluates the Purpose dimension of qualitative text complexity — how explicitly the text's purpose is stated versus implied, and how that affects comprehension demands for the target grade level.

**Supported Grades:** 3-12

**Uses:** Google Gemini 3 Flash Preview

**Constructor:**
```typescript
const evaluator = new PurposeEvaluator({
  googleApiKey: string;                   // Google API key (required by this evaluator)
  modelOverride?: ModelOverride;          // Override the default provider and model
  maxRetries?: number;                    // Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry settings (default: enabled)
  logger?: Logger;                        // Custom logger
  logLevel?: LogLevel;                    // Log verbosity (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string, grade: string)
```

**Returns:**
```typescript
{
  score: 'Slightly complex' | 'Moderately complex' | 'Very complex' | 'Exceedingly complex' | 'More context needed';
  reasoning: string;
  metadata: {
    model: string;
    processingTimeMs: number;
  };
  _internal: {
    complexity_score: 'slightly_complex' | 'moderately_complex' | 'very_complex' | 'exceedingly_complex' | 'more_context_needed';
    reasoning: string;
    details: {
      detailed_summary: Array<{
        factor: string;
        description: string;
        effect_on_complexity_dimension: string;
      }>;
      adjustment_and_scaffolding: Array<{
        scaffolding_need: string;
        suggestion: string;
      }>;
      recommended_use_cases: Array<{
        opportunity: string;
        suggestion: string;
      }>;
    };
  };
}
```

> **Note:** The `'More context needed'` score is used for cases where the text alone is insufficient to determine complexity.

**Example:**
```typescript
import { PurposeEvaluator } from '@learning-commons/evaluators';

const evaluator = new PurposeEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});

const result = await evaluator.evaluate(
  "The author argues that renewable energy is the only viable solution to climate change.",
  "9"
);
console.log(result.score);          // "Moderately complex"
console.log(result.reasoning);
console.log(result._internal.details.adjustment_and_scaffolding);
```

---

## Batch CSV Evaluation

For evaluating many texts at once, the SDK ships a CLI tool that reads a CSV file, runs all evaluators in a group, and produces CSV and HTML reports.

```bash
# Run from the directory containing your CSV
npx evaluators-batch
```

The CLI will prompt for your CSV path, API keys, and output directory, then process all rows in parallel with real-time progress.

See [`src/batch/README.md`](./src/batch/README.md) for full documentation.

---

## Error Handling

The SDK provides specific error types to help you handle different scenarios:

```typescript
import {
  ConfigurationError,
  ValidationError,
  APIError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
  TimeoutError,
} from '@learning-commons/evaluators';

try {
  const evaluator = new VocabularyEvaluator({ googleApiKey, openaiApiKey });
  const result = await evaluator.evaluate(text, grade);
} catch (error) {
  if (error instanceof ConfigurationError) {
    // Missing or invalid API keys — fix your config
    console.error('Configuration error:', error.message);
  } else if (error instanceof ValidationError) {
    // Invalid input (text too short, invalid grade, etc.)
    console.error('Invalid input:', error.message);
  } else if (error instanceof AuthenticationError) {
    // Invalid API keys
    console.error('Check your API keys:', error.message);
  } else if (error instanceof RateLimitError) {
    // Rate limit exceeded - wait and retry
    console.error('Rate limited. Retry after:', error.retryAfter);
  } else if (error instanceof NetworkError) {
    // Network connectivity issues
    console.error('Network error:', error.message);
  } else if (error instanceof TimeoutError) {
    // Request timed out
    console.error('Timeout:', error.message);
  } else if (error instanceof APIError) {
    // Other API errors
    console.error('API error:', error.message, 'Status:', error.statusCode);
  }
}
```

---

## Logging

Control logging verbosity with `logLevel`:

```typescript
import { VocabularyEvaluator, LogLevel } from '@learning-commons/evaluators';

const evaluator = new VocabularyEvaluator({
  googleApiKey: '...',
  openaiApiKey: '...',
  logLevel: LogLevel.INFO, // SILENT | ERROR | WARN | INFO | DEBUG
});
```

Or provide a custom logger:

```typescript
import type { Logger } from '@learning-commons/evaluators';

const customLogger: Logger = {
  debug: (msg, ctx) => myLogger.debug(msg, ctx),
  info: (msg, ctx) => myLogger.info(msg, ctx),
  warn: (msg, ctx) => myLogger.warn(msg, ctx),
  error: (msg, ctx) => myLogger.error(msg, ctx),
};

const evaluator = new VocabularyEvaluator({
  googleApiKey: '...',
  openaiApiKey: '...',
  logger: customLogger,
});
```

---

## Model Override

By default each evaluator uses a recommended provider and model tuned for that task. You can override this with any supported provider — OpenAI, Google, or Anthropic — using the `modelOverride` option.

When `modelOverride` is set:
- All LLM calls within the evaluator use the specified provider and model
- Only the API key for the override provider is required (e.g. `anthropicApiKey` when using `Provider.Anthropic`); default provider keys are not validated
- A warning is logged to indicate results may differ from the defaults
- Telemetry records `model_override: true` so override usage is tracked separately

**Validation:** The SDK validates `modelOverride` at construction time and throws `ConfigurationError` if:
- `provider` is not one of the supported `Provider` values (`openai`, `google`, `anthropic`)
- `model` is empty or blank — no default is assumed; you must always specify the model ID explicitly
- The API key for the chosen provider is missing

If the model ID is valid at construction but doesn't exist on the provider's API, `ConfigurationError` is thrown when `evaluate()` is called.

```typescript
import { VocabularyEvaluator, Provider } from '@learning-commons/evaluators';

const evaluator = new VocabularyEvaluator({
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  modelOverride: {
    provider: Provider.Anthropic,
    model: 'claude-sonnet-4-6',
  },
});

const result = await evaluator.evaluate("Your text here", "5");
console.log(result.metadata.model); // "anthropic:claude-sonnet-4-6"
```

See the [Installation](#installation) section for provider adapter setup if you haven't already.

> **Note:** Evaluators are validated and quality-tested against their default models. Results with other models may vary. Check `result.metadata.model` to confirm which model was used.

---

## Telemetry & Privacy

See [docs/telemetry.md](./docs/telemetry.md) for telemetry configuration and privacy information.

---

## Configuration Options

All evaluators use the same `BaseEvaluatorConfig` interface:

```typescript
interface BaseEvaluatorConfig {
  googleApiKey?: string;                  // Google API key (required by some evaluators)
  openaiApiKey?: string;                  // OpenAI API key (required by some evaluators)
  anthropicApiKey?: string;               // Anthropic API key (required if an evaluator defaults to Claude or when `modelOverride` uses `Provider.Anthropic`)
  modelOverride?: ModelOverride;          // Override the provider and model (see Model Override section)
  maxRetries?: number;                    // Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry settings (default: enabled)
  logger?: Logger;                        // Custom logger
  logLevel?: LogLevel;                    // Log verbosity (default: WARN)
  partnerKey?: string;                    // Learning Commons partner key for authenticated telemetry
}
```

**Note:** Which API keys are required depends on the evaluator. The SDK validates required keys at runtime based on the evaluator's metadata:
- **Vocabulary**: Requires both `googleApiKey` and `openaiApiKey`
- **Sentence Structure**: Requires `openaiApiKey` only
- **Subject Matter Knowledge**: Requires `googleApiKey` only
- **Conventionality**: Requires `googleApiKey` only
- **Text Complexity**: Requires both `googleApiKey` and `openaiApiKey`
- **Grade Level Appropriateness**: Requires `googleApiKey` only
- **Purpose**: Requires `googleApiKey` only

When `modelOverride` is set, the default key requirements are bypassed — only the key for the override provider is required (e.g. `anthropicApiKey` when using `Provider.Anthropic`).

---

## License

MIT
