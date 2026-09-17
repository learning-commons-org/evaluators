"""Shared fakes for the evaluator tests: a recording provider in place of the vendor SDKs."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from learning_commons_evaluators.providers import (
    LLMResponse,
    Message,
    ProviderConfig,
    TextGenerationResponse,
    TokenUsage,
    provider_label,
)


@dataclass
class FakeProvider:
    """An ``LLMProvider`` that returns a scripted payload and records what it was asked."""

    config: ProviderConfig
    payload: Callable[[type[BaseModel]], Any]
    calls: list[dict[str, Any]] = field(default_factory=list)
    failures: list[BaseException] = field(default_factory=list)
    #: What ``generate_text`` answers, for the prose steps of a multi-step contract.
    prose: str = "prose"
    #: Shared with every fake from the same factory, so the run's order survives.
    log: list[dict[str, Any]] = field(default_factory=list)

    def _record(self, call: dict[str, Any]) -> None:
        self.calls.append(call)
        self.log.append(call)

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
        self._record({"messages": list(messages), "schema": schema, "temperature": temperature})
        if self.failures:
            raise self.failures.pop(0)
        return LLMResponse(
            data=self.payload(schema),
            model=self.config.model,
            usage=TokenUsage(input_tokens=7, output_tokens=3),
            latency_ms=12,
        )

    async def generate_text(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> TextGenerationResponse:
        # Recorded alongside the structured calls, with ``schema`` absent, so a test reads
        # one ordered record of everything the evaluator asked for.
        self._record({"messages": list(messages), "schema": None, "temperature": temperature})
        if self.failures:
            raise self.failures.pop(0)
        return TextGenerationResponse(
            text=self.prose,
            usage=TokenUsage(input_tokens=5, output_tokens=2),
            latency_ms=8,
        )


@dataclass
class ProviderFactory:
    """Stands in for ``create_provider``; hands out fakes and remembers every config."""

    payload: Callable[[type[BaseModel]], Any]
    created: list[FakeProvider] = field(default_factory=list)
    failures: list[BaseException] = field(default_factory=list)
    prose: str = "prose"
    #: Every call made through this factory, in the order the evaluator made them. A
    #: multi-step evaluator spreads its calls over one provider per model, so reading one
    #: provider's own ``calls`` would drop the steps that ran on another.
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, config: ProviderConfig) -> FakeProvider:
        provider = FakeProvider(
            config, self.payload, failures=self.failures, prose=self.prose, log=self.calls
        )
        self.created.append(provider)
        return provider

    @property
    def last(self) -> FakeProvider:
        return self.created[-1]


def sample_for(schema: type[BaseModel]) -> BaseModel:
    """A minimal valid instance of a generated output model, from its JSON schema."""
    from tests.unit.schemas.test_generated_outputs import sample

    json_schema = schema.model_json_schema()
    return schema.model_validate(sample(json_schema, json_schema.get("$defs", {})))


@pytest.fixture
def providers() -> Iterator[ProviderFactory]:
    """Route every evaluator's provider construction through recording fakes."""
    factory = ProviderFactory(payload=sample_for)
    with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
        yield factory
