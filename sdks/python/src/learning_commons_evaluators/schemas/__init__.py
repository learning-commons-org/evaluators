"""Pydantic types shared by every evaluator: the result envelope and evaluator metadata.

Per-evaluator ``<Class>Input`` and ``<Class>Output`` models are generated from each
contract into the nested ``<family>/<subject>/`` packages.
"""

from learning_commons_evaluators.schemas.evaluator import (
    EvaluationMetadata,
    EvaluationResult,
    EvaluationTokenUsage,
)
from learning_commons_evaluators.schemas.metadata import EvaluatorMetadata
from learning_commons_evaluators.schemas.outcome import Outcome, read_outcome

__all__ = [
    "EvaluationMetadata",
    "EvaluationResult",
    "EvaluationTokenUsage",
    "EvaluatorMetadata",
    "Outcome",
    "read_outcome",
]
