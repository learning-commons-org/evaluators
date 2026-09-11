"""Every registered evaluator against its contract's fixtures, live.

Judged the way the TypeScript SDK's integration tests judge the same fixtures: each case
gets up to three attempts and passes on the first exact match; if none arrives, a verdict
one rubric step away is accepted where the scale has adjacency (complexity levels and grade
bands), since the models run at the temperature the contract pins and a fixture records
one expert label, not a distribution.
"""

from __future__ import annotations

from typing import Any

import pytest

from learning_commons_evaluators import read_outcome
from learning_commons_evaluators.evaluators.registry import EVALUATORS
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.student_facing_text.ela_reading.grade_level_appropriateness import (
    GradeBand,
)
from tests.integration.conftest import fixtures_for, keys_for

ATTEMPTS = 3

COMPLEXITY_ORDER = ["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"]
GRADE_BAND_ORDER = list(GradeBand.__args__)  # type: ignore[attr-defined]

CASES = [
    pytest.param(evaluator, case, id=f"{evaluator.metadata.slug}/{case['id']}")
    for evaluator in EVALUATORS
    for case in fixtures_for(evaluator.contract)
]


def _adjacent(actual: str | None, expected: str) -> bool:
    if actual is None:
        return False
    for scale in (COMPLEXITY_ORDER, GRADE_BAND_ORDER):
        if actual in scale and expected in scale:
            return abs(scale.index(actual) - scale.index(expected)) <= 1
    return False


@pytest.mark.integration
@pytest.mark.parametrize(("evaluator", "case"), CASES)
async def test_fixture(evaluator: type[SingleStepEvaluator], case: dict[str, Any]) -> None:
    contract = evaluator.contract
    assert contract.outcome is not None
    instance = evaluator(**keys_for(contract), telemetry=False)
    expected = str(case["expected"][contract.outcome.score])

    verdicts: list[str | None] = []
    for _ in range(ATTEMPTS):
        evaluation = await instance.evaluate(**case["input"])
        assert evaluation.evaluator == contract.evaluator.id
        assert evaluation.metadata.model.startswith(f"{contract.providers[0].value}:")
        assert evaluation.metadata.token_usage.output_tokens > 0
        outcome = read_outcome(evaluation, evaluator.metadata.outcome)
        verdicts.append(outcome.score)
        if outcome.score == expected:
            return

    assert _adjacent(verdicts[-1], expected), (
        f"{case['id']}: expected {expected}, got {verdicts} over {ATTEMPTS} attempts. "
        f"Reasoning: {outcome.reasoning[:300]}"
    )
