# GENERATED — do not edit directly.
# Source: evals/feedback/ela-writing/student-response-specificity/output_schema.json
#         evals/feedback/ela-writing/student-response-specificity/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Student Response Specificity Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "feedback.ela_writing.student_response_specificity"


class StudentResponseSpecificityInput(BaseModel):
    """Inputs to the Student Response Specificity Evaluator, named as its input_schema.json declares them."""

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

    specific_reference_to_student_work: KeyFeatureAssessment = Field(description="Feedback should clearly reference or build on the student's specific idea, wording, or use of evidence")
    not_generic_or_template_based: KeyFeatureAssessment = Field(description="Feedback should not be a stock phrase that could apply to any response")
    engage_based_on_accurate_understanding: KeyFeatureAssessment = Field(description="Engages with the student's actual response, rather than something the student did not actually say or attempt. Demonstrates accurate understanding of what the student wrote.")


class StudentResponseSpecificityOutput(BaseModel):
    """Output of the Student Response Specificity Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    reasoning: str = Field(description="Step-by-step reasoning before the final answer: assess the student response against the task goal, then judge whether the teacher feedback meets the criterion.")
    key_features: KeyFeatures
    proposed_adjustment: str = Field(description="How the teacher feedback could be modified to meet the criterion. If it already meets the criterion, say so briefly.")
    quality_score: Literal[0, 1] = Field(description="Overall: 1 if the feedback meets the criterion, 0 otherwise.")


__all__ = [
    "StudentResponseSpecificityInput",
    "StudentResponseSpecificityOutput",
]
