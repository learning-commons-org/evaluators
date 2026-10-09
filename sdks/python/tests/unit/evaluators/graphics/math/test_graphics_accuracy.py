"""Graphics Accuracy: the contract's image path, claim, and verdict, against a fake provider."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from learning_commons_evaluators import (
    ConfigurationError,
    GraphicsAccuracyEvaluator,
    GraphicsAccuracyInput,
    GraphicsAccuracyOutput,
    InputValidationError,
    Provider,
    compose_graphics_accuracy_claim,
    read_outcome,
)
from tests.unit.conftest import ProviderFactory

CONTRACT_DIR = Path(__file__).resolve().parents[7] / "evals/graphics/math/graphics-accuracy"
CONFIG = json.loads((CONTRACT_DIR / "config.json").read_text(encoding="utf-8"))
INPUT_SCHEMA = json.loads((CONTRACT_DIR / "input_schema.json").read_text(encoding="utf-8"))
STEP = CONFIG["steps"][0]
APPLES = CONTRACT_DIR / "images/apples-in-baskets.png"

QUESTION = "How many apples are in the three baskets altogether?"

PAYLOAD = GraphicsAccuracyOutput(
    observed="Three baskets holding 4, 5 and 3 apples.",
    defects=[],
    reasoning=(
        "4 + 5 + 3 = 12. The image yields 12; the specification states 12; "
        "therefore is_correct = true."
    ),
    errors=[],
    correction="12",
    basis="supported",
    is_correct=True,
)


def _payload(schema: type[BaseModel]) -> BaseModel:
    assert schema is GraphicsAccuracyOutput
    return PAYLOAD


@pytest.fixture
def providers() -> Any:
    from unittest.mock import patch

    factory = ProviderFactory(payload=_payload)
    with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
        yield factory


def evaluator(**overrides: Any) -> GraphicsAccuracyEvaluator:
    return GraphicsAccuracyEvaluator(google_api_key="test-key", telemetry=False, **overrides)


class TestConstruction:
    def test_requires_the_google_key(self) -> None:
        with pytest.raises(ConfigurationError, match="Missing required credential: google_api_key"):
            GraphicsAccuracyEvaluator(google_api_key="", telemetry=False)


class TestMetadata:
    def test_identity_comes_from_config_json(self) -> None:
        metadata = GraphicsAccuracyEvaluator.metadata
        assert metadata.id == CONFIG["evaluator"]["id"]
        assert metadata.stable_id == CONFIG["evaluator"]["stable_id"]
        assert metadata.name == CONFIG["evaluator"]["name"]
        assert metadata.description == CONFIG["evaluator"]["description"]

    def test_is_google_only_as_the_contract_declares(self) -> None:
        assert GraphicsAccuracyEvaluator.metadata.default_providers == (Provider.GOOGLE,)

    def test_declares_k_through_12(self) -> None:
        assert GraphicsAccuracyEvaluator.metadata.supported_grades == tuple(
            CONFIG["evaluator"]["supported_grades"]
        )

    def test_names_is_correct_as_the_score_and_reasoning_as_the_reasoning(self) -> None:
        outcome = GraphicsAccuracyEvaluator.metadata.outcome
        assert outcome is not None
        assert (outcome.score, outcome.reasoning) == ("is_correct", "reasoning")


class TestComposeClaim:
    def test_produces_the_measured_claim_text_and_trims_its_parts(self) -> None:
        assert (
            compose_graphics_accuracy_claim(f" {QUESTION} ", " 12 ")
            == f'Question: "{QUESTION}" The answer is 12.'
        )

    def test_matches_the_form_the_contract_documents_for_the_claim_input(self) -> None:
        # The contract's ``claim`` description is the canonical statement of the format; the
        # helper must not drift from it, or callers following the docs and callers using the
        # helper would send different text.
        documented = re.search(
            r'`(Question: "<question>" The answer is <answer>\.)`',
            INPUT_SCHEMA["properties"]["claim"]["description"],
        )
        assert documented is not None, "claim description names the question + answer form"
        expected = documented[1].replace("<question>", QUESTION).replace("<answer>", "12")
        assert compose_graphics_accuracy_claim(QUESTION, "12") == expected

    def test_refuses_a_blank_question_or_answer_which_would_be_judged_as_a_wrong_image(
        self,
    ) -> None:
        # As the TypeScript helper does: the question is checked first, then the answer.
        with pytest.raises(InputValidationError, match="the answer is blank"):
            compose_graphics_accuracy_claim(QUESTION, "")
        with pytest.raises(InputValidationError, match="the answer is blank"):
            compose_graphics_accuracy_claim(QUESTION, "  ")
        with pytest.raises(InputValidationError, match="the question is blank"):
            compose_graphics_accuracy_claim("", "12")
        with pytest.raises(InputValidationError, match="the question is blank"):
            compose_graphics_accuracy_claim(" \n ", " ")


class TestTheModelCall:
    async def test_sends_the_image_as_an_attachment_and_the_claim_as_the_user_text(
        self, providers: ProviderFactory
    ) -> None:
        claim = compose_graphics_accuracy_claim(QUESTION, "12")
        await evaluator().evaluate(image_paths=[str(APPLES)], claim=claim)

        [call] = providers.calls
        system, user = call["messages"]
        assert (system["role"], user["role"]) == ("system", "user")
        assert claim in user["content"]
        assert "{claim}" not in user["content"]
        # The path is an input, not prompt text; it must never reach the model.
        assert str(APPLES) not in user["content"]
        [image] = call["attachments"]
        assert image.data == APPLES.read_bytes()
        assert image.media_type == "image/png"

    async def test_sends_the_system_prompt_verbatim_from_the_contract(
        self, providers: ProviderFactory
    ) -> None:
        await evaluator().evaluate(image_paths=[str(APPLES)], claim="The chart shows 12 apples.")
        system = providers.calls[0]["messages"][0]["content"]
        assert system == (CONTRACT_DIR / "system.txt").read_text(encoding="utf-8")

    async def test_omits_the_temperature_as_the_contract_declares(
        self, providers: ProviderFactory
    ) -> None:
        assert STEP["generation"]["temperature"] is None
        await evaluator().evaluate(image_paths=[str(APPLES)], claim="The chart shows 12 apples.")
        assert providers.calls[0]["temperature"] is None

    async def test_takes_the_input_model(self, providers: ProviderFactory) -> None:
        inputs = GraphicsAccuracyInput(image_paths=[str(APPLES)], claim="12 apples.")
        await evaluator().evaluate(inputs)
        assert len(providers.calls[0]["attachments"]) == 1

    async def test_maps_the_response_onto_the_envelope(self, providers: ProviderFactory) -> None:
        evaluation = await evaluator().evaluate(
            image_paths=[str(APPLES)], claim=compose_graphics_accuracy_claim(QUESTION, "12")
        )
        assert evaluation.evaluator == CONFIG["evaluator"]["id"]
        assert evaluation.result == PAYLOAD
        assert evaluation.result.basis == "supported"
        assert evaluation.metadata.model == f"{STEP['model']['provider']}:{STEP['model']['name']}"
        # Rendered as the TypeScript SDK renders it, String(true), so reports agree.
        assert read_outcome(evaluation, GraphicsAccuracyEvaluator.metadata.outcome).score == "true"


class TestInputValidation:
    async def reject(self, providers: ProviderFactory, match: str, **inputs: Any) -> None:
        with pytest.raises(InputValidationError, match=match):
            await evaluator().evaluate(**inputs)
        assert providers.calls == [], "rejected before any model call"

    async def test_rejects_a_missing_claim(self, providers: ProviderFactory) -> None:
        await self.reject(providers, "claim is required", image_paths=[str(APPLES)])

    async def test_rejects_a_whitespace_only_claim(self, providers: ProviderFactory) -> None:
        await self.reject(providers, "cannot be empty", image_paths=[str(APPLES)], claim="   ")

    async def test_rejects_a_single_path_passed_as_a_string(
        self, providers: ProviderFactory
    ) -> None:
        await self.reject(
            providers, "image_paths must be an array", image_paths=str(APPLES), claim="x"
        )

    async def test_rejects_no_images_and_more_than_one(self, providers: ProviderFactory) -> None:
        await self.reject(providers, "at least 1 item; received 0", image_paths=[], claim="x")
        await self.reject(
            providers,
            "at most 1 item; received 2",
            image_paths=[str(APPLES), str(APPLES)],
            claim="x",
        )

    async def test_rejects_a_whitespace_only_path_before_reading_it(
        self, providers: ProviderFactory
    ) -> None:
        await self.reject(
            providers, r"image_paths\[0\] cannot be empty", image_paths=["   "], claim="x"
        )

    async def test_rejects_an_unknown_input_so_a_single_path_shape_fails_loudly(
        self, providers: ProviderFactory
    ) -> None:
        await self.reject(providers, 'Unknown input "image"', image=str(APPLES), claim="x")

    async def test_rejects_an_image_path_that_does_not_exist(
        self, providers: ProviderFactory
    ) -> None:
        missing = str(CONTRACT_DIR / "images/nope.png")
        await self.reject(
            providers, r"image_paths\[0\]: could not read file", image_paths=[missing], claim="x"
        )

    async def test_rejects_a_file_that_is_not_an_image(self, providers: ProviderFactory) -> None:
        await self.reject(
            providers,
            "not an accepted image",
            image_paths=[str(CONTRACT_DIR / "system.txt")],
            claim="x",
        )

    async def test_enforces_the_contracts_edge_bound(
        self, providers: ProviderFactory, tmp_path: Path
    ) -> None:
        from PIL import Image

        too_wide = tmp_path / "too-wide.png"
        Image.new("RGB", (3000, 100), (255, 255, 255)).save(too_wide, "PNG")
        await self.reject(providers, "3000×100 px", image_paths=[str(too_wide)], claim="x")
