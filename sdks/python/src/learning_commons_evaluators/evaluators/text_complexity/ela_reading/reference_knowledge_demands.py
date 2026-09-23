"""Reference Knowledge Demands: what prior encounters with other texts a passage assumes.

The intertextuality dimension, which is the name it shipped under and still resolves by
through ``id_history``. One model call on Google, with ``{fk_score}`` from ``textstat``,
and the same ``details`` payload Organizational Structure returns.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.text_complexity.ela_reading.reference_knowledge_demands import (
    EVALUATOR_ID,
    ReferenceKnowledgeDemandsInput,
    ReferenceKnowledgeDemandsOutput,
)


class ReferenceKnowledgeDemandsEvaluator(
    SingleStepEvaluator[ReferenceKnowledgeDemandsInput, ReferenceKnowledgeDemandsOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = ReferenceKnowledgeDemandsInput
    output_model = ReferenceKnowledgeDemandsOutput


__all__ = [
    "ReferenceKnowledgeDemandsEvaluator",
    "ReferenceKnowledgeDemandsInput",
    "ReferenceKnowledgeDemandsOutput",
]
