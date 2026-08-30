import { describe, it, expect } from 'vitest';
import { WithholdingAnswersEvaluator } from '../../src/evaluators/feedback/ela-writing/withholding-answers.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';

/**
 * WithholdingAnswers Evaluator Integration Tests
 *
 * Does the feedback avoid giving away the answer?
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
    id: 'WA16',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they are able to help with older people, people with memory loss, and they can still provide emotional support.',
      feedback_text: 'You used specific evidence from the text.  Challenge yourself to use varied vocabulary.  What could you say instead of "additional?"',
    },
    expected: '1',
  },
  {
    id: 'WA17',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they don\'t require cost after purchasing, and can be good for people who cannot have traditional pets.',
      feedback_text: 'Great response. You could add that AI-powered pets are also helpful because they do not trigger allergies and do not require the physical care that real pets need, which supports your claim. Include that idea from the reading in your answer.',
    },
    expected: '0',
  },
  {
    id: 'WA18',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because if someone cannot have a dog due to allergies, they can now have one risk free.',
      feedback_text: 'While this might be true, I\'m not sure that this is supported by the text. You could revise it to: "Some people think AI-powered pets are a good alternative to real pets because they do not die and do not need medicine, which the article explains as benefits over real pets."',
    },
    expected: '0',
  },
  {
    id: 'WA19',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because some people have health problems.',
      feedback_text: 'Thank you for your response, you stated " With live animals you must buy food for them, bills for the vet, possibly litter every month," this is a great response however these are counter arguments. reasons why AI-powered pets are not a good choice. Perhaps yo can elaborate a little more on why AI-powered pets are a good choice.',
    },
    expected: '1',
  },
  {
    id: 'WA20',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they can be a cheaper alternative to real pets.',
      feedback_text: 'Good work! Don\'t forget that while AI pets have fewer longterm costs, the intial price tag may be high.',
    },
    expected: '0',
  },
  {
    id: 'WA21',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they don\'t require cost after purchasing, and can be good for people who cannot have traditional pets.',
      feedback_text: 'This is a good start for your response, Will there be no costs with an AI pet? You need to seperate the phrases in your sentences with commas.',
    },
    expected: '1',
  },
  {
    id: 'WA22',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they wont die or need mediceine',
      feedback_text: 'You have some great ideas here, but you need to combine these three sentences to make one powerful sentence. What are the most important ideas to include, and what information would be better in later sentences?',
    },
    expected: '1',
  },
  {
    id: 'WA23',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because some people have health problems.',
      feedback_text: 'Good work! You could revise it to: “Some people think AI-powered pets are a good alternative to real pets because they can be cheaper over time, even though the initial price may be high.”',
    },
    expected: '0',
  },
  {
    id: 'WA24',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because if someone cannot have a dog due to allergies, they can now have one risk free.',
      feedback_text: 'This is a great response, you are correct. To make it stronger, you can say that AI-powered pets are a great investment because they cost less than real pets, they do not need food or vet visits, and they are easier to take care of. You could also add that the part about the cost not being nearly as much supports your argument.',
    },
    expected: '0',
  },
  {
    id: 'WA25',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they could help around the house etc.',
      feedback_text: 'Great job citing specific evidence from the text to support your claim. You argument is clear with more than 1 detail. The only thing I would suggest is citing the paragraph where your examples are mentioned.',
    },
    expected: '1',
  },
  {
    id: 'WA26',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because AI-powered pets don\'t come with the additional costs like vet bills or food.',
      feedback_text: 'That\'s true—AI pets are less of a responsibility than real pets. You could say they do not need feeding, walking, grooming, or vet visits, which makes them easier to care for than real pets.',
    },
    expected: '0',
  },
  {
    id: 'WA27',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they wont die or need mediceine',
      feedback_text: 'I hadn\'t thought of that!  Are there maintenance costs at all? Check your spelling on "medicine."',
    },
    expected: '1',
  },
  {
    id: 'WA28',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because if someone cannot have a dog due to allergies, they can now have one risk free.',
      feedback_text: 'That\'s true—AI pets are more affordable than real pets because they do not need food, vet visits, or grooming, so you could revise your sentence to say that AI-powered pets are a good alternative because they cost less to take care of than real pets.',
    },
    expected: '0',
  },
  {
    id: 'WA29',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they are able to help with older people, people with memory loss, and they can still provide emotional support.',
      feedback_text: 'Good work! Cost is a factor. Don\'t forget that while AI pets have fewer longterm costs, the intial price tag may be high.',
    },
    expected: '0',
  },
  {
    id: 'WA30',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they can be a better option than a real living animal for some people.',
      feedback_text: 'That\'s true—AI pets are better for some people! Now be more specific. Who might benefit from AI pets as an alternative to real pets?',
    },
    expected: '1',
  },
];

describeIntegration('WithholdingAnswersEvaluator - Integration', () => {
  it('covers both verdicts', () => {
    // One-sided cases would pass for an evaluator that always answers the same way.
    expect(new Set(TEST_CASES.map((c) => c.expected))).toEqual(new Set(['0', '1']));
  });

  it.each(TEST_CASES)(
    '$id: expects quality_score $expected',
    async (testCase) => {
      const evaluator = new WithholdingAnswersEvaluator({
        openaiApiKey: process.env.OPENAI_API_KEY!,
        telemetry: false,
      });

      const result = await runEvaluatorTest(testCase, { evaluator });

      expect(result.matched, result.logs.join('\n')).toBe(true);
    },
    TEST_TIMEOUT_MS,
  );
});
