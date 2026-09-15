# GENERATED — do not edit directly.
# Source: evals/academic-standards-alignment/mathematics/math-standards-alignment/output_schema.json
#         evals/academic-standards-alignment/mathematics/math-standards-alignment/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Math Standards Alignment Evaluator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "academic_standards_alignment.mathematics.math_standards_alignment"


#: Accepted values of ``jurisdiction``, as the input schema declares them.
JURISDICTION_VALUES: tuple[str, ...] = (
    "Multi-State",
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "Washington, D.C.",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
)


class MathStandardsAlignmentInput(BaseModel):
    """Inputs to the Math Standards Alignment Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    question: str = Field(description="The assessment question to evaluate for standards alignment")
    statement_code: str = Field(description="Math standard code to evaluate against (e.g. '3.MD.C.7.d', 'K.CC.A.1').")
    jurisdiction: str = Field(description="Standards jurisdiction — 'Multi-State' for CCSS, or a specific state name. Determines which framework the standard code is resolved against. Mirrors the SDK's Jurisdiction enum.")


class LearningComponentsItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(description="The learning component description from the Knowledge Graph")
    reasoning: str = Field(description="Concise explanation of what the LC requires, what the question asks, and why they do or do not align")
    aligned: bool = Field(description="True if the question directly elicits the skill described by this learning component")
    feedback: str | None = Field(description="If aligned=false: concrete revision to make the item align. If aligned=true: null.")


class MathStandardsAlignmentOutput(BaseModel):
    """Output of the Math Standards Alignment Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    statement_code: str = Field(description="The standard code that was evaluated (matches the statement_code input)")
    learning_components: list[LearningComponentsItem]
    aligned_count: int = Field(ge=0, description="Number of learning components this question aligns to")
    total_count: int = Field(ge=0, description="Total number of learning components for this standard")


__all__ = [
    "MathStandardsAlignmentInput",
    "MathStandardsAlignmentOutput",
]
