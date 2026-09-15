"""Vocabulary Complexity: how demanding a text's words are for a target grade.

Three declared steps, two of which are branches of one. A shared first step asks what
students at the grade already know about the topic, which keeps familiar domain words from
reading as complex; the rating that follows is a different prompt on a different model for
grades 3-4 than for grades 5-12, and the contract expresses that as two steps whose
``condition`` selects on ``grade_level``. The Flesch-Kincaid score is computed only for the
grades whose prompt binds it, which its preprocessing entry states separately from the
step's own condition.

The first step answers in prose, not JSON: it is written to reply with the assumption "and
nothing else", and its answer is pasted into the next prompt verbatim. ``config.json``
cannot say so — the registry schema pins every LLM step's ``parser.kind`` to
``structured_output`` — so the ``None`` below is the SDK's statement of it, and the
TypeScript SDK makes the same call for the same step.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.multi_step import MultiStepEvaluator
from learning_commons_evaluators.schemas.student_facing_text.ela_reading.vocabulary_complexity import (
    EVALUATOR_ID,
    VocabularyComplexityInput,
    VocabularyComplexityOutput,
)


class VocabularyComplexityEvaluator(
    MultiStepEvaluator[VocabularyComplexityInput, VocabularyComplexityOutput]
):
    contract = load_contract(EVALUATOR_ID)
    input_model = VocabularyComplexityInput
    output_model = VocabularyComplexityOutput
    step_models = {
        "background_knowledge": None,
        # Either branch produces the evaluator's result; which one runs is the grade's.
        "vocab_complexity_grades_3_4": VocabularyComplexityOutput,
        "vocab_complexity_other_grades": VocabularyComplexityOutput,
    }


__all__ = [
    "VocabularyComplexityEvaluator",
    "VocabularyComplexityInput",
    "VocabularyComplexityOutput",
]
