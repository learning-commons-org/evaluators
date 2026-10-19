"""The Anthropic adapter against a fake client: request shape, parsing, and failure modes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from anthropic import omit, transform_schema
from pydantic import BaseModel, TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from learning_commons_evaluators.errors import LLMOutputProcessingError
from learning_commons_evaluators.providers import Message, Provider, ProviderConfig
from learning_commons_evaluators.providers.anthropic_sdk import (
    DEFAULT_MAX_TOKENS,
    AnthropicProvider,
)


class _Verdict(BaseModel):
    aligned: bool


MESSAGES: list[Message] = [
    {"role": "system", "content": "You align things."},
    {"role": "user", "content": "Align this."},
    {"role": "assistant", "content": "Working on it."},
]

USAGE = SimpleNamespace(input_tokens=5, output_tokens=9)


def _client(
    parsed: BaseModel | None = None,
    content: list[Any] | None = None,
    stop_reason: str = "end_turn",
) -> Any:
    """A fake whose ``messages.create`` returns ``content``, or ``parsed`` as its JSON text."""
    if content is None and parsed is not None:
        content = [SimpleNamespace(type="text", text=parsed.model_dump_json())]
    result = SimpleNamespace(content=content or [], usage=USAGE, stop_reason=stop_reason)
    return SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(return_value=result)))


def _adapter(client: Any) -> AnthropicProvider:
    config = ProviderConfig(type=Provider.ANTHROPIC, model="claude-haiku-4-5-20251001", api_key="k")
    return AnthropicProvider(config, client=client)


class TestGenerateStructured:
    async def test_returns_the_parsed_output(self) -> None:
        verdict = _Verdict(aligned=True)
        response = await _adapter(_client(parsed=verdict)).generate_structured(MESSAGES, _Verdict)
        assert response.data == verdict
        assert response.model == "claude-haiku-4-5-20251001"
        assert (response.usage.input_tokens, response.usage.output_tokens) == (5, 9)

    async def test_sends_system_out_of_band_and_defaults_max_tokens(self) -> None:
        client = _client(parsed=_Verdict(aligned=True))
        await _adapter(client).generate_structured(MESSAGES, _Verdict)
        kwargs = client.messages.create.await_args.kwargs
        assert kwargs["system"] == "You align things."
        assert kwargs["messages"] == [
            {"role": "user", "content": "Align this."},
            {"role": "assistant", "content": "Working on it."},
        ]
        assert kwargs["max_tokens"] == DEFAULT_MAX_TOKENS
        assert kwargs["output_config"] == {
            "format": {
                "type": "json_schema",
                "schema": transform_schema(TypeAdapter(_Verdict).json_schema()),
            }
        }
        assert "extra_body" not in kwargs

    async def test_temperature_travels_in_the_body_only_when_given(self) -> None:
        # The SDK no longer exposes temperature as a parameter; the contract's pinned value
        # is still sent for the models that accept it, and None sends nothing.
        client = _client(parsed=_Verdict(aligned=True))
        await _adapter(client).generate_structured(
            MESSAGES, _Verdict, temperature=0.0, max_tokens=512
        )
        kwargs = client.messages.create.await_args.kwargs
        assert kwargs["extra_body"] == {"temperature": 0.0}
        assert kwargs["max_tokens"] == 512

    async def test_omits_system_without_a_system_message(self) -> None:
        client = _client(parsed=_Verdict(aligned=True))
        await _adapter(client).generate_structured(MESSAGES[1:], _Verdict)
        assert client.messages.create.await_args.kwargs["system"] is omit

    async def test_a_refusal_with_no_text_is_an_output_processing_error(self) -> None:
        client = _client(stop_reason="refusal")
        with pytest.raises(LLMOutputProcessingError, match="refusal") as exc_info:
            await _adapter(client).generate_structured(MESSAGES, _Verdict)
        assert exc_info.value.retryable is True

    async def test_schema_invalid_text_raises_pydantic_for_the_boundary_to_classify(self) -> None:
        content = [SimpleNamespace(type="text", text='{"aligned": "maybe"}')]
        with pytest.raises(PydanticValidationError):
            await _adapter(_client(content=content)).generate_structured(MESSAGES, _Verdict)

    @pytest.mark.parametrize(
        ("temperature", "retryable"), [(0.0, False), (0, False), (None, True), (0.7, True)]
    )
    async def test_a_max_tokens_stop_is_truncated_and_only_retryable_off_temperature_zero(
        self, temperature: float | None, retryable: bool
    ) -> None:
        # Cut-off JSON is reported from the stop reason, before it could fail the schema.
        content = [SimpleNamespace(type="text", text='{"aligned": tr')]
        client = _client(content=content, stop_reason="max_tokens")
        with pytest.raises(LLMOutputProcessingError) as exc_info:
            await _adapter(client).generate_structured(MESSAGES, _Verdict, temperature=temperature)
        assert str(exc_info.value) == (
            "anthropic:claude-haiku-4-5-20251001 stopped at "
            f"max_tokens={DEFAULT_MAX_TOKENS} before its structured output was complete."
        )
        assert exc_info.value.retryable is retryable


class TestGenerateText:
    async def test_concatenates_text_blocks_only(self) -> None:
        content = [
            SimpleNamespace(type="text", text="Hello, "),
            SimpleNamespace(type="tool_use", name="x"),
            SimpleNamespace(type="text", text="world."),
        ]
        response = await _adapter(_client(content=content)).generate_text(MESSAGES)
        assert response.text == "Hello, world."
        assert response.usage.input_tokens == 5
