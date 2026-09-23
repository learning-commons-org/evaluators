"""Background Knowledge Demands: how much a text assumes its reader already knows.

The subject-matter-knowledge dimension, which is the id it shipped under. One model call on
Google, with ``{fk_score}`` from ``textstat`` — which the prompt takes as a loose proxy for
sentence difficulty, so that a hard-to-read sentence is not mistaken for a knowledge demand.
The payload is flat: the topics found, the curriculum check, what the text assumes against
what it explains, and where the friction actually comes from.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.text_complexity.ela_reading.background_knowledge_demands import (
    EVALUATOR_ID,
    BackgroundKnowledgeDemandsInput,
    BackgroundKnowledgeDemandsOutput,
)


class BackgroundKnowledgeDemandsEvaluator(
    SingleStepEvaluator[BackgroundKnowledgeDemandsInput, BackgroundKnowledgeDemandsOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = BackgroundKnowledgeDemandsInput
    output_model = BackgroundKnowledgeDemandsOutput


__all__ = [
    "BackgroundKnowledgeDemandsEvaluator",
    "BackgroundKnowledgeDemandsInput",
    "BackgroundKnowledgeDemandsOutput",
]
