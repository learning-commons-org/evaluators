"""Prompt templates for the vocabulary evaluator (early release)."""

"""Prompt for generating background knowledge assumption for a given text and grade level."""
bk_prompt = """
Review the following text, which is an educational text written for students in the following grade band: {grade}.

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
"""

"""System and user prompts for evaluating vocabulary complexity of a given text relative to a specified grade level. This is the prompt we tested with the highest accuracy.
"""
SYSTEM_PROMPT = """
You are an expert curriculum designer. Your job is to rate the complexity of a text's vocabulary relative to the grade level.

You will be given a rubric (with levels from least to most complex: slightly complex, moderately complex, very complex, exceedingly complex) as well as guidelines for interpreting the rubric.
IMPORTANT: You should only pay attention to the vocabulary. Do not evaluate any other element of the text's complexity (e.g. sentence structure, meaning, etc.)

**Resource 1: SCASS Vocabulary Rubric**
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
"""

USER_PROMPT = """
Below is the text you need to evaluate. Let's think step by step in order to predict the output of the vocabulary complexity task.

- It is intended for grade {student_grade_level}.

- You can assume the student has the following background knowledge about the text — this background knowledge influences which words from the text are familiar versus unfamiliar for the student: {student_background_knowledge}

- Text Flesch-Kincaid grade level: {fk_level}

- Text to evaluate: [BEGIN TEXT]
{text}
[END TEXT]

{format_instructions}
"""
