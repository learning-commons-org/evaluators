"""Inspect AI model adapter implementing LLMGeneratorProtocol.

This is a separate package (``learning-commons-inspect-scorers``) rather than
part of ``learning-commons-evaluators`` because it introduces ``inspect-ai`` as
a hard dependency — a heavy framework that not all SDK users need.

**Versioning contract**: this package requires ``learning-commons-evaluators>=0.2.0``
where ``LLMGeneratorProtocol`` was introduced. If a new method is added to the
protocol, bump the lower bound here and update this adapter.

**Building a new integration** (e.g. ``integrations/langsmith-python``):
implement ``LLMGeneratorProtocol`` — a single async ``generate()`` method that
calls your framework's model and returns ``LLMResponse`` — then inject it into
any evaluator via ``GradeLevelAppropriatenessEvaluator(config=..., llm_provider=adapter)``.
"""

from __future__ import annotations

from inspect_ai.model import (
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig as InspectGenConfig,
    get_model,
)

from learning_commons_evaluators.schemas.llm_provider import GenerateConfig, LLMResponse


class InspectModelAdapter:
    """Wraps Inspect's get_model() to satisfy LLMGeneratorProtocol.

    Pass a model string in the same form accepted by Inspect's ``--model`` flag,
    for example ``"anthropic/claude-opus-4-8"`` or ``"openai/gpt-4o"``.

    Example::

        adapter = InspectModelAdapter("anthropic/claude-opus-4-8")
        evaluator = GradeLevelAppropriatenessEvaluator(
            config=create_config_no_telemetry(),
            llm_provider=adapter,
        )
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    async def generate(
        self,
        *,
        system: str,
        human: str,
        config: GenerateConfig | None = None,
    ) -> LLMResponse:
        # get_model() is memoized by Inspect — repeated calls with the same string
        # return the cached Model object without reconstruction.
        inspect_model = get_model(self._model_name)
        inspect_config = InspectGenConfig(
            temperature=config.temperature if config is not None else None,
            max_tokens=config.max_tokens if config is not None else None,
        )
        output = await inspect_model.generate(
            [ChatMessageSystem(content=system), ChatMessageUser(content=human)],
            config=inspect_config,
        )
        return LLMResponse(
            content=output.completion,
            model=self._model_name,
            input_tokens=getattr(output.usage, "input_tokens", None),
            output_tokens=getattr(output.usage, "output_tokens", None),
        )
