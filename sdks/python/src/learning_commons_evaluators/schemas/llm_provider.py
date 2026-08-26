"""LLM provider protocol and associated types for framework-agnostic model injection.

These types define the interface that evaluation frameworks (Inspect AI, Braintrust,
Arize/Phoenix, Langfuse, etc.) implement to provide their own model execution to the SDK.

``LLMGeneratorProtocol`` is a structural protocol (``typing.Protocol``) — integration
packages do not need to import or inherit from it. Any class with the correct ``generate``
signature satisfies the protocol automatically for static type checkers.

Response fields are aligned with OpenTelemetry GenAI semantic conventions:
https://opentelemetry.io/docs/specs/semconv/gen-ai/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple, Protocol


class LLMResponse(NamedTuple):
    """Structured response from an LLM generation call.

    A ``NamedTuple`` — immutable, constructible by keyword or position, and
    iterable for adapters that need to destructure the result.

    Fields are aligned with OpenTelemetry GenAI semantic conventions so that
    observability adapters (Arize/Phoenix, Langfuse) can populate their spans
    without additional parsing.

    Required fields (``content``, ``model``) must always be populated.
    Optional fields should be populated whenever the underlying provider returns them.
    """

    content: str
    """The model's text response."""

    model: str
    """The model that generated the response (``gen_ai.response.model``)."""

    input_tokens: int | None = None
    """Number of input/prompt tokens consumed (``gen_ai.usage.input_tokens``)."""

    output_tokens: int | None = None
    """Number of output/completion tokens generated (``gen_ai.usage.output_tokens``)."""


@dataclass
class GenerateConfig:
    """Configuration for a single LLM generation call.

    All fields are optional. Adapters should apply whatever the underlying
    provider supports and ignore the rest.
    """

    temperature: float | None = None
    """Sampling temperature. 0.0 for deterministic output (recommended for evals)."""

    max_tokens: int | None = None
    """Maximum number of tokens to generate."""

    model: str | None = None
    """Model identifier to request from the provider (e.g. ``"claude-opus-4-8"``).

    Adapters should use this when set and ignore it otherwise — the contract is
    identical to all other ``GenerateConfig`` fields. When ``None`` (default),
    the adapter uses whatever model it was constructed with.

    Populated from ``PromptSettings.model`` on the protocol path so that
    adapter authors can inspect which model the evaluator expects without
    reaching into ``prompt_settings`` directly.
    """


class LLMGeneratorProtocol(Protocol):
    """Structural protocol for LLM generation adapters.

    Implement this protocol in an integration package to allow the SDK to call
    your framework's model system.

    No import of this class is required in the implementing package. Structural
    conformance (correct ``generate`` signature) is sufficient for static type
    checkers.

    **Lifecycle**: if your adapter holds a connection pool or HTTP session, add
    ``async def aclose(self) -> None`` and call it when done. The protocol does
    not include ``aclose`` so that stateless adapters remain fully conformant
    without boilerplate. Callers that want to support teardown should use
    ``hasattr(adapter, "aclose")``.

    Example::

        from learning_commons_evaluators.schemas.llm_provider import (
            GenerateConfig,
            LLMResponse,
        )

        class MyFrameworkAdapter:
            async def generate(
                self,
                *,
                system: str,
                human: str,
                config: GenerateConfig | None = None,
            ) -> LLMResponse:
                response = await my_framework.call(system, human)
                return LLMResponse(
                    content=response.text,
                    model=response.model_name,
                    input_tokens=response.usage.input,
                    output_tokens=response.usage.output,
                )
    """

    async def generate(
        self,
        *,
        system: str,
        human: str,
        config: GenerateConfig | None = None,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            system: The system prompt.
            human: The human/user prompt.
            config: Optional generation configuration. Adapters apply whatever
                    fields the underlying provider supports and ignore the rest.

        Returns:
            ``LLMResponse`` with at minimum ``content`` and ``model`` populated.
            Populate optional fields (token counts) whenever the provider returns them.
        """
        ...
