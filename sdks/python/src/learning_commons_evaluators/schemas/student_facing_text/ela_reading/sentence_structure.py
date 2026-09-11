# GENERATED — do not edit directly.
# Source: evals/student-facing-text/ela-reading/sentence-structure/output_schema.json
#         evals/student-facing-text/ela-reading/sentence-structure/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Sentence Structure Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "student_facing_text.ela_reading.sentence_structure"


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


class SentenceStructureInput(BaseModel):
    """Inputs to the Sentence Structure Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="The passage to evaluate.")
    grade_level: int = Field(description="Target student grade level. Selects which of the three rubric_grade_* preprocessing entries supplies {rubric}.")


class SentenceStructureOutput(BaseModel):
    """Output of the Sentence Structure Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    complexity_score: Literal["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"] = Field(description="The sentence structure complexity level of the text.")
    reasoning: str = Field(description="Detailed, pedagogically appropriate reasoning explaining how the qualitative structure and quantitative sentence statistics combine to produce the chosen complexity level.")


__all__ = [
    "SentenceStructureInput",
    "SentenceStructureOutput",
]
