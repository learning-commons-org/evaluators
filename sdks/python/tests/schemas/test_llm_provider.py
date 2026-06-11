"""Tests for LLMGeneratorProtocol, LLMResponse, and GenerateConfig."""

from __future__ import annotations

import learning_commons_evaluators
from learning_commons_evaluators.schemas.llm_provider import (
    GenerateConfig,
    LLMGeneratorProtocol,
    LLMResponse,
)


class TestLLMResponse:
    def test_required_fields(self):
        r = LLMResponse(content="hello", model="anthropic/claude-opus-4-8")
        assert r.content == "hello"
        assert r.model == "anthropic/claude-opus-4-8"
        assert r.input_tokens is None
        assert r.output_tokens is None

    def test_optional_token_fields(self):
        r = LLMResponse(content="text", model="test", input_tokens=100, output_tokens=50)
        assert r.input_tokens == 100
        assert r.output_tokens == 50



class TestGenerateConfig:
    def test_defaults(self):
        c = GenerateConfig()
        assert c.temperature is None
        assert c.max_tokens is None

    def test_with_values(self):
        c = GenerateConfig(temperature=0.0, max_tokens=512)
        assert c.temperature == 0.0
        assert c.max_tokens == 512


class TestLLMGeneratorProtocol:
    async def test_generate_returns_llm_response(self):
        class Adapter:
            async def generate(
                self, *, system: str, human: str, config: GenerateConfig | None = None
            ) -> LLMResponse:
                return LLMResponse(content="hi", model="m", input_tokens=5, output_tokens=2)

        result = await Adapter().generate(system="sys", human="hello")
        assert result.content == "hi"
        assert result.model == "m"
        assert result.input_tokens == 5

    async def test_generate_config_passed_through(self):
        received: list[GenerateConfig | None] = []

        class Adapter:
            async def generate(
                self, *, system: str, human: str, config: GenerateConfig | None = None
            ) -> LLMResponse:
                received.append(config)
                return LLMResponse(content="", model="test")

        cfg = GenerateConfig(temperature=0.0, max_tokens=256)
        await Adapter().generate(system="sys", human="hello", config=cfg)
        assert received[0] is cfg
        assert received[0].temperature == 0.0

    async def test_generate_config_none_by_default(self):
        received: list[GenerateConfig | None] = []

        class Adapter:
            async def generate(
                self, *, system: str, human: str, config: GenerateConfig | None = None
            ) -> LLMResponse:
                received.append(config)
                return LLMResponse(content="", model="test")

        await Adapter().generate(system="sys", human="hello")
        assert received[0] is None

    def test_structural_conformance(self):
        """Static type checkers validate this assignment — no subclassing required.

        LLMGeneratorProtocol is not @runtime_checkable; isinstance() is not available.
        Conformance is enforced at type-check time (mypy/pyright) by the annotation below.
        """

        class Adapter:
            async def generate(
                self,
                *,
                system: str,
                human: str,
                config: GenerateConfig | None = None,
            ) -> LLMResponse:
                return LLMResponse(content="", model="test")

        # mypy/pyright validate this structurally
        _adapter: LLMGeneratorProtocol = Adapter()
        assert _adapter is not None  # runtime no-op; static check is the value


def test_exported_from_package():
    assert "GenerateConfig" in learning_commons_evaluators.__all__
    assert "LLMGeneratorProtocol" in learning_commons_evaluators.__all__
    assert "LLMResponse" in learning_commons_evaluators.__all__
