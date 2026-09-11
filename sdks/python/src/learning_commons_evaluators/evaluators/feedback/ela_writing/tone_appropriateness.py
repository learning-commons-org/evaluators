"""Tone Appropriateness: is teacher feedback's tone appropriate and constructive for the student?

The feedback family's shape: two texts in (``student_text``, ``feedback_text``), a binary
``quality_score`` with per-feature justifications out, one model call on OpenAI.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.feedback.ela_writing.tone_appropriateness import (
    EVALUATOR_ID,
    ToneAppropriatenessInput,
    ToneAppropriatenessOutput,
)


class ToneAppropriatenessEvaluator(
    SingleStepEvaluator[ToneAppropriatenessInput, ToneAppropriatenessOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = ToneAppropriatenessInput
    output_model = ToneAppropriatenessOutput


__all__ = ["ToneAppropriatenessEvaluator", "ToneAppropriatenessInput", "ToneAppropriatenessOutput"]
