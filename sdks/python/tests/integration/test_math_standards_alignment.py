"""Math Standards Alignment against the real Knowledge Graph and a real model.

Skipped unless ``RUN_INTEGRATION_TESTS=1`` and both keys are set. The unit tests cover the
evaluator's logic with the Knowledge Graph injected; what only a live run can tell us is
that the standard still resolves, still carries the components the judgement is made
against, and that the model still answers in the shape the step declares.

The fixtures under ``evals/`` are keyed by statement code, which this release does not
take (DSCR-2190), so the cases below carry the UUID each of those codes resolves to.
Both are Common Core standards that have been stable for years.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest

from learning_commons_evaluators import read_outcome
from learning_commons_evaluators.evaluators.academic_standards_alignment.mathematics.math_standards_alignment import (
    MathStandardsAlignmentEvaluator,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (os.environ.get("LEARNING_COMMONS_API_KEY") and os.environ.get("ANTHROPIC_API_KEY")),
        reason="set LEARNING_COMMONS_API_KEY and ANTHROPIC_API_KEY to run this live",
    ),
]

#: Multi-State (CCSS) 3.MD.C.7.d -- "Recognize area as additive", three learning components.
RECTILINEAR_AREA = "6ba25656-d7cc-11e8-824f-0242ac160002"
#: Multi-State (CCSS) 3.MD.C.7 -- the parent standard, one learning component.
RELATE_AREA = "6ba04403-d7cc-11e8-824f-0242ac160002"

L_SHAPED_PLAYGROUND = (
    "A playground is shaped like an L. One part is a rectangle that is 8 feet long and 3 "
    "feet wide. Attached to it is another rectangle that is 4 feet long and 2 feet wide, "
    "with no overlap. What is the total area of the playground in square feet?"
)
UNRELATED = "What is 12 + 7?"


@pytest.fixture
async def evaluator() -> AsyncIterator[MathStandardsAlignmentEvaluator]:
    instance = MathStandardsAlignmentEvaluator(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        learning_commons_api_key=os.environ["LEARNING_COMMONS_API_KEY"],
        max_retries=2,
        telemetry=False,
    )
    try:
        yield instance
    finally:
        await instance.aclose()


async def test_the_canonical_match_aligns(
    evaluator: MathStandardsAlignmentEvaluator,
) -> None:
    evaluation = await evaluator.evaluate(
        question=L_SHAPED_PLAYGROUND, case_identifier_uuid=RECTILINEAR_AREA
    )

    result = evaluation.result
    assert result.statement_code.upper() == "3.MD.C.7.D"
    # Three components today. Asserted as a floor rather than an equality: the Knowledge
    # Graph may author more, and that is not a regression in this SDK.
    assert result.total_count >= 3
    assert len(result.learning_components) == result.total_count
    assert result.aligned_count > 0, [
        (component.identifier, component.reasoning) for component in result.learning_components
    ]
    # Every component came back judged, with the identifier it was sent under.
    assert all(component.reasoning for component in result.learning_components)
    assert evaluation.evaluator == MathStandardsAlignmentEvaluator.metadata.id
    assert evaluation.metadata.model == "anthropic:claude-haiku-4-5-20251001"
    assert evaluation.metadata.token_usage.output_tokens > 0


async def test_an_unrelated_question_aligns_to_nothing(
    evaluator: MathStandardsAlignmentEvaluator,
) -> None:
    evaluation = await evaluator.evaluate(question=UNRELATED, case_identifier_uuid=RECTILINEAR_AREA)

    assert evaluation.result.total_count > 0, "the standard should still carry components"
    assert evaluation.result.aligned_count == 0, [
        (c.identifier, c.reasoning) for c in evaluation.result.learning_components if c.aligned
    ]


async def test_a_parent_standard_resolves_and_is_judged(
    evaluator: MathStandardsAlignmentEvaluator,
) -> None:
    # The parent of the standard above, with its own components: a different UUID has to
    # reach a different set, not the child's.
    evaluation = await evaluator.evaluate(
        question=L_SHAPED_PLAYGROUND, case_identifier_uuid=RELATE_AREA
    )

    assert evaluation.result.statement_code.upper() == "3.MD.C.7"
    assert evaluation.result.total_count > 0


async def test_it_reports_no_single_score(evaluator: MathStandardsAlignmentEvaluator) -> None:
    # The contract declares no outcome, live or otherwise.
    evaluation = await evaluator.evaluate(
        question=L_SHAPED_PLAYGROUND, case_identifier_uuid=RELATE_AREA
    )
    assert read_outcome(evaluation, evaluator.metadata.outcome).score is None
