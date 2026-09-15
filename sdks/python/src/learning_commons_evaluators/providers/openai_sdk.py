"""OpenAI adapter over the native ``openai`` SDK (D10).

Structured output uses the Responses API's ``parse`` with a pydantic model as
``text_format``: the SDK sends the model's JSON schema in strict mode and validates the
completion against it, so a payload the schema rejects surfaces as a typed failure rather
than a coerced object.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from learning_commons_evaluators.providers._common import (
    elapsed_ms,
    no_structured_output,
    require_config,
    split_system,
)
from learning_commons_evaluators.providers.base import (
    LLMResponse,
    Message,
    Provider,
    ProviderConfig,
    TextGenerationResponse,
    TokenUsage,
    provider_label,
)

if TYPE_CHECKING:
    from openai import AsyncOpenAI

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider:
    """``LLMProvider`` for OpenAI models."""

    def __init__(self, config: ProviderConfig, *, client: AsyncOpenAI | None = None) -> None:
        model, api_key = require_config(config, Provider.OPENAI)
        self._model = model
        self.label = provider_label(Provider.OPENAI, model)
        if client is None:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key, max_retries=config.max_retries)
        self._client = client

    def _request(
        self,
        messages: Sequence[Message],
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        from openai import omit

        system, rest = split_system(messages)
        return {
            "model": self._model,
            "input": [{"role": m["role"], "content": m["content"]} for m in rest],
            "instructions": system if system is not None else omit,
            # A None temperature means "send nothing" — see config.schema.json for which
            # models require that.
            "temperature": temperature if temperature is not None else omit,
            "max_output_tokens": max_tokens if max_tokens is not None else omit,
        }

    @staticmethod
    def _usage(response: Any) -> TokenUsage:
        usage = getattr(response, "usage", None)
        return TokenUsage(
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )

    async def generate_structured(
        self,
        messages: Sequence[Message],
        schema: type[T],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse[T]:
        start = time.perf_counter()
        response = await self._client.responses.parse(
            text_format=schema, **self._request(messages, temperature, max_tokens)
        )
        parsed = response.output_parsed
        if parsed is None:
            # A refusal or an incomplete completion leaves nothing to parse; the SDK reports
            # why on ``incomplete_details`` when it knows.
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", None)
            raise no_structured_output(self.label, reason or getattr(response, "status", None))
        return LLMResponse(
            data=parsed,
            model=self._model,
            usage=self._usage(response),
            latency_ms=elapsed_ms(start),
        )

    async def generate_text(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> TextGenerationResponse:
        start = time.perf_counter()
        response = await self._client.responses.create(
            **self._request(messages, temperature, max_tokens)
        )
        return TextGenerationResponse(
            text=response.output_text,
            usage=self._usage(response),
            latency_ms=elapsed_ms(start),
        )


__all__ = ["OpenAIProvider"]
