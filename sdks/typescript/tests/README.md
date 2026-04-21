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
Requires API keys in `.env`:
```bash
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

Run tests:
```bash
RUN_INTEGRATION_TESTS=true npm run test:integration
```

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
import { config } from 'dotenv';

config();

const SKIP_INTEGRATION = !process.env.RUN_INTEGRATION_TESTS && !process.env.MY_API_KEY;
const describeIntegration = SKIP_INTEGRATION ? describe.skip : describe;
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
    if (SKIP_INTEGRATION) {
      console.log('⏭️  Skipping integration tests');
      return;
    }

    evaluator = new MyEvaluator({
      partnerKey: process.env.MY_PARTNER_KEY!,
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

// Skip integration tests if no API keys
const SKIP_INTEGRATION = !process.env.RUN_INTEGRATION_TESTS && !process.env.API_KEY;
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
Tests run against `src/` with prompts copied from `../../evals/literacy/qualitative-text-complexity/`:
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
- Check API keys: `echo $OPENAI_API_KEY`
- Set: `RUN_INTEGRATION_TESTS=true npm run test:integration`

**Tests timeout?**
- Increase `TEST_TIMEOUT_MS = 3 * 60 * 1000` (3 minutes)

**Tests flaky?**
- Add more acceptable values based on actual LLM output
- Increase `maxAttempts` from 3 to 5
- Check if test case is ambiguous
