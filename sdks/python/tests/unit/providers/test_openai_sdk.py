"""The OpenAI adapter against a fake client: request shape, parsing, and failure modes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from openai import omit
from pydantic import BaseModel

from learning_commons_evaluators.errors import LLMOutputProcessingError
from learning_commons_evaluators.providers import Message, Provider, ProviderConfig
from learning_commons_evaluators.providers.openai_sdk import OpenAIProvider


class _Verdict(BaseModel):
    score: int
    reasoning: str


MESSAGES: list[Message] = [
    {"role": "system", "content": "You grade things."},
    {"role": "user", "content": "Grade this."},
]


def _client(
    parsed: Any = None,
    text: str = "",
    usage: Any = None,
    body: dict[str, Any] | None = None,
    **extra: Any,
) -> Any:
    """A fake whose raw ``responses.parse`` carries ``body`` and parses to ``parsed``."""
    usage = usage if usage is not None else SimpleNamespace(input_tokens=11, output_tokens=7)
    parse_result = SimpleNamespace(output_parsed=parsed, usage=usage, **extra)
    # The async client's raw form is a LegacyAPIResponse: a read httpx body, sync ``parse``.
    raw = SimpleNamespace(
        http_response=SimpleNamespace(
            json=Mock(return_value=body or {"status": "completed", "incomplete_details": None})
        ),
        parse=Mock(return_value=parse_result),
    )
    create_result = SimpleNamespace(output_text=text, usage=usage)
    return SimpleNamespace(
        responses=SimpleNamespace(
            with_raw_response=SimpleNamespace(parse=AsyncMock(return_value=raw)),
            create=AsyncMock(return_value=create_result),
        )
    )


def _adapter(client: Any) -> OpenAIProvider:
    config = ProviderConfig(type=Provider.OPENAI, model="gpt-4o-2024-11-20", api_key="k")
    return OpenAIProvider(config, client=client)


class TestGenerateStructured:
    async def test_returns_the_parsed_payload_with_usage_and_model(self) -> None:
        verdict = _Verdict(score=3, reasoning="fine")
        response = await _adapter(_client(parsed=verdict)).generate_structured(MESSAGES, _Verdict)
        assert response.data is verdict
        assert response.model == "gpt-4o-2024-11-20"
        assert (response.usage.input_tokens, response.usage.output_tokens) == (11, 7)
        assert response.latency_ms >= 0

    async def test_sends_the_system_prompt_as_instructions_and_the_rest_as_input(self) -> None:
        client = _client(parsed=_Verdict(score=1, reasoning="r"))
        await _adapter(client).generate_structured(MESSAGES, _Verdict, temperature=0.0)
        kwargs = client.responses.with_raw_response.parse.await_args.kwargs
        assert kwargs["model"] == "gpt-4o-2024-11-20"
        assert kwargs["instructions"] == "You grade things."
        assert kwargs["input"] == [{"role": "user", "content": "Grade this."}]
        assert kwargs["text_format"] is _Verdict
        assert kwargs["temperature"] == 0.0

    async def test_omits_temperature_and_max_tokens_when_not_given(self) -> None:
        # A None temperature means "send nothing", for models that reject an explicit value.
        client = _client(parsed=_Verdict(score=1, reasoning="r"))
        await _adapter(client).generate_structured(MESSAGES, _Verdict)
        kwargs = client.responses.with_raw_response.parse.await_args.kwargs
        assert kwargs["temperature"] is omit
        assert kwargs["max_output_tokens"] is omit

    async def test_omits_instructions_without_a_system_message(self) -> None:
        client = _client(parsed=_Verdict(score=1, reasoning="r"))
        await _adapter(client).generate_structured(MESSAGES[1:], _Verdict, max_tokens=256)
        kwargs = client.responses.with_raw_response.parse.await_args.kwargs
        assert kwargs["instructions"] is omit
        assert kwargs["max_output_tokens"] == 256

    async def test_no_parsed_output_is_an_output_processing_error(self) -> None:
        # A refusal leaves nothing to parse: the dependency answered, so this is the
        # model's output failing our contract.
        client = _client(parsed=None, status="completed")
        with pytest.raises(LLMOutputProcessingError, match="completed") as exc_info:
            await _adapter(client).generate_structured(MESSAGES, _Verdict)
        assert exc_info.value.retryable is True
        assert "openai:gpt-4o-2024-11-20" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("temperature", "retryable"), [(0.0, False), (None, True), (0.7, True)]
    )
    async def test_an_incomplete_max_output_tokens_response_is_truncated(
        self, temperature: float | None, retryable: bool
    ) -> None:
        # Caught from the raw status, so parse never sees the cut-off JSON.
        body = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
        client = _client(body=body)
        with pytest.raises(LLMOutputProcessingError) as exc_info:
            await _adapter(client).generate_structured(
                MESSAGES, _Verdict, temperature=temperature, max_tokens=256
            )
        assert str(exc_info.value) == (
            "openai:gpt-4o-2024-11-20 stopped at max_tokens=256 before its structured "
            "output was complete."
        )
        assert exc_info.value.retryable is retryable
        raw = client.responses.with_raw_response.parse.return_value
        raw.parse.assert_not_called()

    async def test_missing_usage_counts_as_zero(self) -> None:
        client = _client(parsed=_Verdict(score=1, reasoning="r"), usage=SimpleNamespace())
        response = await _adapter(client).generate_structured(MESSAGES, _Verdict)
        assert response.usage.input_tokens == 0

    async def test_vendor_errors_propagate_unwrapped(self) -> None:
        # Classification is the evaluator boundary's job, via wrap_provider_error.
        client = _client()
        client.responses.with_raw_response.parse = AsyncMock(side_effect=RuntimeError("upstream"))
        with pytest.raises(RuntimeError, match="upstream"):
            await _adapter(client).generate_structured(MESSAGES, _Verdict)


class TestGenerateText:
    async def test_returns_the_output_text(self) -> None:
        client = _client(text="A short assumption.")
        response = await _adapter(client).generate_text(MESSAGES, temperature=0.0)
        assert response.text == "A short assumption."
        assert response.usage.output_tokens == 7
        kwargs = client.responses.create.await_args.kwargs
        assert kwargs["instructions"] == "You grade things."
        assert kwargs["temperature"] == 0.0
        assert "text_format" not in kwargs
