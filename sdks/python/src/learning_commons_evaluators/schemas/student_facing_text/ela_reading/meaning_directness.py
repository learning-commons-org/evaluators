# GENERATED — do not edit directly.
# Source: evals/student-facing-text/ela-reading/meaning-directness/output_schema.json
#         evals/student-facing-text/ela-reading/meaning-directness/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Meaning Directness Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "student_facing_text.ela_reading.meaning_directness"


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


class MeaningDirectnessInput(BaseModel):
    """Inputs to the Meaning Directness Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="The passage to evaluate. Bounds mirror the SDK text input spec (sdks/settings/conventionality/settings.toml: min_text_length / max_text_length).")
    grade_level: int = Field(description="Target student grade level.")


class MeaningDirectnessOutput(BaseModel):
    """Output of the Meaning Directness Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(description="A detailed explanation of the rating, citing specific features in the text and referencing the expert guardrails (e.g., noting if the text relies on abstract qualities/rhetorical idealization, if vocabulary/background knowledge demands make a literal text vague for the grade level, or if it is strictly concrete/procedural).")
    complexity_score: Literal["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"] = Field(description="The conventionality complexity level of the text.")
    conventionality_features: list[str] = Field(description="The specific language features driving the complexity (e.g., literal narrative, concrete actions, less familiar expressions, sustained irony, abstract qualities, rhetorical idealization, archaic phrasing) with direct quotes from the text.")
    grade_context: str = Field(description="How the conventionality demands compare to general expectations for the provided target grade.")
    instructional_insights: str = Field(description="Actionable pedagogical suggestions for scaffolding the conventionality features in the classroom.")


__all__ = [
    "MeaningDirectnessInput",
    "MeaningDirectnessOutput",
]
