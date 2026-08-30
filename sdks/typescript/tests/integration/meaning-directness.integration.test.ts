import { describe, it, expect, beforeAll } from 'vitest';
import { MeaningDirectnessEvaluator } from '../../src/evaluators/student-facing-text/ela-reading/meaning-directness.js';
import {
  runEvaluatorTest,
  type BaseTestCase,
} from '../utils/index.js';

/**
 * Meaning Directness Evaluator Integration Tests
 *
 * Test cases cover grades 3-12, one per grade, drawn from the annotated dataset
 * (dataset_conventionality.csv). complexity_score values are the dataset's own, which
 * the contract's schema also uses.
 *
 * Complexity distribution across test cases:
 * - Slightly complex:    Grades 4, 8
 * - Moderately complex:  Grades 5, 11, 12
 * - Very complex:        Grades 6, 7, 9, 10
 * - Exceedingly complex: Grade 3
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

// One test case per grade (3–12), drawn from dataset_conventionality.csv.
// Expected values are the dataset's complexity_score verbatim.
// Acceptable values are the adjacent complexity levels on the 4-point scale.
const TEST_CASES: BaseTestCase[] = [
  {
    id: 'CONV3',
    grade: '3',
    // dataset item 5915, annotated: exceedingly_complex
    // Abstract rhetoric, possible irony, and figurative language for Grade 3 readers
    text: "May I say a few words? I want to say a few words about this matter. I am a woman's rights. I have as much muscle as any man, and can do as much work as any man. I have plowed and reaped and husked and chopped and mowed, and can any man do more than that? I have heard much about the sexes being equal; I can carry as much as any man, and can eat as much too, if I can get it. I am as strong as any man that is now. As for intellect, all I can say is, if women have a pint and man a quart – why can't she have her little pint full? You need not be afraid to give us our rights for fear we will take too much, for we can't take more than our pint'll hold. The poor men seem to be all in confusion, and don't know what to do. Why children, if you have woman's rights, give it to her and you will feel better. You will have your own rights, and they won't be so much trouble. I can't read, but I can hear.",
    expected: 'exceedingly_complex',
    acceptable: ['very_complex'],
  },
  {
    id: 'CONV4',
    grade: '4',
    // dataset item 3314, annotated: slightly_complex
    // Largely explicit, literal explanatory text well within Grade 4 reach
    text: 'Look up at the sky. In many places you will see clouds. There are many different types of clouds. They are all different shapes and sizes. Some clouds are fluffy, while others are wispy. Some are big and others are small. Some even resemble familiar shapes. Have you ever wondered how clouds are formed? Clouds are made of evaporated water. Evaporation is when water changes from liquid to gas. Water evaporates from different sources all around you, like lakes, rivers, and the ocean. Can you guess the main source of water for clouds? The main source is the ocean. This is because the ocean makes up such a large part of the world. Seventy-one percent of our earth is covered by ocean. Water evaporates and becomes gas. This gas rises and mixes with particles in the air. It rises and rises until it cools and collects in one part of the sky. This forms a cloud. The kind of cloud that forms depends on the environment. Different clouds form at different heights. They change depending on the temperature, too. There are three major types of clouds: cirrus clouds, stratus clouds, and cumulus clouds. Each type of cloud looks different.',
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    id: 'CONV5',
    grade: '5',
    // dataset item 4257, annotated: moderately_complex
    // Some archaic phrasing and borderline figurative language ("zest of his everyday life")
    text: 'A few days ago I sat by the bedside of a wounded sapper\u2014a reservist\u2014and heard the story of life in a signal-box on a branch line in the North of England. The man was dying. I think he knew it. But the zest of his everyday life was still strong in him. He described the manner in which, on leaving the army originally, he had obtained his post on the railway. He told me that there were three trains each way in the day, and mentioned that on Winter nights the last train was frequently very late. This meant a late supper, but his wife saw to it that everything was kept hot. Sometimes his wife came to the box to meet him if it was a dry night. In the next bed there was a young Scotsman from a Highland district which I know very well. We were friends so soon as he learned that I knew his home. He was a roadman, and we talked of his roads and the changes which had been wrought in them of late years by motor traffic.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: 'CONV6',
    grade: '6',
    // dataset item 4336, annotated: very_complex
    // Abstract national qualities, rhetorical idealization, and figurative framing throughout
    text: "The whole world recognizes two qualities in the Englishman: his bravery and his common sense. We know that the Englishman is true to his given word, and that even in the antipodes he never changes his habits. As I write, the postman brings me a letter from the front, dated Oct. 17. The cavalryman who sends it tells of our Allies. 'We are fighting the enemy's cavalry,' he writes, 'and for two days my brigade was in action with the British. They know how to fight and they astonish us by their marvelous powers of organization and their coolness.' Yes, we know that of old. We also know that England never closes her doors to liberty. We have a confused memory of the hospitality given to our priests in the times of the Revolution. Now England provides us with fresh proof of her kindness of heart. You have heard the news\u2013the professors and students of the Catholic University of Louvain invited to Cambridge. The destroyed Belgian university reconstituted in the home of the celebrated English university. What a magnificent idea!",
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    id: 'CONV7',
    grade: '7',
    // dataset item 7385, annotated: very_complex
    // Figurative and abstract language appears regularly; requires interpretation of tone and implied themes
    text: "Our attention was called to the fact that there was 'practicing' going on, and we could, at 8:07, see quick flashes. That these flashes pointed directly at Scarborough we did not for a few minutes comprehend. Then, the fog slowly lifting, we saw a fog that was partly smoke. The castle grew into its place in the six miles distance. It seemed for a moment that the eight-foot-thick Norman walls tottered; but no, whatever tottered was behind the keep. Curiously enough we could barely hear the cannonading, for the wind was keen in the opposite direction, yet we could, as the minutes crept by and the air cleared, see distinctly the flashes from the boats and the flashes in the city. After about fifteen minutes there was a cessation, or perhaps a hesitation, that lasted two minutes; then the flashes continued.",
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    id: 'CONV8',
    grade: '8',
    // dataset item 6178, annotated: slightly_complex
    // Mostly explicit biographical narrative; historical context adds difficulty but language is largely literal
    text: "At Knob Creek the boy began to go to an 'A B C' school. His first teacher was Zachariah Riney. Of course, there were no regular schools in the backwoods then. When a man who 'knew enough' happened to come along, especially if he had nothing else to do, he tried to teach the children of the pioneers in a poor log schoolhouse. It is not likely that little Abe went to school more than a few weeks at this time, for he never had a year's schooling in his life. There was another teacher afterward at Knob Creek\u2013a man named Caleb Hazel. Little is known of either of these teachers except that he taught little Abe Lincoln. If their pupil had not become famous the men and their schools would never have been mentioned in history. An old man, named Austin Gollaher, used to like to tell of the days when he and little Abe went to school together. He said: 'Abe was an unusually bright boy at school, and made splendid progress in his studies. Indeed, he learned faster than any of his schoolmates. Though so young, he studied very hard.'",
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    id: 'CONV9',
    grade: '9',
    // dataset item 5369, annotated: very_complex
    // Abstract reasoning and conceptual framing; metaphors central to meaning; implicit rebuttal structure
    text: 'No one at this moment knows what electricity is; but for our present purpose we may regard it as a fluid, non-elastic, and without weight, and universally diffused through the universe. To judge by recently published statements, a large section of the reading public are taught that this fluid is a source of power, and that it may be made to do the work of coal. This is a delusion. So long as electricity remains in what we may call a normal state of repose, it is inert. Before we can get any work out of electricity a somewhat greater amount of work must be done upon it. If this fundamental and most important truth be kept in view it will not be easy to make a grave mistake in estimating the value of any of the numerous schemes for making electricity do work which will ere long be brought before the public.',
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    id: 'CONV10',
    grade: '10',
    // dataset item 4382, annotated: very_complex
    // Sustained irony and implicit comparison (savage/civilized); abstract social critique throughout
    text: "I know of no savage custom or habit of thought which has not its mate in civilized countries. For every mischievous or absurd practice of the natural man I can name you one of ours that is essentially the same. And nearly every custom of our barbarian ancestors in historic times persists in some form today. We make ourselves look formidable in battle--for that matter, we fight. Our women paint their faces. We feel it obligatory to dress more or less alike, inventing the most ingenious reasons for doing so and actually despising and persecuting those who do not care to conform. Almost within the memory of living persons bearded men were stoned in the streets; and a clergyman in New York who wore his beard as Christ wore his, was put into jail and variously persecuted till he died.",
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    id: 'CONV11',
    grade: '11',
    // dataset item 4323, annotated: moderately_complex
    // Vocabulary-driven complexity; abstract political/ideological language with occasional irony but clear argument
    text: "But the question, Why are we at war? can be answered fairly well by anybody conversant with the facts of the European situation. We are not at war because the Emperor, as war lord, has sent out word to his legions to begin a war of world-wide aggression, carrying into its vortex intellectual Germany, notwithstanding all her peaceful aspirations. I may fairly claim to be a representative of that intellectual Germany which comes in now for a good deal of sympathy, but I must own that intellectual Germany, as far as I know about her, thoroughly approves of the Emperor's present policy. She approves of it not on the principle merely 'Right or wrong, my country'; she does so because she knows that war has become inevitable, and that we must face that ordeal when we are ready for it, not at the moment most agreeable to our enemies.",
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    id: 'CONV12',
    grade: '12',
    // dataset item 5855, annotated: moderately_complex
    // A few abstract turns of phrase; demand mainly from vocabulary and sentence structure rather than conventionality
    text: "Here, the idlers of the place assemble to lounge and gossip, to look out for any outward-bound ships that are to be seen in the Channel, and to criticise the appearance and glorify the capabilities of the little fleet of Looe fishing-boats, riding snugly at anchor before them at the entrance of the bay. The inhabitants number some fourteen hundred; and are as good-humoured and unsophisticated a set of people as you will meet with anywhere. The Fisheries and the Coast Trade form their principal means of subsistence. The women take a very fair share of the hard work out of the men's hands. You constantly see them carrying coals from the vessels to the quay in curious hand-barrows: they laugh, scream, and run in each other's way incessantly: but these little irregularities seem to assist, rather than impede them, in the prosecution of their tasks. As to the men, one absorbing interest appears to govern them all. The whole day long they are mending boats, painting boats, cleaning boats, rowing boats, or, standing with their hands in their pockets, looking at boats.",
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
];

describeIntegration.concurrent('Meaning Directness Evaluator - Comprehensive Test Suite', () => {
  let evaluator: MeaningDirectnessEvaluator;

  beforeAll(() => {
    evaluator = new MeaningDirectnessEvaluator({
      googleApiKey: process.env.GOOGLE_API_KEY!,
    });

    console.log('\n' + '='.repeat(80));
    console.log('CONVENTIONALITY EVALUATOR - TEST SUITE (PARALLEL)');
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
      logBuffer.push(`Text Preview: ${(testCase.text ?? '').substring(0, 100)}...`);
      logBuffer.push('');

      // Run the evaluation (returns logs instead of printing)
      const maxAttempts = 3;
      const result = await runEvaluatorTest(testCase, {
        evaluator,
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
