"""Every evaluator the SDK ships, and lookup by current or historical id."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.feedback.ela_writing.tone_appropriateness import (
    ToneAppropriatenessEvaluator,
)
from learning_commons_evaluators.evaluators.student_facing_text.ela_reading.grade_level_appropriateness import (
    GradeLevelAppropriatenessEvaluator,
)
from learning_commons_evaluators.evaluators.student_facing_text.ela_reading.purpose_clarity import (
    PurposeClarityEvaluator,
)
from learning_commons_evaluators.schemas.metadata import EvaluatorMetadata

#: Every evaluator, in taxonomy order. Adding an evaluator means adding it here; the
#: conformance suite compares this against the public barrel and the ``evals/`` registry.
EVALUATORS: tuple[type[BaseEvaluator], ...] = (
    ToneAppropriatenessEvaluator,
    GradeLevelAppropriatenessEvaluator,
    PurposeClarityEvaluator,
)


def index_by_id(evaluators: Iterable[type[BaseEvaluator]]) -> Mapping[str, type[BaseEvaluator]]:
    """Index every evaluator by its current id and by each id it used to carry.

    Raises on a collision rather than letting one win: two evaluators sharing an id, most
    plausibly one's ``id_history`` entry colliding with another's current id, would
    otherwise resolve to whichever was registered later.
    """
    index: dict[str, type[BaseEvaluator]] = {}
    for evaluator in evaluators:
        for evaluator_id in (evaluator.metadata.id, *evaluator.metadata.id_history):
            claimed = index.get(evaluator_id)
            if claimed is not None and claimed is not evaluator:
                raise ValueError(
                    f'Registry id "{evaluator_id}" is claimed by both {claimed.metadata.name} '
                    f"and {evaluator.metadata.name}. An id, current or historical, must name "
                    "one evaluator."
                )
            index[evaluator_id] = evaluator
    return index


_BY_ID = index_by_id(EVALUATORS)


def get_evaluators() -> tuple[EvaluatorMetadata, ...]:
    """Every evaluator in the SDK, in taxonomy order."""
    return tuple(evaluator.metadata for evaluator in EVALUATORS)


def get_evaluator(evaluator_id: str) -> EvaluatorMetadata | None:
    """The evaluator a registry id names, or ``None``.

    Renames resolve: an id an evaluator used to carry still finds it via ``id_history``.
    """
    evaluator = _BY_ID.get(evaluator_id)
    return evaluator.metadata if evaluator is not None else None


def get_evaluator_class(evaluator_id: str) -> type[BaseEvaluator] | None:
    """The class behind an id, for callers that need to construct it."""
    return _BY_ID.get(evaluator_id)


__all__ = ["EVALUATORS", "get_evaluator", "get_evaluator_class", "get_evaluators", "index_by_id"]
