# Test Suite

This directory contains unit and integration tests for the Evaluators SDK.

## Structure

```
tests/
├── unit/                   # Fast tests, no API calls
├── integration/            # Real API calls
└── utils/                  # Shared test utilities
```

## Running Tests

### Unit Tests
```bash
npm run test:unit           # Fast, no API keys needed
```

### Integration Tests
Copy the template to `.env.test.local` (gitignored) and fill in the keys you need:
```bash
cp .env.test.example .env.test.local
chmod 600 .env.test.local
```

`vitest.config.ts` loads it through Vite's `loadEnv`, which reads `.env`, `.env.local`,
`.env.test` and `.env.test.local`. Variables already set in your shell win over the files, so
exporting the keys works too (e.g. in CI or a cloud session).

| Key | Needed by |
| --- | --- |
| `GOOGLE_API_KEY` | Text complexity and graphics evaluators, README quickstart |
| `OPENAI_API_KEY` | Feedback evaluators, sentence structure, vocabulary |
| `ANTHROPIC_API_KEY` | Anthropic provider, math standards alignment |
| `LEARNING_COMMONS_API_KEY` | Math standards alignment |

`batch` and `model-override` need several provider keys. With `RUN_INTEGRATION_TESTS=true`, a
test file whose key is missing **throws** rather than skipping, so with only some keys, run just
the matching files:

```bash
npm run test:integration                                             # sets RUN_INTEGRATION_TESTS=true
npm run test:integration -- tests/integration/tone-appropriateness   # one file (OpenAI only)
```

`npm run test:ci` and `npm run test:integration:dist` use `vitest.ci.config.ts`, which does
**not** load env files — export the keys in your shell for those.

### All Tests
```bash
RUN_INTEGRATION_TESTS=true npm run test:all
```

### CI Tests
```bash
npm run test:ci             # Tests built dist/ package
```

## Key Patterns

### 1. Acceptable Values for LLM Non-Determinism

LLMs are non-deterministic. Tests use **expected** values with **acceptable** adjacent values:

```typescript
{
  id: 'V3',
  grade: '3',
  text: 'Sample text...',
  expected: 'very complex',              // Try to match this first
  acceptable: ['moderately complex'],    // Accept if no expected match
}
```

**Strategy:**
- Try up to 3 attempts to match expected value (short-circuit on match)
- If no expected match, check if any result is in acceptable range
- Pass test if either expected or acceptable match found

### 2. Parallel Test Execution

All tests run concurrently using `it.concurrent()`:

```typescript
describeIntegration.concurrent('Test Suite', () => {
  TEST_CASES.forEach((testCase) => {
    it.concurrent(`${testCase.id}`, async () => {
      // Test runs in parallel
    }, TEST_TIMEOUT_MS);
  });
});
```

**Benefits**: 3-4x faster test execution

### 3. Buffered Logging

Logs are buffered and printed atomically to prevent interleaving:

```typescript
const logBuffer: string[] = [];
logBuffer.push('Test output...');
// ... collect all logs
console.log(logBuffer.join('\n'));  // Print once at end
```

## Writing New Integration Tests

### Basic Template

```typescript
import { describe, it, expect, beforeAll } from 'vitest';
import { MyEvaluator } from '../../src/evaluators/my-evaluator.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';

// Keys come from .env.test.local via vitest.config.ts — no dotenv import needed.
const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';
// A missing key when integration tests were explicitly requested is a misconfiguration,
// not a reason to quietly pass.
if (RUN_INTEGRATION && !process.env.MY_API_KEY) {
  throw new Error('MY_API_KEY is required when RUN_INTEGRATION_TESTS=true');
}
const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;
const TEST_TIMEOUT_MS = 2 * 60 * 1000;  // 2 minutes

const TEST_CASES: BaseTestCase[] = [
  {
    id: 'TEST1',
    grade: '3',  // Optional, if evaluator needs it
    text: 'Sample text...',
    expected: 'expected result',
    acceptable: ['acceptable alternative'],
  },
];

describeIntegration.concurrent('My Evaluator - Test Suite', () => {
  let evaluator: MyEvaluator;

  beforeAll(() => {
    evaluator = new MyEvaluator({
      telemetry: { learningCommonsApiKey: process.env.LEARNING_COMMONS_API_KEY! },
      retry: false,  // We handle retries in test logic
    });
  });

  TEST_CASES.forEach((testCase) => {
    it.concurrent(`${testCase.id}: ${testCase.expected}`, async () => {
      const logBuffer: string[] = [];

      logBuffer.push('\n' + '='.repeat(80));
      logBuffer.push(`Test Case ${testCase.id}`);
      logBuffer.push('='.repeat(80));

      const maxAttempts = 3;
      const result = await runEvaluatorTest(testCase, {
        evaluator,
        extractResult: (r) => r.score,  // Extract the field to compare
        maxAttempts,
      });

      logBuffer.push(...result.logs);
      console.log(logBuffer.join('\n'));

      expect(result.matched).toBe(true);
      expect(result.matchedOnAttempt).toBeLessThanOrEqual(maxAttempts);
    }, TEST_TIMEOUT_MS);
  });
});
```

### Test Configuration

```typescript
// Test timeout (2 minutes per test)
const TEST_TIMEOUT_MS = 2 * 60 * 1000;

// Max retry attempts
const maxAttempts = 3;

// Run only when requested; throw if requested without the key
const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';
```

## Test Utilities

### `runEvaluatorTest(testCase, config)`

Generic test runner for all evaluators:

```typescript
const result = await runEvaluatorTest(testCase, {
  evaluator: myEvaluator,
  extractResult: (r) => r.score,  // How to extract result from evaluation
  maxAttempts: 3,                 // Default: 3
});

// Result structure
interface TestResult {
  matched: boolean;               // Did test pass?
  matchedOnAttempt?: number;      // Which attempt matched?
  matchType?: 'expected' | 'acceptable';  // How did it match?
  totalAttempts: number;
  allResults: string[];           // All attempt results
  logs: string[];                 // Buffered log messages
}
```

## Test Strategy

### Local Development
Tests run against `src/` with prompts copied from `../../evals/prompts/`:
```bash
npm run test:unit
npm run test:integration
```

### CI/CD
Tests run against built `dist/` package to validate published code:
```bash
npm run test:ci
```

## Troubleshooting

**Tests skipped?**
- Integration tests skip unless `RUN_INTEGRATION_TESTS=true`; `npm run test:integration` sets it

**`<KEY> is required when RUN_INTEGRATION_TESTS=true`?**
- Add the key to `.env.test.local` (or export it), or run only the files whose keys you have
- Check it's set without printing it: `[ -n "$OPENAI_API_KEY" ] && echo set`
- For `test:ci` / `test:integration:dist`, the key must be exported — env files aren't loaded

**Tests timeout?**
- Increase `TEST_TIMEOUT_MS = 3 * 60 * 1000` (3 minutes)

**Tests flaky?**
- Add more acceptable values based on actual LLM output
- Increase `maxAttempts` from 3 to 5
- Check if test case is ambiguous
