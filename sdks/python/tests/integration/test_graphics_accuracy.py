"""Graphics Accuracy against its contract's own fixtures, live.

Each case is a row of ``fixtures.json`` — an image under ``images/`` plus the claim the
evaluator receives — with the verdict it records as the expected result. This is the only
place the image path, the provider's multimodal request and the model's behaviour are
exercised together; the unit tests use a fake provider.

Judged as the TypeScript SDK's live test judges the same fixtures: ``is_correct`` strictly,
and ``basis`` wherever the fixture pins it, since the reasons for a false verdict
(``contradicted``, ``unverified``, ``defective``) imply different actions. Each case gets up
to three attempts, since a single call can land on the wrong side of a hard item.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from learning_commons_evaluators import GraphicsAccuracyEvaluator
from tests.integration.conftest import EVALS_ROOT, fixtures_for, keys_for

ATTEMPTS = 3
CONTRACT_DIR: Path = EVALS_ROOT / "graphics/math/graphics-accuracy"
CONTRACT = GraphicsAccuracyEvaluator.contract
FIXTURES = fixtures_for(CONTRACT)

#: The sentence the output schema makes the model write before it sets the verdict; it is
#: what makes the verdict auditable, so every parsed response must carry it.
X_VS_Y = re.compile(
    r"The image yields .*the specification states .*therefore is_correct", re.I | re.S
)


def test_there_are_fixtures_to_run() -> None:
    # Not marked: it guards against the live cases below passing vacuously.
    assert FIXTURES


@pytest.mark.integration
@pytest.mark.parametrize("case", FIXTURES, ids=lambda case: case["id"])
async def test_fixture(case: dict[str, Any]) -> None:
    evaluator = GraphicsAccuracyEvaluator(**keys_for(CONTRACT), telemetry=False)
    image_paths = [str(CONTRACT_DIR / path) for path in case["input"]["image_paths"]]
    expected = case["expected"]
    model = CONTRACT.steps[0].model
    assert model is not None

    seen: list[dict[str, Any]] = []
    for _ in range(ATTEMPTS):
        evaluation = await evaluator.evaluate(image_paths=image_paths, claim=case["input"]["claim"])
        result = evaluation.result
        seen.append(
            {
                "is_correct": result.is_correct,
                "basis": result.basis,
                "correction": result.correction,
            }
        )
        assert X_VS_Y.search(result.reasoning), f"{case['id']}: no X-vs-Y sentence"
        assert evaluation.metadata.model == f"{model.provider.value}:{model.name}"
        assert evaluation.metadata.token_usage.input_tokens > 0

        verdict_ok = result.is_correct == expected["is_correct"]
        basis_ok = "basis" not in expected or result.basis == expected["basis"]
        if verdict_ok and basis_ok:
            return

    pinned = f" ({expected['basis']})" if "basis" in expected else ""
    pytest.fail(
        f"{case['id']}: expected is_correct={expected['is_correct']}{pinned} in {ATTEMPTS} "
        f"attempts; saw {seen}"
    )
