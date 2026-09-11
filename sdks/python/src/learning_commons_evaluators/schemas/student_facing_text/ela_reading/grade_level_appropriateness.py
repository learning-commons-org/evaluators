# GENERATED — do not edit directly.
# Source: evals/student-facing-text/ela-reading/grade-level-appropriateness/output_schema.json
#         evals/student-facing-text/ela-reading/grade-level-appropriateness/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Grade Level Appropriateness Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "student_facing_text.ela_reading.grade_level_appropriateness"


class GradeLevelAppropriatenessInput(BaseModel):
    """Inputs to the Grade Level Appropriateness Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="The passage to evaluate. Note this evaluator takes no grade input — it determines which grade band the text suits. Bounds mirror the SDK text input spec (sdks/settings/grade-level-appropriateness/settings.toml: min_text_length / max_text_length).")


# A band on the CCSS text-complexity scale — a span of grades, not a single grade.
GradeBand = Literal["K-1", "2-3", "4-5", "6-8", "9-10", "11-12"]


class GradeLevelAppropriatenessOutput(BaseModel):
    """Output of the Grade Level Appropriateness Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(description="Numbered bullet points for each of the 3 analysis steps (quantitative, qualitative, background knowledge), followed by a 4th bullet point called 'synthesis'.")
    grade_band: GradeBand = Field(description="Target grade band for the text at independent reading.")
    alternative_grade_band: GradeBand = Field(description="A second grade band that could read and comprehend the text with the scaffolding named in scaffolding_needed, or as a read-aloud.")
    scaffolding_needed: str = Field(description="The types of scaffolding (picture, graph, additional context, vocabulary pre-teaching, ...) that make the text accessible at alternative_grade_band.")


__all__ = [
    "GradeLevelAppropriatenessInput",
    "GradeLevelAppropriatenessOutput",
]
