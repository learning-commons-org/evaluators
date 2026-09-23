"""Math Standards Alignment against the real Knowledge Graph and a real model.

Skipped unless ``RUN_INTEGRATION_TESTS=1`` and both keys are set. The unit tests cover the
evaluator's logic with the Knowledge Graph injected; what only a live run can tell us is
that these codes still resolve in these jurisdictions, that the standards still carry the
components the judgement is made against, and that the model still answers in the shape
the step declares.

The cases are the contract's own fixtures, which reach this evaluator unchanged, plus a
state-framework case the fixtures do not cover.
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


async def test_the_canonical_match_aligns(evaluator: MathStandardsAlignmentEvaluator) -> None:
    evaluation = await evaluator.evaluate(
        question=L_SHAPED_PLAYGROUND, statement_code="3.MD.C.7.d", jurisdiction="Multi-State"
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
    assert all(component.reasoning for component in result.learning_components)
    assert evaluation.evaluator == MathStandardsAlignmentEvaluator.metadata.id
    assert evaluation.metadata.model == "anthropic:claude-haiku-4-5-20251001"
    assert evaluation.metadata.token_usage.output_tokens > 0


async def test_an_unrelated_question_aligns_to_nothing(
    evaluator: MathStandardsAlignmentEvaluator,
) -> None:
    evaluation = await evaluator.evaluate(
        question=UNRELATED, statement_code="3.MD.C.7.d", grade_level="3"
    )

    assert evaluation.result.total_count > 0, "the standard should still carry components"
    assert evaluation.result.aligned_count == 0, [
        (c.identifier, c.reasoning) for c in evaluation.result.learning_components if c.aligned
    ]


async def test_a_parent_standard_resolves_to_its_own_components(
    evaluator: MathStandardsAlignmentEvaluator,
) -> None:
    # The parent of the standard above. A different code has to reach a different set of
    # components, not the child's.
    evaluation = await evaluator.evaluate(
        question=L_SHAPED_PLAYGROUND, statement_code="3.MD.C.7", grade_level="3"
    )

    assert evaluation.result.statement_code.upper() == "3.MD.C.7"
    assert evaluation.result.total_count > 0


async def test_a_state_framework_is_resolved_under_its_own_spelling(
    evaluator: MathStandardsAlignmentEvaluator,
) -> None:
    # Ohio adopted Common Core and drops the cluster letter, so the same standard is
    # 3.MD.7 there. This is what `jurisdiction` is for, and the components it reaches are
    # the same ones the Multi-State copy carries.
    evaluation = await evaluator.evaluate(
        question=L_SHAPED_PLAYGROUND, statement_code="3.MD.7", grade_level="3", jurisdiction="Ohio"
    )

    assert evaluation.result.statement_code.upper() == "3.MD.7"
    assert evaluation.result.total_count > 0


async def test_a_code_that_names_nothing_is_the_callers_error(
    evaluator: MathStandardsAlignmentEvaluator,
) -> None:
    from learning_commons_evaluators import StandardNotFoundError

    with pytest.raises(StandardNotFoundError):
        await evaluator.evaluate(question=UNRELATED, statement_code="3.ZZ.Q.99")


async def test_it_reports_no_single_score(evaluator: MathStandardsAlignmentEvaluator) -> None:
    # The contract declares no outcome, live or otherwise.
    evaluation = await evaluator.evaluate(question=L_SHAPED_PLAYGROUND, statement_code="3.MD.C.7")
    assert read_outcome(evaluation, evaluator.metadata.outcome).score is None
