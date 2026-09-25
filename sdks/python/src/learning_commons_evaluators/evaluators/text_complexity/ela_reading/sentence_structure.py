"""Sentence Structure: how demanding a text's sentences are for a target grade.

Two model calls on OpenAI. The first counts grammatical features sentence by sentence,
against the deterministic counts ``textstat`` supplies as a reference; the second classifies
complexity against the rubric for the grade, reading ratios derived from those counts rather
than the counts themselves. Which rubric that is, and the fact that the second step's
features come from the first step's output, are both read from ``config.json``.

The intermediate analysis has no schema in the registry — ``config.json`` declares an
``output_schema`` for the evaluator, not one per step — so :class:`SentenceAnalysis` below
is the SDK's own statement of what the first step returns. Its field descriptions reach the
provider's structured-output schema, and are the ones the notebook this evaluator comes from
put in front of the model.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.multi_step import MultiStepEvaluator
from learning_commons_evaluators.features.readability import compute_ground_truth_counts
from learning_commons_evaluators.features.sentence_features import (
    add_engineered_features,
    features_to_json,
)
from learning_commons_evaluators.schemas.text_complexity.ela_reading.sentence_structure import (
    EVALUATOR_ID,
    SentenceStructureInput,
    SentenceStructureOutput,
)


class SentenceAnalysis(BaseModel):
    """What the ``sentence_analysis`` step returns: one pass of grammatical counting.

    Strict, like the generated output models: a key the model invents is a sign it answered
    a different question, and every ratio the next step reads is derived from these counts.
    """

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(
        description="Your step-by-step reasoning as you analyze the text, with a line break between each sentence analyzed."
    )
    num_sentences: int = Field(description="Total number of sentences in the text.")
    num_words: int = Field(description="Total number of words in the text.")
    flesch_kincaid_grade: float = Field(
        description="Flesch-Kincaid Grade Level number from Computational Counts, rounded to two decimal places."
    )
    num_simple_sentences: int = Field(description="Number of simple sentences in the text.")
    num_compound_sentences: int = Field(description="Number of compound sentences in the text.")
    num_complex_sentences: int = Field(description="Number of complex sentences in the text.")
    num_compound_complex_sentences: int = Field(
        description="Number of compound-complex sentences in the text."
    )
    num_other_sentences: int = Field(
        description="Number of sentences that do not fit the four canonical types (e.g., fragments, run-ons, elliptical answers, headlines, or stylized dialogue tags)."
    )
    num_independent_clauses: int = Field(
        description="Total count of all independent clauses in the text."
    )
    num_subordinate_clauses: int = Field(
        description="Total count of all subordinate clauses in the text. A single sentence can have multiple."
    )
    num_total_clauses: int = Field(
        description="The sum of all independent and subordinate clauses in the text."
    )
    num_sentences_with_subordinate: int = Field(
        description="Number of sentences that contain a subordinate clause."
    )
    num_sentences_with_multiple_subordinates: int = Field(
        description="Number of sentences that contain two or more subordinate clauses."
    )
    num_sentences_with_embedded_clauses: int = Field(
        description="Number of sentences with an embedded clause (a subordinate clause inside another clause)."
    )
    num_prepositional_phrases: int = Field(
        description="Number of prepositional phrases in the text."
    )
    num_participle_phrases: int = Field(description="Number of participle phrases in the text.")
    num_appositive_phrases: int = Field(description="Number of appositive phrases in the text.")
    num_simple_transitions: int = Field(description="Number of simple transitions in the text.")
    num_sophisticated_transitions: int = Field(
        description="Number of sophisticated transitions in the text."
    )
    words_in_simple_sentences: int = Field(
        description="Total number of words in all sentences classified as simple."
    )
    words_in_compound_sentences: int = Field(
        description="Total number of words in all sentences classified as compound."
    )
    words_in_complex_sentences: int = Field(
        description="Total number of words in all sentences classified as complex."
    )
    words_in_compound_complex_sentences: int = Field(
        description="Total number of words in all sentences classified as compound-complex."
    )
    words_in_other_sentences: int = Field(
        description="Total number of words in all sentences classified as other."
    )
    sentence_word_counts: list[int] = Field(
        description="A list containing the word count of each individual sentence in the order they appear."
    )
    num_one_concept_sentences: int = Field(
        description="Number of sentences with a single main idea: no subordinate clause and no transition word/phrase."
    )
    num_multi_concept_sentences: int = Field(
        description="Number of sentences with multiple main ideas: either a subordinate clause or a transition word/phrase or both."
    )
    num_cleft_sentences: int = Field(
        description='Number of sentences with cleft constructions (e.g., "It was X that...", "What X did was...").'
    )
    max_clauses_in_any_sentence: int = Field(
        description="Max number of clauses (independent + subordinate) found in a single sentence."
    )
    num_compound: int = Field(description="number of compound sentences in the generated text")
    num_basic_complex: int = Field(
        description="number of basic complex sentences in the generated text"
    )
    num_advanced_complex: int = Field(
        description="number of advanced complex sentences in the generated text"
    )
    percentage_simple: float = Field(description="percentage of all sentences that are simple")
    percentage_compound: float = Field(description="percentage of all sentences that are compound")
    percentage_basic_complex: float = Field(
        description="percentage of all sentences that are basic complex"
    )
    percentage_advanced_complex: float = Field(
        description="percentage of all sentences that are advanced complex"
    )


def sentence_features(analysis: Any) -> str:
    """Bind ``{sentence_features}``: the ratios the rubric is written in, as JSON.

    Takes the first step's output, which the contract names as this entry's ``input``.
    """
    counts = analysis.model_dump() if isinstance(analysis, BaseModel) else dict(analysis)
    return features_to_json(add_engineered_features(counts))


class SentenceStructureEvaluator(
    MultiStepEvaluator[SentenceStructureInput, SentenceStructureOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = SentenceStructureInput
    output_model = SentenceStructureOutput
    step_models = {
        "sentence_analysis": SentenceAnalysis,
        "classify_complexity": SentenceStructureOutput,
    }
    computations = {
        # Keyed by the function name each entry declares under implementation.python, so a
        # contract that renames one fails at import rather than skipping the computation.
        "compute_ground_truth_counts": compute_ground_truth_counts,
        "add_engineered_features": sentence_features,
    }


__all__ = [
    "SentenceAnalysis",
    "SentenceStructureEvaluator",
    "SentenceStructureInput",
    "SentenceStructureOutput",
]
