"""Purpose Clarity: text and grade in, five-level verdict out, fk_score computed by textstat."""

from __future__ import annotations

import pytest
import textstat

from learning_commons_evaluators import (
    InputValidationError,
    Provider,
    PurposeClarityEvaluator,
    PurposeClarityInput,
    PurposeClarityOutput,
    read_outcome,
)
from learning_commons_evaluators.features import format_number
from tests.unit.conftest import ProviderFactory

TEXT = "Trees are important plants that grow in many parts of the world. They have roots."


def test_metadata_is_the_contracts() -> None:
    metadata = PurposeClarityEvaluator.metadata
    assert metadata.id == "student_facing_text.ela_reading.purpose_clarity"
    assert metadata.id_history == ("literacy.gla.purpose",)
    assert metadata.default_providers == (Provider.GOOGLE,)
    assert metadata.supported_grades == tuple(str(g) for g in range(3, 13))


async def test_computes_and_binds_fk_score(providers: ProviderFactory) -> None:
    evaluator = PurposeClarityEvaluator(google_api_key="k")
    await evaluator.evaluate(text=TEXT, grade_level=5)
    [_, user] = providers.last.calls[0]["messages"]
    fk = format_number(round(textstat.flesch_kincaid_grade(TEXT), 2))
    assert user["content"] == f"Analyze:\nText: {TEXT}\nGrade: 5\nFK Score: {fk}"
    assert providers.last.calls[0]["temperature"] == 0


async def test_accepts_the_input_model(providers: ProviderFactory) -> None:
    evaluator = PurposeClarityEvaluator(google_api_key="k")
    evaluation = await evaluator.evaluate(PurposeClarityInput(text=TEXT, grade_level=8))
    assert isinstance(evaluation.result, PurposeClarityOutput)
    assert "Grade: 8" in providers.last.calls[0]["messages"][1]["content"]


@pytest.mark.parametrize("grade", [2, 13, "K"])
async def test_rejects_grades_outside_the_declared_enum(
    providers: ProviderFactory, grade: object
) -> None:
    evaluator = PurposeClarityEvaluator(google_api_key="k")
    with pytest.raises(
        InputValidationError, match=f'Invalid grade_level "{grade}". Accepted values: 3, 4'
    ):
        await evaluator.evaluate(text=TEXT, grade_level=grade)


async def test_verdict_is_one_of_the_five_levels(providers: ProviderFactory) -> None:
    evaluator = PurposeClarityEvaluator(google_api_key="k")
    evaluation = await evaluator.evaluate(text=TEXT, grade_level=5)
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {
        "slightly_complex",
        "moderately_complex",
        "very_complex",
        "exceedingly_complex",
        "more_context_needed",
    }
