"""Revision Actionability: can the student act on this feedback?

Judges whether the feedback names a target clearly, gives a specific next move, and asks
for something a student could reasonably do.

The feedback family's shape: two texts in (``student_text``, ``feedback_text``), a binary
``quality_score`` with per-feature justifications out, one model call on OpenAI.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.feedback.ela_writing.revision_actionability import (
    EVALUATOR_ID,
    RevisionActionabilityInput,
    RevisionActionabilityOutput,
)


class RevisionActionabilityEvaluator(
    SingleStepEvaluator[RevisionActionabilityInput, RevisionActionabilityOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = RevisionActionabilityInput
    output_model = RevisionActionabilityOutput


__all__ = [
    "RevisionActionabilityEvaluator",
    "RevisionActionabilityInput",
    "RevisionActionabilityOutput",
]
