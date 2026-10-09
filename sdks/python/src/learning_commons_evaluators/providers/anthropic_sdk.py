"""Anthropic adapter over the native ``anthropic`` SDK (D10).

Structured output uses ``messages.parse`` with a pydantic model as ``output_format``: the
SDK sends the schema as the message's JSON output format and validates the completion
against it. Anthropic requires ``max_tokens``; a request that names none gets
:data:`DEFAULT_MAX_TOKENS`, the same ceiling the TypeScript SDK's Anthropic adapter applies.

Each call builds its own client and closes it before returning; see
:class:`~learning_commons_evaluators.providers.base.LLMProvider` for why.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from learning_commons_evaluators.providers._common import (
    base64_data,
    elapsed_ms,
    last_user_turn,
    no_structured_output,
    require_config,
    split_system,
)
from learning_commons_evaluators.providers.base import (
    ImageAttachment,
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

    supports_attachments = True

    def __init__(self, config: ProviderConfig, *, client: AsyncAnthropic | None = None) -> None:
        model, api_key = require_config(config, Provider.ANTHROPIC)
        self._model = model
        self.label = provider_label(Provider.ANTHROPIC, model)
        #: A client the caller handed in, used for every call and never closed: its owner
        #: decides its lifetime.
        self._client = client
        self._new_client: Callable[[], AsyncAnthropic] | None = None
        if client is None:
            from anthropic import AsyncAnthropic

            self._new_client = partial(
                AsyncAnthropic, api_key=api_key, max_retries=config.max_retries
            )

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncAnthropic]:
        """The client for one call: the injected one, or a new one closed on the way out."""
        if self._new_client is None:
            assert self._client is not None
            yield self._client
            return
        async with self._new_client() as client:
            yield client

    def _request(
        self,
        messages: Sequence[Message],
        temperature: float | None,
        max_tokens: int | None,
        attachments: Sequence[ImageAttachment] = (),
    ) -> dict[str, Any]:
        from anthropic import omit

        system, rest = split_system(messages)
        turns: list[dict[str, Any]] = [{"role": m["role"], "content": m["content"]} for m in rest]
        if attachments:
            # Each image is an ``image`` block with a base64 source.
            index = last_user_turn(rest)
            turns[index]["content"] = [
                *(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": a.media_type,
                            "data": base64_data(a),
                        },
                    }
                    for a in attachments
                ),
                {"type": "text", "text": rest[index]["content"]},
            ]
        request: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS,
            "messages": turns,
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
        attachments: Sequence[ImageAttachment] = (),
    ) -> LLMResponse[T]:
        start = time.perf_counter()
        async with self._session() as client:
            message = await client.messages.parse(
                output_format=schema,
                **self._request(messages, temperature, max_tokens, attachments),
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
        async with self._session() as client:
            message = await client.messages.create(
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
