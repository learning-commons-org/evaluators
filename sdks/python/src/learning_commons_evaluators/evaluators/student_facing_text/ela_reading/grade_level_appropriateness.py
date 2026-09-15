"""Grade Level Appropriateness: which grade band a text suits at independent reading.

Takes no grade level: unlike the complexity evaluators, which judge a text *against* a
grade, this one determines the grade. Its contract declares only ``text``, so a supplied
``grade_level`` is rejected as an unknown input; ``metadata.supported_grades`` reports the
K-12 span of the bands it can return.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.student_facing_text.ela_reading.grade_level_appropriateness import (
    EVALUATOR_ID,
    GradeLevelAppropriatenessInput,
    GradeLevelAppropriatenessOutput,
)


class GradeLevelAppropriatenessEvaluator(
    SingleStepEvaluator[GradeLevelAppropriatenessInput, GradeLevelAppropriatenessOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = GradeLevelAppropriatenessInput
    output_model = GradeLevelAppropriatenessOutput


__all__ = [
    "GradeLevelAppropriatenessEvaluator",
    "GradeLevelAppropriatenessInput",
    "GradeLevelAppropriatenessOutput",
]
