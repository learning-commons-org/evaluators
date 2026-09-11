import { describe, it, expect } from 'vitest';
import { GradeLevelAppropriatenessEvaluator } from '../../src/evaluators/student-facing-text/ela-reading/grade-level-appropriateness.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';

/**
 * GradeLevelAppropriateness Evaluator Integration Tests
 *
 * Which grade band a text suits at independent reading. Takes no grade — it returns one.
 *
 * Only one fixture records a band, so the rest are texts whose target grade another
 * evaluator's fixtures record: the expected band is the one containing that grade, and
 * its neighbours are accepted. That is a regression detector rather than a measure of
 * quality — it catches a grade-3 text being placed at 11-12, which is what a broken
 * prompt, model or band list looks like.
 *
 * Each case retries up to three times and passes on the first expected match; if none
 * arrives, an adjacent value is accepted. To run these tests:
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
    // fixture
    id: 'trees',
    text: 'Trees are important plants that grow in many parts of the world. They have roots that go deep into the ground to find water and nutrients. Their leaves use sunlight to make food through a process called photosynthesis. Trees provide homes for birds and animals. They also give us wood for building homes and making furniture. Some trees produce fruit that people and animals eat. Forests made of many trees help keep the air clean and fresh.',
    expected: '4-5',
    acceptable: ['2-3', '6-8'],
  },
  {
    // graded text (grade 3)
    id: 'GRADE3-NASA-001',
    text: 'Why Is This Program Called Artemis?\nThe first astronauts landed on the Moon in 1969. The missions were called Apollo. The name Apollo came from stories told by Greek people long ago. In the stories, Apollo was a god. Apollo had a twin sister. Her name was Artemis. She was the goddess of the Moon in the Greek stories.\n\nWhat Spacecraft Will Be Used for the Artemis Program?\nNASA has a new rocket. It is the Space Launch System. It is called SLS for short. It is the most powerful rocket in the world. SLS will carry the Orion spacecraft on top. Orion can carry up to four astronauts. Orion will fly around, or orbit, the Moon. The crew will take trips in spacecraft called landers to get to work on the surface of the Moon. When all of their work is finished, the crew will return to Earth aboard Orion.\n\nWhen Will Artemis Go to the Moon? \nThe first Apollo missions were tests. NASA launched the rocket to be sure it was safe for people and work as planned. Artemis will be tested first, too: Artemis 1 launched SLS and Orion with no astronauts on Nov. 16, 2022. Artemis 2 is carrying astronauts. They will circle past the Moon and return to Earth. Artemis 3 will send a crew with the next man to land on the Moon. Artemis 4 will send astronauts to land on the Moon.\n\nWhat Will Artemis Astronauts Do on the Moon?\nThe Artemis 4 crew will visit the Moon’s South Pole. No one has ever been there. At the Moon, astronauts will:\nSearch for the Moon’s water and use it.\nLearn how to live and work on a different planet or moon. \nTest the new tools that astronauts will need for a mission to Mars.\n\nWhy Is the Artemis Program Important?\nThe Moon is a good place to learn new science. NASA will learn more about the Moon, Earth, and even the Sun. The Moon is also a place to learn how astronauts can one day live and work on Mars.\nAstronauts on the Artemis missions will need new tools. Many companies will make these new tools. This will mean new jobs for people and companies on Earth. Other countries will be NASA’s partners for the new Moon missions. They will work on Artemis to bring the world together for a mission to Earth’s nearest neighbor in space."',
    expected: '2-3',
    acceptable: ['K-1', '4-5'],
  },
  {
    // graded text (grade 4)
    id: 'GRADE4-GUT-3474',
    text: 'A thousand years ago boys and girls did not learn to read. Books were very scarce and very precious, and only a few men could read them.\n\nEach book was written with a pen or a brush. The pictures were painted by hand, and some of them were very beautiful. A good book would sometimes cost as much as a good house.\n\nIn those times there were even some kings who could not read. They thought more of hunting and fighting than of learning.\n\nThere was one such king who had four sons, Ethelbald, Ethelbert, Ethelred, and Alfred. The three older boys were sturdy, half-grown lads; the youngest, Alfred, was a slender, fair-haired child.\n\nOne day when they were with their mother, she showed them a wonderful book that some rich friend had given her. She turned the leaves and showed them the strange letters. She showed them the beautiful pictures, and told them how they had been drawn and painted.\n\nThey admired the book very much, for they had never seen anything like it. "But the best part of it is the story which it tells," said their mother. "If you could only read, you might learn that story and enjoy it. Now I have a mind to give this book to one of you"\n\n"Will you give it to me, mother?" asked little Alfred.\n\n"I will give it to the one who first learns to read in it" she answered.\n\n"I am sure I would rather have a good bow with arrows" said Ethelred.\n\n"And I would rather have a young hawk that has been trained to hunt" said Ethelbert.\n\n"If I were a priest or a monk" said Ethelbald, "I would learn to read. But I am a prince, and it is foolish for princes to waste their time with such things."\n\n"But I should like to know the story which this book tells," said\nAlfred.\n\nA few weeks passed by. Then, one morning, Alfred went into his mother\'s room with a smiling, joyous face.\n\n"Mother," he said, "will you let me see that beautiful book again?"\n\nHis mother unlocked her cabinet and took the precious volume from its place of safe keeping.\n\nAlfred opened it with careful fingers. Then he began with the first word on the first page and read the first story aloud without making one mistake.\n\n"O my child, how did you learn to do that?" cried his mother.\n\n"I asked the monk, Brother Felix, to teach me," said Alfred. "And every day since you showed me the book, he has given me a lesson. It was no easy thing to learn these letters and how they are put together to make words. Now, Brother Felix says I can read almost as well as he."\n\n"How wonderful!" said his mother.\n\n"How foolish!" said Ethelbald.\n\n"You will be a good monk when you grow up," said Ethelred, with a sneer.\n\nBut his mother kissed him and gave him the beautiful book. "The prize is yours, Alfred," she said. "I am sure that whether you grow up to be a monk or a king, you will be a wise and noble man."\n\nAnd Alfred did grow up to become the wisest and noblest king that England ever had. In history he is called Alfred the Great.',
    expected: '4-5',
    acceptable: ['2-3', '6-8'],
  },
  {
    // graded text (grade 7)
    id: 'GRADE7-FYM-1106',
    text: 'How Much Sleep Do You Need?\n\nThe National Sleep Foundation recommends that school-aged kids (6–13 years) sleep between 9 and 11 h a night. Teens are recommended to get 8–10 h a night and adults about 7–9 h . If you are a student, particularly in the United States, you may find it difficult to get this amount of sleep on school nights. As you go through puberty, your body wants to go to bed later and sleep later. But school (particularly in the U.S.) often starts too early! This makes it hard for teenagers to get enough sleep on school nights. By the weekend, you probably have missed so much sleep that you feel particularly sleepy, and you may dramatically oversleep as your sleep homeostat works hard to recover the sleep you need. If you oversleep all weekend, however, this can make waking up on Monday morning a miserable experience.',
    expected: '6-8',
    acceptable: ['4-5', '9-10'],
  },
  {
    // graded text (grade 10)
    id: 'GRADE10-CC-3983',
    text: 'When I spoke eight days ago there was still a glimpse of hope that Italy\'s participation in the war could be avoided. That hope proved fallacious. German feeling strove against the belief in the possibility of such a change. Italy has now inscribed in the book of the world\'s history, in letters of blood which will never fade, her violation of faith.\n\nI believe Machiavelli once said that a war which is necessary is also just. Viewed from this sober, practical, political standpoint, which leaves out of account all moral considerations, has this war been necessary? Is it not, indeed, directly mad? [Cheers.] Nobody threatened Italy; neither Austria-Hungary nor Germany. Whether the Triple Entente was content with blandishments alone history will show later. [Cheers.] Without a drop of blood flowing, and without the life of a single Italian being endangered, Italy could have secured the long list of concessions which I recently read to the House—territory in Tyrol and on the Isonzo as far as the Italian speech is heard, satisfaction of the national aspirations in Trieste, a free hand in Albania, and the valuable port of Valona.\n\nWhy have they not taken it? Do they, perhaps, wish to conquer the German Tyrol? Hands off! [Prolonged cheers.] Did Italy wish to provoke Germany, to whom she owes so much in her upward growth of a great power, and from whom she is not separated by any conflict of interests? We left Rome in no doubt that an Italian attack on Austro-Hungarian troops would also strike the German troops. [Cheers.] Why did Rome refuse so light-heartedly the proposals of Vienna? The Italian manifesto of war, which conceals an uneasy conscience behind vain phrases, does not give us any explanation. They were too shy, perhaps, to say openly what was spread abroad as a pretext by the press and by gossip in the lobbies of the Chamber, namely, that Austria\'s offer came too late and could not be trusted.',
    expected: '9-10',
    acceptable: ['6-8', '11-12'],
  },
  {
    // graded text (grade 12)
    id: 'GRADE12-CC-3565',
    text: 'Six years ago, at the time of the first conference to map out peace -- Dumbarton Oaks -- there was within the Soviet orbit 180 million people. Lined up on the anti-totalitarian side there were in the world at that time roughly 1.625 billion people. Today, only six years later, there are 800 million people under the absolute domination of Soviet Russia -- an increase of over 400 percent. On our\nside, the figure has shrunk to around 500 million. In other words, in less than six years the odds have changed from 9 to 1 in our favor to 8 to 5 against us. This indicates the swiftness of the tempo of communist victories and American defeats in the Cold War. As one of our outstanding historical figures once said, "When a great democracy is destroyed, it will not be because of enemies from without but rather because of enemies from within." The truth of this statement is becoming terrifyingly clear as we see this country each day losing on every front. \n\nAt war\'s end we were physically the strongest nation on Earth and, at least potentially, the most powerful intellectually and morally. Ours could have been the honor of being a beacon in the desert of destruction, a shining, living proof that civilization was not yet ready to destroy itself. Unfortunately, we have failed miserably and tragically to arise to the opportunity.\n\nThe reason why we find ourselves in a position of impotency is not because our only powerful, potential enemy has sent men to invade our shores, but rather because of the traitorous actions of those who have been treated so well by this nation. It has not been the less fortunate or members of minority groups who have been selling this nation out, but rather those who have had all the benefits that the wealthiest nation on earth has had to offer -- the finest homes, the finest college education, and the finest jobs in government we can give.',
    expected: '11-12',
    acceptable: ['9-10'],
  },
];

describeIntegration('GradeLevelAppropriatenessEvaluator - Integration', () => {
  it('spans more than one band', () => {
    expect(new Set(TEST_CASES.map((c) => c.expected)).size).toBeGreaterThan(1);
  });

  it.each(TEST_CASES)(
    '$id: expects $expected',
    async (testCase) => {
      const evaluator = new GradeLevelAppropriatenessEvaluator({
        googleApiKey: process.env.GOOGLE_API_KEY!,
        telemetry: false,
      });

      const result = await runEvaluatorTest(testCase, { evaluator });

      expect(result.matched, result.logs.join('\n')).toBe(true);
    },
    TEST_TIMEOUT_MS,
  );
});
