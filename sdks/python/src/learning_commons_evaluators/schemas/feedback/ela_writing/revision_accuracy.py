# GENERATED — do not edit directly.
# Source: evals/feedback/ela-writing/revision-accuracy/output_schema.json
#         evals/feedback/ela-writing/revision-accuracy/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Revision Accuracy Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "feedback.ela_writing.revision_accuracy"


class RevisionAccuracyInput(BaseModel):
    """Inputs to the Revision Accuracy Evaluator, named as its input_schema.json declares them."""

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

    accurate_task_assessment: KeyFeatureAssessment = Field(description="Identifies whether the feedback correctly assesses revision need.")
    revision_need_identification: KeyFeatureAssessment = Field(description="Distinguishes between needed revision and move-on feedback.")
    appropriate_signal_when_task_complete: KeyFeatureAssessment = Field(description="Provides a clear signal that the student can move on when the task goal is met.")


class RevisionAccuracyOutput(BaseModel):
    """Output of the Revision Accuracy Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(description="Step-by-step reasoning before the final answer: assess the student response against the task goal, then judge whether the teacher feedback meets the criterion.")
    key_features: KeyFeatures
    proposed_adjustment: str = Field(description="How the teacher feedback could be modified to meet the criterion. If it already meets the criterion, say so briefly.")
    quality_score: Literal[0, 1] = Field(description="Overall: 1 if the feedback meets the criterion, 0 otherwise.")


__all__ = [
    "RevisionAccuracyInput",
    "RevisionAccuracyOutput",
]
