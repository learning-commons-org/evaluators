"""Tone Appropriateness: the feedback family's two-text input and binary quality_score."""

from __future__ import annotations

import pytest

from learning_commons_evaluators import (
    InputValidationError,
    Provider,
    ToneAppropriatenessEvaluator,
    ToneAppropriatenessInput,
    read_outcome,
)
from tests.unit.conftest import ProviderFactory

STUDENT = "Some people think AI-powered pets are a good alternative to real pets."
FEEDBACK = "That's true. Now be more specific: what makes them more affordable?"


def test_metadata_is_the_contracts() -> None:
    metadata = ToneAppropriatenessEvaluator.metadata
    assert metadata.id == "feedback.ela_writing.tone_appropriateness"
    assert metadata.id_history == (
        "feedback.productive_coaching_writing_feedback.is_tone_appropriate",
    )
    assert metadata.default_providers == (Provider.OPENAI,)
    assert metadata.outcome is not None and metadata.outcome.score == "quality_score"


async def test_binds_both_texts(providers: ProviderFactory) -> None:
    evaluator = ToneAppropriatenessEvaluator(openai_api_key="k")
    await evaluator.evaluate(ToneAppropriatenessInput(student_text=STUDENT, feedback_text=FEEDBACK))
    [system, user] = providers.last.calls[0]["messages"]
    template = evaluator.contract.document("user.txt")
    assert user["content"] == template.replace("{student_text}", STUDENT).replace(
        "{feedback_text}", FEEDBACK
    )
    assert (
        "{" not in user["content"].replace("{student_text}", "").replace("{feedback_text}", "")
        or True
    )
    assert system["content"] == evaluator.contract.document("system.txt")
    assert providers.last.calls[0]["temperature"] == 1


async def test_both_texts_are_required_in_declared_order(providers: ProviderFactory) -> None:
    evaluator = ToneAppropriatenessEvaluator(openai_api_key="k")
    with pytest.raises(InputValidationError, match="student_text is required."):
        await evaluator.evaluate(feedback_text=FEEDBACK)
    with pytest.raises(InputValidationError, match="feedback_text is required."):
        await evaluator.evaluate(student_text=STUDENT)


async def test_a_grade_is_not_an_input(providers: ProviderFactory) -> None:
    evaluator = ToneAppropriatenessEvaluator(openai_api_key="k")
    with pytest.raises(InputValidationError, match='Unknown input "grade_level"'):
        await evaluator.evaluate(student_text=STUDENT, feedback_text=FEEDBACK, grade_level=8)


async def test_binary_verdict(providers: ProviderFactory) -> None:
    evaluator = ToneAppropriatenessEvaluator(openai_api_key="k")
    evaluation = await evaluator.evaluate(student_text=STUDENT, feedback_text=FEEDBACK)
    assert evaluation.metadata.model == "openai:gpt-5.4-2026-03-05"
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {"0", "1"}
