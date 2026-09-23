"""Revision Accuracy: does the feedback read the student's work correctly?

Judges whether the feedback assesses the task accurately, names a real revision need,
and signals completion honestly when the task is already done.

The feedback family's shape: two texts in (``student_text``, ``feedback_text``), a binary
``quality_score`` with per-feature justifications out, one model call on OpenAI.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.feedback.ela_writing.revision_accuracy import (
    EVALUATOR_ID,
    RevisionAccuracyInput,
    RevisionAccuracyOutput,
)


class RevisionAccuracyEvaluator(SingleStepEvaluator[RevisionAccuracyInput, RevisionAccuracyOutput]):
    contract = load_contract(EVALUATOR_ID)
    input_model = RevisionAccuracyInput
    output_model = RevisionAccuracyOutput


__all__ = [
    "RevisionAccuracyEvaluator",
    "RevisionAccuracyInput",
    "RevisionAccuracyOutput",
]
