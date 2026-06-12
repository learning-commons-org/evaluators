"""LangfuseTracingAdapter — decorator that wraps any LLMGeneratorProtocol and records Langfuse generations.

.. note::
    This adapter targets the Langfuse v2 SDK (``langfuse>=2.0.0,<3.0.0``).
    Langfuse v3+ replaced ``trace()``/``generation()`` with an OTel-based API
    (``start_as_current_generation()``). A migration is tracked as a TODO.

Usage::

    from learning_commons_langfuse_scorers import LangfuseTracingAdapter
    from learning_commons_inspect_scorers.adapter import InspectModelAdapter

    adapter = LangfuseTracingAdapter(InspectModelAdapter("anthropic/claude-opus-4-8"))
    evaluator = GradeLevelAppropriatenessEvaluator(config=..., llm_provider=adapter)
"""

from __future__ import annotations

import asyncio

from langfuse import Langfuse

from learning_commons_evaluators.schemas.llm_provider import (
    GenerateConfig,
    LLMGeneratorProtocol,
    LLMResponse,
)


class LangfuseTracingAdapter:
    """Decorator adapter: wraps any LLMGeneratorProtocol, records Langfuse generations.

    Args:
        inner: The underlying adapter to delegate generation to.
        langfuse: Langfuse client instance. Defaults to ``Langfuse()``, which
                  reads ``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``, and
                  ``LANGFUSE_HOST`` from the environment.
        trace_name: Name for the Langfuse trace. Default: ``"lc_eval"``.

    .. note::
        Each call to ``generate()`` creates a new Langfuse trace. For single-step
        evaluators (GLA, conventionality) this produces one trace per evaluation.
        For multi-step evaluators (vocabulary: 2 steps), this produces one trace
        per LLM call — the steps appear as separate traces rather than nested
        generations on a single trace. Pass a unique ``trace_name`` per evaluation
        run (e.g. a UUID) if you want to group them by name in the Langfuse UI.
    """

    def __init__(
        self,
        inner: LLMGeneratorProtocol,
        langfuse: Langfuse | None = None,
        trace_name: str = "lc_eval",
    ) -> None:
        self._inner = inner
        self._langfuse = langfuse or Langfuse()
        self._trace_name = trace_name

    async def generate(
        self, *, system: str, human: str, config: GenerateConfig | None = None
    ) -> LLMResponse:
        lf_trace = self._langfuse.trace(name=self._trace_name)
        generation = lf_trace.generation(
            name="llm_generate",
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": human},
            ],
            model_parameters={
                k: v for k, v in {
                    "temperature": config.temperature if config else None,
                    "max_tokens": config.max_tokens if config else None,
                }.items() if v is not None
            },
        )
        try:
            response = await self._inner.generate(system=system, human=human, config=config)
            generation.end(
                output=response.content,
                model=response.model,
                # usage_details is the current Langfuse v2 kwarg; the older `usage` kwarg
                # is silently dropped in recent 2.x releases, losing token counts in the UI.
                usage_details={
                    k: v for k, v in {
                        "input": response.input_tokens,
                        "output": response.output_tokens,
                    }.items() if v is not None
                },
            )
            return response
        except Exception as exc:
            generation.end(level="ERROR", status_message=str(exc))
            raise

    async def aclose(self) -> None:
        """Flush buffered Langfuse events. Offloads the blocking flush to a thread pool."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._langfuse.flush)
