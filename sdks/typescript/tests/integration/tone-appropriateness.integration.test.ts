import { describe, it, expect } from 'vitest';
import { ToneAppropriatenessEvaluator } from '../../src/evaluators/feedback/ela-writing/tone-appropriateness.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';

/**
 * ToneAppropriateness Evaluator Integration Tests
 *
 * Is the tone appropriate and constructive for the student?
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
    id: 'TA1',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because AI-powered pets don\'t come with the additional costs like vet bills or food.',
      feedback_text: 'This is absolutely brilliant! AI powered pets don\'t come with additional costs like vet bills or food, and your response is basically perfect. There\'s really not much else to improve, but maybe add a few more details from the article if you want.',
    },
    expected: '0',
  },
  {
    id: 'TA2',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because it\'s more cost efficient. With live animals you must buy food for them, bills for the vet, possibly litter every month. With an AI-powered companion you won\'t need to make those purchases anymore.',
      feedback_text: 'That\'s true—AI pets are more affordable than real pets! Now be more specific. What makes AI pets more affordable than real pets?',
    },
    expected: '1',
  },
  {
    id: 'TA3',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because if someone cannot have a dog due to allergies, they can now have one risk free.',
      feedback_text: 'You used specific evidence from the text.  Challenge yourself to use varied vocabulary.  What could you say instead of "additional?"',
    },
    expected: '1',
  },
  {
    id: 'TA4',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because if someone cannot have a dog due to allergies, they can now have one risk free.',
      feedback_text: 'You put evidence from the text in your own words to finish the sentence, but this response is pretty weak. Let\'s take it up a notch by making the sentence richer; rather than saying a general word like "cost," you should have listed specific costs of owning an animal. Go back to the text and find those details because this answer feels incomplete.',
    },
    expected: '0',
  },
  {
    id: 'TA5',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because it is less of a responsibility to take care of.',
      feedback_text: 'Revise your answer by providing specific details from the text to support your claim. Right now, your response feels careless and underdeveloped. Use that detail to explain why AI-powered pets are a better option than a real living animal for some people.',
    },
    expected: '0',
  },
  {
    id: 'TA6',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because it is less of a responsibility to take care of.',
      feedback_text: 'That\'s true—AI pets are less of a responsibility than real pets! Now be more specific. What makes AI pets less of a responsibility than real pets?',
    },
    expected: '1',
  },
  {
    id: 'TA7',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because the cost is not nearly as much as a regular living animal.',
      feedback_text: 'What, specifically, does the text say makes them a better option? Right now your sentence is too vague and shows careless reading.',
    },
    expected: '0',
  },
  {
    id: 'TA8',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they are able to help with older people, people with memory loss, and they can still provide emotional support.',
      feedback_text: 'Amazing job—this is an excellent response. Could you cite the paragraph where this is stated? Could you elaborate on your reasoning why pets not needing medicine or not dying is a good reason for some people to get AI pets instead?',
    },
    expected: '0',
  },
  {
    id: 'TA9',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they wont die or need mediceine',
      feedback_text: 'Good start; elaborate more on the health problems.  What specific example from the text can you add to make this argument stronger?',
    },
    expected: '1',
  },
  {
    id: 'TA10',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because AI-powered pets don\'t come with the additional costs like vet bills or food.',
      feedback_text: 'This is an absolutely amazing response—you are clearly a brilliant writer. I love how you added extra sentences to support your claim. You also made incredibly sophisticated vocabulary choices (cost efficient).',
    },
    expected: '0',
  },
  {
    id: 'TA11',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they can be a better option than a real living animal for some people.',
      feedback_text: 'This doesn’t make much sense, and it seems like you didn’t really use the text carefully. Go back and find actual details from the article if you want this sentence to work.',
    },
    expected: '0',
  },
  {
    id: 'TA12',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because AI-powered pets don\'t come with the additional costs like vet bills or food.',
      feedback_text: 'Amazing job—this is an excellent example and you clearly understand the assignment perfectly. The only tiny thing you should do is cite the paragraph where your evidence is mentioned, but otherwise this is fantastic work.',
    },
    expected: '0',
  },
  {
    id: 'TA14',
    inputs: {
      student_text: 'Some people think AI-powered pets are a good alternative to real pets because they can be a better option than a real living animal for some people.',
      feedback_text: 'Excellent, flawless response. You\'re obviously an outstanding writer, and this is absolutely perfect because you\'ve brought in multiple details from the text as evidence.',
    },
    expected: '0',
  },
];

describeIntegration('ToneAppropriatenessEvaluator - Integration', () => {
  it('covers both verdicts', () => {
    // One-sided cases would pass for an evaluator that always answers the same way.
    expect(new Set(TEST_CASES.map((c) => c.expected))).toEqual(new Set(['0', '1']));
  });

  it.each(TEST_CASES)(
    '$id: expects quality_score $expected',
    async (testCase) => {
      const evaluator = new ToneAppropriatenessEvaluator({
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
