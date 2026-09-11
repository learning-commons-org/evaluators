# GENERATED — do not edit directly.
# Source: evals/feedback/ela-writing/withholding-answers/output_schema.json
#         evals/feedback/ela-writing/withholding-answers/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Withholding Answers Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "feedback.ela_writing.withholding_answers"


class WithholdingAnswersInput(BaseModel):
    """Inputs to the Withholding Answers Evaluator, named as its input_schema.json declares them."""

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

    points_toward_evidence_without_supplying: KeyFeatureAssessment = Field(description="Whether the feedback points toward where to find evidence rather than supplying the actual evidence")
    prompts_revision_without_rewriting: KeyFeatureAssessment = Field(description="Whether it prompts the student to revise rather than rewriting or modeling the full response")
    leaves_core_thinking_to_student: KeyFeatureAssessment = Field(description="Whether the guidance leaves the core thinking (selecting, explaining, or wording the evidence) to the student")


class WithholdingAnswersOutput(BaseModel):
    """Output of the Withholding Answers Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(description="Step-by-step reasoning before the final answer: assess the student response against the task goal, then judge whether the teacher feedback meets the criterion.")
    key_features: KeyFeatures
    proposed_adjustment: str = Field(description="How the teacher feedback could be modified to meet the criterion. If it already meets the criterion, say so briefly.")
    quality_score: Literal[0, 1] = Field(description="Overall: 1 if the feedback meets the criterion, 0 otherwise.")


__all__ = [
    "WithholdingAnswersInput",
    "WithholdingAnswersOutput",
]
