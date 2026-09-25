"""Revision Manageability: is the revision load something one student can carry?

Judges length, how many distinct issues are raised at once, whether a priority is clear,
and whether the student is left knowing the next step.

The feedback family's shape: two texts in (``student_text``, ``feedback_text``), a binary
``quality_score`` with per-feature justifications out, one model call on OpenAI.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.feedback.ela_writing.revision_manageability import (
    EVALUATOR_ID,
    RevisionManageabilityInput,
    RevisionManageabilityOutput,
)


class RevisionManageabilityEvaluator(
    SingleStepEvaluator[RevisionManageabilityInput, RevisionManageabilityOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = RevisionManageabilityInput
    output_model = RevisionManageabilityOutput


__all__ = [
    "RevisionManageabilityEvaluator",
    "RevisionManageabilityInput",
    "RevisionManageabilityOutput",
]
