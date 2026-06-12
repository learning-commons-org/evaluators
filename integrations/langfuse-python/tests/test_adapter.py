"""Tests for LangfuseTracingAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from learning_commons_evaluators.schemas.llm_provider import GenerateConfig, LLMResponse
from learning_commons_langfuse_scorers import LangfuseTracingAdapter


def _make_mock_langfuse() -> MagicMock:
    """Return a Langfuse mock with the trace/generation chain wired up."""
    mock_generation = MagicMock()
    mock_trace = MagicMock()
    mock_trace.generation.return_value = mock_generation
    mock_langfuse = MagicMock()
    mock_langfuse.trace.return_value = mock_trace
    return mock_langfuse


def _make_inner(response: LLMResponse | None = None, side_effect=None) -> MagicMock:
    if response is None:
        response = LLMResponse(
            content='{"score": "6-8"}',
            model="claude-opus-4-8",
            input_tokens=10,
            output_tokens=20,
        )
    inner = MagicMock()
    inner.generate = AsyncMock(return_value=response, side_effect=side_effect)
    return inner


class TestLangfuseTracingAdapterInit:
    def test_creates_langfuse_when_not_provided(self):
        inner = _make_inner()
        with patch("learning_commons_langfuse_scorers.adapter.Langfuse") as mock_cls:
            mock_cls.return_value = MagicMock()
            adapter = LangfuseTracingAdapter(inner)
        mock_cls.assert_called_once_with()
        assert adapter._inner is inner

    def test_uses_provided_langfuse_instance(self):
        inner = _make_inner()
        mock_langfuse = _make_mock_langfuse()
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)
        assert adapter._langfuse is mock_langfuse

    def test_default_trace_name(self):
        inner = _make_inner()
        mock_langfuse = _make_mock_langfuse()
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)
        assert adapter._trace_name == "lc_eval"

    def test_custom_trace_name(self):
        inner = _make_inner()
        mock_langfuse = _make_mock_langfuse()
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse, trace_name="my_eval")
        assert adapter._trace_name == "my_eval"


class TestLangfuseTracingAdapterGenerate:
    async def test_creates_trace_with_configured_name(self):
        inner = _make_inner()
        mock_langfuse = _make_mock_langfuse()
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse, trace_name="my_trace")

        await adapter.generate(system="You are a grader.", human="Assess this text.")

        mock_langfuse.trace.assert_called_once_with(name="my_trace")

    async def test_creates_generation_with_correct_input(self):
        inner = _make_inner()
        mock_langfuse = _make_mock_langfuse()
        mock_trace = mock_langfuse.trace.return_value
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)

        await adapter.generate(system="sys prompt", human="user prompt")

        mock_trace.generation.assert_called_once()
        call_kwargs = mock_trace.generation.call_args[1]
        assert call_kwargs["name"] == "llm_generate"
        assert call_kwargs["input"] == [
            {"role": "system", "content": "sys prompt"},
            {"role": "user", "content": "user prompt"},
        ]

    async def test_passes_config_model_parameters(self):
        inner = _make_inner()
        mock_langfuse = _make_mock_langfuse()
        mock_trace = mock_langfuse.trace.return_value
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)
        config = GenerateConfig(temperature=0.7, max_tokens=256)

        await adapter.generate(system="s", human="h", config=config)

        call_kwargs = mock_trace.generation.call_args[1]
        assert call_kwargs["model_parameters"] == {"temperature": 0.7, "max_tokens": 256}

    async def test_none_config_sends_none_parameters(self):
        inner = _make_inner()
        mock_langfuse = _make_mock_langfuse()
        mock_trace = mock_langfuse.trace.return_value
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)

        await adapter.generate(system="s", human="h", config=None)

        call_kwargs = mock_trace.generation.call_args[1]
        # None values are filtered out — model_parameters is empty when config is None
        assert call_kwargs["model_parameters"] == {}

    async def test_calls_inner_generate_with_correct_args(self):
        inner = _make_inner()
        mock_langfuse = _make_mock_langfuse()
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)
        config = GenerateConfig(temperature=0.0, max_tokens=128)

        await adapter.generate(system="sys", human="usr", config=config)

        inner.generate.assert_called_once_with(system="sys", human="usr", config=config)

    async def test_returns_inner_response(self):
        response = LLMResponse(
            content="result", model="gpt-4", input_tokens=5, output_tokens=15
        )
        inner = _make_inner(response=response)
        mock_langfuse = _make_mock_langfuse()
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)

        result = await adapter.generate(system="s", human="h")

        assert result is response

    async def test_ends_generation_with_response_data(self):
        response = LLMResponse(
            content="the answer", model="claude-opus-4-8", input_tokens=10, output_tokens=20
        )
        inner = _make_inner(response=response)
        mock_langfuse = _make_mock_langfuse()
        mock_generation = mock_langfuse.trace.return_value.generation.return_value
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)

        await adapter.generate(system="s", human="h")

        mock_generation.end.assert_called_once_with(
            output="the answer",
            model="claude-opus-4-8",
            usage_details={"input": 10, "output": 20},
        )

    async def test_ends_generation_with_error_on_exception(self):
        inner = _make_inner(side_effect=RuntimeError("timeout"))
        mock_langfuse = _make_mock_langfuse()
        mock_generation = mock_langfuse.trace.return_value.generation.return_value
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)

        with pytest.raises(RuntimeError, match="timeout"):
            await adapter.generate(system="s", human="h")

        mock_generation.end.assert_called_once_with(level="ERROR", status_message="timeout")

    async def test_re_raises_exception_after_recording(self):
        inner = _make_inner(side_effect=ValueError("bad input"))
        mock_langfuse = _make_mock_langfuse()
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)

        with pytest.raises(ValueError, match="bad input"):
            await adapter.generate(system="s", human="h")


class TestLangfuseTracingAdapterAclose:
    async def test_aclose_flushes_langfuse(self):
        inner = _make_inner()
        mock_langfuse = _make_mock_langfuse()
        adapter = LangfuseTracingAdapter(inner, langfuse=mock_langfuse)

        await adapter.aclose()

        mock_langfuse.flush.assert_called_once_with()
