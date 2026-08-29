import { describe, it, expect, beforeAll } from 'vitest';
import { BackgroundKnowledgeDemandsEvaluator } from '../../src/evaluators/student-facing-text/ela-reading/background-knowledge-demands.js';
import {
  runEvaluatorTest,
  type BaseTestCase,
} from '../utils/index.js';

/**
 * SMK Evaluator Integration Tests
 *
 * Test cases cover grades 3-12, one per grade, drawn from the annotated dataset.
 * complexity_score values are the dataset's own, which the contract's schema also uses.
 *
 * Each test uses a retry mechanism (up to 3 attempts) to account for LLM non-determinism,
 * with short-circuiting on first expected match. If no expected match is found after all
 * attempts, the test checks if any result falls within the acceptable (adjacent) value range.
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

// Test timeout: 2 minutes per test case (allows for 3 attempts with API latency)
const TEST_TIMEOUT_MS = 2 * 60 * 1000;

// One test case per grade (3–12), first occurrence in dataset_599667ce.
// Expected values are the dataset's complexity_score verbatim.
// Acceptable values are the adjacent complexity levels on the 4-point scale.
const TEST_CASES: BaseTestCase[] = [
  {
    id: 'SMK3',
    grade: '3',
    // dataset item 6205, annotated: moderately_complex
    text: 'Vesuvius is a dangerous thing, but very beautiful. It stands tall and pointed and graceful against a lovely sky. Its little cloud waves from it like a plume. At night the mountain is swallowed by the dark. But the red rivers down its slopes glare in the sky. It is beautiful and terrible like a tiger. Thousands of people have loved it. They have climbed it and looked down its crater. It is like looking into the heart of the earth. One of these travelers wrote of his visit in 1793. He said: "For many days Vesuvius has been in action. I have watched it from Naples. It is wonderfully beautiful and always changing. On one day huge clouds poured out of the top. They hung in the sky far above, white as snow. Suddenly a cloud of smoke rushed out of another mouth. It was as black as ink. The black column rose tall and curling beside the snowy clouds. That was a picture in black and white. But at another time I saw one in bright colors.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: 'SMK4',
    grade: '4',
    // dataset item 3538, annotated: moderately_complex
    text: "About a year after the family moved to Oklahoma, Will Johnson got a neighbor boy to go with him back to their place in Texas to bring another wagon load of household goods. They were gone about two weeks. While the family was in Oklahoma, Will — who was about 20 — taught school two terms at Nubbin Ridge, somewhere near Duncan. Simpson, being about 17 at the time, was not about to go to school to a teacher who was his older brother, so he saddled his horse and slipped away back to Melvin's ranch, to be with his brother Joe. He said he got tired of riding but not nearly as tired as his horse. The journey was about 300 miles. He was on the trail three days and nights and had to stop at times to let his horse rest. When he got to the ranch, Joe wrote to the family saying that Simpson was with him and for them not to worry. They had suspected where he had gone but were not sure.",
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: 'SMK5',
    grade: '5',
    // dataset item 2620, annotated: moderately_complex
    text: 'Imagine you are walking in a park full of brightly colored flowers and some of their greatest admirers—honeybees. Suddenly, you hear the buzzing of a bee very near your ear. Without even thinking about it, your muscles tense up, and you stop dead in your tracks. You find yourself frozen, hoping the bee ignores you and buzzes on by. What just happened? Well, one of your brain\'s most important jobs is keeping you safe. Somewhere in your past, you learned two things: First, bees can sting! And second, bees buzz. So, when your ears perked up at the sound of bees buzzing, alarm bells went off in your brain. Your brain responded by telling your muscles to freeze so that the bee would hopefully just buzz off. And you did not even have to think about it… Pretty cool! Now imagine something just a little different. You are taking an afternoon stroll through the very same park, but earlier that morning an angry bee stung you in the arm—and it hurt! So now when you hear bees buzzing in the park, will your brain, whose job is to protect you, simply tell your body to freeze in place? Heck no!',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: 'SMK6',
    grade: '6',
    // dataset item 7419, annotated: moderately_complex
    text: 'Imagine you are indoors on a sunny day. A beam of sunlight through a window lights up a section of the floor. How would you draw this sunbeam? You might draw a series of parallel lines showing the path of the sunlight from the window to the floor. This is not exactly accurate — no matter how hard you look, you will not find unique lines of light in the sunbeam! However, this is a good way to draw light and to model light geometrically. We call these narrow, imaginary lines of light light rays. Recall that light can behave like a wave and so you can think of a light ray as the path of a point on the crest of a wave. We can use light rays to model the behaviour of light relative to mirrors, lenses, telescopes, microscopes, and prisms. The study of how light interacts with materials is called optics. When dealing with light rays, we are usually interested in the shape of a material and the angles at which light rays hit it.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: 'SMK7',
    grade: '7',
    // dataset item 3171, annotated: moderately_complex
    text: 'Most immigrant groups that had formerly come to America by choice seemed distinct, but in fact had many similarities. Most had come from Northern and Western Europe. Most had some experience with representative democracy. With the exception of the Irish, most were Protestant. Many were literate, and some possessed a fair degree of wealth. The later groups arriving by the boatload in the Gilded Age were characterized by few of these traits. Their nationalities included Greek, Italian, Polish, Slovak, Serb, Russian, Croat, and others. Until cut off by federal decree, Japanese and Chinese settlers relocated to the American West Coast. None of these groups were predominantly Protestant. The vast majority were Roman Catholic or Eastern Orthodox. However, due to increased persecution of Jews in Eastern Europe, many Jewish immigrants sought freedom from torment. Very few newcomers spoke any English, and large numbers were illiterate in their native tongues. None of these groups hailed from democratic regimes. The American form of government was as foreign as its culture',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: 'SMK8',
    grade: '8',
    // dataset item 6178, annotated: moderately_complex
    text: 'At Knob Creek the boy began to go to an "A B C" school. His first teacher was Zachariah Riney. Of course, there were no regular schools in the backwoods then. When a man who "knew enough" happened to come along, especially if he had nothing else to do, he tried to teach the children of the pioneers in a poor log schoolhouse. It is not likely that little Abe went to school more than a few weeks at this time, for he never had a year\'s schooling in his life. There was another teacher afterward at Knob Creek—a man named Caleb Hazel. Little is known of either of these teachers except that he taught little Abe Lincoln. If their pupil had not become famous the men and their schools would never have been mentioned in history. An old man, named Austin Gollaher, used to like to tell of the days when he and little Abe went to school together. He said: "Abe was an unusually bright boy at school, and made splendid progress in his studies. Indeed, he learned faster than any of his schoolmates. Though so young, he studied very hard."',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: 'SMK9',
    grade: '9',
    // dataset item 6570, annotated: moderately_complex
    text: 'By looking at any map of Europe, it will be seen that England is separated from France by the English Channel, a passage which, though it looks quite narrow on the map, is really very wide, especially toward the west. The narrowest place is between Dover and Calais, where the distance across is only about twenty-two miles. This narrow passage is called the Straits of Dover. It would have been very convenient for travellers that have to pass between London and Paris if this strait had happened to lie in the line, or nearly in the line, between these two cities; but it does not. It lies considerably to the eastward of it; so that, to cross the channel at the narrowest part, requires that the traveller should take quite a circuit round. To go by the shortest distance, it is necessary to cross the channel at a place where Dieppe is the harbor, on the French side, and New Haven on the English.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: 'SMK10',
    grade: '10',
    // dataset item 7313, annotated: very_complex
    text: 'Hydraulic propulsion by reaction consists, in principle, in effecting a movement of boats, by sucking in water at the bow and forcing it out at the stern. This is a very old idea. Naturalists cite whole families of mollusks that move about in this way with great rapidity. It is probable that such was the origin of the first idea of this mode of operating. However this may be, as long ago as 1661 a patent was taken out in England, on this principle, by Toogood & Hayes. After this we find the patents of Allen (1729) and Rumsay (1788). In France, Daniel Bernouilli presented to the Académic des Sciences a similar project during the last century. Mr. Seydell was the first to build a vessel on this principle. This ship, which was called the Enterprise, was of 100 tons burden, and was constructed at Edinburgh for marine fishery. The success of this was incomplete, but it was sufficient to show all the advantage that could be got from the idea.',
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    id: 'SMK11',
    grade: '11',
    // dataset item 7429, annotated: very_complex
    text: 'Let us turn to another example in a different branch of science. Whichever of our modern discoveries we may consider to be the most startling and important, there can I think be no doubt that the most beautiful is that of the spectroscope. It has enabled us to do that which but a few years before its introduction was taken for the very type of the impossible, viz., to study the chemical composition of the stars; and it is giving us clearer and clearer insight every day into the condition of the great luminary which forms the center of our system. Still, however beautiful and interesting such results may be, it might well be thought that they could never have any practical application, and that the spectroscope at least would remain an instrument of science, but of science alone. This, however, is not the case.',
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    id: 'SMK12',
    grade: '12',
    // dataset item 2577, annotated: moderately_complex
    text: 'Corals in the Red Sea have to handle higher temperatures, yet they seem to grow and do just fine. The Red Sea is a very warm sea compared to other places. There, summer temperatures can reach up to 34°C, while other ocean waters may reach around 29–32°C. Interestingly, corals in the Red Sea are not only living in higher temperatures but also in higher salinity, or the amount of salt in water, for example, in seawater. You can find a range of different salinities in the ocean, depending on the region. The Red Sea has some of the highest levels of salt. Salinity is a measure of the amount of salt in the water, and the Red Sea has some of the world\'s highest salt levels. That is why we started wondering whether salinity could be a piece of the puzzle and the ability to live in high salinity one of the secrets of the strong Red Sea corals? To answer this and other questions related to coral bleaching, scientists often use a coral model organism, which means an animal that is easier to study than corals but at the same time is very similar to corals.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
];

describeIntegration.concurrent('SMK Evaluator - Comprehensive Test Suite', () => {
  let evaluator: BackgroundKnowledgeDemandsEvaluator;

  beforeAll(() => {
    evaluator = new BackgroundKnowledgeDemandsEvaluator({
      googleApiKey: process.env.GOOGLE_API_KEY!,
    });

    console.log('\n' + '='.repeat(80));
    console.log('SMK EVALUATOR - TEST SUITE (PARALLEL)');
    console.log('='.repeat(80));
    console.log(`Running ${TEST_CASES.length} test cases with up to 3 attempts each`);
    console.log('Short-circuiting on first expected match');
    console.log('Checking acceptable values if no expected match');
    console.log('='.repeat(80));
  });

  // Generate individual test for each case
  TEST_CASES.forEach((testCase) => {
    it.concurrent(`${testCase.id}: Grade ${testCase.grade} - ${testCase.expected}`, async () => {
      // Buffer all logs to print atomically at the end (prevents interleaving in parallel tests)
      const logBuffer: string[] = [];

      // Test header
      logBuffer.push('\n' + '='.repeat(80));
      logBuffer.push(`Test Case ${testCase.id} | Grade: ${testCase.grade}`);
      logBuffer.push('='.repeat(80));
      logBuffer.push(`Expected Complexity: ${testCase.expected}`);
      logBuffer.push(`Text Preview: ${testCase.text.substring(0, 100)}...`);
      logBuffer.push('');

      // Run the evaluation (returns logs instead of printing)
      const maxAttempts = 3;
      const result = await runEvaluatorTest(testCase, {
        evaluator,
        extractResult: (r) => r.score,
        maxAttempts,
      });

      // Add evaluation logs to buffer (includes detailed summary)
      logBuffer.push(...result.logs);

      // Print all logs atomically at the end - single console.log to prevent interleaving
      console.log(logBuffer.join('\n'));

      // Assert that we got a match within maxAttempts (expected or acceptable)
      expect(result.matched).toBe(true);
      expect(result.matchedOnAttempt).toBeDefined();
      expect(result.matchedOnAttempt).toBeLessThanOrEqual(maxAttempts);
    }, TEST_TIMEOUT_MS);
  });
});
