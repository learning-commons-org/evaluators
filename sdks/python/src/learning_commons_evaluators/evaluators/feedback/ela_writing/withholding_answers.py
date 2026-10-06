"""Withholding Answers: does the feedback coach rather than do the work?

Judges whether the feedback points toward evidence without supplying it, prompts revision
without rewriting, and leaves the core thinking to the student.

The feedback family's shape: two texts in (``student_text``, ``feedback_text``), a binary
``quality_score`` with per-feature justifications out, one model call on OpenAI.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.feedback.ela_writing.withholding_answers import (
    EVALUATOR_ID,
    WithholdingAnswersInput,
    WithholdingAnswersOutput,
)


class WithholdingAnswersEvaluator(
    SingleStepEvaluator[WithholdingAnswersInput, WithholdingAnswersOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = WithholdingAnswersInput
    output_model = WithholdingAnswersOutput


__all__ = [
    "WithholdingAnswersEvaluator",
    "WithholdingAnswersInput",
    "WithholdingAnswersOutput",
]
