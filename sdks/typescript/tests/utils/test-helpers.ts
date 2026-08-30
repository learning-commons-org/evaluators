/**
 * Streamlined test utilities for evaluator testing
 */

import { readOutcome, type DeclaredOutcome } from '../../src/schemas/outcome.js';
import type { EvaluationResult } from '../../src/schemas/index.js';

export interface TestAttempt<T> {
  attempt: number;
  result: T;
  matched: boolean;
}

export interface TestResult<T> {
  matched: boolean;
  matchedOnAttempt?: number;
  matchType?: 'expected' | 'acceptable'; // How the match occurred
  totalAttempts: number;
  attempts: TestAttempt<T>[];
  allResults: T[];
  logs: string[]; // Buffered log messages for atomic printing
}

export interface RetryTestOptions<TInput, TOutput> {
  /** Function that executes the test and returns the actual output */
  testFn: (input: TInput) => Promise<TOutput>;

  /** Input to pass to the test function */
  input: TInput;

  /** Expected output value */
  expected: TOutput;

  /** Maximum number of attempts (default: 3) */
  maxAttempts?: number;

  /** Custom comparison function (default: strict equality) */
  compareFn?: (actual: TOutput, expected: TOutput) => boolean;

  /** Optional callback after each attempt */
  onAttempt?: (attempt: number, result: TOutput, matched: boolean) => void;
}

/**
 * Default comparison function (case-insensitive string comparison)
 */
function defaultCompareFn<T>(actual: T, expected: T): boolean {
  if (typeof actual === 'string' && typeof expected === 'string') {
    return actual.toLowerCase() === expected.toLowerCase();
  }
  return actual === expected;
}

/**
 * Runs a test function multiple times with retry logic and short-circuiting.
 */
export async function runTestWithRetry<TInput, TOutput>(
  options: RetryTestOptions<TInput, TOutput>
): Promise<TestResult<TOutput>> {
  const {
    testFn,
    input,
    expected,
    maxAttempts = 3,
    compareFn = defaultCompareFn,
    onAttempt,
  } = options;

  const attempts: TestAttempt<TOutput>[] = [];
  let matched = false;
  let matchedOnAttempt: number | undefined;

  for (let attemptNum = 1; attemptNum <= maxAttempts; attemptNum++) {
    const result = await testFn(input);
    const isMatch = compareFn(result, expected);

    attempts.push({
      attempt: attemptNum,
      result,
      matched: isMatch,
    });

    if (onAttempt) {
      onAttempt(attemptNum, result, isMatch);
    }

    // Short-circuit on match
    if (isMatch) {
      matched = true;
      matchedOnAttempt = attemptNum;
      break;
    }
  }

  return {
    matched,
    matchedOnAttempt,
    totalAttempts: attempts.length,
    attempts,
    allResults: attempts.map(a => a.result),
    logs: [], // No logs for this simple retry function
  };
}

/**
 * Generic test case structure
 * All evaluator-specific test cases extend this
 */
export interface BaseTestCase {
  id: string;
  /** The primary text. Omit when the evaluator takes something else — see `inputs`. */
  text?: string;
  grade?: string; // Optional: some evaluators need it, some don't
  /**
   * The whole input object, for evaluators that take something other than `text` — the
   * feedback family takes `student_text` and `feedback_text`. Passed verbatim, so the
   * schema rejects a wrong key rather than the harness silently sending `text`.
   */
  inputs?: Record<string, string>;
  expected: string; // Expected output value (checked on each attempt)
  acceptable?: string[]; // Acceptable adjacent values (checked if no expected match after all retries)
}

/**
 * The only surface the harness uses: a single `evaluate` call. Narrower than the evaluator
 * classes themselves, so any evaluator satisfies it without the harness depending on which
 * one it was handed.
 */
export interface TestableEvaluator {
  evaluate(input: Record<string, unknown>): Promise<EvaluationResult<Record<string, unknown>>>;
}

/**
 * The object a case is evaluated with: `inputs` verbatim when given, otherwise the
 * `text` (+ `grade_level`) shape the text-taking evaluators declare.
 */
function evaluatorInputs(testCase: BaseTestCase): Record<string, string> {
  if (testCase.inputs) return testCase.inputs;

  // Not defaulted to '': an empty string is a valid input, so a case missing both fields
  // would read as a real evaluation of empty text — a failing verdict pointing at the
  // evaluator rather than at the case that is malformed.
  if (testCase.text === undefined) {
    throw new Error(
      `Test case "${testCase.id}" declares neither \`text\` nor \`inputs\`, ` +
        'so the harness has nothing to evaluate.',
    );
  }

  return testCase.grade
    ? { text: testCase.text, grade_level: testCase.grade }
    : { text: testCase.text };
}

/**
 * Configuration for running evaluator tests
 */
export interface EvaluatorTestConfig<TEvaluator extends TestableEvaluator = TestableEvaluator> {
  /** The evaluator instance to test */
  evaluator: TEvaluator;

  /**
   * How to read the value being compared. Defaults to the field the evaluator's contract
   * names in `outcome.score`, which is what a caller reads and what the batch report shows.
   * Pass this only to assert on something other than the declared verdict.
   *
   * Typed as the envelope rather than `any` so an extractor reaching for a field the
   * envelope does not carry is a compile error instead of a run that silently compares
   * `undefined` against every expected value.
   */
  extractResult?: (evalResult: EvaluationResult<Record<string, unknown>>) => string;

  /** Maximum retry attempts (default: 3) */
  maxAttempts?: number;
}

/**
 * Generic evaluator test runner
 * Works for any evaluator with retry logic
 *
 * @example
 * ```typescript
 * // Vocabulary evaluator
 * const result = await runEvaluatorTest(
 *   {
 *     id: 'V1',
 *     text: 'Sample text...',
 *     grade: '3',
 *     expected: 'very complex'
 *   },
 *   { evaluator: vocabularyEvaluator }
 * );
 *
 * // Grade level evaluator
 * const result = await runEvaluatorTest(
 *   {
 *     id: 'GLA1',
 *     text: 'Sample text...',
 *     expected: '6-8'
 *   },
 *   { evaluator: gradeLevelEvaluator }
 * );
 * ```
 */
export async function runEvaluatorTest(
  testCase: BaseTestCase,
  config: EvaluatorTestConfig
): Promise<TestResult<string>> {
  const { evaluator, maxAttempts = 3 } = config;
  const compareFn = defaultCompareFn;

  // The declared outcome travels with the class, so the verdict field comes from the
  // contract rather than being named per suite.
  const declaredOutcome = (
    evaluator.constructor as { metadata?: { outcome?: DeclaredOutcome } }
  ).metadata?.outcome;
  const extractResult =
    config.extractResult ??
    ((evalResult: EvaluationResult<Record<string, unknown>>) =>
      readOutcome(evalResult, declaredOutcome).score ?? 'undefined');

  // Buffer logs to print atomically at the end (prevents interleaving in parallel tests)
  const logBuffer: string[] = [];

  // Log test criteria upfront
  logBuffer.push(`\n  Expected: "${testCase.expected}"`);
  if (testCase.acceptable && testCase.acceptable.length > 0) {
    logBuffer.push(`  Acceptable: [${testCase.acceptable.map(v => `"${v}"`).join(', ')}]`);
  }
  logBuffer.push('');

  const attempts: TestAttempt<string>[] = [];
  let matched = false;
  let matchedOnAttempt: number | undefined;
  let matchType: 'expected' | 'acceptable' | undefined;

  // Phase 1: Try to match expected value (short-circuit on match)
  for (let attemptNum = 1; attemptNum <= maxAttempts; attemptNum++) {
    const result = await evaluator.evaluate(evaluatorInputs(testCase));

    const actualValue = extractResult(result);
    const isExpectedMatch = compareFn(actualValue, testCase.expected);

    attempts.push({
      attempt: attemptNum,
      result: actualValue,
      matched: isExpectedMatch,
    });

    logBuffer.push(`  Attempt ${attemptNum}: "${actualValue}" ${isExpectedMatch ? '✓ EXPECTED MATCH' : '✗'}`);

    // Short-circuit on expected match
    if (isExpectedMatch) {
      matched = true;
      matchedOnAttempt = attemptNum;
      matchType = 'expected';
      break;
    }
  }

  // Phase 2: If no expected match, check if any result is in acceptable range
  // Only check acceptable values if they are defined and non-empty
  if (!matched && testCase.acceptable?.length) {
    logBuffer.push('\n  No expected match. Checking acceptable values...');

    for (let i = 0; i < attempts.length; i++) {
      const attemptResult = attempts[i].result;
      const isAcceptable = testCase.acceptable.some(acceptable =>
        compareFn(attemptResult, acceptable)
      );

      if (isAcceptable) {
        matched = true;
        matchedOnAttempt = i + 1;
        matchType = 'acceptable';
        logBuffer.push(`  ✓ ACCEPTABLE MATCH: Attempt ${matchedOnAttempt} result "${attemptResult}" is in acceptable range`);
        break;
      }
    }

    if (!matched) {
      logBuffer.push(`  ✗ NO MATCH: None of the attempts matched expected or acceptable values`);
    }
  }

  // Summary logging
  logBuffer.push('\n  Summary:');
  logBuffer.push(`    All Results: [${attempts.map(a => `"${a.result}"`).join(', ')}]`);
  if (matched) {
    logBuffer.push(`    Status: ✓ PASS (matched ${matchType} on attempt ${matchedOnAttempt})`);
  } else {
    logBuffer.push(`    Status: ✗ FAIL (no match after ${attempts.length} attempts)`);
  }

  // Return logs for atomic printing by the caller
  return {
    matched,
    matchedOnAttempt,
    matchType,
    totalAttempts: attempts.length,
    attempts,
    allResults: attempts.map(a => a.result),
    logs: logBuffer,
  };
}