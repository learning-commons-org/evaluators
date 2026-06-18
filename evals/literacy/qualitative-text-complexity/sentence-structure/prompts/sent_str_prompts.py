"""Prompt templates for sentence structure evaluator (early release)."""

"""System and user prompts for sentence structure analysis."""
SYSTEM_PROMPT_ANALYSIS = """You are an expert in grammar and literacy."""

USER_PROMPT_ANALYSIS = """
# Task
I am going to give you a text, and I need you to look through the text sentence-by-sentence to perform a comprehensive grammatical analysis. Use the computational counts as a reference; they can be incorrect in ambiguous cases.

# Definitions
* Sentences: Count a complete grammatical unit ending in a terminal punctuation mark.
* Words: Count any sequence of characters separated by a space as one word. Treat hyphenated words (e.g., "state-of-the-art") and numbers (e.g., "2025") as single words.
* Independent Clauses: Clauses that can stand alone as a complete sentence.
* Subordinate Clauses: Clauses that are dependent on the main clause and cannot stand alone as a complete sentence.
* Simple Sentences: Sentences with one independent clause and no subordinate clauses.
* Compound Sentences: Sentences with two or more independent clauses and no subordinate clauses.
* Complex Sentences: Sentences with one independent clause and at least one subordinate clause.
* Compound-Complex Sentences: Sentences with two or more independent clauses and at least one subordinate clause.
* Other / Non-Canonical Sentences: Sentences that cannot be reliably classified as simple, compound, complex, or compound-complex (e.g., sentence fragments, run-ons, elliptical responses, headlines, imperatives lacking an explicit subject, or stylized dialogue tags).
* Subordinate Clauses: Clauses that are dependent on the main clause and cannot stand alone as a complete sentence.
* Embedded Clauses: Clauses that are nested within another clause.
* Prepositional Phrases: Phrases that begin with a preposition and end with a noun phrase.
* Participle Phrases: Phrases that begin with a participle and end with a noun phrase.
* Appositive Phrases: Phrases that rename or identify a noun phrase.
* Simple Transitions: Basic coordinating conjunctions and chronological adverbs. Examples: 'and', 'but', 'or', 'so', 'then', 'next', 'first'.
* Sophisticated Transitions: Conjunctive adverbs and phrases signaling logical relationships. Examples: 'however', 'therefore', 'consequently', 'as a result', 'for example', 'although'.
* One-Concept Sentence: A sentence with ZERO subordinate clauses AND ZERO transition words/phrases (neither simple nor sophisticated).
* Multi-Concept Sentence: Any sentence that has ≥1 subordinate clause OR ≥1 transition word/phrase (or both).
* Basic Complex Sentences: Sentences with exactly one independent clause and at one dependent (subordinate) clause.
* Advanced Complex Sentences: Sentences with two or more of any of those following (can include a mix, doesn't have to be two of the same type) subordinate phrases, clauses, transition words, or any other meaningful "interruptions" to the flow of the sentence (like not-only-but-also constructions, dashes, semicolons, and lengthy appositives). A sentence can be advanced complex if it has just one subordinate phrase or clause alongside a transition phrase, like: "For example, the British favored trade with Hong Kong, assuming favorable trade conditions.

# Computational Counts
Use these as reference, your internal heuristics can be more reliable.
{ground_truth_counts}

# Text to Analyze
[BEGIN TEXT]
{text}
[END TEXT]

IMPORTANT: Your response should be a single JSON object with the following structure. Do not produce anything outside of the JSON object.

{format_instructions}
"""

"""System and user prompts for text complexity evaluation."""
SYSTEM_PROMPT_COMPLEXITY = "You are an expert in grammar and literacy, and understand K-12 and Qualitative Text Complexity rubric (SAP)."

USER_PROMPT_COMPLEXITY = """
Your task is to perform a text complexity analysis for a Grade {grade} student. You will be given a text excerpt and a set of quantitative sentence-level statistics for that text.

You must integrate both the qualitative aspects of the text and the quantitative statistics to make your final judgment. Do not rely on the numbers alone.

1.  Read the TEXT EXCERPT to understand its topic, conceptual load, and overall structure.
2.  Review the TEXT STATISTICS as a guide for complexity level.
3.  Synthesize your findings in your reasoning. Explain how the structure (qualitative) interact with the text statistics (quantitative) to determine the complexity. For example, a text with simple sentences might still be complex if the topic is very dense or abstract.

Your final answer must be one of ["Slightly Complex," "Moderately Complex," "Very Complex", "Exceedingly Complex"].

# GRADE {grade} RUBRIC
{rubric}

# TEXT EXCERPT
[BEGIN TEXT]
{excerpt}
[END TEXT]

# TEXT STATISTICS
{sentence_features}

# OUTPUT FORMAT
{format_instructions}
"""

""" Rubrics for different grade levels. Each rubric provides detailed criteria for classifying text complexity into four categories: Slightly Complex, Moderately Complex, Very Complex, and Exceedingly Complex.
    For early release, we are only providing rubrics for grades 3 and 4.
"""
GRADE_SPECIFIC_RUBRICS = {
    "GRADE_3": """
    **Instructions for Analysis:** First, evaluate if the text meets the criteria for "Slightly Complex" or "Exceedingly Complex". If it does not fit into these categories, then decide between "Moderately Complex" and "Very Complex".

    **Slightly Complex:**
    * **Description:** The text consists of simple, straightforward language and sentence structures.
    * **Statistical Guidelines:** The text is likely "Slightly Complex" if it meets at least TWO of the following criteria:
        * **Sentence Type:** Primarily simple sentences. (`percent_simple_sentences` is typically > 60%).
        * **Sentence Length:** Short sentences. (`avg_sentence_length` is typically < 12 words).
        * **Subordination:** Very low use of clauses. (`percent_sentences_with_subordinate` is typically < 25%).

    **Moderately Complex:**
    * **Description:** The text shows a mix of simple and more complex sentences, introducing some variety in structure without being overly demanding.
    * **Statistical Guidelines:** If the text is not "Slightly Complex", consider "Moderately Complex" if it generally aligns with these ranges:
        * **Sentence Type:** A balanced mix of sentence types. (`percent_simple_sentences` is typically between 40% and 60%).
        * **Sentence Length:** Medium length sentences. (`avg_sentence_length` is typically between 12 and 16 words).
        * **Subordination:** A moderate use of clauses. (`percent_sentences_with_subordinate` is typically between 25% and 45%).

    **Very Complex:**
    * **Description:** The text features more elaborate sentences with multiple clauses and ideas, requiring more effort from the reader to parse. This is often the default category for grade-level text that isn't simple or exceptionally difficult.
    * **Statistical Guidelines:** If the text is more complex than "Moderately" but does not meet the "Exceedingly" criteria, it is likely "Very Complex". Key indicators include:
        * **Sentence Type:** Complex structures are common. (`percent_simple_sentences` is a minority, typically < 40%).
        * **Sentence Length:** Longer sentences are frequent. (`avg_sentence_length` is typically between 16 and 19 words).
        * **Subordination:** Subordinate clauses are a key feature. (`percent_sentences_with_subordinate` is typically > 45%).

    **Exceedingly Complex:**
    * **Description:** The text is dense with very long, intricate sentences and a high degree of subordination, making it exceptionally challenging for this grade level.
    * **Statistical Guidelines:** The text is "Exceedingly Complex" if it shows an extreme combination of sentence length and structural density. It should meet at least **TWO** of the following criteria, including at least **ONE** from the "Structural Density" group.
        * **Structural Density Indicators:**
            * High Subordination: `percent_sentences_with_subordinate` is extensive (typically > 50%).
            * Multiple Subordinates: `percent_sentences_with_multiple_subordinates` is consistently present (typically > 12%).
            * High Syntactic Complexity: `percent_compound_complex_sentences` is significant (typically > 15%).
        * **Length Indicators:**
            * Extreme Sentence Length: `avg_sentence_length` is very long (typically > 19 words).
            * Low Simplicity: `percent_simple_sentences` is very low (typically < 30%).
            * Concentrated Length: `percent_very_long_sentences` is notable (typically > 10%).
    """,
    "GRADE_4": """
    **Instructions for Analysis:** First, evaluate if the text meets the criteria for "Slightly Complex" or "Exceedingly Complex". If it does not fit into these categories, then decide between "Moderately Complex" and "Very Complex".

    **Slightly Complex:**
    * **Description:** The text uses clear, direct language with basic sentence structures appropriate for developing readers.
    * **Statistical Guidelines:** The text is likely "Slightly Complex" if it meets at least TWO of the following criteria:
        * **Sentence Type:** Dominated by simple sentences. (`percent_simple_sentences` is typically > 55%).
        * **Sentence Length:** Short to medium sentences. (`avg_sentence_length` is typically < 13 words).
        * **Subordination:** Infrequent use of clauses. (`percent_sentences_with_subordinate` is typically < 30%).

    **Moderately Complex:**
    * **Description:** The text contains a variety of sentence structures, including compound and complex sentences, but remains accessible.
    * **Statistical Guidelines:** If the text is not "Slightly Complex", consider "Moderately Complex" if it generally aligns with these ranges:
        * **Sentence Type:** A healthy mix of sentence types. (`percent_simple_sentences` is typically between 40% and 55%).
        * **Sentence Length:** Medium length sentences. (`avg_sentence_length` is typically between 13 and 17 words).
        * **Subordination:** A moderate number of clauses. (`percent_sentences_with_subordinate` is typically between 30% and 50%).

    **Very Complex:**
    * **Description:** The text is characterized by longer sentences and the regular use of dependent clauses, requiring readers to track multiple ideas. This is the default for challenging, on-grade-level texts.
    * **Statistical Guidelines:** If the text is more complex than "Moderately" but does not meet the "Exceedingly" criteria, it is likely "Very Complex". Key indicators include:
        * **Sentence Type:** Simple sentences are a clear minority. (`percent_simple_sentences` is typically < 40%).
        * **Sentence Length:** Sentences are consistently long. (`avg_sentence_length` is typically between 17 and 22 words).
        * **Subordination:** Subordination is a major feature. (`percent_sentences_with_subordinate` is typically > 50%).
        * **Multiple Subordination:** Sentences with multiple clauses appear more often. (`percent_sentences_with_multiple_subordinates` is typically > 8%).

    **Exceedingly Complex:**
    * **Description:** The text's structure is highly sophisticated and dense, marked by extensive use of embedded clauses and long, flowing sentences that are well above grade-level expectations.
    * **Statistical Guidelines:** A text is "Exceedingly Complex" if its structure is highly sophisticated and dense. It should meet at least **TWO** of the following criteria, including at least **ONE** from the "Structural Density" group.
        * **Structural Density Indicators:**
            * High Subordination: `percent_sentences_with_subordinate` is very high (typically > 60%).
            * Multiple Subordinates: `percent_sentences_with_multiple_subordinates` is high and consistent (typically > 15%).
            * High Syntactic Complexity: `percent_compound_complex_sentences` is a notable feature (typically > 20%).
        * **Length Indicators:**
            * Extreme Sentence Length: `avg_sentence_length` is exceptionally long (typically > 22 words).
            * Low Simplicity: `percent_simple_sentences` is very low (typically < 25%).
            * Concentrated Length: `percent_very_long_sentences` is significant (typically > 15%).
    """,
    "GRADES_5_TO_12": """
    **Slightly Complex:** A text is in the Slightly Complex bucket if it has at least 50% simple sentences. If it doesn't, the text is a higher level of complexity. If the % of simple sentences is >= 50% and the % of compound sentences is >= 20%, the text is Moderately Complex, otherwise, the text is Slightly Complex. Slightly Complex texts NEVER have advanced complex sentences — the presence of an advanced complex sentence always leads to a higher level of complexity than Slightly.
    **For Moderately Complex:** These texts can take on any distribution of sentence types as long as there aren't more than 2 advanced complex sentences and as long as there aren't so many simple sentences that the text becomes Slightly Complex. That means Moderately Complex texts may have many simple sentences (although not so many that the text is Slightly Complex), compound sentences, and/or basic complex sentences. It's also possible for a moderately complex text to contain one or two advanced complex sentences, as long as there aren't more than 2. If there are more than 2, then the text is either Very or Exceedingly complex.
    **Very Complex:** These texts contain 3 or more advanced complex sentences (unless the percentage of advanced complex sentences is >= 65)%, in which case the text becomes Exceedingly Complex). They may still contain many simple, compound, and basic complex sentences, but a text is not Very Complex unless there are 3 or more advanced complex sentences.
    **Exceedingly Complex:** These texts have 65%+ of their sentences being advanced complex sentences.
    """,
}
