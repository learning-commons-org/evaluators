# GENERATED — do not edit directly.
# Source: evals/feedback/ela-writing/revision-actionability/output_schema.json
#         evals/feedback/ela-writing/revision-actionability/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Revision Actionability Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "feedback.ela_writing.revision_actionability"


class RevisionActionabilityInput(BaseModel):
    """Inputs to the Revision Actionability Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    student_text: str = Field(description="The student's written response.")
    feedback_text: str = Field(description="The teacher's feedback to the student.")


class KeyFeatureAssessment(BaseModel):
    """Independent assessment of a single key feature."""

    model_config = ConfigDict(extra="forbid")

    met: Literal[0, 1] = Field(description="1 if this key feature is satisfied by the feedback, 0 otherwise.")
    justification: str = Field(description="One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.")


class KeyFeatures(BaseModel):
    """Per-key-feature assessment; each feature judged independently."""

    model_config = ConfigDict(extra="forbid")

    directive_verb_or_focused_question: KeyFeatureAssessment = Field(description="Presence of a directive verb or focused question")
    clarity_of_target: KeyFeatureAssessment = Field(description="Clarity of the target (what to revise)")
    specificity_of_next_move: KeyFeatureAssessment = Field(description="Specificity of the next move")
    reasonable_student_action: KeyFeatureAssessment = Field(description="Whether the student could reasonably act without further clarification")


class RevisionActionabilityOutput(BaseModel):
    """Output of the Revision Actionability Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(description="Step-by-step reasoning before the final answer: assess the student response against the task goal, then judge whether the teacher feedback meets the criterion.")
    key_features: KeyFeatures
    proposed_adjustment: str = Field(description="How the teacher feedback could be modified to meet the criterion. If it already meets the criterion, say so briefly.")
    quality_score: Literal[0, 1] = Field(description="Overall: 1 if the feedback meets the criterion, 0 otherwise.")


__all__ = [
    "RevisionActionabilityInput",
    "RevisionActionabilityOutput",
]
