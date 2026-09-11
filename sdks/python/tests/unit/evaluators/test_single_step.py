"""The single-step flow, tested on a synthetic contract so every branch is reachable."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx2
import openai
import pytest
import textstat
from pydantic import BaseModel

from learning_commons_evaluators import (
    AuthenticationError,
    EvaluationResult,
    InputValidationError,
    LLMOutputProcessingError,
    ModelOverride,
    Provider,
    read_outcome,
)
from learning_commons_evaluators.contracts.loader import Contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from tests.unit.conftest import ProviderFactory

STABLE_ID = "11111111-1111-1111-1111-111111111111"


def contract(**overrides: Any) -> Contract:
    raw: dict[str, Any] = {
        "evaluator": {
            "id": "demo.area.thing",
            "stable_id": STABLE_ID,
            "id_history": ["demo.area.old_thing"],
            "name": "Thing Evaluator",
            "description": "Demonstration contract.",
            # Deliberately wider than the input enum, which is the only way to tell which
            # of the two the class read.
            "supported_grades": ["3", "4", "5", "6"],
        },
        "input_schema": {
            "type": "object",
            "required": ["text", "grade_level"],
            "additionalProperties": False,
            "properties": {
                "text": {"type": "string", "minLength": 1},
                "grade_level": {"type": "string", "enum": ["3", "4", "5"]},
            },
        },
        "output_schema": {
            "type": "object",
            "required": ["verdict", "reasoning"],
            "properties": {"verdict": {"type": "string"}, "reasoning": {"type": "string"}},
        },
        "preprocessing": [
            {
                "id": "fk_score",
                "type": "computation",
                "kind": "flesch_kincaid_grade",
                "input": "text",
                "output": "fk_score",
                "implementation": {
                    "python": {
                        "library": "textstat",
                        "function": "flesch_kincaid_grade",
                        "post_transform": {"type": "round", "precision": 2},
                    }
                },
            }
        ],
        "steps": [
            {
                "id": "evaluate_thing",
                "type": "llm",
                "prompt": {
                    "messages": [
                        {"role": "system", "source_path": "system.txt"},
                        {"role": "user", "source_path": "user.txt"},
                    ],
                    "placeholders": {
                        "text": {"required": True, "source": "input"},
                        "grade_level": {"required": True, "source": "input"},
                        "fk_score": {"required": True, "source": "preprocessing.fk_score"},
                    },
                },
                "model": {"provider": "google", "name": "gemini-3-flash-preview"},
                "generation": {"temperature": 0.5},
                "parser": {"kind": "structured_output"},
            }
        ],
        "outcome": {"score": "verdict", "reasoning": "reasoning"},
        "documents": {
            "system.txt": "system: {text} at {grade_level} with {fk_score} {undeclared}",
            "user.txt": "user: {text} at {grade_level} with {fk_score}",
        },
    }
    raw.update(overrides)
    return Contract.model_validate(raw)


class ThingOutput(BaseModel):
    verdict: str
    reasoning: str


class ThingInput(BaseModel):
    text: str
    grade_level: int


def define(**overrides: Any) -> type[SingleStepEvaluator[ThingInput, ThingOutput]]:
    class ThingEvaluator(SingleStepEvaluator[ThingInput, ThingOutput]):
        contract = globals()["contract"](**overrides)
        input_model = ThingInput
        output_model = ThingOutput

    return ThingEvaluator


INPUT = {"text": "The cat sat on the mat.", "grade_level": "4"}
FK = textstat.flesch_kincaid_grade(INPUT["text"])


def _verdict(schema: type[BaseModel]) -> BaseModel:
    return schema.model_validate({"verdict": "clear", "reasoning": "because"})


@pytest.fixture
def providers() -> Any:
    from unittest.mock import patch

    factory = ProviderFactory(payload=_verdict)
    with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
        yield factory


class TestRefusesAContractItCannotRun:
    def test_names_the_step_the_convention_expects(self) -> None:
        steps = [
            {
                "id": "not_the_convention",
                "type": "llm",
                "model": {"provider": "google", "name": "m"},
                "prompt": {"messages": [], "placeholders": {}},
                "generation": {"temperature": 0},
                "parser": {"kind": "structured_output"},
            }
        ]
        with pytest.raises(LookupError, match='Step "evaluate_thing" not found in Thing Evaluator'):
            define(steps=steps)

    def test_refuses_a_placeholder_that_reads_another_step(self) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["steps"][0]["prompt"]["placeholders"]["extra"] = {
            "required": True,
            "source": "steps.other.output",
        }
        with pytest.raises(ValueError, match="reads another step"):
            define(**{k: raw[k] for k in ("steps",)})

    def test_refuses_preprocessing_without_a_python_computation(self) -> None:
        entry = {
            "id": "x",
            "type": "computation",
            "kind": "custom",
            "input": "text",
            "output": "x",
            "implementation": {"typescript": {"library": "l", "function": "f"}},
        }
        with pytest.raises(ValueError, match='Preprocessing "x".*no Python computation'):
            define(preprocessing=[entry])


class TestReadsBehaviourFromTheContract:
    def test_metadata(self) -> None:
        metadata = define().metadata
        assert metadata.id == "demo.area.thing"
        assert metadata.stable_id == STABLE_ID
        assert metadata.id_history == ("demo.area.old_thing",)
        assert metadata.name == "Thing Evaluator"
        assert metadata.supported_grades == ("3", "4", "5", "6")
        assert metadata.default_providers == (Provider.GOOGLE,)
        assert metadata.required_credentials == ()
        assert metadata.outcome is not None and metadata.outcome.score == "verdict"

    def test_builds_the_provider_the_step_declares(self, providers: ProviderFactory) -> None:
        define()(google_api_key="k", max_retries=1)
        config = providers.last.config
        assert (config.type, config.model, config.api_key, config.max_retries) == (
            Provider.GOOGLE,
            "gemini-3-flash-preview",
            "k",
            1,
        )

    async def test_sends_the_temperature_and_schema_the_contract_declares(
        self, providers: ProviderFactory
    ) -> None:
        await define()(google_api_key="k").evaluate(**INPUT)
        call = providers.last.calls[0]
        assert call["temperature"] == 0.5
        assert call["schema"] is ThingOutput

    async def test_renders_prompts_with_declared_placeholders_only(
        self, providers: ProviderFactory
    ) -> None:
        await define()(google_api_key="k").evaluate(**INPUT)
        messages = providers.last.calls[0]["messages"]
        fk = str(round(FK, 2)) if not round(FK, 2).is_integer() else str(int(round(FK, 2)))
        assert messages[0] == {
            "role": "system",
            "content": f"system: The cat sat on the mat. at 4 with {fk} {{undeclared}}",
        }
        assert messages[1] == {
            "role": "user",
            "content": f"user: The cat sat on the mat. at 4 with {fk}",
        }

    async def test_a_conditional_preprocessing_entry_only_runs_when_its_condition_holds(
        self, providers: ProviderFactory
    ) -> None:
        raw = contract().model_dump(by_alias=True)
        raw["preprocessing"][0]["condition"] = {"input": "grade_level", "in": ["3"]}
        raw["steps"][0]["prompt"]["placeholders"]["fk_score"]["required"] = False
        evaluator = define(preprocessing=raw["preprocessing"], steps=raw["steps"])(
            google_api_key="k"
        )
        await evaluator.evaluate(**INPUT)
        assert "{fk_score}" in providers.last.calls[0]["messages"][1]["content"]


class TestInputs:
    async def test_accepts_the_input_model_and_an_int_grade(
        self, providers: ProviderFactory
    ) -> None:
        await define()(google_api_key="k").evaluate(ThingInput(text="Hello there.", grade_level=4))
        assert " at 4 with" in providers.last.calls[0]["messages"][1]["content"]

    async def test_accepts_keyword_fields_with_an_int_grade(
        self, providers: ProviderFactory
    ) -> None:
        await define()(google_api_key="k").evaluate(text="Hello there.", grade_level=5)
        assert " at 5 with" in providers.last.calls[0]["messages"][1]["content"]

    async def test_rejects_both_forms_at_once(self, providers: ProviderFactory) -> None:
        with pytest.raises(TypeError, match="not both"):
            await define()(google_api_key="k").evaluate(
                ThingInput(text="t", grade_level=4), text="t"
            )

    @pytest.mark.parametrize(
        ("inputs", "message"),
        [
            ({"text": "t"}, "grade_level is required."),
            ({**INPUT, "grade_level": "6"}, 'Invalid grade_level "6". Accepted values: 3, 4, 5.'),
            ({**INPUT, "extra": 1}, 'Unknown input "extra"'),
            ({**INPUT, "text": "  "}, "text cannot be empty"),
        ],
    )
    async def test_validation_happens_before_any_call(
        self, providers: ProviderFactory, inputs: dict[str, Any], message: str
    ) -> None:
        evaluator = define()(google_api_key="k")
        with pytest.raises(InputValidationError, match=message):
            await evaluator.evaluate(**inputs)
        assert providers.last.calls == []

    def test_grades_are_validated_against_the_input_enum_not_supported_grades(
        self, providers: ProviderFactory
    ) -> None:
        # supported_grades says 6; the input schema does not. The schema decides (§4.2).
        with pytest.raises(InputValidationError, match='Invalid grade_level "6"'):
            define()(google_api_key="k").evaluate_sync(text="Hello there.", grade_level=6)


class TestEnvelope:
    async def test_three_fields(self, providers: ProviderFactory) -> None:
        evaluation = await define()(google_api_key="k").evaluate(**INPUT)
        assert isinstance(evaluation, EvaluationResult)
        assert evaluation.evaluator == "demo.area.thing"
        assert evaluation.result == ThingOutput(verdict="clear", reasoning="because")
        assert evaluation.metadata.model == "google:gemini-3-flash-preview"
        assert evaluation.metadata.token_usage.input_tokens == 7
        assert evaluation.metadata.token_usage.output_tokens == 3
        assert evaluation.metadata.processing_time_ms >= 0

    async def test_the_model_reflects_an_override(self, providers: ProviderFactory) -> None:
        override = ModelOverride(provider=Provider.OPENAI, model="gpt-4o-2024-11-20")
        evaluator = define()(openai_api_key="o", model_override=override)
        evaluation = await evaluator.evaluate(**INPUT)
        assert evaluation.metadata.model == "openai:gpt-4o-2024-11-20"

    async def test_read_outcome_reads_the_declared_fields(self, providers: ProviderFactory) -> None:
        evaluator = define()(google_api_key="k")
        evaluation = await evaluator.evaluate(**INPUT)
        outcome = read_outcome(evaluation, evaluator.metadata.outcome)
        assert (outcome.score, outcome.reasoning) == ("clear", "because")

    def test_evaluate_sync(self, providers: ProviderFactory) -> None:
        assert define()(google_api_key="k").evaluate_sync(**INPUT).result.verdict == "clear"

    async def test_evaluate_sync_refuses_a_running_loop(self, providers: ProviderFactory) -> None:
        with pytest.raises(RuntimeError, match="await evaluator.evaluate"):
            define()(google_api_key="k").evaluate_sync(**INPUT)


class TestFailures:
    async def test_provider_failures_are_classified_and_attributed(
        self, providers: ProviderFactory
    ) -> None:
        response = httpx2.Response(401, request=httpx2.Request("POST", "https://x"))
        providers.failures.append(openai.APIStatusError("nope", response=response, body=None))
        with pytest.raises(AuthenticationError) as exc_info:
            await define()(google_api_key="k").evaluate(**INPUT)
        assert exc_info.value.dependency == "google"
        assert exc_info.value.model == "gemini-3-flash-preview"

    async def test_output_failures_are_resampled_up_to_max_retries(
        self, providers: ProviderFactory
    ) -> None:
        providers.failures.extend(
            [LLMOutputProcessingError("bad"), LLMOutputProcessingError("bad")]
        )
        evaluation = await define()(google_api_key="k", max_retries=2).evaluate(**INPUT)
        assert evaluation.result.verdict == "clear"
        assert len(providers.last.calls) == 3

    async def test_output_failures_surface_once_the_budget_is_spent(
        self, providers: ProviderFactory
    ) -> None:
        providers.failures.append(LLMOutputProcessingError("bad"))
        with pytest.raises(LLMOutputProcessingError):
            await define()(google_api_key="k", max_retries=0).evaluate(**INPUT)

    async def test_logs_never_carry_the_input_text(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="learning_commons_evaluators"):
            await define()(google_api_key="k").evaluate(**INPUT)
        assert caplog.records
        for record in caplog.records:
            assert INPUT["text"] not in record.getMessage()
            assert INPUT["text"] not in str(vars(record))

    async def test_a_failure_is_logged_with_the_error_class(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            caplog.at_level(logging.ERROR, logger="learning_commons_evaluators"),
            pytest.raises(InputValidationError),
        ):
            await define()(google_api_key="k").evaluate(text="t")
        [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert record.error == "InputValidationError"  # type: ignore[attr-defined]
        assert record.evaluator == "demo.area.thing"  # type: ignore[attr-defined]


def test_the_loop_guard_is_the_only_sync_restriction() -> None:
    # Sanity: outside a loop asyncio.run is available to evaluate_sync.
    asyncio.run(asyncio.sleep(0))
