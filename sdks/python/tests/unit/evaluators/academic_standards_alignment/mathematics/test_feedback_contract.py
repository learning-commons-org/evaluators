"""The verdict's feedback key is required and nullable, as the contract declares it (DSCR-2453)."""

import pytest
from pydantic import ValidationError

from learning_commons_evaluators.evaluators.academic_standards_alignment.mathematics.math_standards_alignment import (
    BatchedLCEvaluation,
)


def verdict(**overrides: object) -> dict[str, object]:
    return {"lc_id": "lc-1", "reasoning": "r", "answer": "Yes", **overrides}


def test_a_verdict_without_the_feedback_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BatchedLCEvaluation.model_validate({"evaluations": [verdict()]})


def test_a_null_feedback_is_accepted_for_an_aligned_verdict() -> None:
    parsed = BatchedLCEvaluation.model_validate({"evaluations": [verdict(feedback=None)]})

    assert parsed.evaluations[0].feedback is None


def test_text_feedback_is_accepted() -> None:
    parsed = BatchedLCEvaluation.model_validate({"evaluations": [verdict(feedback="Revise it.")]})

    assert parsed.evaluations[0].feedback == "Revise it."
