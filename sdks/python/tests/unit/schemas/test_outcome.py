"""read_outcome reads the declared fields and reports a missing verdict as None."""

from __future__ import annotations

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
