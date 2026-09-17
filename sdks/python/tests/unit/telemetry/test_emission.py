"""One event per evaluation, from the base class, for every evaluator the SDK ships.

The checks that matter here are the ones no single evaluator's suite can make: that an
evaluator added later reports without code of its own, that a failure reports as loudly as a
success, and that nothing an evaluation was given ever reaches the wire.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import pytest

from learning_commons_evaluators import (
    EvaluatorConfig,
    InputValidationError,
    ModelOverride,
    Provider,
    PurposeClarityEvaluator,
    SentenceStructureEvaluator,
    TelemetryOptions,
    __version__,
)
from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.errors import RateLimitError
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.inputs import primary_text_field
from learning_commons_evaluators.evaluators.multi_step import MultiStepEvaluator
from learning_commons_evaluators.evaluators.registry import EVALUATORS
from learning_commons_evaluators.telemetry import client as telemetry_client
from tests.conftest import EventSink
from tests.unit.conftest import ProviderFactory

EVALS_ROOT = Path(__file__).resolve().parents[5] / "evals"

#: Every registered evaluator, named by its registry id.
EACH_EVALUATOR = pytest.mark.parametrize("evaluator", EVALUATORS, ids=lambda e: e.metadata.id)


def fixture_input(evaluator: type[BaseEvaluator]) -> dict[str, Any]:
    """The first fixture case's inputs for an evaluator, as a caller would pass them."""
    contract = load_contract(evaluator.metadata.id)
    directory = EVALS_ROOT.joinpath(
        *(segment.replace("_", "-") for segment in contract.evaluator.id.split("."))
    )
    path = (
        contract.fixtures.path if contract.fixtures and contract.fixtures.path else "fixtures.json"
    )
    return dict(json.loads((directory / path).read_text(encoding="utf-8"))[0]["input"])


def construct(evaluator: type[BaseEvaluator], **overrides: Any) -> BaseEvaluator:
    keys = {f"{p.value}_api_key": "test-key" for p in evaluator.metadata.default_providers}
    return evaluator(**keys, **overrides)


def steps_planned(evaluator: type[BaseEvaluator], inputs: Mapping[str, Any]) -> list[str]:
    """The step ids these inputs run, read off the contract rather than the evaluator."""
    contract = load_contract(evaluator.metadata.id)
    if not issubclass(evaluator, MultiStepEvaluator):
        return [contract.steps[0].id]
    values = {key: str(value) for key, value in inputs.items()}
    return [
        step.id for step in contract.steps if step.condition is None or step.condition.holds(values)
    ]


class TestEveryEvaluatorReports:
    """Parametrized over the registry, so a later phase cannot add a silent evaluator."""

    @EACH_EVALUATOR
    async def test_a_successful_evaluation_emits_one_event(
        self, providers: ProviderFactory, event_sink: EventSink, evaluator: type[BaseEvaluator]
    ) -> None:
        inputs = fixture_input(evaluator)
        await construct(evaluator).evaluate(**inputs)

        [event] = event_sink.events()
        assert event["evaluator_type"] == evaluator.metadata.id
        assert event["status"] == "success"
        assert event["sdk_version"] == f"learning-commons-evaluators-python-{__version__}"
        assert event["latency_ms"] >= 0
        assert "error_code" not in event
        # One stage per step the contract plans for these inputs, in run order.
        stages = event["metadata"]["stage_details"]
        assert [stage["stage"] for stage in stages] == steps_planned(evaluator, inputs)
        assert event["token_usage"] == {
            "input_tokens": sum(s["token_usage"]["input_tokens"] for s in stages),
            "output_tokens": sum(s["token_usage"]["output_tokens"] for s in stages),
        }
        # The model that answered last, which is what the envelope's model ends with too.
        assert event["provider"] == stages[-1]["provider"]

    @EACH_EVALUATOR
    async def test_a_failed_evaluation_emits_one_event_naming_the_error(
        self, providers: ProviderFactory, event_sink: EventSink, evaluator: type[BaseEvaluator]
    ) -> None:
        providers.failures.append(RateLimitError("slow down", dependency="openai"))
        with pytest.raises(RateLimitError):
            await construct(evaluator).evaluate(**fixture_input(evaluator))

        [event] = event_sink.events()
        assert event["status"] == "error"
        assert event["error_code"] == "RateLimitError"
        assert event["evaluator_type"] == evaluator.metadata.id
        # The first step failed, so nothing completed and nothing was spent.
        assert "token_usage" not in event
        assert "metadata" not in event

    @EACH_EVALUATOR
    @pytest.mark.parametrize("fail", [False, True], ids=["success", "failure"])
    async def test_no_event_carries_the_text_it_evaluated(
        self,
        providers: ProviderFactory,
        event_sink: EventSink,
        evaluator: type[BaseEvaluator],
        fail: bool,
    ) -> None:
        inputs = fixture_input(evaluator)
        if fail:
            providers.failures.append(RateLimitError("slow down", dependency="openai"))
        with contextlib.suppress(RateLimitError):
            await construct(evaluator).evaluate(**inputs)

        [request] = event_sink.requests()
        # Every free text the evaluator was given, which is every string input that is not
        # one of an enumerated set — the grade is reported, and is not text.
        schema = load_contract(evaluator.metadata.id).input_schema
        texts = [
            name
            for name, spec in schema["properties"].items()
            if spec.get("type") == "string" and "enum" not in spec
        ]
        assert texts, "an evaluator with no text input would make this check vacuous"
        for name in texts:
            assert inputs[name] not in request["body"]
        # A length, and no field that could hold the text.
        text_field = primary_text_field(schema)
        assert text_field is not None
        assert json.loads(request["body"])["text_length_chars"] == len(inputs[text_field])


class TestWhatTheEventSays:
    """The fields the collector reads, on the single-step base."""

    TEXT = "Trees are important plants that grow in many parts of the world. They have roots."

    def evaluator(self, **overrides: Any) -> PurposeClarityEvaluator:
        return PurposeClarityEvaluator(google_api_key="k", **overrides)

    async def test_a_rejected_input_is_reported_as_an_error_event(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        # §4: validation runs inside the error boundary, so a rejected input is telemetered
        # rather than silently costing the caller nothing.
        with pytest.raises(InputValidationError):
            await self.evaluator().evaluate(text=self.TEXT, grade_level=2)

        [event] = event_sink.events()
        assert event["status"] == "error"
        assert event["error_code"] == "InputValidationError"
        # Nothing was read, nothing ran: no length, no grade, no cost.
        assert event["text_length_chars"] == 0
        assert event["grade"] == ""
        assert "token_usage" not in event
        assert "metadata" not in event
        # Still attributed to the model that would have been called.
        assert event["provider"] == "google:gemini-3-flash-preview"
        assert providers.calls == []

    async def test_the_grade_evaluated_is_reported_as_the_contract_spells_it(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        await self.evaluator().evaluate(text=self.TEXT, grade_level=5)

        assert event_sink.events()[0]["grade"] == "5"

    async def test_an_evaluator_without_a_grade_reports_an_empty_one(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        evaluator = construct(EVALUATORS[0])
        assert "grade_level" not in evaluator.contract.input_schema["properties"]
        await evaluator.evaluate(**fixture_input(type(evaluator)))

        assert event_sink.events()[0]["grade"] == ""

    async def test_a_model_override_is_reported_and_names_the_override_model(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        override = ModelOverride(provider=Provider.ANTHROPIC, model="claude-opus-5")
        evaluator = PurposeClarityEvaluator(anthropic_api_key="k", model_override=override)
        await evaluator.evaluate(text=self.TEXT, grade_level=5)

        event = event_sink.events()[0]
        assert event["model_override"] is True
        assert event["provider"] == "anthropic:claude-opus-5"

    async def test_an_evaluation_on_default_models_says_nothing_about_overrides(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        # Absent rather than false, which is the field the TypeScript SDK sends.
        await self.evaluator().evaluate(text=self.TEXT, grade_level=5)

        assert "model_override" not in event_sink.events()[0]

    async def test_the_event_is_sent_once_per_evaluation(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        evaluator = self.evaluator()
        await evaluator.evaluate(text=self.TEXT, grade_level=5)
        await evaluator.evaluate(text=self.TEXT, grade_level=6)

        assert [event["grade"] for event in event_sink.events()] == ["5", "6"]

    def test_a_synchronous_caller_reports_too(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        # The event outlives the event loop ``evaluate_sync`` opens and closes, which a
        # task on that loop would not.
        self.evaluator().evaluate_sync(text=self.TEXT, grade_level=5)

        assert len(event_sink.events()) == 1


class TestMultiStepReporting:
    """Per-step detail, and which model a mid-run failure is attributed to."""

    TEXT = "The dog ran. Because the gate was open, the dog ran down the street and away."

    async def test_each_step_is_reported_with_what_that_call_cost(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        await SentenceStructureEvaluator(openai_api_key="k").evaluate(text=self.TEXT, grade_level=5)

        stages = event_sink.events()[0]["metadata"]["stage_details"]
        assert stages == [
            {
                "stage": "sentence_analysis",
                "provider": "openai:gpt-4o-2024-08-06",
                "latency_ms": 12,
                "token_usage": {"input_tokens": 7, "output_tokens": 3},
            },
            {
                "stage": "classify_complexity",
                "provider": "openai:gpt-4o-2024-08-06",
                "latency_ms": 12,
                "token_usage": {"input_tokens": 7, "output_tokens": 3},
            },
        ]

    async def test_a_failure_reports_the_steps_that_did_complete(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        evaluator = SentenceStructureEvaluator(openai_api_key="k")
        # Both steps run on one model, so the client they share is what has to fail, and
        # only on the second call.
        provider = providers.created[0]
        answer = provider.generate_structured
        calls = 0

        async def fail_on_the_second_step(*args: Any, **kwargs: Any) -> Any:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RateLimitError("slow down", dependency="openai")
            return await answer(*args, **kwargs)

        provider.generate_structured = fail_on_the_second_step  # type: ignore[method-assign]
        with pytest.raises(RateLimitError):
            await evaluator.evaluate(text=self.TEXT, grade_level=5)

        [event] = event_sink.events()
        assert event["status"] == "error"
        assert [s["stage"] for s in event["metadata"]["stage_details"]] == ["sentence_analysis"]
        assert event["token_usage"] == {"input_tokens": 7, "output_tokens": 3}


class TestTelemetryCostsTheCallerNothing:
    TEXT = "Trees are important plants that grow in many parts of the world. They have roots."

    @pytest.mark.parametrize(
        "telemetry", [False, TelemetryOptions(enabled=False)], ids=["shorthand", "options"]
    )
    async def test_disabled_telemetry_builds_no_client_and_sends_nothing(
        self, providers: ProviderFactory, event_sink: EventSink, telemetry: Any
    ) -> None:
        evaluator = PurposeClarityEvaluator(
            EvaluatorConfig(google_api_key="k", telemetry=telemetry)
        )
        await evaluator.evaluate(text=self.TEXT, grade_level=5)

        assert evaluator._telemetry is None
        assert event_sink.requests() == []
        # Not even a sender thread: nothing was queued, so nothing was started.
        assert telemetry_client._sender_instance is None

    async def test_an_identified_caller_is_attributed_by_their_key(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        evaluator = PurposeClarityEvaluator(
            google_api_key="k",
            telemetry=TelemetryOptions(learning_commons_api_key="partner-key"),
        )
        await evaluator.evaluate(text=self.TEXT, grade_level=5)

        assert event_sink.requests()[0]["headers"]["X-API-Key"] == "partner-key"

    async def test_an_anonymous_caller_sends_no_key(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        await PurposeClarityEvaluator(google_api_key="k").evaluate(text=self.TEXT, grade_level=5)

        assert "X-API-Key" not in event_sink.requests()[0]["headers"]

    async def test_a_collector_that_is_down_does_not_fail_the_evaluation(
        self, providers: ProviderFactory, event_sink: EventSink
    ) -> None:
        event_sink.failure = httpx.ConnectError("getaddrinfo ENOTFOUND")

        evaluation = await PurposeClarityEvaluator(google_api_key="k").evaluate(
            text=self.TEXT, grade_level=5
        )

        assert evaluation.result is not None
        assert len(event_sink.events()) == 1
