"""Anthropic adapter over the native ``anthropic`` SDK (D10).

Structured output sends the pydantic model's JSON schema as the message's output format,
the same one ``messages.parse`` builds, through ``messages.create``, and validates the text
afterwards. That order lets the stop reason be read first: a completion cut off at
``max_tokens`` is reported as truncated rather than as a schema error, and prose cut off
there is reported the same way rather than returned. Anthropic requires
``max_tokens``. A request that names none gets :data:`DEFAULT_MAX_TOKENS`. The TypeScript
adapter sends the model's own ceiling instead (128,000 for ``claude-opus-5``). This client
makes non-streaming calls, which the SDK refuses above 21,333 tokens. The default is 20,000, the higher ceiling we send
pending a team discussion of anything above it.

Each call builds its own client and closes it before returning; see
:class:`~learning_commons_evaluators.providers.base.LLMProvider` for why.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, TypeAdapter

from learning_commons_evaluators.errors import LLMRefusalError
from learning_commons_evaluators.providers._common import (
    around_text,
    base64_data,
    elapsed_ms,
    last_user_turn,
    no_structured_output,
    refused,
    require_config,
    split_system,
    truncated_output,
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
#: A non-streaming call above 21,333 tokens is refused before it is sent. 20,000 is the
#: higher ceiling we send pending a team discussion of anything above it.
DEFAULT_MAX_TOKENS = 20000


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
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        from anthropic import omit

        system, rest = split_system(messages)
        turns: list[dict[str, Any]] = [{"role": m["role"], "content": m["content"]} for m in rest]
        if attachments:
            # Each image is an ``image`` block with a base64 source.
            index = last_user_turn(rest)
            turns[index]["content"] = around_text(
                {"type": "text", "text": rest[index]["content"]},
                attachments,
                lambda a: {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": a.media_type,
                        "data": base64_data(a),
                    },
                },
            )
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
        # ``output_config`` also carries the structured-output format, which
        # ``generate_structured`` adds to this same object. Unset sends nothing, which leaves
        # the model at its default effort.
        if reasoning_effort is not None:
            request["output_config"] = {"effort": reasoning_effort}
        return request

    def _refusal(self, message: Any) -> LLMRefusalError:
        """The error for a message Anthropic stopped with ``stop_reason: "refusal"``.

        The response is HTTP 200 and carries why on ``stop_details``: a ``category`` (for
        example ``reasoning_extraction``) and an ``explanation``. An SDK release that
        declares the field hands it over as a typed object; an older one (0.77.0, the
        oldest supported) keeps it as the raw dictionary, so both shapes are read. Older
        models omit it altogether, so each value may be ``None``.
        """
        details = getattr(message, "stop_details", None)

        def detail(name: str) -> Any:
            if isinstance(details, Mapping):
                return details.get(name)
            return getattr(details, name, None)

        category = detail("category")
        explanation = detail("explanation")
        request_id = getattr(message, "_request_id", None)
        return refused(
            dependency="anthropic",
            model=self._model,
            category=category if isinstance(category, str) else None,
            explanation=explanation if isinstance(explanation, str) else None,
            request_id=request_id if isinstance(request_id, str) else None,
        )

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
        reasoning_effort: str | None = None,
    ) -> LLMResponse[T]:
        from anthropic import transform_schema

        start = time.perf_counter()
        request = self._request(messages, temperature, max_tokens, attachments, reasoning_effort)
        # The JSON output format ``messages.parse`` would send, sent through ``create`` so
        # the stop reason can be read before the text is validated: ``parse`` validates
        # inside the call, and cut-off JSON would surface as a schema error instead.
        output_format = {
            "type": "json_schema",
            "schema": transform_schema(TypeAdapter(schema).json_schema()),
        }
        request["output_config"] = {**request.get("output_config", {}), "format": output_format}
        async with self._session() as client:
            message = await client.messages.create(**request)
        stop_reason = getattr(message, "stop_reason", None)
        if stop_reason == "refusal":
            raise self._refusal(message)
        if stop_reason == "max_tokens":
            raise truncated_output(
                self.label, temperature=temperature, max_tokens=request["max_tokens"]
            )
        text = "".join(
            getattr(block, "text", "") for block in message.content if block.type == "text"
        )
        if not text.strip():
            # An empty completion that is not a refusal; the stop reason is all there is.
            raise no_structured_output(self.label, stop_reason)
        # A pydantic ValidationError here classifies as LLMOutputProcessingError, as before.
        parsed = schema.model_validate_json(text)
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
        reasoning_effort: str | None = None,
    ) -> TextGenerationResponse:
        start = time.perf_counter()
        request = self._request(
            messages, temperature, max_tokens, reasoning_effort=reasoning_effort
        )
        async with self._session() as client:
            message = await client.messages.create(**request)
        # A completion cut off at the output limit would otherwise read as the whole answer.
        if getattr(message, "stop_reason", None) == "max_tokens":
            raise truncated_output(
                self.label, temperature=temperature, max_tokens=request["max_tokens"]
            )
        if getattr(message, "stop_reason", None) == "refusal":
            raise self._refusal(message)
        text = "".join(
            getattr(block, "text", "") for block in message.content if block.type == "text"
        )
        return TextGenerationResponse(
            text=text,
            usage=self._usage(message),
            latency_ms=elapsed_ms(start),
        )


__all__ = ["DEFAULT_MAX_TOKENS", "AnthropicProvider"]
