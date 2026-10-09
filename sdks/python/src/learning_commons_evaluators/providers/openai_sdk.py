"""OpenAI adapter over the native ``openai`` SDK (D10).

Structured output uses the Responses API's ``parse`` with a pydantic model as
``text_format``: the SDK sends the model's JSON schema in strict mode and validates the
completion against it, so a payload the schema rejects surfaces as a typed failure rather
than a coerced object.

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
    around_text,
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
    from openai import AsyncOpenAI

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider:
    """``LLMProvider`` for OpenAI models."""

    supports_attachments = True

    def __init__(self, config: ProviderConfig, *, client: AsyncOpenAI | None = None) -> None:
        model, api_key = require_config(config, Provider.OPENAI)
        self._model = model
        self.label = provider_label(Provider.OPENAI, model)
        #: A client the caller handed in, used for every call and never closed: its owner
        #: decides its lifetime.
        self._client = client
        self._new_client: Callable[[], AsyncOpenAI] | None = None
        if client is None:
            from openai import AsyncOpenAI

            self._new_client = partial(AsyncOpenAI, api_key=api_key, max_retries=config.max_retries)

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[AsyncOpenAI]:
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
        from openai import omit

        system, rest = split_system(messages)
        turns: list[dict[str, Any]] = [{"role": m["role"], "content": m["content"]} for m in rest]
        if attachments:
            # Each image is an ``input_image`` part carrying a base64 data URL. ``detail`` is
            # the API's own default, written out because the SDK's type requires it; the
            # TypeScript SDK sends none and so gets the same.
            index = last_user_turn(rest)
            turns[index]["content"] = around_text(
                {"type": "input_text", "text": rest[index]["content"]},
                attachments,
                lambda a: {
                    "type": "input_image",
                    "image_url": f"data:{a.media_type};base64,{base64_data(a)}",
                    "detail": "auto",
                },
            )
        return {
            "model": self._model,
            "input": turns,
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
        attachments: Sequence[ImageAttachment] = (),
    ) -> LLMResponse[T]:
        start = time.perf_counter()
        async with self._session() as client:
            response = await client.responses.parse(
                text_format=schema, **self._request(messages, temperature, max_tokens, attachments)
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
        async with self._session() as client:
            response = await client.responses.create(
                **self._request(messages, temperature, max_tokens)
            )
        return TextGenerationResponse(
            text=response.output_text,
            usage=self._usage(response),
            latency_ms=elapsed_ms(start),
        )


__all__ = ["OpenAIProvider"]
