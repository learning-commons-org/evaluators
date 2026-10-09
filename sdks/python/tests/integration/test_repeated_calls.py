"""One evaluator called repeatedly with ``evaluate_sync``, against the real providers.

Skipped unless ``RUN_INTEGRATION_TESTS=1`` and the keys a case needs are set. Each
``evaluate_sync`` runs on an event loop of its own, so a client an evaluator kept from one
call would hand the next a connection whose loop is gone, and every second call would fail
with "Event loop is closed" (DSCR-2424). The unit tests hold the adapters to building a
client per call against loop-bound fakes; this is the same check against the real vendor
SDKs, whose pooling is what the fakes stand in for.

One evaluator per provider, on its default model, plus the Knowledge Graph through Math
Standards Alignment. Retries are off: with them on, a retryable failure on the second call
is absorbed by the retry, which is how the Anthropic case hid this bug.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import Any

import pytest

from learning_commons_evaluators import (
    GradeLevelAppropriatenessEvaluator,
    MathStandardsAlignmentEvaluator,
    ToneAppropriatenessEvaluator,
)
from learning_commons_evaluators.dependencies.knowledge_graph import KnowledgeGraphClient
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.schemas.kg_taxonomy import AcademicSubject, Jurisdiction

pytestmark = pytest.mark.integration

#: Enough calls to cross from a fresh client to a reused one twice.
CALLS = 3


def _keys(*names: str) -> dict[str, str]:
    """The named keys from the environment, as config fields, or skip."""
    keys: dict[str, str] = {}
    for name in names:
        value = os.environ.get(name)
        if not value:
            pytest.skip(f"{name} is not set")
        keys[name.lower()] = value
    return keys


def _standard_uuid(api_key: str) -> str:
    async def lookup() -> str:
        async with KnowledgeGraphClient(api_key) as kg:
            matches = await kg.search_standards(
                "3.MD.C.7.D",
                jurisdiction=Jurisdiction.MULTI_STATE,
                academic_subject=AcademicSubject.MATHEMATICS,
            )
        return matches[0].case_identifier_uuid

    return asyncio.run(lookup())


def _grade_level() -> tuple[BaseEvaluator, dict[str, Any]]:
    evaluator = GradeLevelAppropriatenessEvaluator(
        **_keys("GOOGLE_API_KEY"), max_retries=0, telemetry=False
    )
    return evaluator, {"text": "The cat's out of the bag now."}


def _tone() -> tuple[BaseEvaluator, dict[str, Any]]:
    evaluator = ToneAppropriatenessEvaluator(
        **_keys("OPENAI_API_KEY"), max_retries=0, telemetry=False
    )
    return evaluator, {
        "student_text": "Dogs make better pets than cats because they are loyal.",
        "feedback_text": "Good start. Can you add an example that shows a dog being loyal?",
    }


def _math_standards() -> tuple[BaseEvaluator, dict[str, Any]]:
    keys = _keys("ANTHROPIC_API_KEY", "LEARNING_COMMONS_API_KEY")
    evaluator = MathStandardsAlignmentEvaluator(
        anthropic_api_key=keys["anthropic_api_key"],
        learning_commons_api_key=keys["learning_commons_api_key"],
        max_retries=0,
        telemetry=False,
    )
    return evaluator, {
        "question": (
            "A garden is made of two rectangles, 3 m by 4 m and 2 m by 5 m, that do not "
            "overlap. What is the total area?"
        ),
        "case_identifier_uuid": _standard_uuid(keys["learning_commons_api_key"]),
    }


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(_grade_level, id="google"),
        pytest.param(_tone, id="openai"),
        pytest.param(_math_standards, id="anthropic+knowledge-graph"),
    ],
)
def test_repeated_evaluate_sync_calls_on_one_evaluator_all_succeed(
    build: Callable[[], tuple[BaseEvaluator, dict[str, Any]]],
) -> None:
    evaluator, inputs = build()
    try:
        for _ in range(CALLS):
            evaluator.evaluate_sync(**inputs)
    finally:
        evaluator.close()
