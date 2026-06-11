"""Tests for PhoenixTracingAdapter using InMemorySpanExporter."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from learning_commons_evaluators.schemas.llm_provider import GenerateConfig, LLMResponse
from learning_commons_arize_scorers import PhoenixTracingAdapter


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def exporter() -> InMemorySpanExporter:
    return InMemorySpanExporter()


@pytest.fixture()
def tracer(exporter: InMemorySpanExporter):
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider.get_tracer("test")


def _make_response(
    content: str = "The answer is 42.",
    model: str = "claude-test",
    input_tokens: int | None = 10,
    output_tokens: int | None = 5,
) -> LLMResponse:
    return LLMResponse(
        content=content,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _make_inner(response: LLMResponse | None = None, side_effect=None) -> AsyncMock:
    mock = AsyncMock()
    mock.generate = AsyncMock(
        return_value=response or _make_response(),
        side_effect=side_effect,
    )
    return mock


# ── Basic span emission ───────────────────────────────────────────────────────


class TestPhoenixTracingAdapterSpans:
    async def test_emits_one_span_per_call(self, tracer, exporter):
        inner = _make_inner()
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        await adapter.generate(system="You are helpful.", human="What is 6×7?")
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "llm.generate"

    async def test_span_kind_attribute(self, tracer, exporter):
        inner = _make_inner()
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        await adapter.generate(system="sys", human="user")
        span = exporter.get_finished_spans()[0]
        assert span.attributes["openinference.span.kind"] == "LLM"
        assert span.attributes["gen_ai.operation.name"] == "chat"

    async def test_input_message_attributes(self, tracer, exporter):
        inner = _make_inner()
        # capture_message_content=True required — off by default for K-12 privacy compliance
        adapter = PhoenixTracingAdapter(inner, tracer=tracer, capture_message_content=True)
        await adapter.generate(system="Be concise.", human="Hello?")
        attrs = exporter.get_finished_spans()[0].attributes
        assert attrs["llm.input_messages.0.message.role"] == "system"
        assert attrs["llm.input_messages.0.message.content"] == "Be concise."
        assert attrs["llm.input_messages.1.message.role"] == "user"
        assert attrs["llm.input_messages.1.message.content"] == "Hello?"

    async def test_input_message_attributes_absent_by_default(self, tracer, exporter):
        inner = _make_inner()
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)  # capture_message_content=False
        await adapter.generate(system="Be concise.", human="Hello?")
        attrs = exporter.get_finished_spans()[0].attributes
        assert "llm.input_messages.0.message.content" not in attrs
        assert "llm.input_messages.1.message.content" not in attrs

    async def test_output_message_attributes(self, tracer, exporter):
        inner = _make_inner(_make_response(content="Hi there!"))
        adapter = PhoenixTracingAdapter(inner, tracer=tracer, capture_message_content=True)
        await adapter.generate(system="sys", human="user")
        attrs = exporter.get_finished_spans()[0].attributes
        assert attrs["llm.output_messages.0.message.role"] == "assistant"
        assert attrs["llm.output_messages.0.message.content"] == "Hi there!"

    async def test_model_attributes(self, tracer, exporter):
        inner = _make_inner(_make_response(model="claude-opus-4"))
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        await adapter.generate(system="sys", human="user")
        attrs = exporter.get_finished_spans()[0].attributes
        assert attrs["gen_ai.response.model"] == "claude-opus-4"
        assert attrs["llm.model_name"] == "claude-opus-4"

    async def test_token_count_attributes(self, tracer, exporter):
        inner = _make_inner(_make_response(input_tokens=20, output_tokens=8))
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        await adapter.generate(system="sys", human="user")
        attrs = exporter.get_finished_spans()[0].attributes
        assert attrs["gen_ai.usage.input_tokens"] == 20
        assert attrs["llm.token_count.prompt"] == 20
        assert attrs["gen_ai.usage.output_tokens"] == 8
        assert attrs["llm.token_count.completion"] == 8

    async def test_none_token_counts_omitted(self, tracer, exporter):
        inner = _make_inner(_make_response(input_tokens=None, output_tokens=None))
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        await adapter.generate(system="sys", human="user")
        attrs = exporter.get_finished_spans()[0].attributes
        assert "gen_ai.usage.input_tokens" not in attrs
        assert "gen_ai.usage.output_tokens" not in attrs

    async def test_passes_config_to_inner(self, tracer, exporter):
        inner = _make_inner()
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        cfg = GenerateConfig(temperature=0.3, max_tokens=512)
        await adapter.generate(system="sys", human="user", config=cfg)
        inner.generate.assert_called_once_with(system="sys", human="user", config=cfg)

    async def test_returns_inner_response(self, tracer, exporter):
        response = _make_response(content="42", model="gpt-test", input_tokens=3, output_tokens=1)
        inner = _make_inner(response)
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        result = await adapter.generate(system="sys", human="user")
        assert result is response


# ── Exception handling ────────────────────────────────────────────────────────


class TestPhoenixTracingAdapterErrors:
    async def test_exception_is_recorded_on_span(self, tracer, exporter):
        inner = _make_inner(side_effect=RuntimeError("boom"))
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        with pytest.raises(RuntimeError, match="boom"):
            await adapter.generate(system="sys", human="user")
        span = exporter.get_finished_spans()[0]
        events = [e.name for e in span.events]
        assert "exception" in events

    async def test_exception_propagates(self, tracer, exporter):
        inner = _make_inner(side_effect=ValueError("bad input"))
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        with pytest.raises(ValueError, match="bad input"):
            await adapter.generate(system="sys", human="user")

    async def test_span_still_finished_after_exception(self, tracer, exporter):
        inner = _make_inner(side_effect=RuntimeError("fail"))
        adapter = PhoenixTracingAdapter(inner, tracer=tracer)
        with pytest.raises(RuntimeError):
            await adapter.generate(system="sys", human="user")
        assert len(exporter.get_finished_spans()) == 1


# ── Default tracer ────────────────────────────────────────────────────────────


class TestPhoenixTracingAdapterDefaultTracer:
    async def test_uses_default_tracer_when_none_provided(self):
        inner = _make_inner()
        adapter = PhoenixTracingAdapter(inner)
        result = await adapter.generate(system="sys", human="user")
        assert result.content == "The answer is 42."
