"""The Anthropic adapter against a fake client: request shape, parsing, and failure modes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from anthropic import omit, transform_schema
from pydantic import BaseModel, TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from learning_commons_evaluators.errors import (
    LLMOutputProcessingError,
    LLMProviderError,
    LLMRefusalError,
)
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

REFUSAL_DETAILS = SimpleNamespace(
    type="refusal", category="reasoning_extraction", explanation="This request was blocked."
)


def _client(
    parsed: BaseModel | None = None,
    content: list[Any] | None = None,
    stop_reason: str = "end_turn",
    **extra: Any,
) -> Any:
    """A fake whose ``messages.create`` returns ``content``, or ``parsed`` as its JSON text.

    ``extra`` sets further attributes on the returned message, such as ``stop_details``.
    """
    if content is None and parsed is not None:
        content = [SimpleNamespace(type="text", text=parsed.model_dump_json())]
    result = SimpleNamespace(content=content or [], usage=USAGE, stop_reason=stop_reason, **extra)
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

    async def test_a_refusal_raises_the_refusal_error_with_the_providers_reason(self) -> None:
        client = _client(
            stop_reason="refusal",
            stop_details=REFUSAL_DETAILS,
            _request_id="req_123",
        )
        with pytest.raises(LLMRefusalError) as exc_info:
            await _adapter(client).generate_structured(MESSAGES, _Verdict)
        error = exc_info.value
        assert str(error) == (
            "anthropic:claude-haiku-4-5-20251001 refused the request (reasoning_extraction). "
            "The provider declined it, so sending the same request again will not help; "
            "use another model or provider."
        )
        assert error.category == "reasoning_extraction"
        assert error.explanation == "This request was blocked."
        assert error.dependency == "anthropic"
        assert error.model == "claude-haiku-4-5-20251001"
        assert error.request_id == "req_123"
        # Refused again if resent, and billed each time.
        assert error.retryable is False
        # Callers already catching the provider catch-all keep catching it.
        assert isinstance(error, LLMProviderError)
        assert not isinstance(error, LLMOutputProcessingError)

    async def test_a_refusal_without_stop_details_still_raises_the_refusal_error(self) -> None:
        # Older models and SDK releases stop with ``refusal`` and say nothing more.
        with pytest.raises(LLMRefusalError) as exc_info:
            await _adapter(_client(stop_reason="refusal")).generate_structured(MESSAGES, _Verdict)
        error = exc_info.value
        assert str(error).startswith(
            "anthropic:claude-haiku-4-5-20251001 refused the request. The provider declined it"
        )
        assert error.category is None
        assert error.explanation is None
        assert error.request_id is None

    async def test_a_refusal_that_left_partial_text_is_still_a_refusal(self) -> None:
        # The stop reason decides, so cut-off text is not handed to the schema.
        content = [SimpleNamespace(type="text", text='{"aligned": tr')]
        client = _client(content=content, stop_reason="refusal", stop_details=REFUSAL_DETAILS)
        with pytest.raises(LLMRefusalError):
            await _adapter(client).generate_structured(MESSAGES, _Verdict)

    async def test_an_empty_completion_that_is_not_a_refusal_is_an_output_error(self) -> None:
        with pytest.raises(LLMOutputProcessingError, match="end_turn") as exc_info:
            await _adapter(_client()).generate_structured(MESSAGES, _Verdict)
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
    async def test_a_refusal_raises_the_refusal_error(self) -> None:
        client = _client(stop_reason="refusal", stop_details=REFUSAL_DETAILS)
        with pytest.raises(LLMRefusalError) as exc_info:
            await _adapter(client).generate_text(MESSAGES)
        assert exc_info.value.category == "reasoning_extraction"

    async def test_concatenates_text_blocks_only(self) -> None:
        content = [
            SimpleNamespace(type="text", text="Hello, "),
            SimpleNamespace(type="tool_use", name="x"),
            SimpleNamespace(type="text", text="world."),
        ]
        response = await _adapter(_client(content=content)).generate_text(MESSAGES)
        assert response.text == "Hello, world."
        assert response.usage.input_tokens == 5
