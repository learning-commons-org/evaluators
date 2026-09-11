# GENERATED — do not edit directly.
# Source: evals/student-facing-text/ela-reading/background-knowledge-demands/output_schema.json
#         evals/student-facing-text/ela-reading/background-knowledge-demands/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Background Knowledge Demands Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "student_facing_text.ela_reading.background_knowledge_demands"


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


class BackgroundKnowledgeDemandsInput(BaseModel):
    """Inputs to the Background Knowledge Demands Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="The passage to evaluate.")
    grade_level: int = Field(description="Target student grade level.")


class BackgroundKnowledgeDemandsOutput(BaseModel):
    """Output of the Background Knowledge Demands Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    identified_topics: list[str] = Field(description="The core subjects/concepts found in the text.")
    curriculum_check: str = Field(description="Whether the topics are standard K-8 knowledge or specialized high-school-level knowledge.")
    assumptions_and_scaffolding: str = Field(description="What the author assumes the reader already knows versus what is explained in the text.")
    friction_analysis: str = Field(description="Whether difficulty comes from vocabulary/sentence structure or from actual background knowledge demands.")
    complexity_score: Literal["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"] = Field(description="The background knowledge complexity level of the text.")
    reasoning: str = Field(description="A detailed synthesis of why the text fits the chosen complexity level.")


__all__ = [
    "BackgroundKnowledgeDemandsInput",
    "BackgroundKnowledgeDemandsOutput",
]
