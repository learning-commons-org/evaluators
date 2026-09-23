"""Student Response Specificity: is the feedback about *this* student's writing?

Judges whether the feedback refers to the student's actual work, avoids generic or
template phrasing, and engages from an accurate reading of what the student wrote.

The feedback family's shape: two texts in (``student_text``, ``feedback_text``), a binary
``quality_score`` with per-feature justifications out, one model call on OpenAI.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.feedback.ela_writing.student_response_specificity import (
    EVALUATOR_ID,
    StudentResponseSpecificityInput,
    StudentResponseSpecificityOutput,
)


class StudentResponseSpecificityEvaluator(
    SingleStepEvaluator[StudentResponseSpecificityInput, StudentResponseSpecificityOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = StudentResponseSpecificityInput
    output_model = StudentResponseSpecificityOutput


__all__ = [
    "StudentResponseSpecificityEvaluator",
    "StudentResponseSpecificityInput",
    "StudentResponseSpecificityOutput",
]
