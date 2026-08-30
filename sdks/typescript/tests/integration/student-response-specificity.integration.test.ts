import { describe, it, expect } from 'vitest';
import { StudentResponseSpecificityEvaluator } from '../../src/evaluators/feedback/ela-writing/student-response-specificity.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';

/**
 * StudentResponseSpecificity Evaluator Integration Tests
 *
 * Is the feedback clearly based on the student's specific response?
 *
 * Cases are the inputs from this evaluator's `fixtures.json`, with the `quality_score` it
 * records as the expected verdict. The verdict is binary, so there is no adjacent value to
 * accept — a case matches within its retries or it fails.
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
    id: 'SRS0',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they could help around the house etc.',
      feedback_text: 'You\'re right, the AI pets could help around the house. Can you find some other details from the article that you could add to make your claim stronger?',
    },
    expected: '1',
  },
  {
    id: 'SRS1',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because AI powered pets can be helpfull for people with health issues.',
      feedback_text: 'How so? Can you give an example? Check your spelling of helpful.',
    },
    expected: '0',
  },
];

describeIntegration('StudentResponseSpecificityEvaluator - Integration', () => {
  it('covers both verdicts', () => {
    // One-sided cases would pass for an evaluator that always answers the same way.
    expect(new Set(TEST_CASES.map((c) => c.expected))).toEqual(new Set(['0', '1']));
  });

  it.each(TEST_CASES)(
    '$id: expects quality_score $expected',
    async (testCase) => {
      const evaluator = new StudentResponseSpecificityEvaluator({
        openaiApiKey: process.env.OPENAI_API_KEY!,
        telemetry: false,
      });

      const result = await runEvaluatorTest(testCase, { evaluator });

      expect(result.matched, result.logs.join('\n')).toBe(true);
    },
    TEST_TIMEOUT_MS,
  );
});
