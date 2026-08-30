import { describe, it, expect } from 'vitest';
import { PurposeClarityEvaluator } from '../../src/evaluators/student-facing-text/ela-reading/purpose-clarity.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';

/**
 * PurposeClarity Evaluator Integration Tests
 *
 * How hard it is for a reader at the target grade to identify the author's purpose.
 *
 * Cases are this evaluator's `fixtures.json`, with the `complexity_score` it records as the
 * expected verdict. Each case retries up to three times and passes on the first expected
 * match; if none arrives, an adjacent level on the four-point scale is accepted.
 *
 * To run these tests:
 * ```bash
 * RUN_INTEGRATION_TESTS=true npm run test:integration
 * ```
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';
// A missing key when integration tests were explicitly requested is a
// misconfiguration, not a reason to quietly pass (matches batch/anthropic-provider).
if (RUN_INTEGRATION && !process.env.GOOGLE_API_KEY) {
  throw new Error('GOOGLE_API_KEY is required when RUN_INTEGRATION_TESTS=true');
}
const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;

const TEST_TIMEOUT_MS = 2 * 60 * 1000;

const TEST_CASES: BaseTestCase[] = [
  {
    id: '1926',
    grade: '3',
    text: 'When going to the beach, find out which ones have lifeguards. Always try to visit beaches that have lifeguards watching the swimmers. The lifeguards on duty will put red and yellow flags on the beach to show you where it is safe to swim. Many people find it hard to see a rip current in the sea. Rip currents are like fast-flowing rivers that can pull even strong swimmers away from the beach. This is why it is better to swim between the lifeguard flags. If you get pulled out by a rip current, try not to panic. Try to swim to the left or to the right of the current\'s flow. Don\'t try to fight the current or to swim against the current. That will make you tired and more scared. To be safe when you visit the beach, you should always listen to the lifeguards. And make sure that you stay between the red and yellow flags on the beach. The flags show you where the currents are safe.',
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    id: '2483',
    grade: '9',
    text: 'We could say that genes are small pieces of biological information, passed from parents to their children, encoded in the DNA. Think of genes as a recipe with instructions that list ingredients, amounts, and steps for how to make food. In this example, you are the food, and your DNA is both the paper and the letters used to write the recipe. Although our genes are like recipes, keep in mind that it is a very difficult recipe, with many (many!) ingredients and steps that we are still trying to discover and understand. Now, there are many types of food in the world, just like there are many types of people. Cupcakes are different from cookies because their recipes are different. People are different from each other because of differences in their genes (recipes). Some people are more similar than others (for instance, you and your brother or sister look more alike than you and your friends). This would be like cupcakes and muffins‚Äîthey are not the same, but they are pretty similar. This is because their recipes are alike but not exactly the same.',
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    id: '2521',
    grade: '11',
    text: 'Deep convection in the Ocean depends on the water temperature, but also on the salinity (the "saltiness") of the water. The colder and the saltier the water is, the more oxygen it can take up. Now that the Earth is warming up, snow, glaciers, and the polar ice caps may melt. This is particularly bad in the Polar regions, because the fresh water from this melting ice flows into the sea and forms a layer of water that is far less salty than the seawater. This may lead to less oxygen being taken up by the ocean, which means there will be less oxygen for life in the oceans. Another reason that the Ocean is losing its breath is that, if the surface layer of water becomes warmer, it does not mix that well with deeper water layers. When the layers stop mixing, the oxygen that is produced by photosynthesis and by exchange with the air cannot get into deeper waters anymore.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: '3021',
    grade: '9',
    text: 'We have the ability to form two different types of long-lasting memories. First, we can learn to perform certain actions, such as talking, riding a bike, or playing a musical instrument, and we will remember how to do these things forever. We learn these actions in a way that lets us unconsciously repeat them, meaning that we can perform these actions without needing to think about them to remember them. However, other types of memories require something called intentional recall. This means that we need to think about these things to remember them. Examples of this form of memory are things like our first-grade teacher\'s name, the meaning of words, or the street where we were attacked by a dog. In our laboratory, we study the kind of memories that we can intentionally recall. In our everyday lives, we very often form this type of memory by a process called association. Learning by association was first studied by a Russian scientist named Ivan Pavlov. Pavlov played a clicking sound to hungry dogs before feeding them meat.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: '3164',
    grade: '6',
    text: 'Early pharaohs of the New Kingdom evicted the Hyksos. The New Kingdom is remembered as a time of renaissance in artistic creation, but also as the end of dynastic rule. This period was also marred by corrupt priests and tomb-robbing by government officials. A famed pharaoh of the new period was Amenhotep IV, who triggered a religious revolution. Before Amenhotep\'s rule, Egypt was a polytheistic society that believed in many gods, the most important named Amon. But, Amenhotep believed only in Aton, the sun god. Belief in only one god (monotheism) was a radical notion. To show his devotion to Aton, the pharaoh changed his name to Akenhaton ("he who is loyal to Aton"). Akhenaten moved his capital from Thebes, where Amon was worshipped, to Tell el Amarna. Naturally, the priests who represented the other gods did not like this change one bit. Many Egyptians also did not like the pharaoh discrediting their gods. After the death of Akhenaten, the powerful priests forced the new capital to be moved back to Thebes.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
];

describeIntegration('PurposeClarityEvaluator - Integration', () => {
  it('spans more than one complexity level', () => {
    // Cases that all expect the same value would pass for an evaluator stuck on it.
    expect(new Set(TEST_CASES.map((c) => c.expected)).size).toBeGreaterThan(1);
  });

  it.each(TEST_CASES)(
    '$id: grade $grade expects $expected',
    async (testCase) => {
      const evaluator = new PurposeClarityEvaluator({
        googleApiKey: process.env.GOOGLE_API_KEY!,
        telemetry: false,
      });

      const result = await runEvaluatorTest(testCase, { evaluator });

      expect(result.matched, result.logs.join('\n')).toBe(true);
    },
    TEST_TIMEOUT_MS,
  );
});
