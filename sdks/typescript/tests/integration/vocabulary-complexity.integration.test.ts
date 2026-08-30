import { describe, it, expect, beforeAll } from 'vitest';
import { VocabularyComplexityEvaluator } from '../../src/evaluators/student-facing-text/ela-reading/vocabulary-complexity.js';
import {
  runEvaluatorTest,
  type BaseTestCase,
} from '../utils/index.js';

/**
 * Vocabulary Evaluator Integration Tests
 *
 * Test cases cover grades 3-9 with varying complexity levels.
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
if (RUN_INTEGRATION) {
  if (!process.env.OPENAI_API_KEY) throw new Error('OPENAI_API_KEY is required when RUN_INTEGRATION_TESTS=true');
  if (!process.env.GOOGLE_API_KEY) throw new Error('GOOGLE_API_KEY is required when RUN_INTEGRATION_TESTS=true');
}
const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;

// Test timeout: 2 minutes per test case (allows for 3 attempts with API latency)
const TEST_TIMEOUT_MS = 2 * 60 * 1000;

// Test cases from PR #6
const TEST_CASES: BaseTestCase[] = [
  {
    id: 'V3',
    grade: '3',
    text: 'Civil rights are rights that all people in a country have. The civil rights of a country apply to all the citizens within its borders. These rights are given by the laws of the country. Civil rights are sometimes thought to be the same as natural rights. In many countries civil rights include freedom of speech, freedom of the press, freedom of religion, and freedom of assembly. Civil rights also include the right to own property and the right to get fair and equal treatment from the government, from other citizens, and from private groups.',
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    id: 'V4',
    grade: '4',
    text: 'Bluetooth is a protocol for wireless communication over short distances. It was developed in the 1990s, to reduce the number of cables. Devices such as mobile phones, laptops, PCs, printers, digital cameras and video game consoles can connect to each other, and exchange information. This is done using radio waves. It can be done securely. Bluetooth is only used for relatively short distances, like a few metres. There are different standards. Data rates vary. Currently, they are at 1-3 MBit per second.',
    expected: 'exceedingly_complex',
    acceptable: ['very_complex'],
  },
  {
    id: 'V5',
    grade: '5',
    text: `The scientific method is a way to learn about the world around us. It helps us figure out how things work. Scientists use the scientific method to test their ideas. They start by making observations and asking questions. Then, they make a guess, or a hypothesis, about what might be the answer. They use their hypothesis to make predictions about what will happen in an experiment. Scientists then test their predictions by doing experiments. If the results of the experiment match their predictions, then their hypothesis is supported. If the results don't match, then they need to change their hypothesis. Scientists repeat this process many times to make sure their hypothesis is correct. The scientific method is important because it helps us learn new things. It helps us understand the world around us. Scientists use the scientific method to make new discoveries and solve problems.`,
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    id: 'V6',
    grade: '6',
    text: `Chicago in 1871 was a city ready to burn. The city boasted having 59,500 buildings, many of them—such as the Courthouse and the Tribune Building—large and ornately decorated. The trouble was that about two-thirds of all these structures were made entirely of wood. Many of the remaining buildings (even the ones proclaimed to be 'fireproof') looked solid, but were actually jerrybuilt affairs; the stone or brick exteriors hid wooden frames and floors, all topped with highly flammable tar or shingle roofs. It was also a common practice to disguise wood as another kind of building material. The fancy exterior decorations on just about every building were carved from wood, then painted to look like stone or marble.`,
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    id: 'V7',
    grade: '7',
    text: `The scientific method is a way of learning about the world around us. It's a process that helps us understand how things work and why they happen. It's not just for scientists; we all use the scientific method in our everyday lives, even if we don't realize it. The scientific method starts with an observation. We notice something interesting and want to know more about it. For example, you might notice that your plant is wilting. You might wonder why this is happening. Next, we form a hypothesis, which is a possible explanation for our observation. In our plant example, you might hypothesize that the plant is wilting because it needs more water. Then, we test our hypothesis by doing an experiment. We change something in our experiment to see if it affects the outcome. In our plant example, you could water the plant and see if it recovers. Based on the results of our experiment, we can either support or reject our hypothesis. If the plant recovers after being watered, then your hypothesis is supported. If the plant doesn't recover, then you need to come up with a new hypothesis. The scientific method is a powerful tool for learning and understanding the world around us. It's a process of asking questions, testing ideas, and drawing conclusions based on evidence. It's a way of thinking that helps us to be curious, to be critical, and to be open to new ideas.`,
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    id: 'V8',
    grade: '8',
    text: 'The American Revolution was a war for independence between the thirteen American colonies and Great Britain. The war started in 1775 and ended in 1783. The colonists wanted to be free from British rule. They wanted to make their own laws and govern themselves. The colonists were angry about new taxes that the British Parliament imposed on them. They felt that they were being taxed without having a say in how the money was spent. The colonists also felt that the British government was not treating them fairly. The war began with the Battles of Lexington and Concord in April 1775. The colonists, led by General George Washington, fought against the British army. The war was long and difficult, but the colonists eventually won. The colonists won the war because they had the support of the French. The French helped the colonists by providing them with soldiers, ships, and money. The colonists also had a strong leader in George Washington. He was a skilled military leader and he inspired the colonists to fight for their freedom. The American Revolution was a turning point in history. It showed that colonies could break free from their mother countries and become independent nations. The American Revolution also inspired other revolutions around the world.',
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    id: 'V9',
    grade: '9',
    text: `Mr. President: I would like to speak briefly and simply about a serious national condition. It is a national feeling of fear and frustration that could result in national suicide and the end of everything that we Americans hold dear. It is a condition that comes from the lack of effective leadership in either the Legislative Branch or the Executive Branch of our Government. That leadership is so lacking that serious and responsible proposals are being made that national advisory commissions be appointed to provide such critically needed leadership. I speak as briefly as possible because too much harm has already been done with irresponsible words of bitterness and selfish political opportunism. I speak as briefly as possible because the issue is too great to be obscured by eloquence. I speak simply and briefly in the hope that my words will be taken to heart. I speak as a Republican. I speak as a woman. I speak as a United States Senator. I speak as an American. The United States Senate has long enjoyed worldwide respect as the greatest deliberative body in the world. But recently that deliberative character has too often been debased to the level of a forum of hate and character assassination sheltered by the shield of congressional immunity. It is ironical that we Senators can in debate in the Senate directly or indirectly, by any form of words, impute to any American who is not a Senator any conduct or motive unworthy or unbecoming an American—and without that non-Senator American having any legal redress against us—yet if we say the same thing in the Senate about our colleagues we can be stopped on the grounds of being out of order. It is strange that we can verbally attack anyone else without restraint and with full protection and yet we hold ourselves above the same type of criticism here on the Senate Floor. Surely the United States Senate is big enough to take self-criticism and self-appraisal. Surely we should be able to take the same kind of character attacks that we "dish out" to outsiders. I think that it is high time for the United States Senate and its members to do some soul-searching—for us to weigh our consciences—on the manner in which we are performing our duty to the people of America—on the manner in which we are using or abusing our individual powers and privileges. I think that it is high time that we remembered that we have sworn to uphold and defend the Constitution. I think that it is high time that we remembered that the Constitution, as amended, speaks not only of the freedom of speech but also of trial by jury instead of trial by accusation. Whether it be a criminal prosecution in court or a character prosecution in the Senate, there is little practical distinction when the life of a person has been ruined. Those of us who shout the loudest about Americanism in making character assassinations are all too frequently those who, by our own words and acts, ignore some of the basic principles of Americanism: The right to criticize; The right to hold unpopular beliefs; The right to protest; The right of independent thought. The exercise of these rights should not cost one single American citizen his reputation or his right to a livelihood nor should he be in danger of losing his reputation or livelihood merely because he happens to know someone who holds unpopular beliefs. Who of us doesn't? Otherwise none of us could call our souls our own. Otherwise thought control would have set in. The American people are sick and tired of being afraid to speak their minds lest they be politically smeared as "Communists" or "Fascists" by their opponents. Freedom of speech is not what it used to be in America. It has been so abused by some that it is not exercised by others. The American people are sick and tired of seeing innocent people smeared and guilty people whitewashed. But there have been enough proved cases, such as the Amerasia case, the Hiss case, the Coplon case, the Gold case, to cause the nationwide distrust and strong suspicion that there may be something to the unproved, sensational accusations. I doubt if the Republican Party could—simply because I don't believe the American people will uphold any political party that puts political exploitation above national interest. Surely we Republicans aren't that desperate for victory. I don't want to see the Republican Party win that way. While it might be a fleeting victory for the Republican Party, it would be a more lasting defeat for the American people. Surely it would ultimately be suicide for the Republican Party and the two-party system that has protected our American liberties from the dictatorship of a one-party system. As members of the Minority Party, we do not have the primary authority to formulate the policy of our Government. But we do have the responsibility of rendering constructive criticism, of clarifying issues, of allaying fears by acting as responsible citizens. As a woman, I wonder how the mothers, wives, sisters, and daughters feel about the way in which members of their families have been politically mangled in the Senate debate—and I use the word "debate" advisedly. As a United States Senator, I am not proud of the way in which the Senate has been made a publicity platform for irresponsible sensationalism. I am not proud of the reckless abandon in which unproved charges have been hurled from the side of the aisle. I am not proud of the obviously staged, undignified countercharges that have been attempted in retaliation from the other side of the aisle. I don't like the way the Senate has been made a rendezvous for vilification, for selfish political gain at the sacrifice of individual reputations and national unity. I am not proud of the way we smear outsiders from the Floor of the Senate and hide behind the cloak of congressional immunity and still place ourselves beyond criticism on the Floor of the Senate. As an American, I am shocked at the way Republicans and Democrats alike are playing directly into the Communist design of "confuse, divide, and conquer." As an American, I don't want a Democratic Administration "whitewash" or "cover-up" any more than I want a Republican smear or witch hunt. As an American, I condemn a Republican "Fascist" just as much I condemn a Democratic "Communist." I condemn a Democrat "Fascist" just as much as I condemn a Republican "Communist." They are equally dangerous to you and me and to our country. As an American, I want to see our nation recapture the strength and unity it once had when we fought the enemy instead of ourselves. It is with these thoughts that I have drafted what I call a "Declaration of Conscience." I am gratified that Senator Tobey, Senator Aiken, Senator Morse, Senator Ives, Senator Thye, and Senator Hendrickson have concurred in that declaration and have authorized me to announce their concurrence.`,
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
];

describeIntegration.concurrent('Vocabulary Evaluator - Comprehensive Test Suite', () => {
  let evaluator: VocabularyComplexityEvaluator;

  beforeAll(() => {
    evaluator = new VocabularyComplexityEvaluator({
      googleApiKey: process.env.GOOGLE_API_KEY!,
      openaiApiKey: process.env.OPENAI_API_KEY!,
    });

    console.log('\n' + '='.repeat(80));
    console.log('VOCABULARY EVALUATOR - TEST SUITE (PARALLEL)');
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
