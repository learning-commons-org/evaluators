"""Graphics Complexity against its contract's own fixtures, live.

Each case is a row of ``fixtures.json`` — a passage, its grade, the images under ``images/``
and their labels — with the rating it records as the expected result. This is the only place
the images-after-text request, the model-only response schema and the model's behaviour are
exercised together; the unit tests use a fake provider.

Judged as the TypeScript SDK's live test judges the same fixtures: the contract's tolerance
applies, so a rating one rubric step from the expected one passes, and
``more_context_needed`` has no neighbours. Each case gets up to three attempts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from learning_commons_evaluators import GraphicsComplexityEvaluator
from tests.integration.conftest import EVALS_ROOT, fixtures_for, keys_for
from tests.unit.conftest import resolve_attached_paths

ATTEMPTS = 3
CONTRACT_DIR: Path = EVALS_ROOT / "graphics/ela/graphics-complexity"
CONTRACT = GraphicsComplexityEvaluator.contract
FIXTURES = fixtures_for(CONTRACT)
RUBRIC = ["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"]


def within_tolerance(actual: str, expected: str) -> bool:
    if actual == expected:
        return True
    assert CONTRACT.fixtures is not None
    if not CONTRACT.fixtures.tolerance.get("allow_adjacent_levels"):
        return False
    if actual not in RUBRIC or expected not in RUBRIC:
        return False
    return abs(RUBRIC.index(actual) - RUBRIC.index(expected)) == 1


def test_there_are_fixtures_to_run() -> None:
    # Not marked: it guards against the live cases below passing vacuously.
    assert FIXTURES


@pytest.mark.integration
@pytest.mark.parametrize("case", FIXTURES, ids=lambda case: case["id"])
async def test_fixture(case: dict[str, Any]) -> None:
    evaluator = GraphicsComplexityEvaluator(**keys_for(CONTRACT), telemetry=False)
    inputs = resolve_attached_paths(CONTRACT, CONTRACT_DIR, case["input"])
    expected = case["expected"]["complexity_score"]
    model = CONTRACT.steps[0].model
    assert model is not None

    seen: list[str] = []
    for _ in range(ATTEMPTS):
        evaluation = await evaluator.evaluate(**inputs)
        result = evaluation.result
        seen.append(result.complexity_score)
        # The model-only working fields are asked for and never returned.
        assert sorted(result.model_dump()) == ["complexity_score", "details", "reasoning"]
        assert evaluation.metadata.model == f"{model.provider.value}:{model.name}"

        if within_tolerance(result.complexity_score, expected):
            return

    pytest.fail(f"{case['id']}: expected {expected} (±1) in {ATTEMPTS} attempts; saw {seen}")
