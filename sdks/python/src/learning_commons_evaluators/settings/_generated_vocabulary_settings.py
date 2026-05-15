# !! AUTO-GENERATED — do not edit directly.
# Source: sdks/settings/vocabulary/settings.toml
# Regenerate : python scripts/generate_settings.py
# Staleness check: python scripts/generate_settings.py --check

from __future__ import annotations

from learning_commons_evaluators.schemas.config import LLMProvider, PromptSettings
from learning_commons_evaluators.schemas.input_specs import GradeInputSpec, TextInputSpec
from learning_commons_evaluators.schemas.metadata import EvaluatorMaturity, EvaluatorMetadata
from learning_commons_evaluators.schemas.vocabulary import VocabularyEvaluationSettings
from learning_commons_evaluators.settings.load_settings import EvaluatorSettingsResult

# ── Evaluator metadata ────────────────────────────────────────────────────────

_EVALUATOR_METADATA = EvaluatorMetadata(
    id='vocabulary',
    version='0.1',
    name='Vocabulary',
    description='Vocabulary Complexity Evaluator',
    maturity=EvaluatorMaturity.alpha,
    inputs={
        'text': TextInputSpec(
            name='text',
            description='The text to evaluate for vocabulary complexity.',
        ),
        'grade': GradeInputSpec(
            name='grade',
            description='The grade level of the text (3–12).',
            allowed_grades=[3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        ),
    },
)

# ── Prompt templates ──────────────────────────────────────────────────────────

_PROMPTS: dict[str, str] = {
    'background_knowledge_prompt': """Review the following text, which is an educational text written for students in the following grade band: {grade}.

Your job is to give me a background knowledge assumption; that is: what topics, if any, from the text students are likely to be familiar with based on a standard progression of topics in US public school education, as well as topics, if any the student is not likely to be familiar with.

Make sure your response is concise (between 1 - 3 lines max) and is about the topics themselves, not about any other aspect of the text (e.g. flowery language, complicated sentence structure, etc.).

Here's an example:
[START EXAMPLE]
Grade Band: 11th
Text: I went to the woods because I wished to live deliberately, to front only the essential facts of life, and see if I could not
learn what it had to teach, and not, when I came to die, discover that I had not lived. I did not wish to live what was
not life, living is so dear; nor did I wish to practise resignation, unless it was quite necessary. I wanted to live deep and suck out all the marrow of life, to live so sturdily and Spartan-like as to put to rout all that was not life, to cut a broad swath and shave close, to drive life into a corner, and reduce it to its lowest terms, and, if it proved to be mean, why then to get the whole and genuine meanness of it, and publish its meanness to the world; or if it were sublime, to
know it by experience, and be able to give a true account of it in my next excursion. For most men, it appears to me,
are in a strange uncertainty about it, whether it is of the devil or of God, and have somewhat hastily concluded that it
is the chief end of man here to “glorify God and enjoy him forever.”

Background Knowledge Assumption: Assume they’ve studied American Transcendentalists like Thoreau and Emerson, including the mid-19th-century context of nature-focused philosophy.
[END EXAMPLE]

You should assume that the student is an average US public school who is learning from common core curriculum. When you respond, just respond with the background knowledge assumption and nothing else.

You can use the following list of topics that we know are covered for each grade level, although use your best judgement if you know there are other topics out there that students are likely to have covered. And this doesn't cover higher grade levels, so you'll have to again use your judgement for, say, what background knowledge a 9th grader is likely to have:
[BEGIN TOPICS]
[
    K: [
        "Toys and Play", "Weather Wonders", "Trees are Alive", "Enjoying and Appreciating Trees",
        "The Five Senses: How do our senses help us learn?", "Once Upon a Farm: What makes a good story?",
        "America, Then and Now: How has life in America changed over time?", "The Continents: What makes the world fascinating?",
        "Needs of Plants and Animals", "Pushes and Pulls", "Sunlight and Weather", "Learning and Working Together",
        "How Do People Learn and Work Together?", "Where Do We Live?", "What Does it Mean to Be an American?",
        "How Has Our World Changed?", "Why Do People Have Jobs?"
    ],
    1: [
        "Tools and Work", "A Study of the Sun, Moon, and Stars", "Birds' Amazing Bodies", "Caring for Birds",
        "A World of Books: How do books change lives around the world?", "Creature Features: What can we discover about animals’ unique features?",
        "Powerful Forces: How do people respond to the powerful force of the wind?", "Cinderella Stories: Why do people around the world admire Cinderella?",
        "Animal and Plant Defenses", "Light and Sounds", "Spinning Earth", "Our Place in the World",
        "What Are the Rights and Responsibilities of Citizens?", "How Can We Describe Where We Live?",
        "How Do We Celebrate Our Country?", "How Does the Past Shape Our Lives?", "Why Do People Work?"
    ],
    2: [
        "Schools and Community", "Fossils Tell of Earth's Changes", "The Secret World of Pollination", "Providing for Pollinators",
        "A Season of Change: How does change impact people and nature?", "The American West: What was life like in the West for early Americans?",
        "Civil Rights Heroes: How can people respond to injustice?", "Good Eating: How does food nourish us?",
        "Plant and Animal Relationships", "Properties of Matter", "Changing Landforms", "Exploring Who We Are",
        "Why Is It Important to Learn About the Past?", "How Does Geography Help Us Understand Our World?",
        "How Do We Get What We Want and Need?", "Why Do We Need Government?", "How Can People Make a Difference in Our World?"
    ],
    "3": [
        "Overcoming Learning Challenges Near and Far", "Adaptations and the Wide World of Frogs", "Exploring Literary Classics",
        "Water Around the World", "Ocean/Sea Exploration", "Outer Space", "Immigration", "Art/Being an Artist",
        "Balancing Forces", "Inheritance and Traits", "Environments and Survival", "Weather and Climate",
        "Communities", "Why Does It Matter Where We Live?", "What Is Our Relationship With Our Environment?",
        "What Makes a Community Unique?", "How Does the Past Impact the Present?", "Why Do Governments and Citizens Need Each Other?",
        "How Do People in a Community Meet Their Wants and Needs?"
    ],
    4: [
        "Poetry", "Animal Defense Mechanisms", "The American Revolution",
        "Responding to Inequality: Ratifying the 19th Amendment (covers gender and racial inequality)",
        "A Great Heart: What does it mean to have a great heart, literally and figuratively?",
        "Extreme Settings: How does a challenging setting or physical environment change a person?",
        "American Revolution/Multiple Perspectives", "Myths/Myth Making", "Energy Conversions", "Vision and Light",
        "Earth's Features", "Waves, Energy, and Information", "Regions of the United States",
        "How Does America Use Its Strengths and Face Its Challenges?", "Why Have People Moved to and From the Northeast?",
        "How Has the Southeast Changed Over Time?", "How Does the Midwest Reflect the Spirit of America?",
        "How Does the Southwest Reflect Its Diverse Past and Unique Environment?", "What Draws People to the West?"
    ],
    5: [
        "Human Rights", "Biodiversity in the Rainforest", "Athlete Leaders of Social Change",
        "Impact of Natural Disasters", "Cultures in Conflict: How do cultural beliefs and values guide people?",
        "Word Play: How and why do writers play with words?", "A War Between Us: How did the Civil War impact people?",
        "Breaking Barriers: How can sports influence individuals and societies?", "Patterns of Earth and Sky",
        "Modeling Matter", "The Earth System", "Ecosystem Restoration", "U.S. History: Making a New Nation",
        "How Were the Lives of Native Peoples Influenced by Where They Lived?",
        "What Happened When Diverse Cultures Crossed Paths?", "What Is the Impact of People Settling in a New Place?",
        "Why Would a Nation Want to Become Independent?", "What Does the Revolutionary Era Tell Us About Our Nation Today?",
        "How Does the Constitution Help Us Understand What It Means to Be an American?",
        "What Do the Early Years of the United States Reveal About the Character of the Nation?",
        "What Was the Effect of the Civil War on U.S. Society?"
    ],
    6: [
        "Greek Mythology", "Critical Problems and Design Solutions", "American Indian Boarding Schools",
        "Remarkable Accomplishments in Space Science", "Resilience in the Great Depression: How can enduring tremendous hardship contribute to personal transformation?",
        "A Hero’s Journey: What is the significance and power of the hero’s journey?",
        "Narrating the Unknown: How did the social and environmental factors in the unknown world of Jamestown shape its development and decline?",
        "Courage in Crisis: How can the challenges of a hostile environment inspire heroism?",
        "Microbiome", "Metabolism", "Metabolism Engineering", "Traits and Reproduction", "Thermal Energy",
        "Ocean, Atmosphere, and Climate", "Weather Patterns", "Earth's Changing Climate",
        "Earth's Changing Climate: Engineering Internship", "The First Americans (up to 1492)",
        "Exploration and Colonization", "English Colonies", "American Revolution", "First Governments and the Constitution",
        "The Early American Republic", "Political and Geographic Changes (1828-1850)", "Life in the North and South (1820-1860)",
        "Division and Civil War (1821-1865)", "Reconstruction (1865-1896)", "The West (1858-1896)",
        "New Industry and a Changing Society", "Expansion and War", "The 1920s and 1930s", "World War II",
        "The Cold War", "Civil Rights and American Society", "America Since the 1970s"
    ],
    7: [
        "The Lost Children of Sudan (Genocide, Genocide in Sudan)", "Epidemics", "Harlem Renaissance", "Plastic Pollution",
        "Identity in the Middle Ages: How does society both support and limit the development of identity?",
        "Americans All: How did World War II affect individuals?", "Language and Power: What is the power of language?",
        "Fever: How can times of crisis affect citizens and society?", "Geology on Mars", "Plane Motion", "Plane Motion Engineering",
        "Rock Formations", "Phase Change", "Phase Change Engineering", "Chemical Reactions", "Populations and Resources",
        "Matter and Energy in Ecosystems", "Early Humans and Agricultural Revolution", "Fertile Crescent",
        "Ancient Egypt and Kush", "The Israelites", "Ancient Greece", "Ancient South Asia", "Early China, Korea, and Japan",
        "Ancient Rome", "Rise of Christian Kingdoms", "The Americas", "Medieval Europe", "The Rise of Islamic Empires",
        "China in the Middle Ages", "Korea and Japan in the Middle Ages", "African Civilizations", "New Ways of Thinking",
        "Age of Exploration and Trade", "Revolutions and Empires", "The Modern World"
    ],
    8: [
        "Folklore of Latin America", "Food Choices", "The Holocaust", "Japanese American Internment",
        "The Poetics and Power of Storytelling: What is the power of storytelling?",
        "The Great War: How do literature and art illuminate the effects of World War I?", "What Is Love?",
        "Teens as Change Agents: How do people effect social change?", "Harnessing Human Energy",
        "Force and Motion", "Force and Motion Engineering", "Magnetic Fields", "Light Waves", "Earth, Moon, and Sun",
        "Natural Selection", "Natural Selection Engineering", "Evolutionary History", "The World in Spatial Terms",
        "Places and Regions", "Physical Geography", "Population Geography", "Economic Geography",
        "Political Geography", "Human-Environment Geography", "What is Economics?", "Markets, Money, and Businesses",
        "Government and the Economy", "The Global Economy"
    ]
]
[END TOPICS]

Here is the text:
[BEGIN TEXT]
{text}
[END TEXT]
""",
    'vocab_grades_3_4_system_prompt': """You are an expert curriculum designer. Your job is to rate the complexity of a text's vocabulary relative to the grade level.

You will be given a rubric (with levels from least to most complex: slightly complex, moderately complex, very complex, exceedingly complex) as well as guidelines for interpreting the rubric.
IMPORTANT: You should only pay attention to the vocabulary. Do not evaluate any other element of the text's complexity (e.g. sentence structure, meaning, etc.)

**Resource 1: Qualitative Text Complexity rubric (SAP)**
1.  **Level 1: Slightly complex**
    *   Original Definition: Vocabulary that is almost entirely not complex: contemporary, conversational, and/or familiar. A very low proportion of complex words (archaic, subject-specific, academic) is OK -- i.e. doesn't need to be 0.
    *   Summary definition: Overall, vocabulary is easy to understand and does not impede comprehension of the bulk of the text (including main idea and supporting claims). 1-2 quick pauses for processing by the student are ok here!
2.  **Level 2: Moderately complex**
    *   Original Definition: Vocabulary that is mostly not complex: contemporary, conversational, and/or familiar. A low proportion of complex words (archaic, subject-specific, academic) is OK
    *   Summary definition: Overall, vocabulary generally allows students to comprehend the bulk of the text with little difficulty, though there may be occasional pauses for clarification. Several quick pauses or occasional prolonged pauses may occur.
3.  **Level 3: Very complex**
    *   Original Definition: Vocabulary that is often complex: unfamiliar, archaic, subject-specific, and/or overly academic
    *   Summary definition: Overall, vocabulary often presents challenges that may slow down comprehension but does not completely block the comprehension of the bulk of the text.
4.  **Level 4: Exceedingly complex**
    *   Original Definition: Vocabulary that is mostly complex: unfamiliar, archaic, subject-specific, and/or overly academic. May be ambiguous or purposefully misleading.
    *   Summary definition: Overall, vocabulary is so complex that it makes comprehension of the bulk of the text very challenging and requires careful effort to interpret.

**Resource 2: Flesch-Kincaid Grade Level**
Use the Flesch-Kincaid (FK) Grade Level as light guidance of the approximate grade level based on readability. The metric alone does not provide final information of vocabulary complexity, but a ballpark of the difficulty of the entire text.
*   grade 2-3: 1.98-5.34
*   grade 4-5: 4.51-7.73
*   grade 6-8: 6.51-10.34
*   grade 9-10: 8.32-12.12
*   grade 11-College: 10.34-14.2

**Guidelines for Interpretation and Reasoning**

Your reasoning is the most critical part of your analysis. It's not enough to simply count complex words. You must analyze their impact on a student at the specified grade level. Use the following principles to guide your judgment:

1.  **Density and Cumulative Effect:** Do not just count complex words; evaluate their concentration. A short text with a high density of challenging Tier 2 words (e.g., `peculiar`, `mischievous`, `courageous` for a 4th grader) can be more overwhelming than a longer text with a few scattered Tier 3 words. A constant barrage of unfamiliar words can elevate complexity from `very` to `exceedingly`.
2.  **Contextual Scaffolding:** Assess how the text supports new vocabulary.
    *   Are new, complex terms explicitly defined or explained with simple examples (e.g., "volume... to see if it is big enough to hold a liter of food")?
    *   Is the surrounding language simple and conversational, making the meaning of new words easier to infer?
    *   Strong scaffolding can lower the complexity rating. A text with many Tier 3 words that are well-explained might only be `moderately complex`.
3.  **Abstract vs. Concrete Vocabulary:** Differentiate between words for abstract concepts and words for concrete things. A text built on abstract Tier 2 words (e.g., `relationships`, `performance`, `non-physical`) can be more challenging than a text that introduces Tier 3 labels for concrete things or people (e.g., `Sumerians`, `polonium`).
4.  **Conceptual Load:** Consider the cognitive load of the vocabulary. A list of many new, multi-syllabic, conceptually-heavy terms (e.g., `Paleolithic`, `Mesolithic`, `Neolithic` for a 3rd grader) can be `very complex` even if the terms are briefly defined, because the student must process multiple new concepts at once.
5.  **Calibrating the Top Levels:** Be precise in your use of `very complex` vs. `exceedingly complex`.
    *   **Very complex:** The vocabulary creates significant hurdles and slows the reader down, but the main ideas of the text are still accessible with effort.
    *   **Exceedingly complex:** The vocabulary is so dense, technical, or abstract that it acts as a barrier, making it nearly impossible for the target student to grasp the bulk of the text's meaning without extensive outside help. Reserve this for texts saturated with advanced terminology.
6.  **Consider Background Knowledge:** Pay close attention to the provided `student_background_knowledge`. Do not classify a word as complex if the student is likely to be familiar with it (e.g., 'oxygen' for a 3rd grader who has learned about the human body).

**Final Analysis Format**

Provide these information as your final analysis:
1.  **Complex vocabulary:**
    *   Tier 2 words: Words that are commonly used in academic settings and more complex than colloquial, or everyday language and often have multiple meanings.
    *   Tier 3 words: Overly academic or domain-specific words.
    *   Archaic words: Words, or uses of words that are not commonly used in modern conversational language. E.g., “The jury retired to deliberate on their verdict." The use of “retire” to mean withdrawing to a private place is an archaic use.
    *   Other complex words: All other words that can increase complexity of the text (e.g., idioms, unfamiliar proper nouns that function as vocabulary).
2.  **Vocabulary complexity:** one of: slightly complex, moderately complex, very complex, exceedingly complex
3.  **Your reasoning of the complexity:** A detailed explanation of your rating, referencing the principles above.
""",
    'vocab_grades_3_4_user_prompt': """Below is the text you need to evaluate. Let's think step by step in order to predict the output of the vocabulary complexity task.

- It is intended for grade {student_grade_level}.

- You can assume the student has the following background knowledge about the text — this background knowledge influences which words from the text are familiar versus unfamiliar for the student: {student_background_knowledge}

- Text Flesch-Kincaid grade level: {fk_level}

- Text to evaluate: [BEGIN TEXT]
{text}
[END TEXT]

{format_instructions}
""",
    'vocab_other_grades_system_prompt': """You are an expert curriculum designer. Your job involves reading text snippets intended for students in K-12 and evaluating the complexity of the vocabulary in each text.

You will be given a rubric (with options 1, 2, 3, 4) as well as guidelines for interpreting the rubric.

IMPORTANT: You should only pay attention to the vocabulary. Do not evaluate any other element of the text's complexity (e.g. sentence structure, meainng, etc.)
IMPORTANT: Rely on the supplied rubric and annotation guidelines along. Do not introduce any new crtieria for evaluating the complexity of a text's vocabulary.

Please first reason out loud about the vocabulary complexity of the text and then provide an answer between 1 and 4 (whole numbers only). Provide the answer as an integer (not a float).
""",
    'vocab_other_grades_user_prompt': """Your job is to rate the complexity of a text's vocabulary (relative to the intended level of the text) according to a rubric and annotation guide. Stick to the rubric and annotation guide exactly — do not introduce any additional criteria or lenses for judging the complexity of the text.

[BEGIN ANNOTATION GUIDE AND RUBRIC]
Instructions
For the following task, please assume that:
    - The student is on grade level and proficient in all core content areas, including reading fluency, comprehension, science, & social studies. (example).
    - The student is moving through a common progression of topics (detailed here).
    - The student is fluent in speaking English.
    - The student has an "average" amount of background knowledge on topics not commonly covered in curriculum.
    - The student will use this material for independent reading/work, without direct instruction.
    - The text is reasonable for the given grade level.

Please do not consider the presence of figurative language when scoring Vocabulary. For example: with a phrase like "kicked the bucket," consider only the qualities of the words themselves ("kicked", "the" and "bucket").

Please do be sure to consider:
- all of the different types of vocabulary (listed below)
- the overall proportion of complex words in the text - including repeated complex words.
- the resulting holistic complexity of the vocabulary (described in the Summary section below).

Level 1:
Rubric: Vocabulary that is almost entirely not complex: contemporary, conversational, and/or familiar. That said, a very low proportion of complex words (archaic, subject-specific, academic) is OK -- i.e. doesn't need to be 0.

Level 2:
Rubric: Vocabulary that is mostly not complex: contemporary, conversational, and/or familiar. A low proportion of complex words (archaic, subject-specific, academic) is OK, but if it's very low, the text is probably level 1.

Level 3:
Rubric: Vocabulary that is often complex: unfamiliar, archaic, subject-specific, and/or overly academic

Level 4:
Rubric: Vocabulary that is mostly complex: unfamiliar, archaic, subject-specific, and/or overly academic. May be ambiguous or purposefully misleading

And here are some relevant definitions:
    - Conversational: Everyday language.
    - Familiar: Words that the student is likely to have seen/heard, from everyday life or their curriculum. Reminder: assume an "average" level of background knowledge.
    - Unfamiliar: Words the student has probably not heard, or are being used in an unfamiliar way.
        - For ex: 4th graders are familiar with the word "table" but may not be familiar with the use of the word with respect to data ("a table of data").
        - Note:
            - Words with in-line definitions (via appositives, or because they can be easily inferred from other parts of the text) should be evaluated as less unfamiliar.
            - For ex: "The pharaoh, a powerful ruler of ancient Egypt, was buried in a grand tomb."
                - The word "pharaoh" might be unfamiliar or subject-specific, but since is defined within the text, you can consider it a more familiar word.
        - Unfamiliar proper nouns:
            - A person's name, even if unfamiliar, generally does not add to complexity.
            - Other unfamiliar proper nouns (eg locations, organizations) do add to complexity.

- Subject-specific: Words that are specific to a subject or field of study that are essential for understanding concepts and engaging with the content.
- Overly-academic: Words that are excessively formal, complex, or specialized.
    - For ex: "The agrarian societal structure of the Neolithic Revolution precipitated a paradigm shift in agriculture"
- Archaic: A word that was common in the past but is now rarely/almost never used. Could also be a word used in an archaic way.
    - For ex: "After a long day of court proceedings, the jury 'retired' to deliberate on their verdict."
        - The word "retire" meaning to stop working may be familiar to a student, but "retire" meaning "withdrawing to a private place" is an archaic use.


Examples
The student is on-grade-level:
- Consider a 6th grade passage about earth systems. Per NGSS standards, students are introduced to earth systems starting in 2nd grade. They encounter words like: wind, water, river, lake, solids, and liquids. For our rating purposes, we would assume most students following 2nd have encountered these words. In 5th grade, they dive more fully into earth systems concepts, learning vocabulary words like geosphere, sediment, biosphere, atmosphere, ecosystems, organisms and climate. While rating, we would consider the words listed in the NGSS standards as more familiar following that grade level.  If the same passage were intended for 3rd graders, though, then the subject-specific vocabulary is likely to be unfamiliar.

Figurative Language
- Kicked the bucket.
- The pen is mightier than the sword.
- The classroom was a zoo.
- He ran faster than the speed of light.
[END ANNOTATION GUIDE AND RUBRIC]

Here are a couple examples of texts that have already been scored along with justification for their scores, which you can use as exemplars:
[BEGIN EXAMPLES]

*** EXAMPLE 1 ***
The following text was intended for grade level 11 and received a complexity level of 1.

Here is the background knowledge assumption for that text: N/A

Here is the text:
// START TEXT //
"In a recent lecture, "Is Nothing Sacred?", Salman Rushdie, one of the most censored authors of our time, talked about the importance of books. He grew up in a household in India where books were as sacred as bread. If anyone in the household dropped a piece of bread or a book, the person not only picked it up, but also kissed the object by way of apologizing for clumsy disrespect.

He goes on to say that he had kissed many books before he had kissed a girl. Bread and books were for his household, and for many like his, food for the body and the soul. This image of the kissing of the book one had accidentally dropped made an impression on me. It speaks to the love and respect many people have for them.

I grew up in a small town in New Mexico, and we had very few books in our household. The first one I remember reading was my catechism book. Before I went to school to learn English, my mother taught me catechism in Spanish.

I remember the questions and answers I had to learn, and I remember the well-thumbed, frayed volume which was sacred to me.

Growing up with few books in the house created in me a desire and a need for them. When I started school, I remember visiting the one room library of our town and standing in front of the dusty shelves. In reality there were only a few shelves and not over a thousand books, but I wanted to read them all. There was food for my soul in the books, that much I realized."
// END TEXT //

Here is the reasoning for that complexity level:
// START REASONING //
This text is a 1 for vocabulary, because the vocabulary that is used is familiar and accessible for a proficient 11th grader. Most of the words used in the text are very common everyday vocabulary for describing growing up, family life, and the importance of reading. A few examples of these very common words are: small town, book, school, learn, food, kissed, image, respect, love, speaks. There are many more in the text. In this text there are only a few "juicier" or more complex words, you can think of those as words that are less familiar, have a more abstract or nuanced meaning, or carry a very large concept. Less commonly spoken words that were used in the text were: frayed, volume, censored, clumsy, sacred. These are still well within reach of a proficient 11th grader, and would still be considered familiar, because they will have encountered them in past reading or academic studies. In the text there are a couple of words that are outliers, but they are not essential to the understanding of the larger text. One of these words or hyphenated compound phrase is well-frayed. A compound phrase is a phrase consisting of multiple words that work together to create a specific meaning or idea, often acting as a single unit in a sentence. If the meaning of individual words is familiar, it is typically quite easy for proficient readers to generalize the larger meaning that the author is implying with their word choice. In this case, proficient students will be accustomed to the phrase well, with the secondary meaning of very, rather than a description of positivity or health; and they will be accustomed to the use frayed, as in worn, aged, or damaged from use. Making the leap to identify the meaning of "well-frayed" as a book that is very used, will take only moments for a proficient 11th grader. Another word that stands out in the text is the word catechism, which might be new for many students based on their personal background or location, but a full understanding of what a catechism book contains is not essential for understanding the paragraph or whole text. The reader can make it through using minimum context clues to know that the catechism must be something important to his family. The type of book he learned to read before going to school is not critical for comprehension, it's enough to understand that reading was so important in his family, his mother started instruction before he even started school. Additionally, it's important to know that having one unknown word for an 11th grade reading, does not merit a rating higher than one.

It is worth noting that another reason this text is a 1, is that the content or topic of the passage is so familiar and covered extensively in K-12 education, i.e. reading is important, loving books, growing up; that coupled with the simple vocabulary choices, getting to the meaning of the overall text, and even the paragraphs, would be incredibly easy for a proficient 11th grader.
// END REASONING //
*** EXAMPLE 2 ***
The following text was intended for grade level 5 and received a complexity level of 2.

Here is the background knowledge assumption for that text: Background Knowledge Assumption: Students are likely familiar with the concept of natural disasters, including hurricanes, and basic atmospheric concepts like high and low pressure from their studies on weather and climate. They may not be familiar with the specific formation processes of hurricanes or the global terminology differences (hurricane, typhoon, cyclone).

Here is the text:
// START TEXT //
Great whirling storms roar out of the oceans in many parts of the world. They are called by several names—hurricane, typhoon, and cyclone are the three most familiar ones. But no matter what they are called, they are all the same sort of storm. They are born in the same way, in tropical waters. They develop the same way, feeding on warm, moist air. And they do the same kind of damage, both ashore and at sea. Other storms may cover a bigger area or have higher winds, but none can match both the size and the fury of hurricanes. They are earth's mightiest storms.

Like all storms, they take place in the atmosphere, the envelope of air that surrounds the earth and presses on its surface. The pressure at any one place is always changing. There are days when air is sinking and the atmosphere presses harder on the surface. These are the times of high pressure. There are days when a lot of air is rising and the atmosphere does not press down as hard. These are times of low pressure. Low-pressure areas over warm oceans give birth to hurricanes.
// END TEXT //

Here is the reasoning for that complexity level:
// START REASONING //
I scored this a 2 because of the density of subject-specific vocabulary related to weather and climate, which is often covered in lower grade levels. This adds to the complexity above a 1, but it is not a level 3 because of the familiarity with the topic, which implies some familiarity with the vocabulary as well. The specific formation process and the vocabulary used to explain the processes are also subject-specfiic but not famliar, which would make the second paragraph a level 3 in the rubric language, but when considering the language used in the overall SUMMARY below the rubric, this new content and vocabulary would cause quick pauses and/or occasional prolonged pauses but would not cause the reader to slow down to due to challenging overall comprehension of the key ideas and supporting claims. This is especially the case because the second paragraph builds upon prior knowledge and familiar vocabulary use, so it is not entirely new information and vocabulary. While there is subject-specific vocabulary used, overly academic vocabulary is NOT used and is more conversational in nature, such as "great whiring storms" and "born" / "giving birth" to storm  (although this is the way storms are described!) rather than more technical terms which made comprehension easier due to the accessibility of the vocabulary (even if used in other contexts before reading this text). Words such as "a lot" and "bigger" are more conversational, and while technical, unfamiliar words are provided, such as "hurricane," "typhoon," and "cyclone," knowing and understanding their differences is not necessary to grasp the main idea. The processes by which they are formed are what need to be retained while reading the entire text, and familiarity with the bulk of the vocabulary used would allow for that to happen without too much struggle to make meaning of it. Additionally, the text does not contain any archaic vocabulary or ambiguous words, which prevents it from reaching a rating of 4, although it is not necessary that they text have such vocabulary to meet a level 4, the frequent inclusion of such vocabulary makes it more likely to land at least a 3 or 4.
// END REASONING //

*** EXAMPLE 3 ***
The following text was intended for grade level 6 and received a complexity level of 3.

Here is the background knowledge assumption for that text: Background Knowledge Assumption: Students are likely familiar with basic Earth science concepts such as rocks, minerals, and fossils, as well as natural processes like volcanic eruptions and earthquakes. They may not be familiar with more advanced topics like plate tectonics or the specific branches of geology such as mineralogy, petrology, and seismology.

Here is the text:
// START TEXT //
Geology is the scientific study of Earth. Geologists study the planet—its formation, its internal structure, its materials, its chemical and physical processes, and its history. Mountains, valleys, plains, sea floors, minerals, rocks, fossils, and the processes that create and destroy each of these are all the domain of the geologist. Geology is divided into two broad categories of study: physical geology and historical geology.

Physical geology is concerned with the processes occurring on or below the surface of Earth and the materials on which they operate. These processes include volcanic eruptions, landslides, earthquakes, and floods. Materials include rocks, air, seawater, soils, and sediment. Physical geology further divides into more specific branches, each of which deals with its own part of Earth's materials, landforms, and processes. Mineralogy and petrology investigate the composition and origin of minerals and rocks. Volcanologists study lava, rocks, and gases on live, dormant, and extinct volcanoes. Seismologists use instruments to monitor and predict earthquakes and volcanic eruptions.

Historical geology is concerned with the chronology of events, both physical and biological, that have taken place in Earth's history. Paleontologists study fossils (remains of ancient life) for evidence of the evolution of life on Earth. Fossils not only relate evolution, but also speak of the environment in which the organism lived. Corals in rocks at the top of the Grand Canyon in Arizona, for example, show a shallow sea flooded the area around 290 million years ago. In addition, by determining the ages and types of rocks around the world, geologists piece together continental and oceanic history over the past few billion years. Plate tectonics (the study of the movement of the sections of Earth's crust) adds to Earth's story with details of the changing configuration of the continents and oceans.
// END TEXT //

Here is the reasoning for that complexity level:
// START REASONING //
To determine the complexity rating of this text based on the vocabulary present, I used the annotation guide, scoring rubric, and examples to set the expectations for rating. During the first read of the text, I "bolded" and categorized the more challenging vocabulary words according to the following complexity groupings: archaic, unfamiliar, archaic, subject-specific, and/or overly academic. On the second read, I considered the main idea or "gist" that students need to acquire understanding of. I then referenced the previously mentioned tools–annotation guide, scoring rubric, and examples to remind myself of the expectations for rating.  I agreed that readers would have familiarity with basic concepts of geology; however, I also considered the definitions provided for words such as Geology, Geologists, Physical Geology, Historical Geology, Mineralogy, and Petrology. I considered how students might pause for clarification and for how long. After reviewing the Annotation Guide while considering, I narrowed the rating down because the definitions provided throughout the text of more complex words should make the meaning of the text more accessible for readers, which is why although the words are subject-specific, I rated this text as a 3 instead of a 2-less complex or a 4–more complex. I read the text one final time to ensure clarity around my rating, scored and wrote the justification.
// END REASONING //
[END EXAMPLES]

Below is the text you need to evaluate. It is intended for grade {student_grade_level}.

As you read the text, you can assume the student has the following background knowledge about the text — this background knowledge influences which words from the text are familiar versus unfamiliar for the student: {student_background_knowledge}

[BEGIN TEXT]
{text}
[END TEXT]

In your response, when specifying the level of complexity, be sure to use only a single integer (e.g. 2) and don't include any other text (e.g. don't say "level 2").

{format_instructions}
""",
}

# ── Evaluation settings ───────────────────────────────────────────────────────

_EVALUATION_SETTINGS = VocabularyEvaluationSettings(
    prompt_settings_step_background_knowledge=PromptSettings(
        provider_type=LLMProvider.OPENAI,
        model='gpt-4o-2024-11-20',
        temperature=0.0,
    ),
    prompt_settings_step_vocab_grades_3_4=PromptSettings(
        provider_type=LLMProvider.GOOGLE,
        model='gemini-2.5-pro',
        temperature=0.0,
    ),
    prompt_settings_step_vocab_other_grades=PromptSettings(provider_type=LLMProvider.OPENAI, model='gpt-4.1', temperature=0.0),
)

# ── Public config object (imported by evaluator modules) ──────────────────────

CONFIG: EvaluatorSettingsResult[VocabularyEvaluationSettings] = EvaluatorSettingsResult(
    evaluator_metadata=_EVALUATOR_METADATA,
    evaluation_settings=_EVALUATION_SETTINGS,
    prompts=_PROMPTS,
)
