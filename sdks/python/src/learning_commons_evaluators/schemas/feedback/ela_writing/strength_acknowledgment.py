# GENERATED — do not edit directly.
# Source: evals/feedback/ela-writing/strength-acknowledgment/output_schema.json
#         evals/feedback/ela-writing/strength-acknowledgment/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Strength Acknowledgment Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "feedback.ela_writing.strength_acknowledgment"


class StrengthAcknowledgmentInput(BaseModel):
    """Inputs to the Strength Acknowledgment Evaluator, named as its input_schema.json declares them."""

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

    presence_of_praise: KeyFeatureAssessment = Field(description="Presence of praise that is specific and authentic")
    specificity: KeyFeatureAssessment = Field(description="Specificity of the acknowledgment rather than generic praise")
    anchoring_to_evidence: KeyFeatureAssessment = Field(description="Anchoring to evidence in the student response")
    process_vs_trait_framing: KeyFeatureAssessment = Field(description="Process-vs-trait framing")


class StrengthAcknowledgmentOutput(BaseModel):
    """Output of the Strength Acknowledgment Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(description="Step-by-step reasoning before the final answer: assess the student response against the task goal, then judge whether the teacher feedback meets the criterion.")
    key_features: KeyFeatures
    proposed_adjustment: str = Field(description="How the teacher feedback could be modified to meet the criterion. If it already meets the criterion, say so briefly.")
    quality_score: Literal[0, 1] = Field(description="Overall: 1 if the feedback meets the criterion, 0 otherwise.")


__all__ = [
    "StrengthAcknowledgmentInput",
    "StrengthAcknowledgmentOutput",
]
