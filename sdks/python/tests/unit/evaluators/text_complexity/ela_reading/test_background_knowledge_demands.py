"""Background Knowledge Demands: a ten-character floor on the text, and a flat payload."""

from __future__ import annotations

import pytest

from learning_commons_evaluators import (
    BackgroundKnowledgeDemandsEvaluator,
    BackgroundKnowledgeDemandsInput,
    BackgroundKnowledgeDemandsOutput,
    InputValidationError,
    Provider,
    get_evaluator,
    read_outcome,
)
from tests.unit.conftest import ProviderFactory

TEXT = "Proteins fold into thousands of shapes, and each shape decides what the protein does."


def test_metadata_is_the_contracts() -> None:
    metadata = BackgroundKnowledgeDemandsEvaluator.metadata
    assert metadata.id == "text_complexity.ela_reading.background_knowledge_demands"
    assert metadata.id_history == ("subject-matter-knowledge",)
    assert metadata.default_providers == (Provider.GOOGLE,)
    assert metadata.supported_grades == tuple(str(g) for g in range(3, 13))
    assert get_evaluator("subject-matter-knowledge") is metadata


async def test_binds_text_grade_and_fk_score(providers: ProviderFactory) -> None:
    evaluator = BackgroundKnowledgeDemandsEvaluator(google_api_key="k")
    await evaluator.evaluate(text=TEXT, grade_level=11)
    [system, user] = providers.last.calls[0]["messages"]
    assert system["content"] == evaluator.contract.document("system.txt")
    assert user["content"].startswith(f"Analyze:\nText: {TEXT}\nGrade: 11\nFK Score: ")
    assert providers.last.calls[0]["temperature"] == 0


async def test_enforces_the_contracts_ten_character_minimum(providers: ProviderFactory) -> None:
    # Unlike Organizational Structure and Reference Knowledge Demands, whose schemas take
    # any non-blank text, this one declares minLength 10.
    evaluator = BackgroundKnowledgeDemandsEvaluator(google_api_key="k")
    with pytest.raises(
        InputValidationError, match="text is too short. Minimum length is 10 characters."
    ):
        await evaluator.evaluate(text="Proteins.", grade_level=11)


async def test_returns_the_analysis_fields_beside_the_verdict(providers: ProviderFactory) -> None:
    evaluator = BackgroundKnowledgeDemandsEvaluator(google_api_key="k")
    evaluation = await evaluator.evaluate(
        BackgroundKnowledgeDemandsInput(text=TEXT, grade_level=11)
    )
    result = evaluation.result
    assert isinstance(result, BackgroundKnowledgeDemandsOutput)
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {
        "slightly_complex",
        "moderately_complex",
        "very_complex",
        "exceedingly_complex",
    }
    # Flat, not nested under details: topics, the curriculum check, what the text assumes,
    # and where the difficulty actually comes from.
    assert result.identified_topics
    assert result.curriculum_check
    assert result.assumptions_and_scaffolding
    assert result.friction_analysis
