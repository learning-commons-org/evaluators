"""read_outcome reads the declared fields and reports a missing verdict as None."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from learning_commons_evaluators import (
    EvaluationMetadata,
    EvaluationResult,
    EvaluationTokenUsage,
    Outcome,
    read_outcome,
)
from learning_commons_evaluators.contracts.loader import DeclaredOutcome

METADATA = EvaluationMetadata(
    model="google:m",
    processing_time_ms=1,
    token_usage=EvaluationTokenUsage(input_tokens=1, output_tokens=1),
)


class _Payload(BaseModel):
    quality_score: int
    reasoning: str


def _evaluation(result: object) -> EvaluationResult:
    return EvaluationResult(evaluator="x.y.z", result=result, metadata=METADATA)


def test_reads_a_model_payload_and_stringifies_the_score() -> None:
    outcome = read_outcome(
        _evaluation(_Payload(quality_score=1, reasoning="fine")),
        DeclaredOutcome(score="quality_score", reasoning="reasoning"),
    )
    assert outcome == Outcome(score="1", reasoning="fine")


def test_reads_a_mapping_payload() -> None:
    outcome = read_outcome(
        _evaluation({"grade_band": "4-5", "reasoning": "r"}),
        DeclaredOutcome(score="grade_band", reasoning="reasoning"),
    )
    assert outcome.score == "4-5"


def test_no_declared_outcome_is_no_verdict() -> None:
    assert read_outcome(_evaluation({"a": 1}), None) == Outcome(score=None, reasoning="")


def test_a_missing_declared_field_is_none_not_an_error() -> None:
    outcome = read_outcome(
        _evaluation({"other": 1}), DeclaredOutcome(score="score", reasoning="reasoning")
    )
    assert outcome == Outcome(score=None, reasoning="")


def test_a_non_string_reasoning_is_reported_empty() -> None:
    outcome = read_outcome(
        _evaluation({"score": 2, "reasoning": 5}),
        DeclaredOutcome(score="score", reasoning="reasoning"),
    )
    assert outcome == Outcome(score="2", reasoning="")


def test_a_scalar_payload_has_no_verdict() -> None:
    assert (
        read_outcome(_evaluation("text"), DeclaredOutcome(score="s", reasoning="r")).score is None
    )


#: Each value beside what JavaScript's ``String()`` returns for it, taken from Node: the
#: same verdict must read the same in a report whichever SDK produced it.
JAVASCRIPT_STRINGS: list[tuple[object, str]] = [
    (True, "true"),
    (False, "false"),
    (7, "7"),
    (-7, "-7"),
    (7.0, "7"),
    (0.5, "0.5"),
    (0.1 + 0.2, "0.30000000000000004"),
    (-0.0, "0"),
    # Plain notation runs from 1e-6 up to, but not including, 1e21.
    (1e-6, "0.000001"),
    (1.5e-6, "0.0000015"),
    (1e-7, "1e-7"),
    (1.5e-7, "1.5e-7"),
    (1e20, "100000000000000000000"),
    (9.999999999999999e20, "999999999999999900000"),
    (1e21, "1e+21"),
    (1.2345e25, "1.2345e+25"),
    (5e-324, "5e-324"),
    (1.7976931348623157e308, "1.7976931348623157e+308"),
    (float("nan"), "NaN"),
    (float("inf"), "Infinity"),
    (float("-inf"), "-Infinity"),
    # An int is read as the double JavaScript would parse from the same JSON.
    (2**53 + 1, "9007199254740992"),
    (10**22, "1e+22"),
    (10**400, "Infinity"),
    (-(10**400), "-Infinity"),
]


@pytest.mark.parametrize(("value", "token"), JAVASCRIPT_STRINGS, ids=repr)
def test_a_scalar_score_is_rendered_as_typescript_renders_it(value: object, token: str) -> None:
    declared = DeclaredOutcome(score="score", reasoning="reasoning")
    outcome = read_outcome(_evaluation({"score": value, "reasoning": "r"}), declared)
    assert outcome.score == token
