# @learning-commons/evaluators

TypeScript SDK for Learning Commons educational text complexity evaluators.

## Installation

```bash
npm install ai @learning-commons/evaluators
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

**Uses:** Google Gemini 2.5 Pro + OpenAI GPT-4o

**Constructor:**
```typescript
const evaluator = new VocabularyEvaluator({
  googleApiKey: string;   // Required - Google API key
  openaiApiKey: string;   // Required - OpenAI API key
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
    promptVersion: string;
    model: string;
    timestamp: Date;
    processingTimeMs: number;
  };
  _internal: VocabularyComplexity; // Detailed analysis
}
```

## Error Handling

The SDK provides specific error types to help you handle different scenarios:

```typescript
import {
  ValidationError,
  APIError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
  TimeoutError,
} from '@learning-commons/evaluators';

try {
  const result = await evaluator.evaluate(text, grade);
} catch (error) {
  if (error instanceof ValidationError) {
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

All evaluators support these common options:

```typescript
interface BaseEvaluatorConfig {
  maxRetries?: number;    // Max API retry attempts (default: 2)
  telemetry?: boolean | TelemetryOptions; // Telemetry config (default: true)
  logger?: Logger;        // Custom logger (optional)
  logLevel?: LogLevel;    // Console log level (default: WARN)
  apiKey?: string;        // Learning Commons API key for authenticated telemetry (optional)
}
```

---

## License

MIT
