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
        self.calls.append(
            {"messages": list(messages), "schema": schema, "temperature": temperature}
        )
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
        raise NotImplementedError


@dataclass
class ProviderFactory:
    """Stands in for ``create_provider``; hands out fakes and remembers every config."""

    payload: Callable[[type[BaseModel]], Any]
    created: list[FakeProvider] = field(default_factory=list)
    failures: list[BaseException] = field(default_factory=list)

    def __call__(self, config: ProviderConfig) -> FakeProvider:
        provider = FakeProvider(config, self.payload, failures=self.failures)
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
