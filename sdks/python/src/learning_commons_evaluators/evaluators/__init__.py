"""Evaluator classes and the registry.

Concrete evaluators live in the nested ``<family>/<subject>/`` packages mirroring
``evals/``; the public barrel re-exports every class flat.
"""

from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.feedback.ela_writing.tone_appropriateness import (
    ToneAppropriatenessEvaluator,
)
from learning_commons_evaluators.evaluators.registry import (
    EVALUATORS,
    get_evaluator,
    get_evaluator_class,
    get_evaluators,
)
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.evaluators.student_facing_text.ela_reading.grade_level_appropriateness import (
    GradeLevelAppropriatenessEvaluator,
)
from learning_commons_evaluators.evaluators.student_facing_text.ela_reading.purpose_clarity import (
    PurposeClarityEvaluator,
)

__all__ = [
    "EVALUATORS",
    "BaseEvaluator",
    "GradeLevelAppropriatenessEvaluator",
    "PurposeClarityEvaluator",
    "SingleStepEvaluator",
    "ToneAppropriatenessEvaluator",
    "get_evaluator",
    "get_evaluator_class",
    "get_evaluators",
]
