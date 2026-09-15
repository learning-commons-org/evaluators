"""The provider protocol every LLM adapter implements (D10), mirroring the TypeScript SDK's ``providers/base.ts``.

An evaluator talks to a model through :class:`LLMProvider` and nothing else. The three
built-in adapters (:mod:`.openai_sdk`, :mod:`.anthropic_sdk`, :mod:`.google_genai`) each
own their vendor's structured-output mechanism behind this one interface, and a caller may
inject any object satisfying it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Literal, Protocol, TypedDict, TypeVar, runtime_checkable

from pydantic import BaseModel

from learning_commons_evaluators.errors import PROVIDER_DEPENDENCIES, DependencyId

T = TypeVar("T", bound=BaseModel)


class Provider(str, Enum):
    """The closed set of supported LLM providers (SDK spec §3.3).

    A ``str`` subclass so it compares and serialises as the canonical value, which is also
    what a contract's ``model.provider`` declares.
    """

    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"


class Message(TypedDict):
    """One turn of an LLM conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class TokenUsage:
    """Token counts for one model call."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class LLMResponse(Generic[T]):
    """A structured completion: the parsed payload plus what it cost."""

    data: T
    #: The model id the adapter was configured with.
    model: str
    usage: TokenUsage
    latency_ms: int


@dataclass(frozen=True)
class TextGenerationResponse:
    """A plain-text completion plus what it cost."""

    text: str
    usage: TokenUsage
    latency_ms: int


@runtime_checkable
class LLMProvider(Protocol):
    """What an evaluator needs from a model.

    ``temperature`` is sent only when given: ``None`` omits the parameter, for models that
    reject an explicit value (the contract schema's ``generation.temperature: null``).
    """

    @property
    def label(self) -> str:
        """Canonical label for the provider and model in use, e.g. ``"openai:gpt-4o-2024-11-20"``."""
        ...

    async def generate_structured(
        self,
        messages: Sequence[Message],
        schema: type[T],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse[T]:
        """Generate output validated against a pydantic model.

        A response the schema rejects raises ``LLMOutputProcessingError`` (possibly via
        ``wrap_provider_error`` at the evaluator boundary); it is never silently coerced.
        """
        ...

    async def generate_text(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> TextGenerationResponse:
        """Generate plain text."""
        ...


@dataclass(frozen=True)
class ProviderConfig:
    """What it takes to build a built-in adapter.

    ``max_retries`` is handed to the vendor SDK, which owns dependency backoff (§6.3): the
    SDK retries its own 408/409/429/5xx and connection failures, honouring ``Retry-After``,
    so the evaluator layer never re-implements that loop. ``0`` disables it.
    """

    type: Provider
    model: str
    api_key: str | None = None
    max_retries: int = 0


def provider_label(provider: Provider | str, model: str) -> str:
    """The canonical ``provider:model`` label (SDK spec §3.4)."""
    value = provider.value if isinstance(provider, Provider) else provider
    return f"{value}:{model}"


def provider_context(provider: LLMProvider) -> tuple[DependencyId, str]:
    """Dependency attribution for errors raised while calling ``provider``.

    The label is ``provider:model``, and its prefix is a :class:`Provider` value on both the
    default and ``model_override`` paths, so those report their real vendor. An injected
    provider can label itself anything; that reports ``custom`` rather than guessing a
    vendor we never called. The label is always kept as ``model``, so the caller's own
    identifier is never lost.
    """
    label = provider.label
    prefix, separator, rest = label.partition(":")
    if prefix not in PROVIDER_DEPENDENCIES:
        return "custom", label
    # ``prefix`` is one of the three provider ids by the membership test above.
    dependency: DependencyId = prefix  # type: ignore[assignment]
    return dependency, rest if separator and rest else label


__all__ = [
    "LLMProvider",
    "LLMResponse",
    "Message",
    "Provider",
    "ProviderConfig",
    "TextGenerationResponse",
    "TokenUsage",
    "provider_context",
    "provider_label",
]
