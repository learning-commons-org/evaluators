"""The Anthropic adapter against a fake client: request shape, parsing, and failure modes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from anthropic import omit
from pydantic import BaseModel

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
    parsed: Any = None, content: list[Any] | None = None, stop_reason: str = "end_turn"
) -> Any:
    parse_result = SimpleNamespace(parsed_output=parsed, usage=USAGE, stop_reason=stop_reason)
    create_result = SimpleNamespace(content=content or [], usage=USAGE)
    return SimpleNamespace(
        messages=SimpleNamespace(
            parse=AsyncMock(return_value=parse_result),
            create=AsyncMock(return_value=create_result),
        )
    )


def _adapter(client: Any) -> AnthropicProvider:
    config = ProviderConfig(type=Provider.ANTHROPIC, model="claude-haiku-4-5-20251001", api_key="k")
    return AnthropicProvider(config, client=client)


class TestGenerateStructured:
    async def test_returns_the_parsed_output(self) -> None:
        verdict = _Verdict(aligned=True)
        response = await _adapter(_client(parsed=verdict)).generate_structured(MESSAGES, _Verdict)
        assert response.data is verdict
        assert response.model == "claude-haiku-4-5-20251001"
        assert (response.usage.input_tokens, response.usage.output_tokens) == (5, 9)

    async def test_sends_system_out_of_band_and_defaults_max_tokens(self) -> None:
        client = _client(parsed=_Verdict(aligned=True))
        await _adapter(client).generate_structured(MESSAGES, _Verdict)
        kwargs = client.messages.parse.await_args.kwargs
        assert kwargs["system"] == "You align things."
        assert kwargs["messages"] == [
            {"role": "user", "content": "Align this."},
            {"role": "assistant", "content": "Working on it."},
        ]
        assert kwargs["max_tokens"] == DEFAULT_MAX_TOKENS
        assert kwargs["output_format"] is _Verdict
        assert "extra_body" not in kwargs

    async def test_temperature_travels_in_the_body_only_when_given(self) -> None:
        # The SDK no longer exposes temperature as a parameter; the contract's pinned value
        # is still sent for the models that accept it, and None sends nothing.
        client = _client(parsed=_Verdict(aligned=True))
        await _adapter(client).generate_structured(
            MESSAGES, _Verdict, temperature=0.0, max_tokens=512
        )
        kwargs = client.messages.parse.await_args.kwargs
        assert kwargs["extra_body"] == {"temperature": 0.0}
        assert kwargs["max_tokens"] == 512

    async def test_omits_system_without_a_system_message(self) -> None:
        client = _client(parsed=_Verdict(aligned=True))
        await _adapter(client).generate_structured(MESSAGES[1:], _Verdict)
        assert client.messages.parse.await_args.kwargs["system"] is omit

    async def test_no_parsed_output_is_an_output_processing_error(self) -> None:
        client = _client(parsed=None, stop_reason="max_tokens")
        with pytest.raises(LLMOutputProcessingError, match="max_tokens") as exc_info:
            await _adapter(client).generate_structured(MESSAGES, _Verdict)
        assert exc_info.value.retryable is True


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
