"""PhoenixTracingAdapter — decorates any LLMGeneratorProtocol with OpenInference OTel spans."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.trace import Tracer
from opentelemetry.trace.status import Status, StatusCode

from learning_commons_evaluators.schemas.llm_provider import (
    GenerateConfig,
    LLMGeneratorProtocol,
    LLMResponse,
)


class PhoenixTracingAdapter:
    """Decorator adapter: wraps any LLMGeneratorProtocol, emits OpenInference OTel spans.

    Composes with any other adapter::

        from learning_commons_arize_scorers import PhoenixTracingAdapter
        from learning_commons_inspect_scorers.adapter import InspectModelAdapter

        adapter = PhoenixTracingAdapter(InspectModelAdapter("anthropic/claude-opus-4-8"))
        evaluator = GradeLevelAppropriatenessEvaluator(config=..., llm_provider=adapter)

    Args:
        inner: The underlying adapter to delegate generation to.
        tracer: OTel Tracer instance. Defaults to a tracer named
                ``"learning_commons_arize_scorers"``.
        capture_message_content: If ``True``, writes system and human prompt text
                and the model response into span attributes. Defaults to ``False``.

                .. warning::
                    Enabling this may capture student-submitted text and other PII
                    into your observability backend. Ensure your data handling
                    controls (FERPA, COPPA for K-12) permit this before enabling.
    """

    def __init__(
        self,
        inner: LLMGeneratorProtocol,
        tracer: Tracer | None = None,
        *,
        capture_message_content: bool = False,
    ) -> None:
        self._inner = inner
        self._tracer = tracer or trace.get_tracer("learning_commons_arize_scorers")
        self._capture_message_content = capture_message_content

    async def generate(
        self, *, system: str, human: str, config: GenerateConfig | None = None
    ) -> LLMResponse:
        with self._tracer.start_as_current_span("llm.generate") as span:
            span.set_attribute("openinference.span.kind", "LLM")
            span.set_attribute("gen_ai.operation.name", "chat")
            if self._capture_message_content:
                span.set_attribute("llm.input_messages.0.message.role", "system")
                span.set_attribute("llm.input_messages.0.message.content", system)
                span.set_attribute("llm.input_messages.1.message.role", "user")
                span.set_attribute("llm.input_messages.1.message.content", human)
            try:
                response = await self._inner.generate(system=system, human=human, config=config)
                span.set_attribute("gen_ai.response.model", response.model)
                span.set_attribute("llm.model_name", response.model)
                if response.input_tokens is not None:
                    span.set_attribute("gen_ai.usage.input_tokens", response.input_tokens)
                    span.set_attribute("llm.token_count.prompt", response.input_tokens)
                if response.output_tokens is not None:
                    span.set_attribute("gen_ai.usage.output_tokens", response.output_tokens)
                    span.set_attribute("llm.token_count.completion", response.output_tokens)
                if self._capture_message_content:
                    span.set_attribute("llm.output_messages.0.message.role", "assistant")
                    span.set_attribute("llm.output_messages.0.message.content", response.content)
                return response
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
