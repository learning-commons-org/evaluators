"""The Google adapter against a fake client: request shape, parsing, and failure modes."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel, ValidationError

from learning_commons_evaluators.errors import LLMOutputProcessingError, wrap_provider_error
from learning_commons_evaluators.providers import Message, Provider, ProviderConfig
from learning_commons_evaluators.providers.google_genai import GoogleProvider


class _Verdict(BaseModel):
    grade_band: str
    met: int


MESSAGES: list[Message] = [
    {"role": "system", "content": "You band things."},
    {"role": "user", "content": "Band this."},
    {"role": "assistant", "content": "Banding."},
]

USAGE = SimpleNamespace(prompt_token_count=13, candidates_token_count=4)


def _client(
    parsed: Any = None, text: str | None = None, candidates: list[Any] | None = None
) -> Any:
    result = SimpleNamespace(
        parsed=parsed, text=text, usage_metadata=USAGE, candidates=candidates or []
    )
    return SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=AsyncMock(return_value=result)))
    )


def _adapter(client: Any) -> GoogleProvider:
    config = ProviderConfig(type=Provider.GOOGLE, model="gemini-3.6-flash", api_key="k")
    return GoogleProvider(config, client=client)


class TestGenerateStructured:
    async def test_uses_the_sdk_parsed_object_when_it_matches_the_schema(self) -> None:
        verdict = _Verdict(grade_band="K-1", met=1)
        response = await _adapter(_client(parsed=verdict)).generate_structured(MESSAGES, _Verdict)
        assert response.data is verdict
        assert response.model == "gemini-3.6-flash"
        assert (response.usage.input_tokens, response.usage.output_tokens) == (13, 4)

    async def test_validates_the_text_when_parsed_is_unset(self) -> None:
        client = _client(parsed=None, text='{"grade_band": "2-3", "met": 0}')
        response = await _adapter(client).generate_structured(MESSAGES, _Verdict)
        assert response.data == _Verdict(grade_band="2-3", met=0)

    async def test_sends_the_raw_json_schema_and_system_instruction(self) -> None:
        client = _client(text='{"grade_band": "2-3", "met": 0}')
        await _adapter(client).generate_structured(
            MESSAGES, _Verdict, temperature=1.0, max_tokens=99
        )
        kwargs = client.aio.models.generate_content.await_args.kwargs
        assert kwargs["model"] == "gemini-3.6-flash"
        config = kwargs["config"]
        assert config.system_instruction == "You band things."
        assert config.temperature == 1.0
        assert config.max_output_tokens == 99
        assert config.response_mime_type == "application/json"
        assert config.response_json_schema == _Verdict.model_json_schema()
        assert config.response_schema is None

    async def test_maps_assistant_turns_to_the_model_role(self) -> None:
        client = _client(text='{"grade_band": "2-3", "met": 0}')
        await _adapter(client).generate_structured(MESSAGES, _Verdict)
        contents = client.aio.models.generate_content.await_args.kwargs["contents"]
        assert [c.role for c in contents] == ["user", "model"]
        assert contents[0].parts[0].text == "Band this."

    async def test_omits_temperature_when_not_given(self) -> None:
        client = _client(text='{"grade_band": "2-3", "met": 0}')
        await _adapter(client).generate_structured(MESSAGES[1:], _Verdict)
        config = client.aio.models.generate_content.await_args.kwargs["config"]
        assert config.temperature is None
        assert config.system_instruction is None

    async def test_schema_invalid_text_raises_pydantic_which_classifies_as_output_processing(
        self,
    ) -> None:
        client = _client(text='{"grade_band": "2-3"}')
        with pytest.raises(ValidationError) as exc_info:
            await _adapter(client).generate_structured(MESSAGES, _Verdict)
        wrapped = wrap_provider_error(exc_info.value, dependency="google", model="gemini-3.6-flash")
        assert isinstance(wrapped, LLMOutputProcessingError)
        assert wrapped.validation_errors is not None

    async def test_empty_text_is_an_output_processing_error_naming_the_finish_reason(self) -> None:
        client = _client(text=None, candidates=[SimpleNamespace(finish_reason="SAFETY")])
        with pytest.raises(LLMOutputProcessingError, match="SAFETY"):
            await _adapter(client).generate_structured(MESSAGES, _Verdict)


class TestGenerateText:
    async def test_returns_the_text_without_a_response_schema(self) -> None:
        client = _client(text="An assumption.")
        response = await _adapter(client).generate_text(MESSAGES, temperature=0.0)
        assert response.text == "An assumption."
        config = client.aio.models.generate_content.await_args.kwargs["config"]
        assert config.response_mime_type is None
        assert config.response_json_schema is None


def test_max_retries_becomes_total_attempts_on_the_real_client() -> None:
    # google-genai counts attempts including the original request; 0 retries is 1 attempt.
    config = ProviderConfig(
        type=Provider.GOOGLE, model="gemini-3.6-flash", api_key="k", max_retries=2
    )
    adapter = GoogleProvider(config)
    retry_options = adapter._client._api_client._http_options.retry_options
    assert retry_options is not None
    assert retry_options.attempts == 3
