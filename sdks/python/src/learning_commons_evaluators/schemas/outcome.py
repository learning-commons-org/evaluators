"""Reading one comparable value out of an evaluation payload.

The envelope carries the payload exactly as the registry declares it, so there is no
top-level score. Reports still need a single scalar per evaluation to sort and chart on,
and it is read here from the evaluator's declared ``outcome`` block, so no SDK keeps a
per-evaluator table of which field holds the verdict.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from learning_commons_evaluators.contracts.loader import DeclaredOutcome
from learning_commons_evaluators.features.preprocessing import format_number
from learning_commons_evaluators.schemas.evaluator import EvaluationResult


@dataclass(frozen=True)
class Outcome:
    """The scalar verdict and its rationale, as a report consumes them.

    ``score`` is ``None`` when the payload carries no verdict field. That is a reporting
    gap rather than an evaluation failure, so it is surfaced as absent for the caller to
    handle, not quietly rendered as an empty string.
    """

    score: str | None
    reasoning: str


def _as_text(value: object) -> str:
    """A verdict as JavaScript's ``String()`` renders it, so both SDKs report the same token.

    A boolean verdict is ``"true"``/``"false"`` there, where Python's ``str`` would say
    ``"True"``; a number is ``7`` rather than ``7.0``.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return format_number(value)
    return str(value)


def read_outcome(evaluation: EvaluationResult[Any], outcome: DeclaredOutcome | None) -> Outcome:
    """Pick the verdict and reasoning out of an evaluation's payload.

    ``outcome`` is the evaluator's declared block (``EvaluatorClass.metadata.outcome``).
    An evaluator with no declared outcome, or a payload missing the declared property,
    yields a ``None`` score rather than raising.
    """
    payload = evaluation.result
    if isinstance(payload, BaseModel):
        record: Mapping[str, Any] = payload.model_dump()
    elif isinstance(payload, Mapping):
        record = payload
    else:
        return Outcome(score=None, reasoning="")
    if outcome is None:
        return Outcome(score=None, reasoning="")

    score = record.get(outcome.score)
    reasoning = record.get(outcome.reasoning)
    return Outcome(
        score=None if score is None else _as_text(score),
        reasoning=reasoning if isinstance(reasoning, str) else "",
    )


__all__ = ["Outcome", "read_outcome"]
