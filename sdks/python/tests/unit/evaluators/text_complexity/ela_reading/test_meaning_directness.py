"""Meaning Directness: the conventionality dimension, taking grade_level with no alias."""

from __future__ import annotations

import pytest

from learning_commons_evaluators import (
    InputValidationError,
    MeaningDirectnessEvaluator,
    MeaningDirectnessInput,
    MeaningDirectnessOutput,
    Provider,
    get_evaluator,
    read_outcome,
)
from tests.unit.conftest import ProviderFactory

TEXT = "The old man and the sea were one, bound together by a rope of years."


def test_metadata_is_the_contracts() -> None:
    metadata = MeaningDirectnessEvaluator.metadata
    assert metadata.id == "text_complexity.ela_reading.meaning_directness"
    assert metadata.id_history == ("conventionality",)
    assert metadata.default_providers == (Provider.GOOGLE,)
    assert metadata.supported_grades == tuple(str(g) for g in range(3, 13))
    assert get_evaluator("conventionality") is metadata


async def test_takes_grade_level_and_not_0_2_0s_grade(providers: ProviderFactory) -> None:
    # 0.2.0's ConventionalityEvaluator took `grade`; 1.0 takes the contract's name, with no
    # alias (D4), so the old keyword is an unknown input rather than a silent synonym.
    evaluator = MeaningDirectnessEvaluator(google_api_key="k")
    with pytest.raises(
        InputValidationError,
        match='Unknown input "grade". This evaluator accepts: text, grade_level.',
    ):
        await evaluator.evaluate(text=TEXT, grade=8)


async def test_binds_text_grade_and_fk_score(providers: ProviderFactory) -> None:
    evaluator = MeaningDirectnessEvaluator(google_api_key="k")
    await evaluator.evaluate(text=TEXT, grade_level=8)
    [system, user] = providers.last.calls[0]["messages"]
    assert system["content"] == evaluator.contract.document("system.txt")
    assert user["content"].startswith(f"Analyze:\nText: {TEXT}\nGrade: 8\nFK Score: ")
    assert providers.last.calls[0]["temperature"] == 0


async def test_returns_the_features_behind_the_verdict(providers: ProviderFactory) -> None:
    evaluator = MeaningDirectnessEvaluator(google_api_key="k")
    evaluation = await evaluator.evaluate(MeaningDirectnessInput(text=TEXT, grade_level=8))
    result = evaluation.result
    assert isinstance(result, MeaningDirectnessOutput)
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {
        "slightly_complex",
        "moderately_complex",
        "very_complex",
        "exceedingly_complex",
    }
    assert result.conventionality_features
    assert result.grade_context
    assert result.instructional_insights
