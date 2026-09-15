# GENERATED — do not edit directly.
# Source: evals/student-facing-text/ela-reading/reference-knowledge-demands/output_schema.json
#         evals/student-facing-text/ela-reading/reference-knowledge-demands/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Reference Knowledge Demands Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "student_facing_text.ela_reading.reference_knowledge_demands"


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


class ReferenceKnowledgeDemandsInput(BaseModel):
    """Inputs to the Reference Knowledge Demands Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="The passage to evaluate.")
    grade_level: int = Field(description="Target student grade level.")


class DetailedSummaryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor: str = Field(description="The specific text complexity factor identified.")
    description: str = Field(description="How this factor manifests in the text.")
    effect_on_complexity_dimension: str = Field(description="How this factor affects the reader's ability to understand the text's specific complexity dimension.")


class ScaffoldingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scaffolding_need: str = Field(description="The complexity factor that requires scaffolding.")
    suggestion: str = Field(description="A specific instructional strategy to support students with this factor.")


class UseCaseItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunity: str = Field(description="An instructional opportunity related to the text.")
    suggestion: str = Field(description="A specific way to leverage this text for that instructional purpose.")


class ReferenceKnowledgeDemandsDetails(BaseModel):
    """Practical instructional details including scaffolding strategies and recommended use cases."""

    model_config = ConfigDict(extra="forbid")

    detailed_summary: list[DetailedSummaryItem] = Field(description="Individual complexity factors with descriptions and their effects.")
    adjustment_and_scaffolding: list[ScaffoldingItem] = Field(description="Scaffolding strategies to make the text accessible at the target grade.")
    recommended_use_cases: list[UseCaseItem] = Field(description="Additional instructional opportunities for using this text.")


class ReferenceKnowledgeDemandsOutput(BaseModel):
    """Output of the Reference Knowledge Demands Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    complexity_score: Literal["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"] = Field(description="The Reference Knowledge Demands complexity level for the target grade.")
    reasoning: str = Field(description="A high-level summary of why the text is at this complexity level for the target grade.")
    details: ReferenceKnowledgeDemandsDetails


__all__ = [
    "ReferenceKnowledgeDemandsInput",
    "ReferenceKnowledgeDemandsOutput",
]
