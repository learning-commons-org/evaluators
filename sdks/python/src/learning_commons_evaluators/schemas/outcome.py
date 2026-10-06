"""Reading one comparable value out of an evaluation payload.

The envelope carries the payload exactly as the registry declares it, so there is no
top-level score. Reports still need a single scalar per evaluation to sort and chart on,
and it is read here from the evaluator's declared ``outcome`` block, so no SDK keeps a
per-evaluator table of which field holds the verdict.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from learning_commons_evaluators.contracts.loader import DeclaredOutcome
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


def _number_as_text(value: float) -> str:
    """A number as ECMAScript's ``Number::toString`` writes it.

    The digits are Python's: ``repr`` and JavaScript both produce the shortest digit
    string that reads back as the same double, choosing the closest when several do, so
    they always agree. Only the layout is JavaScript's: plain notation for decimal
    exponents from -7 to 20, ``1e-7`` / ``1e+21`` beyond them, ``NaN`` and ``Infinity``,
    and ``-0`` written as ``0``.
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "0"
    if value < 0:
        return "-" + _number_as_text(-value)

    _, digit_tuple, exponent = Decimal(repr(value)).as_tuple()
    assert isinstance(exponent, int)  # finite, so never "n", "N" or "F"
    digits = "".join(map(str, digit_tuple)).rstrip("0")
    exponent += len(digit_tuple) - len(digits)
    # The value is 0.<digits> × 10^n, in the spec's terms: k digits, decimal exponent n.
    k, n = len(digits), exponent + len(digits)
    if k <= n <= 21:
        return digits + "0" * (n - k)
    if 0 < n <= 21:
        return f"{digits[:n]}.{digits[n:]}"
    if -6 < n <= 0:
        return "0." + "0" * -n + digits
    mantissa = digits if k == 1 else f"{digits[0]}.{digits[1:]}"
    return f"{mantissa}e{'+' if n - 1 >= 0 else '-'}{abs(n - 1)}"


def _as_text(value: object) -> str:
    """A verdict as JavaScript's ``String()`` renders it, so both SDKs report the same token.

    A boolean verdict is ``"true"``/``"false"`` there, where Python's ``str`` would say
    ``"True"``; a number is ``7`` rather than ``7.0``, and ``1e+21`` rather than
    twenty-two digits. A Python ``int`` is read as the double JavaScript would have parsed
    from the same JSON, so one beyond 2**53 loses precision exactly as it does there.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        try:
            return _number_as_text(float(value))
        except OverflowError:
            return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, float):
        return _number_as_text(value)
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
