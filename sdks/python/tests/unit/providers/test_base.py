"""The provider protocol, labels, and dependency attribution."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel

from learning_commons_evaluators.providers import (
    LLMProvider,
    LLMResponse,
    Message,
    Provider,
    TextGenerationResponse,
    TokenUsage,
    provider_context,
    provider_label,
)

T = TypeVar("T", bound=BaseModel)


class _Fake:
    label = "mygateway"

    async def generate_structured(
        self,
        messages: Sequence[Message],
        schema: type[T],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse[T]:
        raise NotImplementedError

    async def generate_text(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> TextGenerationResponse:
        raise NotImplementedError


class TestProvider:
    def test_is_the_closed_set_of_canonical_values(self) -> None:
        assert {p.value for p in Provider} == {"openai", "google", "anthropic"}

    def test_compares_and_serialises_as_its_value(self) -> None:
        assert Provider.OPENAI == "openai"
        assert Provider("google") is Provider.GOOGLE


class TestLabels:
    def test_label_is_provider_colon_model(self) -> None:
        assert provider_label(Provider.OPENAI, "gpt-4o-2024-11-20") == "openai:gpt-4o-2024-11-20"
        assert provider_label("google", "gemini-3.6-flash") == "google:gemini-3.6-flash"


class TestProviderContext:
    def test_reports_the_real_vendor_and_bare_model_for_a_built_in_label(self) -> None:
        fake = _Fake()
        fake.label = "anthropic:claude-haiku-4-5-20251001"
        assert provider_context(fake) == ("anthropic", "claude-haiku-4-5-20251001")

    def test_reports_custom_and_keeps_the_whole_label_for_an_injected_provider(self) -> None:
        assert provider_context(_Fake()) == ("custom", "mygateway")

    def test_keeps_the_whole_label_when_there_is_no_model_to_strip(self) -> None:
        fake = _Fake()
        fake.label = "openai:"
        assert provider_context(fake) == ("openai", "openai:")


class TestProtocol:
    def test_a_duck_typed_object_satisfies_the_runtime_check(self) -> None:
        assert isinstance(_Fake(), LLMProvider)

    def test_an_object_missing_a_method_does_not(self) -> None:
        class _Half:
            label = "x"

            async def generate_text(self, messages, *, temperature=None, max_tokens=None):  # type: ignore[no-untyped-def]
                raise NotImplementedError

        assert not isinstance(_Half(), LLMProvider)

    def test_token_usage_is_a_value_object(self) -> None:
        assert TokenUsage(1, 2) == TokenUsage(input_tokens=1, output_tokens=2)
