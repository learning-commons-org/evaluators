"""Vocabulary Complexity: prose background knowledge, then the branch the grade selects."""

from __future__ import annotations

import pytest
import textstat

from learning_commons_evaluators import (
    ConfigurationError,
    InputValidationError,
    Provider,
    VocabularyComplexityEvaluator,
    VocabularyComplexityInput,
    VocabularyComplexityOutput,
    read_outcome,
)
from learning_commons_evaluators.features import format_number
from tests.unit.conftest import ProviderFactory

TEXT = "Polo went on a 24-year trip to China with his father and uncle, merchants of Venice."
KEYS = {"openai_api_key": "o", "google_api_key": "g"}

BACKGROUND_MODEL = "openai:gpt-4o-2024-11-20"
GRADES_34_MODEL = "google:gemini-2.5-pro"
OTHER_GRADES_MODEL = "openai:gpt-4.1-2025-04-14"


def test_metadata_is_the_contracts() -> None:
    metadata = VocabularyComplexityEvaluator.metadata
    assert metadata.id == "student_facing_text.ela_reading.vocabulary_complexity"
    assert metadata.id_history == ("vocabulary",)
    # Either branch may run, so both vendors' keys are required at construction.
    assert metadata.default_providers == (Provider.OPENAI, Provider.GOOGLE)
    assert metadata.supported_grades == tuple(str(g) for g in range(3, 13))


def test_both_provider_keys_are_required_whatever_grade_follows() -> None:
    with pytest.raises(ConfigurationError, match="Missing required credential: google_api_key"):
        VocabularyComplexityEvaluator(openai_api_key="o")


class TestBackgroundKnowledge:
    async def test_runs_first_as_prose_and_feeds_the_rating(
        self, providers: ProviderFactory
    ) -> None:
        providers.prose = "  Assume they have studied Venetian trade routes.  "
        await VocabularyComplexityEvaluator(**KEYS).evaluate(text=TEXT, grade_level=3)
        background, rating = providers.calls
        # No schema: the step is written to answer with the assumption and nothing else.
        assert background["schema"] is None
        assert background["messages"][0]["role"] == "user"
        assert TEXT in background["messages"][0]["content"]
        # Trimmed before it is pasted in, so the model's own padding is not read as structure.
        assert (
            "background knowledge about the text — this background knowledge influences which "
            "words from the text are familiar versus unfamiliar for the student: Assume they "
            "have studied Venetian trade routes."
        ) in rating["messages"][1]["content"]


class TestGradeSelectsTheBranch:
    async def test_grades_3_and_4_rate_on_google_with_the_readability_score(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await VocabularyComplexityEvaluator(**KEYS).evaluate(text=TEXT, grade_level=4)
        rating = providers.calls[1]
        assert rating["schema"] is VocabularyComplexityOutput
        fk = format_number(round(textstat.flesch_kincaid_grade(TEXT), 2))
        assert f"Text Flesch-Kincaid grade level: {fk}" in rating["messages"][1]["content"]
        assert "It is intended for grade 4." in rating["messages"][1]["content"]
        assert evaluation.metadata.model == f"{BACKGROUND_MODEL}+{GRADES_34_MODEL}"

    async def test_grades_5_to_12_rate_on_openai_without_a_readability_score(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await VocabularyComplexityEvaluator(**KEYS).evaluate(text=TEXT, grade_level=7)
        rating = providers.calls[1]
        assert "It is intended for grade 7." in rating["messages"][1]["content"]
        # The entry's own condition excludes these grades, so the score is never computed.
        assert "Flesch-Kincaid" not in rating["messages"][1]["content"]
        assert evaluation.metadata.model == f"{BACKGROUND_MODEL}+{OTHER_GRADES_MODEL}"

    async def test_only_one_branch_runs(self, providers: ProviderFactory) -> None:
        await VocabularyComplexityEvaluator(**KEYS).evaluate(text=TEXT, grade_level=7)
        assert len(providers.calls) == 2

    @pytest.mark.parametrize("grade", [2, 13])
    async def test_rejects_grades_outside_the_declared_enum(
        self, providers: ProviderFactory, grade: int
    ) -> None:
        evaluator = VocabularyComplexityEvaluator(**KEYS)
        with pytest.raises(InputValidationError, match=f'Invalid grade_level "{grade}"'):
            await evaluator.evaluate(text=TEXT, grade_level=grade)
        assert providers.calls == []


async def test_accepts_the_input_model_and_returns_the_ratings_payload(
    providers: ProviderFactory,
) -> None:
    evaluator = VocabularyComplexityEvaluator(**KEYS)
    evaluation = await evaluator.evaluate(VocabularyComplexityInput(text=TEXT, grade_level=5))
    assert isinstance(evaluation.result, VocabularyComplexityOutput)
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {
        "slightly_complex",
        "moderately_complex",
        "very_complex",
        "exceedingly_complex",
    }
    # Both steps' tokens, added.
    assert evaluation.metadata.token_usage.input_tokens == 12
