import { describe, it, expect, beforeAll } from 'vitest';
import { SentenceStructureEvaluator } from '../../src/evaluators/student-facing-text/ela-reading/sentence-structure.js';
import {
  runEvaluatorTest,
  type BaseTestCase,
} from '../utils/index.js';

/**
 * Sentence Structure Evaluator Integration Tests
 *
 * Test cases cover grades 3-6 with varying complexity levels.
 *
 * Each test uses a retry mechanism (up to 3 attempts) to account for LLM non-determinism,
 * with short-circuiting on first expected match. If no expected match is found after all
 * attempts, the test checks if any result falls within the acceptable value range.
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

// Test timeout: 2 minutes per test case (allows for 3 attempts with API latency)
const TEST_TIMEOUT_MS = 2 * 60 * 1000;

const TEST_CASES: BaseTestCase[] = [
  // {
  //   id: 'SS2',
  //   grade: '2',
  //   text: "The Roman Empire was a powerful empire that lasted for hundreds of years. It started as a small village in Italy and grew into a huge empire that controlled much of Europe, Asia, and Africa. The Roman Empire had many strong leaders like Julius Caesar and Augustus. These leaders helped the empire grow and become very powerful.\n \n\n The Roman Empire had a period of peace and prosperity called the Pax Romana. This time was good for the empire, but it didn't last forever. The empire started to have problems. The army became weaker, and the economy had problems. The empire was also attacked by groups of people called barbarians.\n \n\n The Roman Empire was divided into two parts: the Western Roman Empire and the Eastern Roman Empire. The Western Roman Empire eventually fell apart in 476 AD. The Eastern Roman Empire, also known as the Byzantine Empire, lasted for many more years. The Roman Empire left behind many things that we still use today, like the Roman alphabet and the calendar.",
  //   expected: 'moderately_complex',
  //   acceptable: ['slightly_complex', 'very_complex'],
  // },
  {
    id: 'SS3',
    grade: '3',
    text: "The hoisting gear consists of a double system of chains 13/16 in. in diameter placed side by side; each chain is anchored by an adjustable screw to the end of the jib, and, passing round the traveling carriage and down to the falling block, is taken along the jib over a sliding pulley which leads it on to the grooved barrel, 3 ft. 9 in. in diameter. In front of the barrel is placed an automatic winder which insures a proper coiling of the chain in the grooves. The motive power is derived from two cylinders 10 in. in diameter and 16 in. stroke, one being bolted to each side frame; these cylinders, which are provided with link motion and reversing gear, drive a steel crank shaft 2¾ in. in diameter; on this shaft is a steel sliding pinion which drives the barrel by a double purchase.",
    expected: 'exceedingly_complex',
    acceptable: ['very_complex'],
  },
  {
    id: 'SS4',
    grade: '4',
    text: "Before corals bleach, they do not show many other signs of feeling stressed. So, if we want to understand a coral's health, we have to study its cells. Inside cells we have a lot of information, including DNA, RNA, and proteins. These molecules can help us find clues about the communication between the coral and the algae. But also, these molecules can teach us how to know when corals are stressed.\nWhen an organism is stressed, every cell in its body will react. Everything will do its best to survive! In response to stress, the cell will use its DNA to make RNA, so that it can then make proteins that will fight off the stress. If an organism has been stressed before, it can respond to the stress faster and better. Think of it like visiting a city: the first time you visit, you will need a map to find your hotel. The more often you visit the city, the less you will need the map because you will remember, and you will get back to the hotel faster.",
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    id: 'SS5',
    grade: '5',
    text: "Mesopotamia, located in present-day Iraq, is known as the 'Cradle of Civilization' because it was home to some of the earliest civilizations in the world. The region got its name from the ancient Greek words for 'land between the rivers,' referring to the Tigris and Euphrates rivers. These rivers provided water for the fertile land, making it perfect for farming. The regular flooding of the rivers made the land around them ideal for growing crops, which helped people settle down and form permanent villages. These villages eventually grew into cities, where people developed many of the characteristics of civilization, like organized government, complex buildings, and different social classes.\n \n\n The first civilizations in Mesopotamia were the Sumerians, who lived around 5,000 years ago. They invented the world's first written language, called cuneiform, which they used to keep track of things like food supplies and trade. They also developed a system of numbers, which helped them with math and measurement. The Sumerians built impressive cities like Ur, Eridu, and Uruk, which had populations of over 50,000 people. These cities were centers of learning and culture, and they helped spread knowledge and ideas throughout the region.\n \n\n Over time, other civilizations rose and fell in Mesopotamia, including the Akkadians, Babylonians, and Assyrians. Each civilization made its own contributions to the development of human society. The Babylonians are famous for their code of laws, which was one of the first written legal systems in the world. The Assyrians were known for their powerful military and their impressive palaces. Mesopotamia's history is full of amazing inventions and innovations that shaped the world we live in today.\n \n\n The development of civilization in Mesopotamia was not just about the fertile land and the rivers. Changes in climate and the environment also played a role. People had to become more organized and work together to survive. This led to the development of complex societies and governments. Mesopotamia's story is a reminder of how human ingenuity and adaptability can lead to amazing achievements.\n \n\n The 'Cradle of Civilization' is a term that refers to the regions where the earliest known human civilizations emerged. Mesopotamia is a prime example of this, as it was a place where people learned to live together, build cities, and develop new technologies that changed the course of human history. The innovations that came from Mesopotamia, like writing, mathematics, and agriculture, continue to influence our lives today. By studying ancient Mesopotamia, we can learn about the origins of our own civilization and the challenges and triumphs of early humans.",
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
    // TODO: Valiadate the test-case with additional data from Grade 5
    // expected: 'exceedingly_complex',
    // acceptable: ['very_complex'],
  },
  {
    id: 'SS6',
    grade: '6',
    text: "Benjamin Franklin was a very important person in American history. He was born in Boston, Massachusetts in 1706. He was one of 17 children. Franklin did not go to school for very long. He learned to be a printer from his brother. Franklin was a very smart man. He invented many things, like bifocals, the Franklin stove, and the lightning rod. He also started the first public library in Philadelphia. Franklin was a writer, too. He wrote a book called *Poor Richard's Almanack*. It had many famous sayings, like \"Lost Time is never found again.\"\n\nFranklin was also a politician. He helped write the Declaration of Independence. He was a diplomat, too. He helped the United States get help from France during the Revolutionary War. He was a very busy man! Franklin was a scientist, a writer, a politician, and an inventor. He was a very important person in American history.\n\nFranklin was a very interesting person. He was a scientist who did experiments with electricity. He was a writer who wrote a book of sayings. He was a politician who helped the United States become independent. He was a diplomat who helped the United States get help from other countries. He was a very busy man!\n\nFranklin was a very smart man. He was a self-taught man who learned a lot on his own. He was a very creative man who invented many things. He was a very kind man who helped others. He was a very important man who helped shape the United States.\n\nFranklin was a very influential person. He was a leader who helped people. He was a thinker who came up with new ideas. He was a writer who shared his thoughts with others. He was a scientist who helped people understand the world. He was a very important person who helped make the United States what it is today.",
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
];

describeIntegration.concurrent('Sentence Structure Evaluator - Comprehensive Test Suite', () => {
  let evaluator: SentenceStructureEvaluator;

  beforeAll(() => {
    evaluator = new SentenceStructureEvaluator({
      openaiApiKey: process.env.OPENAI_API_KEY!,
    });

    console.log('\n' + '='.repeat(80));
    console.log('SENTENCE STRUCTURE EVALUATOR - TEST SUITE (PARALLEL)');
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
