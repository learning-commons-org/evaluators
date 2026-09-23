"""Strength Acknowledgment: does the feedback name what the student did well, specifically?

Judges the presence of praise, its specificity, whether it is anchored to evidence in the
work, and whether it frames process rather than a fixed trait. The American spelling is the
name in code and in the registry id (D7).

The feedback family's shape: two texts in (``student_text``, ``feedback_text``), a binary
``quality_score`` with per-feature justifications out, one model call on OpenAI.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.feedback.ela_writing.strength_acknowledgment import (
    EVALUATOR_ID,
    StrengthAcknowledgmentInput,
    StrengthAcknowledgmentOutput,
)


class StrengthAcknowledgmentEvaluator(
    SingleStepEvaluator[StrengthAcknowledgmentInput, StrengthAcknowledgmentOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = StrengthAcknowledgmentInput
    output_model = StrengthAcknowledgmentOutput


__all__ = [
    "StrengthAcknowledgmentEvaluator",
    "StrengthAcknowledgmentInput",
    "StrengthAcknowledgmentOutput",
]
