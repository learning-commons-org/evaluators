"""Purpose Clarity: the Purpose dimension of qualitative text complexity for a target grade.

One model call on Google, with the Flesch-Kincaid grade computed by ``textstat`` and bound
to ``{fk_score}`` as the contract's preprocessing entry declares. The rating scale has a
fifth level, ``more_context_needed``, with no adjacency to the other four.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.student_facing_text.ela_reading.purpose_clarity import (
    EVALUATOR_ID,
    PurposeClarityInput,
    PurposeClarityOutput,
)


class PurposeClarityEvaluator(SingleStepEvaluator[PurposeClarityInput, PurposeClarityOutput]):
    contract = load_contract(EVALUATOR_ID)
    input_model = PurposeClarityInput
    output_model = PurposeClarityOutput


__all__ = ["PurposeClarityEvaluator", "PurposeClarityInput", "PurposeClarityOutput"]
