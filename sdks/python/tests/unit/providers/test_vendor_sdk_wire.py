"""Each adapter driven through its real vendor client over an in-memory transport.

The neighbouring tests use fake clients, so they cannot tell whether the installed SDK
accepts our request keyword arguments or parses its own response shape. Here the vendor
client is real and only the HTTP transport is mocked: no network and a fake key.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from learning_commons_evaluators.errors import (
    AuthenticationError,
    ConfigurationError,
    DependencyId,
    LLMOutputProcessingError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
    wrap_provider_error,
)
from learning_commons_evaluators.providers import ImageAttachment, Message, Provider, ProviderConfig
from learning_commons_evaluators.providers.anthropic_sdk import (
    DEFAULT_MAX_TOKENS,
    AnthropicProvider,
)
from learning_commons_evaluators.providers.google_genai import (
    THINKING_LEVEL_SINCE,
    GoogleProvider,
)
from learning_commons_evaluators.providers.openai_sdk import OpenAIProvider

PNG = b"\x89PNG\r\n\x1a\nfake"
MODEL = "test-model"
VERDICT = '{"score": 3, "reasoning": "fine"}'


class _Verdict(BaseModel):
    score: int
    reasoning: str


MESSAGES: list[Message] = [
    {"role": "system", "content": "You grade things."},
    {"role": "user", "content": "Grade this."},
]
IMAGE = ImageAttachment(data=PNG, media_type="image/png", position="before_text")

#: The reasoning efforts config.schema.json admits per provider, read from it, each of which
#: must reach the wire unchanged through the installed vendor SDK, the lowest one included.
_DEFS = json.loads(
    (Path(__file__).resolve().parents[5] / "evals/_schemas/config.schema.json").read_text(
        encoding="utf-8"
    )
)["$defs"]
OPENAI_EFFORTS: list[str] = _DEFS["ReasoningEffortOpenAI"]["enum"]
ANTHROPIC_EFFORTS: list[str] = _DEFS["ReasoningEffortAnthropic"]["enum"]
GOOGLE_EFFORTS: list[str] = _DEFS["ReasoningEffortGoogle"]["enum"]


class _Wire:
    """A mock transport that records each request's path and JSON body and replies once."""

    def __init__(self, httpx_module: Any, status: int = 200, body: Any = None, **headers: str):
        self.module = httpx_module
        self.status, self.body, self.headers = status, body, headers
        #: Name of an httpx exception class to raise from the transport instead of replying.
        self.failure: str | None = None
        self.paths: list[str] = []
        self.bodies: list[dict[str, Any]] = []
        self.transport = httpx_module.MockTransport(self._reply)

    def _reply(self, request: Any) -> Any:
        if self.failure is not None:
            raise getattr(self.module, self.failure)("transport failed", request=request)
        self.paths.append(request.url.path)
        self.bodies.append(json.loads(request.content))
        return self.module.Response(self.status, json=self.body, headers=self.headers)

    @property
    def sent(self) -> dict[str, Any]:
        assert len(self.bodies) == 1
        return self.bodies[0]


def _config(provider: Provider) -> ProviderConfig:
    return ProviderConfig(type=provider, model=MODEL, api_key="fake-key", max_retries=0)


def _sdk_httpx(client_class: type) -> Any:
    """The httpx module the SDK itself transports over (``httpx`` or ``httpx2``)."""
    return importlib.import_module(client_class.__mro__[1].__module__.split(".")[0])


# ── OpenAI ────────────────────────────────────────────────────────────────────


def _openai_body(
    text: str = VERDICT, status: str = "completed", incomplete: str | None = None
) -> dict[str, Any]:
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 0,
        "model": MODEL,
        "status": status,
        "incomplete_details": {"reason": incomplete} if incomplete else None,
        "output": [
            {
                "type": "message",
                "id": "msg_1",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "usage": {
            "input_tokens": 11,
            "output_tokens": 7,
            "total_tokens": 18,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
    }


def _openai(status: int = 200, body: Any = None, **headers: str) -> tuple[OpenAIProvider, _Wire]:
    from openai import AsyncOpenAI, DefaultAsyncHttpxClient

    wire = _Wire(_sdk_httpx(DefaultAsyncHttpxClient), status, body, **headers)
    client = AsyncOpenAI(
        api_key="fake-key",
        max_retries=0,
        http_client=DefaultAsyncHttpxClient(transport=wire.transport),
    )
    return OpenAIProvider(_config(Provider.OPENAI), client=client), wire


class TestOpenAI:
    async def test_structured_request_and_response(self) -> None:
        adapter, wire = _openai(body=_openai_body())
        response = await adapter.generate_structured(MESSAGES, _Verdict)
        assert response.data == _Verdict(score=3, reasoning="fine")
        assert (response.usage.input_tokens, response.usage.output_tokens) == (11, 7)
        sent = wire.sent
        assert wire.paths == ["/v1/responses"]
        assert sent["model"] == MODEL
        assert sent["instructions"] == "You grade things."
        assert "temperature" not in sent
        schema = sent["text"]["format"]
        assert schema["type"] == "json_schema"
        assert set(schema["schema"]["properties"]) == {"score", "reasoning"}

    async def test_sends_temperature_and_max_tokens_when_given(self) -> None:
        adapter, wire = _openai(body=_openai_body())
        await adapter.generate_structured(MESSAGES, _Verdict, temperature=0.0, max_tokens=50)
        assert wire.sent["temperature"] == 0.0
        assert wire.sent["max_output_tokens"] == 50

    @pytest.mark.parametrize("effort", OPENAI_EFFORTS)
    async def test_a_reasoning_effort_is_sent_as_reasoning_effort(self, effort: str) -> None:
        adapter, wire = _openai(body=_openai_body())
        await adapter.generate_structured(MESSAGES, _Verdict, reasoning_effort=effort)
        assert wire.sent["reasoning"] == {"effort": effort}

    async def test_no_reasoning_effort_sends_no_reasoning(self) -> None:
        adapter, wire = _openai(body=_openai_body())
        await adapter.generate_structured(MESSAGES, _Verdict)
        assert "reasoning" not in wire.sent

    async def test_generate_text_sends_a_reasoning_effort(self) -> None:
        adapter, wire = _openai(body=_openai_body(text="hello"))
        await adapter.generate_text(MESSAGES, reasoning_effort="low")
        assert wire.sent["reasoning"] == {"effort": "low"}

    async def test_a_completion_cut_off_at_the_limit_is_truncated(self) -> None:
        body = _openai_body(text='{"score": 3, "rea', status="incomplete")
        body["incomplete_details"] = {"reason": "max_output_tokens"}
        adapter, _ = _openai(body=body)
        with pytest.raises(LLMOutputProcessingError, match="max_tokens=9"):
            await adapter.generate_structured(MESSAGES, _Verdict, max_tokens=9)

    async def test_generate_text_sends_the_cap_as_max_output_tokens(self) -> None:
        adapter, wire = _openai(body=_openai_body(text="hello"))
        await adapter.generate_text(MESSAGES, max_tokens=700)
        assert wire.sent["max_output_tokens"] == 700

    async def test_generate_text_sends_no_cap_when_none_is_given(self) -> None:
        adapter, wire = _openai(body=_openai_body(text="hello"))
        await adapter.generate_text(MESSAGES)
        assert "max_output_tokens" not in wire.sent

    async def test_prose_cut_off_at_the_limit_is_truncated(self) -> None:
        body = _openai_body(
            text="The text assumes", status="incomplete", incomplete="max_output_tokens"
        )
        adapter, _ = _openai(body=body)
        with pytest.raises(LLMOutputProcessingError, match="max_tokens=9") as exc_info:
            await adapter.generate_text(MESSAGES, temperature=0.0, max_tokens=9)
        assert exc_info.value.retryable is False

    async def test_generate_text(self) -> None:
        adapter, wire = _openai(body=_openai_body(text="hello"))
        response = await adapter.generate_text(MESSAGES)
        assert response.text == "hello"
        assert response.usage.output_tokens == 7
        assert "temperature" not in wire.sent

    async def test_an_image_is_sent_as_an_input_image_part(self) -> None:
        adapter, wire = _openai(body=_openai_body())
        await adapter.generate_structured(MESSAGES, _Verdict, attachments=[IMAGE])
        parts = wire.sent["input"][0]["content"]
        assert [p["type"] for p in parts] == ["input_image", "input_text"]
        assert parts[0]["image_url"].startswith("data:image/png;base64,")

    async def test_error_statuses_are_classified(self) -> None:
        await _classify(_openai, "openai", {"error": {"message": "x"}})

    async def test_transport_failures_are_classified(self) -> None:
        await _classify_transport(_openai, "openai")


# ── Anthropic ─────────────────────────────────────────────────────────────────


def _anthropic_body(text: str = VERDICT, stop_reason: str = "end_turn") -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": MODEL,
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 11, "output_tokens": 7},
    }


def _anthropic(
    status: int = 200, body: Any = None, **headers: str
) -> tuple[AnthropicProvider, _Wire]:
    from anthropic import AsyncAnthropic, DefaultAsyncHttpxClient

    wire = _Wire(_sdk_httpx(DefaultAsyncHttpxClient), status, body, **headers)
    client = AsyncAnthropic(
        api_key="fake-key",
        max_retries=0,
        http_client=DefaultAsyncHttpxClient(transport=wire.transport),
    )
    return AnthropicProvider(_config(Provider.ANTHROPIC), client=client), wire


class TestAnthropic:
    async def test_structured_request_and_response(self) -> None:
        adapter, wire = _anthropic(body=_anthropic_body())
        response = await adapter.generate_structured(MESSAGES, _Verdict)
        assert response.data == _Verdict(score=3, reasoning="fine")
        assert (response.usage.input_tokens, response.usage.output_tokens) == (11, 7)
        sent = wire.sent
        assert wire.paths == ["/v1/messages"]
        assert sent["model"] == MODEL
        assert sent["system"] == "You grade things."
        assert sent["max_tokens"] == DEFAULT_MAX_TOKENS
        assert "temperature" not in sent
        output_format = sent["output_config"]["format"]
        assert output_format["type"] == "json_schema"
        assert set(output_format["schema"]["properties"]) == {"score", "reasoning"}

    async def test_temperature_travels_in_the_body(self) -> None:
        adapter, wire = _anthropic(body=_anthropic_body())
        await adapter.generate_structured(MESSAGES, _Verdict, temperature=0.0, max_tokens=50)
        assert wire.sent["temperature"] == 0.0
        assert wire.sent["max_tokens"] == 50

    @pytest.mark.parametrize("effort", ANTHROPIC_EFFORTS)
    async def test_a_reasoning_effort_shares_output_config_with_the_format(
        self, effort: str
    ) -> None:
        adapter, wire = _anthropic(body=_anthropic_body())
        await adapter.generate_structured(MESSAGES, _Verdict, reasoning_effort=effort)
        output_config = wire.sent["output_config"]
        assert output_config["effort"] == effort
        assert output_config["format"]["type"] == "json_schema"

    async def test_no_reasoning_effort_sends_no_effort(self) -> None:
        adapter, wire = _anthropic(body=_anthropic_body())
        await adapter.generate_structured(MESSAGES, _Verdict)
        assert "effort" not in wire.sent["output_config"]

    async def test_generate_text_sends_a_reasoning_effort(self) -> None:
        adapter, wire = _anthropic(body=_anthropic_body(text="hello"))
        await adapter.generate_text(MESSAGES, reasoning_effort="low")
        assert wire.sent["output_config"] == {"effort": "low"}

    async def test_a_completion_cut_off_at_the_limit_is_truncated(self) -> None:
        body = _anthropic_body(text='{"score": 3, "rea', stop_reason="max_tokens")
        adapter, _ = _anthropic(body=body)
        with pytest.raises(LLMOutputProcessingError, match="max_tokens=9"):
            await adapter.generate_structured(MESSAGES, _Verdict, max_tokens=9)

    async def test_generate_text_sends_the_cap_as_max_tokens(self) -> None:
        adapter, wire = _anthropic(body=_anthropic_body(text="hello"))
        await adapter.generate_text(MESSAGES, max_tokens=700)
        assert wire.sent["max_tokens"] == 700

    async def test_generate_text_sends_the_default_when_no_cap_is_given(self) -> None:
        adapter, wire = _anthropic(body=_anthropic_body(text="hello"))
        await adapter.generate_text(MESSAGES)
        assert wire.sent["max_tokens"] == DEFAULT_MAX_TOKENS

    async def test_prose_cut_off_at_the_limit_is_truncated(self) -> None:
        body = _anthropic_body(text="The text assumes", stop_reason="max_tokens")
        adapter, _ = _anthropic(body=body)
        with pytest.raises(LLMOutputProcessingError, match="max_tokens=9") as exc_info:
            await adapter.generate_text(MESSAGES, temperature=0.0, max_tokens=9)
        assert exc_info.value.retryable is False

    async def test_generate_text(self) -> None:
        adapter, wire = _anthropic(body=_anthropic_body(text="hello"))
        response = await adapter.generate_text(MESSAGES)
        assert response.text == "hello"
        assert response.usage.input_tokens == 11
        assert "output_config" not in wire.sent

    async def test_an_image_is_sent_as_an_image_block(self) -> None:
        adapter, wire = _anthropic(body=_anthropic_body())
        await adapter.generate_structured(MESSAGES, _Verdict, attachments=[IMAGE])
        blocks = wire.sent["messages"][0]["content"]
        assert [b["type"] for b in blocks] == ["image", "text"]
        assert blocks[0]["source"]["media_type"] == "image/png"

    async def test_error_statuses_are_classified(self) -> None:
        await _classify(_anthropic, "anthropic", {"type": "error", "error": {"type": "x"}})

    async def test_transport_failures_are_classified(self) -> None:
        await _classify_transport(_anthropic, "anthropic")


# ── Google ────────────────────────────────────────────────────────────────────


def _google_body(text: str = VERDICT, finish: str = "STOP") -> dict[str, Any]:
    return {
        "candidates": [
            {"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": finish}
        ],
        "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7, "totalTokenCount": 18},
    }


def _google(status: int = 200, body: Any = None, **headers: str) -> tuple[GoogleProvider, _Wire]:
    from google.genai import Client, types

    # google-genai transports over httpx 0.x and takes the async transport through
    # ``async_client_args``, which is passed to ``httpx.AsyncClient``.
    wire = _Wire(httpx, status, body, **headers)
    client = Client(
        api_key="fake-key",
        http_options=types.HttpOptions(async_client_args={"transport": wire.transport}),
    )
    return GoogleProvider(_config(Provider.GOOGLE), client=client), wire


def _google_can_send(effort: str) -> bool:
    """Whether the installed google-genai has this thinking level (1.51.0 LOW and HIGH,
    1.56.0 all four)."""
    from google.genai import types

    levels = getattr(types, "ThinkingLevel", None)
    return levels is not None and effort.upper() in levels.__members__


def _thinking_level(wire: _Wire) -> str:
    # The SDK sends ``thinkingConfig``'s own keys unconverted, as ``thinking_level``; the API
    # takes either spelling.
    thinking = wire.sent["generationConfig"]["thinkingConfig"]
    assert len(thinking) == 1
    return str(thinking.get("thinkingLevel") or thinking.get("thinking_level"))


class TestGoogle:
    async def test_structured_request_and_response(self) -> None:
        adapter, wire = _google(body=_google_body())
        response = await adapter.generate_structured(MESSAGES, _Verdict)
        assert response.data == _Verdict(score=3, reasoning="fine")
        assert (response.usage.input_tokens, response.usage.output_tokens) == (11, 7)
        sent = wire.sent
        assert wire.paths[0].endswith(f"models/{MODEL}:generateContent")
        assert sent["systemInstruction"]["parts"][0]["text"] == "You grade things."
        config = sent["generationConfig"]
        assert config["responseMimeType"] == "application/json"
        assert set(config["responseJsonSchema"]["properties"]) == {"score", "reasoning"}
        assert "temperature" not in config

    async def test_sends_temperature_and_max_tokens_when_given(self) -> None:
        adapter, wire = _google(body=_google_body())
        await adapter.generate_structured(MESSAGES, _Verdict, temperature=0.0, max_tokens=50)
        assert wire.sent["generationConfig"]["temperature"] == 0.0
        assert wire.sent["generationConfig"]["maxOutputTokens"] == 50

    @pytest.mark.parametrize("effort", GOOGLE_EFFORTS)
    async def test_a_reasoning_effort_is_sent_as_thinking_level(self, effort: str) -> None:
        # Below THINKING_LEVEL_SINCE the installed SDK cannot send it, and the adapter says
        # so before any request; the lowest-vendor-SDKs job runs that branch.
        adapter, wire = _google(body=_google_body())
        if not _google_can_send(effort):
            with pytest.raises(ConfigurationError, match=f"google-genai {THINKING_LEVEL_SINCE}"):
                await adapter.generate_structured(MESSAGES, _Verdict, reasoning_effort=effort)
            assert wire.bodies == []
            return
        await adapter.generate_structured(MESSAGES, _Verdict, reasoning_effort=effort)
        assert _thinking_level(wire) == effort.upper()

    async def test_an_sdk_without_the_level_refuses_before_any_request(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from google.genai import types

        # Whatever is installed, as a release that predates thinking_level.
        monkeypatch.delattr(types, "ThinkingLevel", raising=False)
        adapter, wire = _google(body=_google_body())
        with pytest.raises(ConfigurationError, match=f"google-genai {THINKING_LEVEL_SINCE}"):
            await adapter.generate_structured(MESSAGES, _Verdict, reasoning_effort="high")
        assert wire.bodies == []

    async def test_no_reasoning_effort_sends_no_thinking_config(self) -> None:
        adapter, wire = _google(body=_google_body())
        await adapter.generate_structured(MESSAGES, _Verdict)
        assert "thinkingConfig" not in wire.sent["generationConfig"]

    async def test_generate_text_sends_a_reasoning_effort(self) -> None:
        adapter, wire = _google(body=_google_body(text="hello"))
        if not _google_can_send("low"):
            with pytest.raises(ConfigurationError):
                await adapter.generate_text(MESSAGES, reasoning_effort="low")
            return
        await adapter.generate_text(MESSAGES, reasoning_effort="low")
        assert _thinking_level(wire) == "LOW"

    async def test_a_completion_cut_off_at_the_limit_is_truncated(self) -> None:
        body = _google_body(text='{"score": 3, "rea', finish="MAX_TOKENS")
        adapter, _ = _google(body=body)
        with pytest.raises(LLMOutputProcessingError, match="max_tokens=9"):
            await adapter.generate_structured(MESSAGES, _Verdict, max_tokens=9)

    async def test_generate_text_sends_the_cap_as_max_output_tokens(self) -> None:
        adapter, wire = _google(body=_google_body(text="hello"))
        await adapter.generate_text(MESSAGES, max_tokens=700)
        assert wire.sent["generationConfig"]["maxOutputTokens"] == 700

    async def test_generate_text_sends_no_cap_when_none_is_given(self) -> None:
        adapter, wire = _google(body=_google_body(text="hello"))
        await adapter.generate_text(MESSAGES)
        assert "maxOutputTokens" not in wire.sent.get("generationConfig", {})

    async def test_prose_cut_off_at_the_limit_is_truncated(self) -> None:
        body = _google_body(text="The text assumes", finish="MAX_TOKENS")
        adapter, _ = _google(body=body)
        with pytest.raises(LLMOutputProcessingError, match="max_tokens=9") as exc_info:
            await adapter.generate_text(MESSAGES, temperature=0.0, max_tokens=9)
        assert exc_info.value.retryable is False

    async def test_generate_text(self) -> None:
        adapter, wire = _google(body=_google_body(text="hello"))
        response = await adapter.generate_text(MESSAGES)
        assert response.text == "hello"
        assert response.usage.input_tokens == 11
        assert "responseJsonSchema" not in wire.sent.get("generationConfig", {})

    async def test_an_image_is_sent_as_an_inline_data_part(self) -> None:
        adapter, wire = _google(body=_google_body())
        await adapter.generate_structured(MESSAGES, _Verdict, attachments=[IMAGE])
        parts = wire.sent["contents"][0]["parts"]
        # The SDK has spelled the key both ``mimeType`` and ``mime_type``; the API takes either.
        inline = parts[0]["inlineData"]
        assert (inline.get("mimeType") or inline.get("mime_type")) == "image/png"
        assert parts[1]["text"] == "Grade this."

    async def test_error_statuses_are_classified(self) -> None:
        await _classify(_google, "google", {"error": {"code": 0, "message": "x", "status": "X"}})

    async def test_transport_failures_are_classified(self) -> None:
        await _classify_transport(_google, "google")


# ── Client lifecycle ──────────────────────────────────────────────────────────


class TestAdapterBuiltClients:
    """The clients the adapters build themselves are real, so closing them is checked here."""

    async def test_openai_client_is_closed_on_the_way_out(self) -> None:
        async with OpenAIProvider(_config(Provider.OPENAI))._session() as client:
            assert not client.is_closed()
        assert client.is_closed()

    async def test_anthropic_client_is_closed_on_the_way_out(self) -> None:
        async with AnthropicProvider(_config(Provider.ANTHROPIC))._session() as client:
            assert not client.is_closed()
        assert client.is_closed()

    async def test_google_client_is_closed_on_the_way_out(self) -> None:
        # ``Client.close`` and ``AsyncClient.aclose`` are what the adapter calls on exit.
        async with GoogleProvider(_config(Provider.GOOGLE))._session():
            pass


# ── Error classification ──────────────────────────────────────────────────────


async def _classify(
    build: Callable[..., tuple[Any, _Wire]], dependency: DependencyId, body: dict[str, Any]
) -> None:
    """A real client's 401 and 429 (with ``retry-after``) classify through the taxonomy."""
    adapter, _ = build(status=401, body=body)
    with pytest.raises(Exception) as unauthorized:
        await adapter.generate_text(MESSAGES)
    wrapped = wrap_provider_error(unauthorized.value, dependency=dependency, model=MODEL)
    assert isinstance(wrapped, AuthenticationError)
    assert wrapped.status_code == 401

    adapter, _ = build(status=429, body=body, **{"retry-after": "2"})
    with pytest.raises(Exception) as limited:
        await adapter.generate_text(MESSAGES)
    wrapped = wrap_provider_error(limited.value, dependency=dependency, model=MODEL)
    assert isinstance(wrapped, RateLimitError)
    assert wrapped.retry_after_ms == 2000


async def _classify_transport(
    build: Callable[..., tuple[Any, _Wire]], dependency: DependencyId
) -> None:
    """A timeout and a refused connection raised by the transport classify as retryable."""
    for failure, expected in (("ReadTimeout", RequestTimeoutError), ("ConnectError", NetworkError)):
        adapter, wire = build()
        wire.failure = failure
        with pytest.raises(Exception) as raised:
            await adapter.generate_text(MESSAGES)
        wrapped = wrap_provider_error(raised.value, dependency=dependency, model=MODEL)
        assert isinstance(wrapped, expected)
        assert wrapped.retryable is True
