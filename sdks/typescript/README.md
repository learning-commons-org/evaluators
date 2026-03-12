# @learning-commons/evaluators

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
console.log(result.score); // "moderately complex"
```

---

## Evaluators

### 1. Vocabulary Evaluator

Evaluates vocabulary complexity using the Qual Text Complexity rubric (SAP).

**Supported Grades:** 3-12

**Uses:** OpenAI GPT-4o (background knowledge) + Google Gemini 2.5 Pro (grades 3–4) / OpenAI GPT-4.1 (grades 5–12)

**Constructor:**
```typescript
const evaluator = new VocabularyEvaluator({
  googleApiKey?: string;  // Google API key (required by this evaluator)
  openaiApiKey?: string;  // OpenAI API key (required by this evaluator)
  maxRetries?: number;    // Optional - Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Optional (default: true)
  logger?: Logger;        // Optional - Custom logger
  logLevel?: LogLevel;    // Optional - SILENT | ERROR | WARN | INFO | DEBUG (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string, grade: string)
```

**Returns:**
```typescript
{
  score: 'slightly complex' | 'moderately complex' | 'very complex' | 'exceedingly complex';
  reasoning: string;
  metadata: {
    model: string;
    processingTimeMs: number;
  };
  _internal: VocabularyComplexity; // Detailed analysis
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
  openaiApiKey?: string;  // OpenAI API key (required by this evaluator)
  maxRetries?: number;    // Optional - Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Optional (default: true)
  logger?: Logger;        // Optional - Custom logger
  logLevel?: LogLevel;    // Optional - Logging verbosity (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string, grade: string)
```

**Returns:**
```typescript
{
  score: 'Slightly Complex' | 'Moderately Complex' | 'Very Complex' | 'Exceedingly Complex';
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

### 3. Text Complexity Evaluator

Composite evaluator that analyzes both vocabulary and sentence structure complexity in parallel.

**Supported Grades:** 3-12

**Uses:** Google Gemini 2.5 Pro + OpenAI GPT-4o (composite)

**Constructor:**
```typescript
const evaluator = new TextComplexityEvaluator({
  googleApiKey?: string;  // Google API key (required by this evaluator)
  openaiApiKey?: string;  // OpenAI API key (required by this evaluator)
  maxRetries?: number;    // Optional - Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Optional (default: true)
  logger?: Logger;        // Optional - Custom logger
  logLevel?: LogLevel;    // Optional - Logging verbosity (default: WARN)
});
```

**API:**
```typescript
await evaluator.evaluate(text: string, grade: string)
```

**Returns:**
```typescript
{
  score: {
    overall: string;           // Overall complexity (highest of the two)
    vocabulary: string;        // Vocabulary complexity score
    sentenceStructure: string; // Sentence structure complexity score
  };
  reasoning: string;  // Combined reasoning from both evaluators
  metadata: EvaluationMetadata;
  _internal: {
    vocabulary: EvaluationResult | { error: Error };
    sentenceStructure: EvaluationResult | { error: Error };
  };
}
```

---

### 4. Grade Level Appropriateness Evaluator

Determines appropriate grade level for text.

**No grade parameter required** - evaluates what grade the text is appropriate for.

**Uses:** Google Gemini 2.5 Pro

**Constructor:**
```typescript
const evaluator = new GradeLevelAppropriatenessEvaluator({
  googleApiKey?: string;  // Google API key (required by this evaluator)
  maxRetries?: number;    // Optional - Max retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Optional (default: true)
  logger?: Logger;        // Optional - Custom logger
  logLevel?: LogLevel;    // Optional - Logging verbosity (default: WARN)
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

## Telemetry & Privacy

See [docs/telemetry.md](./docs/telemetry.md) for telemetry configuration and privacy information.

---

## Configuration Options

All evaluators use the same `BaseEvaluatorConfig` interface:

```typescript
interface BaseEvaluatorConfig {
  googleApiKey?: string;  // Google API key (required by some evaluators)
  openaiApiKey?: string;  // OpenAI API key (required by some evaluators)
  maxRetries?: number;    // Max API retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry config (default: true)
  logger?: Logger;        // Custom logger (optional)
  logLevel?: LogLevel;    // Console log level (default: WARN)
  partnerKey?: string;    // Learning Commons partner key for authenticated telemetry (optional)
}
```

**Note:** Which API keys are required depends on the evaluator. The SDK validates required keys at runtime based on the evaluator's metadata:
- **Vocabulary**: Requires both `googleApiKey` and `openaiApiKey`
- **Sentence Structure**: Requires `openaiApiKey` only
- **Text Complexity**: Requires both `googleApiKey` and `openaiApiKey`
- **Grade Level Appropriateness**: Requires `googleApiKey` only

---

## License

MIT
