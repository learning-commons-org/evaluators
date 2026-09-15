# GENERATED — do not edit directly.
# Source: evals/student-facing-text/ela-reading/vocabulary-complexity/output_schema.json
#         evals/student-facing-text/ela-reading/vocabulary-complexity/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Vocabulary Complexity Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "student_facing_text.ela_reading.vocabulary_complexity"


#: Accepted values of ``grade_level``, as the input schema declares them.
GRADE_LEVEL_VALUES: tuple[str, ...] = (
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
)


class VocabularyComplexityInput(BaseModel):
    """Inputs to the Vocabulary Complexity Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="The passage to evaluate for vocabulary complexity.")
    grade_level: int = Field(description="Target student grade level.")


class VocabularyComplexityOutput(BaseModel):
    """Output of the Vocabulary Complexity Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    tier_2_words: str = Field(description="List of Tier 2 words: words commonly used in academic settings, more complex than colloquial or everyday language, often with multiple meanings.")
    tier_3_words: str = Field(description="List of Tier 3 words: overly academic or domain-specific words.")
    archaic_words: str = Field(description="List of archaic words, or common words used in an archaic way, not commonly used in modern conversational language.")
    other_complex_words: str = Field(description="All other words that can increase complexity of the text (e.g., idioms, unfamiliar proper nouns that function as vocabulary).")
    complexity_score: Literal["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"] = Field(description="The vocabulary complexity level of the text.")
    reasoning: str = Field(description="A detailed explanation of the rating. Grades 3-4 reference density and cumulative effect, contextual scaffolding, abstract vs. concrete vocabulary, conceptual load, and the provided student background knowledge; other grades reference the annotation guide and rubric.")


__all__ = [
    "VocabularyComplexityInput",
    "VocabularyComplexityOutput",
]
