"""Meaning Directness: how far a text's meaning sits below its surface.

The conventionality dimension, which is the id it shipped under and still resolves by. One
model call on Google, with ``{fk_score}`` from ``textstat``. The 0.2.0 evaluator took
``grade``; this one takes ``grade_level``, as the contract's input schema names it, with no
alias (D4).
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.text_complexity.ela_reading.meaning_directness import (
    EVALUATOR_ID,
    MeaningDirectnessInput,
    MeaningDirectnessOutput,
)


class MeaningDirectnessEvaluator(
    SingleStepEvaluator[MeaningDirectnessInput, MeaningDirectnessOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = MeaningDirectnessInput
    output_model = MeaningDirectnessOutput


__all__ = [
    "MeaningDirectnessEvaluator",
    "MeaningDirectnessInput",
    "MeaningDirectnessOutput",
]
