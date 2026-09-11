import { describe, it, expect } from 'vitest';
import { StrengthAcknowledgmentEvaluator } from '../../src/evaluators/feedback/ela-writing/strength-acknowledgment.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';

/**
 * StrengthAcknowledgment Evaluator Integration Tests
 *
 * Does the feedback identify what the student did well?
 *
 * Cases are the inputs from this evaluator's `fixtures.json`, with the `quality_score` it
 * records as the expected verdict. The verdict is binary, so there is no adjacent value to
 * accept — a case matches within one of its five attempts or it fails.
 *
 * The retries are load-bearing: the contract's declared temperature never reaches this
 * model. gpt-5.4 is a reasoning model, which rejects `temperature`, so the AI SDK drops it
 * with a warning and the model answers with its own variability regardless.
 *
 * To run these tests:
 * ```bash
 * RUN_INTEGRATION_TESTS=true npm run test:integration
 * ```
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';
// A missing key when integration tests were explicitly requested is a
// misconfiguration, not a reason to quietly pass (matches batch/anthropic-provider).
if (RUN_INTEGRATION && !process.env.OPENAI_API_KEY) {
  throw new Error('OPENAI_API_KEY is required when RUN_INTEGRATION_TESTS=true');
}
const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;

const TEST_TIMEOUT_MS = 2 * 60 * 1000;

const TEST_CASES: BaseTestCase[] = [
  {
    id: 'SA0',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they could help around the house etc.',
      feedback_text: 'You\'re right, the AI pets could help around the house. Can you find some other details from the article that you could add to make your claim stronger?',
    },
    expected: '1',
  },
  {
    id: 'SA1',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because AI powered pets can be helpfull for people with health issues.',
      feedback_text: 'How so? Can you give an example? Check your spelling of helpful.',
    },
    expected: '0',
  },
];

describeIntegration('StrengthAcknowledgmentEvaluator - Integration', () => {
  it('covers both verdicts', () => {
    // One-sided cases would pass for an evaluator that always answers the same way.
    expect(new Set(TEST_CASES.map((c) => c.expected))).toEqual(new Set(['0', '1']));
  });

  it.each(TEST_CASES)(
    '$id: expects quality_score $expected',
    async (testCase) => {
      const evaluator = new StrengthAcknowledgmentEvaluator({
        openaiApiKey: process.env.OPENAI_API_KEY!,
        telemetry: false,
      });

      // Five attempts, not the default three. The verdict is binary, so an `acceptable`
      // value would be the opposite answer and the assertion would pass for anything.
      // Sampling one case 10 times gave 7 correct: at three attempts that is a ~3% chance
      // of a spurious failure per run, at five it is ~0.2%. Attempts short-circuit on the
      // first match, so this costs nothing unless a case is already failing.
      const result = await runEvaluatorTest(testCase, { evaluator, maxAttempts: 5 });

      expect(result.matched, result.logs.join('\n')).toBe(true);
    },
    TEST_TIMEOUT_MS,
  );
});
