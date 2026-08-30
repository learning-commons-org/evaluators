import { describe, it, expect } from 'vitest';
import { OrganizationalStructureEvaluator } from '../../src/evaluators/student-facing-text/ela-reading/organizational-structure.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';

/**
 * OrganizationalStructure Evaluator Integration Tests
 *
 * How clearly the text's organization supports a reader at the target grade.
 *
 * Cases are this evaluator's `fixtures.json`, plus two whose expected values were
 * captured against the same model and temperature this contract declares.
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
    id: 'NASA-001',
    grade: '3',
    text: 'Why Is This Program Called Artemis?\nThe first astronauts landed on the Moon in 1969. The missions were called Apollo. The name Apollo came from stories told by Greek people long ago. In the stories, Apollo was a god. Apollo had a twin sister. Her name was Artemis. She was the goddess of the Moon in the Greek stories.\n\nWhat Spacecraft Will Be Used for the Artemis Program?\nNASA has a new rocket. It is the Space Launch System. It is called SLS for short. It is the most powerful rocket in the world. SLS will carry the Orion spacecraft on top. Orion can carry up to four astronauts. Orion will fly around, or orbit, the Moon. The crew will take trips in spacecraft called landers to get to work on the surface of the Moon. When all of their work is finished, the crew will return to Earth aboard Orion.\n\nWhen Will Artemis Go to the Moon? \nThe first Apollo missions were tests. NASA launched the rocket to be sure it was safe for people and work as planned. Artemis will be tested first, too: Artemis 1 launched SLS and Orion with no astronauts on Nov. 16, 2022. Artemis 2 is carrying astronauts. They will circle past the Moon and return to Earth. Artemis 3 will send a crew with the next man to land on the Moon. Artemis 4 will send astronauts to land on the Moon.\n\nWhat Will Artemis Astronauts Do on the Moon?\nThe Artemis 4 crew will visit the Moon’s South Pole. No one has ever been there. At the Moon, astronauts will:\nSearch for the Moon’s water and use it.\nLearn how to live and work on a different planet or moon. \nTest the new tools that astronauts will need for a mission to Mars.\n\nWhy Is the Artemis Program Important?\nThe Moon is a good place to learn new science. NASA will learn more about the Moon, Earth, and even the Sun. The Moon is also a place to learn how astronauts can one day live and work on Mars.\nAstronauts on the Artemis missions will need new tools. Many companies will make these new tools. This will mean new jobs for people and companies on Earth. Other countries will be NASA’s partners for the new Moon missions. They will work on Artemis to bring the world together for a mission to Earth’s nearest neighbor in space."',
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    // fixture
    id: 'GUT-4164',
    grade: '3',
    text: 'One day in spring four men were riding on horseback along a country road. These men were lawyers, and they were going to the next town to attend court.\n\nThere had been a rain, and the ground was very soft. Water was dripping from the trees, and the grass was wet.\n\nThe four lawyers rode along, one behind another; for the pathway was narrow, and the mud on each side of it was deep. They rode slowly, and talked and laughed and were very jolly.\n\nAs they were passing through a grove of small trees, they heard a great fluttering over their heads and a feeble chirping in the grass by the roadside.\n\n"Stith! stith! stith!" came from the leafy branches above them.\n\n"Cheep! cheep! cheep!" came from the wet grass.\n\n"What is the matter here?" asked the first lawyer, whose name was Speed. "Oh, it\'s only some old robins!" said the second lawyer, whose name was Hardin. "The storm has blown two of the little ones out of the nest. They are too young to fly, and the mother bird is making a great fuss about it."\n\n"What a pity! They\'ll die down there in the grass," said the third lawyer, whose name I forget.\n\n"Oh, well! They\'re nothing but birds," said Mr. Hardin. "Why should we bother?"\n\n"Yes, why should we?" said Mr. Speed.\n\nThe three men, as they passed, looked down and saw the little birds fluttering in the cold, wet grass. They saw the mother robin flying about, and crying to her mate.\n\nThen they rode on, talking and laughing as before. In a few minutes they had forgotten about the birds.\n\nBut the fourth lawyer, whose name was Abraham Lincoln, stopped. He got down from his horse and very gently took the little ones up in his big warm hands.\n\nThey did not seem frightened, but chirped softly, as if they knew they were safe.\n\n"Never mind, my little fellows," said Mr. Lincoln "I will put you in your own cozy little bed."\n\nThen he looked up to find the nest from which they had fallen. It was high, much higher than he could reach.\n\nBut Mr. Lincoln could climb. He had climbed many a tree when he was a boy. He put the birds softly, one by one, into their warm little home. Two other baby birds were there, that had not fallen out. All cuddled down together and were very happy.',
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    // fixture
    id: 'FYM-1106',
    grade: '7',
    text: 'How Much Sleep Do You Need?\n\nThe National Sleep Foundation recommends that school-aged kids (6–13 years) sleep between 9 and 11 h a night. Teens are recommended to get 8–10 h a night and adults about 7–9 h . If you are a student, particularly in the United States, you may find it difficult to get this amount of sleep on school nights. As you go through puberty, your body wants to go to bed later and sleep later. But school (particularly in the U.S.) often starts too early! This makes it hard for teenagers to get enough sleep on school nights. By the weekend, you probably have missed so much sleep that you feel particularly sleepy, and you may dramatically oversleep as your sleep homeostat works hard to recover the sleep you need. If you oversleep all weekend, however, this can make waking up on Monday morning a miserable experience.',
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    // fixture
    id: 'CC-3517',
    grade: '11',
    text: 'Shredded in salads and slaws, steamed, or just peeled and dunked in an herb-speckled dip, carrots are versatile veggies that add colorful zest to our dinner plates. These crunchy orange roots are also a well-known source of vitamin A. Just a single, full-size carrot more than fulfills an adult\'s daily quotient of the essential vitamin.\n\nBut the carrot hasn\'t always been the vitamin A powerhouse that it is today. Over two decades ago, scientists in the ARS Vegetable Crops Research Unit at Madison, Wisconsin, began a quest to breed carrots packed with beta-carotene—an orange pigment used by the body to create vitamin A. Thanks largely to this ARS work, today\'s carrots provide consumers with 75 percent more beta-carotene than those available 25 years ago.\n  \nThe researchers, led by plant geneticist Philipp Simon, haven\'t limited themselves to the color orange. They\'ve selectively bred a rainbow of carrots—purple, red, yellow, even white. Scientists are learning that these plant pigments perform a range of protective duties in the human body—which is not surprising, says Simon, since many of the pigments serve to shield plant cells during photosynthesis.\n\nRed carrots derive their color mainly from lycopene, a type of carotene believed to guard against heart disease and some cancers. Yellow carrots accumulate xanthophylls, pigments similar to beta-carotene that support good eye health. Purple carrots possess an entirely different class of pigments—anthocyanins—which act as powerful antioxidants.\n\nWhile colored carrots are unusual, they\'re not exactly new. "Purple and yellow carrots were eaten more than 1,000 years ago in Afghanistan and 700 years ago in western Europe," says Simon. "But the carrot-breeding process has gone on intensively for just 50 years."',
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    // fixture
    id: 'CC-3983',
    grade: '10',
    text: 'When I spoke eight days ago there was still a glimpse of hope that Italy\'s participation in the war could be avoided. That hope proved fallacious. German feeling strove against the belief in the possibility of such a change. Italy has now inscribed in the book of the world\'s history, in letters of blood which will never fade, her violation of faith.\n\nI believe Machiavelli once said that a war which is necessary is also just. Viewed from this sober, practical, political standpoint, which leaves out of account all moral considerations, has this war been necessary? Is it not, indeed, directly mad? [Cheers.] Nobody threatened Italy; neither Austria-Hungary nor Germany. Whether the Triple Entente was content with blandishments alone history will show later. [Cheers.] Without a drop of blood flowing, and without the life of a single Italian being endangered, Italy could have secured the long list of concessions which I recently read to the House—territory in Tyrol and on the Isonzo as far as the Italian speech is heard, satisfaction of the national aspirations in Trieste, a free hand in Albania, and the valuable port of Valona.\n\nWhy have they not taken it? Do they, perhaps, wish to conquer the German Tyrol? Hands off! [Prolonged cheers.] Did Italy wish to provoke Germany, to whom she owes so much in her upward growth of a great power, and from whom she is not separated by any conflict of interests? We left Rome in no doubt that an Italian attack on Austro-Hungarian troops would also strike the German troops. [Cheers.] Why did Rome refuse so light-heartedly the proposals of Vienna? The Italian manifesto of war, which conceals an uneasy conscience behind vain phrases, does not give us any explanation. They were too shy, perhaps, to say openly what was spread abroad as a pretext by the press and by gossip in the lobbies of the Chamber, namely, that Austria\'s offer came too late and could not be trusted.',
    expected: 'very_complex',
    acceptable: ['moderately_complex', 'exceedingly_complex'],
  },
  {
    // fixture
    id: 'CC-3565',
    grade: '12',
    text: 'Six years ago, at the time of the first conference to map out peace -- Dumbarton Oaks -- there was within the Soviet orbit 180 million people. Lined up on the anti-totalitarian side there were in the world at that time roughly 1.625 billion people. Today, only six years later, there are 800 million people under the absolute domination of Soviet Russia -- an increase of over 400 percent. On our\nside, the figure has shrunk to around 500 million. In other words, in less than six years the odds have changed from 9 to 1 in our favor to 8 to 5 against us. This indicates the swiftness of the tempo of communist victories and American defeats in the Cold War. As one of our outstanding historical figures once said, "When a great democracy is destroyed, it will not be because of enemies from without but rather because of enemies from within." The truth of this statement is becoming terrifyingly clear as we see this country each day losing on every front. \n\nAt war\'s end we were physically the strongest nation on Earth and, at least potentially, the most powerful intellectually and morally. Ours could have been the honor of being a beacon in the desert of destruction, a shining, living proof that civilization was not yet ready to destroy itself. Unfortunately, we have failed miserably and tragically to arise to the opportunity.\n\nThe reason why we find ourselves in a position of impotency is not because our only powerful, potential enemy has sent men to invade our shores, but rather because of the traitorous actions of those who have been treated so well by this nation. It has not been the less fortunate or members of minority groups who have been selling this nation out, but rather those who have had all the benefits that the wealthiest nation on earth has had to offer -- the finest homes, the finest college education, and the finest jobs in government we can give.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    // fixture
    id: 'GUT-3474',
    grade: '4',
    text: 'A thousand years ago boys and girls did not learn to read. Books were very scarce and very precious, and only a few men could read them.\n\nEach book was written with a pen or a brush. The pictures were painted by hand, and some of them were very beautiful. A good book would sometimes cost as much as a good house.\n\nIn those times there were even some kings who could not read. They thought more of hunting and fighting than of learning.\n\nThere was one such king who had four sons, Ethelbald, Ethelbert, Ethelred, and Alfred. The three older boys were sturdy, half-grown lads; the youngest, Alfred, was a slender, fair-haired child.\n\nOne day when they were with their mother, she showed them a wonderful book that some rich friend had given her. She turned the leaves and showed them the strange letters. She showed them the beautiful pictures, and told them how they had been drawn and painted.\n\nThey admired the book very much, for they had never seen anything like it. "But the best part of it is the story which it tells," said their mother. "If you could only read, you might learn that story and enjoy it. Now I have a mind to give this book to one of you"\n\n"Will you give it to me, mother?" asked little Alfred.\n\n"I will give it to the one who first learns to read in it" she answered.\n\n"I am sure I would rather have a good bow with arrows" said Ethelred.\n\n"And I would rather have a young hawk that has been trained to hunt" said Ethelbert.\n\n"If I were a priest or a monk" said Ethelbald, "I would learn to read. But I am a prince, and it is foolish for princes to waste their time with such things."\n\n"But I should like to know the story which this book tells," said\nAlfred.\n\nA few weeks passed by. Then, one morning, Alfred went into his mother\'s room with a smiling, joyous face.\n\n"Mother," he said, "will you let me see that beautiful book again?"\n\nHis mother unlocked her cabinet and took the precious volume from its place of safe keeping.\n\nAlfred opened it with careful fingers. Then he began with the first word on the first page and read the first story aloud without making one mistake.\n\n"O my child, how did you learn to do that?" cried his mother.\n\n"I asked the monk, Brother Felix, to teach me," said Alfred. "And every day since you showed me the book, he has given me a lesson. It was no easy thing to learn these letters and how they are put together to make words. Now, Brother Felix says I can read almost as well as he."\n\n"How wonderful!" said his mother.\n\n"How foolish!" said Ethelbald.\n\n"You will be a good monk when you grow up," said Ethelred, with a sneer.\n\nBut his mother kissed him and gave him the beautiful book. "The prize is yours, Alfred," she said. "I am sure that whether you grow up to be a monk or a king, you will be a wise and noble man."\n\nAnd Alfred did grow up to become the wisest and noblest king that England ever had. In history he is called Alfred the Great.',
    expected: 'slightly_complex',
    acceptable: ['moderately_complex'],
  },
  {
    // upstream
    id: 'newfoundland_cod',
    grade: '5',
    text: 'For centuries, the cod off Newfoundland seemed endless — boats returned so full that fishermen said you could walk across the water on their backs. Today the fishery is closed. The story of how that happened is not a simple one. New technology let trawlers catch more fish faster than ever before, scooping up entire schools in a single haul. But the fish were also vanishing for reasons the boats couldn\'t see: warming waters shifted the cod\'s feeding grounds, and the removal of so many large fish left populations too young to rebuild. Government scientists had warned of decline for years. Their estimates, it turned out, had been based on the catch reports of the very fleets with the most to lose from a shutdown. By the time the cod were counted accurately, there were almost none left to count.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
  {
    // upstream
    id: 'whales_sing',
    grade: '3',
    text: 'Whales sing short and long songs. Some songs last just a few minutes. Some songs can go on for half an hour. Whales can also sing the same song for hours on end. There are many kinds of whales. Blue Whales and Grey Whales are named after colours. Humpback Whales and Bowhead Whales are named after the shapes of their backs and heads. Omura\'s Whales and Bryde\'s Whales are named after people. Each kind of whale has its own song. Just listen and you will be able to tell who is singing! Each species has different communities. They live in different parts of the ocean. Each community has its own songs. A blue whale in the Indian Ocean will sing a different song from his cousin in the Pacific. Humpback whales are excellent composers. They mix and match several notes together. Blue whales sing much simpler songs. Their songs consist of just a note or two.',
    expected: 'moderately_complex',
    acceptable: ['slightly_complex', 'very_complex'],
  },
];

describeIntegration('OrganizationalStructureEvaluator - Integration', () => {
  it('spans more than one complexity level', () => {
    // Cases that all expect the same value would pass for an evaluator stuck on it.
    expect(new Set(TEST_CASES.map((c) => c.expected)).size).toBeGreaterThan(1);
  });

  it.each(TEST_CASES)(
    '$id: expects $expected',
    async (testCase) => {
      const evaluator = new OrganizationalStructureEvaluator({
        googleApiKey: process.env.GOOGLE_API_KEY!,
        telemetry: false,
      });

      const result = await runEvaluatorTest(testCase, { evaluator });

      expect(result.matched, result.logs.join('\n')).toBe(true);
    },
    TEST_TIMEOUT_MS,
  );
});
