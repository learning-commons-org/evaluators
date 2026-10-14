"""Graphics Complexity: images after the text, labels, and model-only fields, against a fake provider.

The cases mirror the TypeScript SDK's ``graphics-complexity.test.ts``, so the two SDKs are
held to the same request and the same refusals.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from learning_commons_evaluators import (
    ConfigurationError,
    GraphicsComplexityEvaluator,
    GraphicsComplexityInput,
    GraphicsComplexityOutput,
    InputValidationError,
    Provider,
    read_outcome,
)
from learning_commons_evaluators.schemas.graphics.ela.graphics_complexity import (
    GraphicsComplexityResponse,
)
from tests.unit.conftest import FakeProvider, ProviderFactory

CONTRACT_DIR = Path(__file__).resolve().parents[7] / "evals/graphics/ela/graphics-complexity"
CONFIG = json.loads((CONTRACT_DIR / "config.json").read_text(encoding="utf-8"))
STEP = CONFIG["steps"][0]
CZERNY = [
    str(CONTRACT_DIR / "images" / name)
    for name in ("GUT-35601_czerny.png", "GUT-35601_czerny_2.png", "GUT-35601_czerny_3.png")
]

TEXT = "His name was Carl Czerny. Here is his picture."

RETURNED: dict[str, Any] = {
    "complexity_score": "slightly_complex",
    "reasoning": "Three captioned portraits that restate the text.",
    "details": {
        "detailed_summary": [],
        "adjustment_and_scaffolding": [],
        "recommended_use_cases": [],
    },
}

RESPONSE = GraphicsComplexityResponse.model_validate(
    {
        **RETURNED,
        "graphics": [
            {
                "label": f"Image {i}",
                "role": "supporting",
                "demand_notes": "A portrait.",
                "complexity": "slightly_complex",
            }
            for i in (1, 2, 3)
        ],
        "joint_reading": {
            "applies": False,
            "which": [],
            "complexity": None,
            "reasoning": "Each stands alone.",
        },
        "aggregation_rule": "highest_individual",
    }
)


def _payload(schema: type[BaseModel]) -> BaseModel:
    assert schema is GraphicsComplexityResponse
    return RESPONSE


@pytest.fixture
def providers() -> Iterator[ProviderFactory]:
    factory = ProviderFactory(payload=_payload)
    with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
        yield factory


def evaluator() -> GraphicsComplexityEvaluator:
    return GraphicsComplexityEvaluator(google_api_key="test-key", telemetry=False)


class TestConstructionAndMetadata:
    def test_requires_the_google_key(self) -> None:
        with pytest.raises(ConfigurationError, match="Missing required credential: google_api_key"):
            GraphicsComplexityEvaluator(google_api_key="", telemetry=False)

    def test_refuses_a_provider_that_does_not_declare_attachment_support(self) -> None:
        def text_only(config: Any) -> FakeProvider:
            return FakeProvider(config, _payload, supports_attachments=False)

        with (
            patch("learning_commons_evaluators.evaluators.base.create_provider", text_only),
            pytest.raises(ConfigurationError, match="does not declare support for attachments"),
        ):
            evaluator()

    def test_derives_identity_provider_grades_and_outcome_from_config_json(self) -> None:
        metadata = GraphicsComplexityEvaluator.metadata
        assert metadata.id == CONFIG["evaluator"]["id"]
        assert metadata.stable_id == CONFIG["evaluator"]["stable_id"]
        assert metadata.default_providers == (Provider.GOOGLE,)
        assert metadata.supported_grades == tuple(CONFIG["evaluator"]["supported_grades"])
        assert metadata.outcome is not None
        assert (metadata.outcome.score, metadata.outcome.reasoning) == (
            "complexity_score",
            "reasoning",
        )


class TestTheModelCall:
    async def test_attaches_every_image_after_the_text_in_image_paths_order(
        self, providers: ProviderFactory
    ) -> None:
        await evaluator().evaluate(text=TEXT, grade_level=4, image_paths=CZERNY)

        [call] = providers.calls
        assert [(a.data, a.media_type, a.position) for a in call["attachments"]] == [
            (Path(path).read_bytes(), "image/png", "after_text") for path in CZERNY
        ]
        for path in CZERNY:
            assert path not in call["messages"][1]["content"]

    async def test_renders_the_text_grade_flesch_kincaid_score_and_labels(
        self, providers: ProviderFactory
    ) -> None:
        await evaluator().evaluate(
            text=TEXT, grade_level=4, image_paths=CZERNY, figure_labels="Mother,Father ,  Czerny"
        )
        user = providers.calls[0]["messages"][1]["content"]
        assert f"Text to Evaluate - text: {TEXT}" in user
        assert "It is intended for grade 4" in user
        assert re.search(r"Flesch–Kincaid grade level: -?\d+(\.\d+)?\n", user)
        assert "Graphics in scope: Mother, Father, Czerny" in user
        assert not re.search(r"\{\w+\}", user)

    async def test_labels_the_images_image_1_to_n_when_figure_labels_is_omitted(
        self, providers: ProviderFactory
    ) -> None:
        await evaluator().evaluate(text=TEXT, grade_level=4, image_paths=CZERNY)
        user = providers.calls[0]["messages"][1]["content"]
        assert "Graphics in scope: Image 1, Image 2, Image 3" in user

    async def test_sends_the_system_prompt_verbatim_and_the_temperature_from_config_json(
        self, providers: ProviderFactory
    ) -> None:
        await evaluator().evaluate(text=TEXT, grade_level=4, image_paths=CZERNY)
        [call] = providers.calls
        assert call["messages"][0]["content"] == (CONTRACT_DIR / "system.txt").read_text(
            encoding="utf-8"
        )
        assert call["temperature"] == STEP["generation"]["temperature"]

    async def test_asks_the_model_for_the_model_only_fields_and_returns_without_them(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await evaluator().evaluate(text=TEXT, grade_level=4, image_paths=CZERNY)

        sent = providers.calls[0]["schema"]
        assert {"graphics", "joint_reading", "aggregation_rule"} <= set(sent.model_fields)
        assert isinstance(evaluation.result, GraphicsComplexityOutput)
        assert evaluation.result.model_dump() == RETURNED
        assert evaluation.evaluator == CONFIG["evaluator"]["id"]
        assert evaluation.metadata.token_usage.input_tokens > 0
        outcome = read_outcome(evaluation, GraphicsComplexityEvaluator.metadata.outcome)
        assert outcome.score == "slightly_complex"

    async def test_takes_the_input_model(self, providers: ProviderFactory) -> None:
        inputs = GraphicsComplexityInput(text=TEXT, grade_level=4, image_paths=CZERNY[:1])
        await evaluator().evaluate(inputs)
        assert "Graphics in scope: Image 1\n" in providers.calls[0]["messages"][1]["content"]


class TestInputValidation:
    async def reject(self, providers: ProviderFactory, match: str, **inputs: Any) -> None:
        with pytest.raises(InputValidationError, match=match):
            await evaluator().evaluate(**{"text": TEXT, "grade_level": 4, **inputs})
        assert providers.calls == [], "rejected before any model call"

    @pytest.mark.parametrize(
        ("labels", "message"),
        [
            ("Mother, Father", "received 2 for 3 images"),
            ("A, B, C, D", "received 4 for 3 images"),
            ("A, , C", "one distinct, non-empty label per image"),
            ("A, B, A", "one distinct, non-empty label per image"),
        ],
        ids=["too few", "too many", "a blank one", "a repeat"],
    )
    async def test_rejects_figure_labels_that_do_not_name_each_image_once(
        self, providers: ProviderFactory, labels: str, message: str
    ) -> None:
        await self.reject(providers, message, image_paths=CZERNY, figure_labels=labels)

    async def test_names_one_image_in_the_singular(self, providers: ProviderFactory) -> None:
        await self.reject(
            providers, "received 2 for 1 image.", image_paths=CZERNY[:1], figure_labels="A, B"
        )

    async def test_rejects_whitespace_only_figure_labels_as_any_blank_string_input(
        self, providers: ProviderFactory
    ) -> None:
        await self.reject(
            providers, "figure_labels cannot be empty", image_paths=CZERNY, figure_labels="  "
        )

    async def test_accepts_at_most_five_images_and_at_least_one(
        self, providers: ProviderFactory
    ) -> None:
        await self.reject(providers, "at most 5 items; received 6", image_paths=CZERNY * 2)
        await self.reject(providers, "at least 1 item; received 0", image_paths=[])

    async def test_rejects_a_grade_outside_3_to_12(self, providers: ProviderFactory) -> None:
        await self.reject(providers, 'Invalid grade_level "2"', grade_level=2, image_paths=CZERNY)

    async def test_names_the_image_that_cannot_be_read_by_its_position(
        self, providers: ProviderFactory
    ) -> None:
        await self.reject(
            providers,
            r"image_paths\[1\]: .* is not an accepted image",
            image_paths=[CZERNY[0], str(CONTRACT_DIR / "system.txt")],
        )
