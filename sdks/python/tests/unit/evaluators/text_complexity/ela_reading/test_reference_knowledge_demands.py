"""Reference Knowledge Demands: the intertextuality dimension, under its current id."""

from __future__ import annotations

import pytest

from learning_commons_evaluators import (
    InputValidationError,
    Provider,
    ReferenceKnowledgeDemandsEvaluator,
    ReferenceKnowledgeDemandsInput,
    ReferenceKnowledgeDemandsOutput,
    get_evaluator,
    read_outcome,
)
from tests.unit.conftest import ProviderFactory

TEXT = "Icarus flew too near the sun, and the wax that held his wings gave way."


def test_metadata_is_the_contracts() -> None:
    metadata = ReferenceKnowledgeDemandsEvaluator.metadata
    assert metadata.id == "text_complexity.ela_reading.reference_knowledge_demands"
    assert metadata.id_history == ("literacy.gla.intertextuality",)
    assert metadata.default_providers == (Provider.GOOGLE,)
    assert metadata.supported_grades == tuple(str(g) for g in range(3, 13))


def test_the_dimensions_old_name_still_resolves() -> None:
    # It shipped as "intertextuality"; the rename is a lookup alias, not a second evaluator.
    assert (
        get_evaluator("literacy.gla.intertextuality") is ReferenceKnowledgeDemandsEvaluator.metadata
    )


async def test_binds_text_grade_and_fk_score(providers: ProviderFactory) -> None:
    evaluator = ReferenceKnowledgeDemandsEvaluator(google_api_key="k")
    await evaluator.evaluate(text=TEXT, grade_level=7)
    [system, user] = providers.last.calls[0]["messages"]
    assert system["content"] == evaluator.contract.document("system.txt")
    assert user["content"].startswith(f"Analyze:\nText: {TEXT}\nGrade: 7\nFK Score: ")
    assert providers.last.calls[0]["temperature"] == 0


@pytest.mark.parametrize("grade", [2, 13])
async def test_rejects_grades_outside_the_declared_enum(
    providers: ProviderFactory, grade: int
) -> None:
    evaluator = ReferenceKnowledgeDemandsEvaluator(google_api_key="k")
    with pytest.raises(InputValidationError, match=f'Invalid grade_level "{grade}"'):
        await evaluator.evaluate(text=TEXT, grade_level=grade)


async def test_returns_a_verdict_alongside_the_instructional_details(
    providers: ProviderFactory,
) -> None:
    evaluator = ReferenceKnowledgeDemandsEvaluator(google_api_key="k")
    evaluation = await evaluator.evaluate(ReferenceKnowledgeDemandsInput(text=TEXT, grade_level=9))
    assert isinstance(evaluation.result, ReferenceKnowledgeDemandsOutput)
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {
        "slightly_complex",
        "moderately_complex",
        "very_complex",
        "exceedingly_complex",
    }
    assert evaluation.result.details.detailed_summary[0].effect_on_complexity_dimension is not None
