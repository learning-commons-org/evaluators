"""Google adapter over the native ``google-genai`` SDK (D10).

Structured output sends the pydantic model's JSON Schema as ``response_json_schema`` with a
JSON MIME type, so Gemini constrains decoding server-side. The raw schema is used rather
than the SDK's ``response_schema`` conversion because that conversion only admits string
enums, and the registry's feedback contracts score with ``enum: [0, 1]``. The completion is
validated here with the same pydantic model, so a payload the schema rejects surfaces as a
pydantic ``ValidationError`` (classified as ``LLMOutputProcessingError`` by
``wrap_provider_error``) rather than as a silently coerced object.
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
    from google.genai import Client

T = TypeVar("T", bound=BaseModel)

# Gemini's turn roles; the protocol's ``assistant`` is Gemini's ``model``.
_ROLES = {"user": "user", "assistant": "model"}


class GoogleProvider:
    """``LLMProvider`` for Google Gemini models."""

    def __init__(self, config: ProviderConfig, *, client: Client | None = None) -> None:
        model, api_key = require_config(config, Provider.GOOGLE)
        self._model = model
        self.label = provider_label(Provider.GOOGLE, model)
        if client is None:
            from google.genai import Client, types

            # ``attempts`` counts the original request, so ``max_retries`` retries is one
            # more; 1 disables retrying, matching the other SDKs' ``max_retries=0``.
            client = Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(attempts=config.max_retries + 1)
                ),
            )
        self._client = client

    def _request(
        self,
        messages: Sequence[Message],
        temperature: float | None,
        max_tokens: int | None,
        schema: type[BaseModel] | None,
    ) -> dict[str, Any]:
        from google.genai import types

        system, rest = split_system(messages)
        config: dict[str, Any] = {}
        if system is not None:
            config["system_instruction"] = system
        # A None temperature means "send nothing" — see config.schema.json.
        if temperature is not None:
            config["temperature"] = temperature
        if max_tokens is not None:
            config["max_output_tokens"] = max_tokens
        if schema is not None:
            config["response_mime_type"] = "application/json"
            config["response_json_schema"] = schema.model_json_schema()
        return {
            "model": self._model,
            "contents": [
                types.Content(
                    role=_ROLES[m["role"]], parts=[types.Part.from_text(text=m["content"])]
                )
                for m in rest
            ],
            "config": types.GenerateContentConfig(**config),
        }

    @staticmethod
    def _usage(response: Any) -> TokenUsage:
        usage = getattr(response, "usage_metadata", None)
        return TokenUsage(
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
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
        response = await self._client.aio.models.generate_content(
            **self._request(messages, temperature, max_tokens, schema)
        )
        # The SDK only populates ``parsed`` for its own ``response_schema`` path; with a raw
        # JSON schema the text is the payload, and the model validates it.
        parsed = response.parsed
        if not isinstance(parsed, schema):
            text = response.text
            if text is None or not text.strip():
                # Safety blocks and empty candidates end with no text; the finish reason
                # of the first candidate says which, when there is one.
                candidates = getattr(response, "candidates", None) or []
                reason = getattr(candidates[0], "finish_reason", None) if candidates else None
                raise no_structured_output(self.label, str(reason) if reason else None)
            parsed = schema.model_validate_json(text)
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
        response = await self._client.aio.models.generate_content(
            **self._request(messages, temperature, max_tokens, None)
        )
        return TextGenerationResponse(
            text=response.text or "",
            usage=self._usage(response),
            latency_ms=elapsed_ms(start),
        )


__all__ = ["GoogleProvider"]
