"""Cross-SDK telemetry check: Python emits the events the TypeScript SDK emits.

Both SDKs' events land in one collector and are aggregated together, so the TypeScript
events are the oracle. ``sdks/typescript/tests/unit/telemetry/cross-sdk-events.test.ts``
runs a list of cases against a captured event sink and writes each case — the evaluator, the
inputs, how the provider behaved, and the event that came out — to the JSON read below. Here
the same cases are replayed through the Python SDK and the events compared field for field,
including the order the fields are written in.

What a run cannot reproduce is masked in both SDKs: the clock, the wall-clock latency, and
``sdk_version``, which each SDK reports as itself and which is asserted separately here.

Regenerating the oracle (``UPDATE_TELEMETRY_ORACLE=1 npm run test:unit`` in
``sdks/typescript``) is what a deliberate change to the shared event format looks like: it
fails this suite until Python matches, which is the migration both SDKs have to make together.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from learning_commons_evaluators import ModelOverride, Provider, __version__
from learning_commons_evaluators.errors import EvaluatorError, RateLimitError
from learning_commons_evaluators.evaluators.registry import get_evaluator_class
from learning_commons_evaluators.providers import (
    LLMResponse,
    Message,
    ProviderConfig,
    TextGenerationResponse,
    TokenUsage,
    provider_label,
)
from tests.conftest import EventSink
from tests.unit.conftest import sample_for

ORACLE = (
    Path(__file__).resolve().parents[5]
    / "sdks"
    / "typescript"
    / "tests"
    / "fixtures"
    / "telemetry-events.json"
)

#: What the TypeScript stub reports for every call, restated so the numbers in an event are
#: the same on both sides.
USAGE = TokenUsage(input_tokens=250, output_tokens=120)
STAGE_LATENCY_MS = 900

MASK = "<masked>"

CASES: list[dict[str, Any]] = json.loads(ORACLE.read_text(encoding="utf-8"))


@dataclass
class Calls:
    """The run's call counter, shared by every provider the evaluator builds."""

    fail_at: int | None = None
    count: int = 0

    def next(self) -> None:
        self.count += 1
        if self.count == self.fail_at:
            raise RateLimitError("slow down", dependency="openai")


@dataclass
class OracleProvider:
    """A provider answering exactly what the TypeScript stub answers.

    Its payload is a sample derived from the step's own schema rather than the literal the
    TypeScript stub returns: no event carries a model's output, so the two only have to be
    something their steps can consume.
    """

    config: ProviderConfig
    calls: Calls
    log: list[dict[str, Any]] = field(default_factory=list)

    @property
    def label(self) -> str:
        return provider_label(self.config.type, self.config.model)

    async def generate_structured(
        self,
        messages: Sequence[Message],
        schema: type[BaseModel],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse[Any]:
        self.calls.next()
        return LLMResponse(
            data=sample_for(schema),
            model=self.config.model,
            usage=USAGE,
            latency_ms=STAGE_LATENCY_MS,
        )

    async def generate_text(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> TextGenerationResponse:
        self.calls.next()
        return TextGenerationResponse(text="prose", usage=USAGE, latency_ms=STAGE_LATENCY_MS)


@pytest.fixture
def calls() -> Iterator[Calls]:
    """Route provider construction through the oracle's provider."""
    state = Calls()
    with patch(
        "learning_commons_evaluators.evaluators.base.create_provider",
        lambda config: OracleProvider(config, state),
    ):
        yield state


def config_for(case: dict[str, Any]) -> dict[str, Any]:
    """The same configuration the TypeScript case used, in this SDK's field names."""
    evaluator = get_evaluator_class(case["evaluator"])
    assert evaluator is not None, f"{case['evaluator']} is not in the Python registry"
    override = case.get("model_override")
    providers = (
        [Provider(override["provider"])] if override else list(evaluator.metadata.default_providers)
    )
    config: dict[str, Any] = {f"{p.value}_api_key": "test-key" for p in providers}
    if override:
        config["model_override"] = ModelOverride(
            provider=Provider(override["provider"]), model=override["model"]
        )
    return config


def masked(event: dict[str, Any]) -> dict[str, Any]:
    return {**event, "timestamp": MASK, "sdk_version": MASK, "latency_ms": MASK}


async def event_for(case: dict[str, Any], calls: Calls, event_sink: EventSink) -> dict[str, Any]:
    evaluator = get_evaluator_class(case["evaluator"])
    assert evaluator is not None
    calls.fail_at = case.get("fail_at_call")

    instance = evaluator(**config_for(case))
    try:
        await instance.evaluate(**case["inputs"])
    except EvaluatorError:
        assert case.get("raises"), f"{case['id']}: this case is not expected to raise"
    else:
        assert not case.get("raises"), f"{case['id']}: this case is expected to raise"

    [event] = event_sink.events()
    return event


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
class TestTheEventsMatchTheTypeScriptOracle:
    async def test_the_event_is_the_one_typescript_emits(
        self, case: dict[str, Any], calls: Calls, event_sink: EventSink
    ) -> None:
        event = await event_for(case, calls, event_sink)

        assert masked(event) == case["event"]

    async def test_the_fields_are_written_in_the_same_order(
        self, case: dict[str, Any], calls: Calls, event_sink: EventSink
    ) -> None:
        # Not a wire requirement, but the field set is: a field appearing in a different
        # place is a field one SDK sends and the other does not, or one it renamed.
        event = await event_for(case, calls, event_sink)

        assert list(event) == list(case["event"])

    async def test_the_event_names_this_sdk_as_its_source(
        self, case: dict[str, Any], calls: Calls, event_sink: EventSink
    ) -> None:
        # The one field whose value differs by design: the collector tells the SDKs apart by
        # the identifier this one prefixes its version with.
        event = await event_for(case, calls, event_sink)

        assert event["sdk_version"] == f"learning-commons-evaluators-python-{__version__}"


def test_the_oracle_covers_both_evaluator_bases() -> None:
    """A single-step and a multi-step case, so neither base can drift unnoticed."""
    covered = {case["evaluator"] for case in CASES}
    assert covered == {
        "student_facing_text.ela_reading.purpose_clarity",
        "student_facing_text.ela_reading.sentence_structure",
    }
