"""Anthropic adapter over the native ``anthropic`` SDK (D10).

Structured output uses ``messages.parse`` with a pydantic model as ``output_format``: the
SDK sends the schema as the message's JSON output format and validates the completion
against it. Anthropic requires ``max_tokens``; a request that names none gets
:data:`DEFAULT_MAX_TOKENS`, the same ceiling the TypeScript SDK's Anthropic adapter applies.
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
    from anthropic import AsyncAnthropic

T = TypeVar("T", bound=BaseModel)

#: Output ceiling when the caller names none. Anthropic makes the parameter mandatory.
DEFAULT_MAX_TOKENS = 4096


class AnthropicProvider:
    """``LLMProvider`` for Anthropic models."""

    def __init__(self, config: ProviderConfig, *, client: AsyncAnthropic | None = None) -> None:
        model, api_key = require_config(config, Provider.ANTHROPIC)
        self._model = model
        self.label = provider_label(Provider.ANTHROPIC, model)
        if client is None:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=api_key, max_retries=config.max_retries)
        self._client = client

    def _request(
        self,
        messages: Sequence[Message],
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict[str, Any]:
        from anthropic import omit

        system, rest = split_system(messages)
        request: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS,
            "messages": [{"role": m["role"], "content": m["content"]} for m in rest],
            "system": system if system is not None else omit,
        }
        # The SDK no longer exposes ``temperature`` as a parameter, since the newest Claude
        # models reject it; the contract still pins one for the models that accept it, so it
        # travels in the body. None sends nothing (config.schema.json's ``null``).
        if temperature is not None:
            request["extra_body"] = {"temperature": temperature}
        return request

    @staticmethod
    def _usage(message: Any) -> TokenUsage:
        usage = getattr(message, "usage", None)
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
        message = await self._client.messages.parse(
            output_format=schema, **self._request(messages, temperature, max_tokens)
        )
        parsed = message.parsed_output
        if parsed is None:
            # Truncation (``max_tokens``) and refusals both end without a parseable block;
            # the stop reason says which.
            raise no_structured_output(self.label, getattr(message, "stop_reason", None))
        return LLMResponse(
            data=parsed,
            model=self._model,
            usage=self._usage(message),
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
        message = await self._client.messages.create(
            **self._request(messages, temperature, max_tokens)
        )
        text = "".join(
            getattr(block, "text", "") for block in message.content if block.type == "text"
        )
        return TextGenerationResponse(
            text=text,
            usage=self._usage(message),
            latency_ms=elapsed_ms(start),
        )


__all__ = ["DEFAULT_MAX_TOKENS", "AnthropicProvider"]
