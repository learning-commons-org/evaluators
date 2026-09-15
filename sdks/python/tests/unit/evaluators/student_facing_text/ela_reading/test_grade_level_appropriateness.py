"""Grade Level Appropriateness: text only, grade-band verdict, Google."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from learning_commons_evaluators import (
    GradeLevelAppropriatenessEvaluator,
    GradeLevelAppropriatenessInput,
    InputValidationError,
    Provider,
    read_outcome,
)
from tests.unit.conftest import ProviderFactory

TEXT = "Trees are important plants that grow in many parts of the world. They have roots."


def test_metadata_is_the_contracts() -> None:
    metadata = GradeLevelAppropriatenessEvaluator.metadata
    assert metadata.id == "student_facing_text.ela_reading.grade_level_appropriateness"
    assert metadata.id_history == ("grade-level-appropriateness",)
    assert metadata.default_providers == (Provider.GOOGLE,)
    assert metadata.supported_grades[0] == "K" and metadata.supported_grades[-1] == "12"
    assert metadata.outcome is not None and metadata.outcome.score == "grade_band"


async def test_rejects_a_supplied_grade(providers: ProviderFactory) -> None:
    # Grade validation exists iff grade is an input (§4.2): a grade-free evaluator must not
    # silently consume one.
    evaluator = GradeLevelAppropriatenessEvaluator(google_api_key="k")
    with pytest.raises(
        InputValidationError, match='Unknown input "grade_level". This evaluator accepts: text.'
    ):
        await evaluator.evaluate(text=TEXT, grade_level=5)
    with pytest.raises(ValidationError):  # the typed input model forbids it too
        GradeLevelAppropriatenessInput(text=TEXT, grade_level=5)  # type: ignore[call-arg]


async def test_binds_the_text_into_the_user_prompt(providers: ProviderFactory) -> None:
    evaluator = GradeLevelAppropriatenessEvaluator(google_api_key="k")
    await evaluator.evaluate(GradeLevelAppropriatenessInput(text=TEXT))
    [system, user] = providers.last.calls[0]["messages"]
    assert system["content"] == evaluator.contract.document("system.txt")
    assert user["content"] == evaluator.contract.document("user.txt").replace("{text}", TEXT)
    assert providers.last.calls[0]["temperature"] == 1


async def test_returns_a_band_verdict(providers: ProviderFactory) -> None:
    evaluator = GradeLevelAppropriatenessEvaluator(google_api_key="k")
    evaluation = await evaluator.evaluate(text=TEXT)
    assert evaluation.evaluator == evaluator.metadata.id
    assert evaluation.metadata.model == "google:gemini-3.6-flash"
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {
        "K-1",
        "2-3",
        "4-5",
        "6-8",
        "9-10",
        "11-12",
    }
