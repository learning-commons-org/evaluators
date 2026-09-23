"""Organizational Structure: the one evaluator in the family whose contract pins temperature 1."""

from __future__ import annotations

import textstat

from learning_commons_evaluators import (
    OrganizationalStructureEvaluator,
    OrganizationalStructureInput,
    OrganizationalStructureOutput,
    Provider,
    read_outcome,
)
from learning_commons_evaluators.features import format_number
from tests.unit.conftest import ProviderFactory

TEXT = "Trees are important plants that grow in many parts of the world. They have roots."


def test_metadata_is_the_contracts() -> None:
    metadata = OrganizationalStructureEvaluator.metadata
    assert metadata.id == "text_complexity.ela_reading.organizational_structure"
    assert metadata.id_history == ("literacy.gla.organizational_structure",)
    assert metadata.default_providers == (Provider.GOOGLE,)
    assert metadata.supported_grades == tuple(str(g) for g in range(3, 13))


async def test_computes_and_binds_fk_score_at_the_contracts_temperature(
    providers: ProviderFactory,
) -> None:
    # Temperature 1 here where the family's other three pin 0, so it is asserted rather
    # than left to the conformance sweep.
    evaluator = OrganizationalStructureEvaluator(google_api_key="k")
    await evaluator.evaluate(text=TEXT, grade_level=5)
    [system, user] = providers.last.calls[0]["messages"]
    fk = format_number(round(textstat.flesch_kincaid_grade(TEXT), 2))
    assert system["content"] == evaluator.contract.document("system.txt")
    assert user["content"] == f"Analyze:\nText: {TEXT}\nGrade: 5\nFK Score: {fk}"
    assert providers.last.calls[0]["temperature"] == 1


async def test_returns_a_verdict_alongside_the_instructional_details(
    providers: ProviderFactory,
) -> None:
    evaluator = OrganizationalStructureEvaluator(google_api_key="k")
    evaluation = await evaluator.evaluate(OrganizationalStructureInput(text=TEXT, grade_level=8))
    assert isinstance(evaluation.result, OrganizationalStructureOutput)
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {
        "slightly_complex",
        "moderately_complex",
        "very_complex",
        "exceedingly_complex",
    }
    # The verdict travels with a details payload; a caller reads the three lists off it.
    details = evaluation.result.details
    assert details.detailed_summary[0].factor is not None
    assert details.adjustment_and_scaffolding[0].scaffolding_need is not None
    assert details.recommended_use_cases[0].opportunity is not None
