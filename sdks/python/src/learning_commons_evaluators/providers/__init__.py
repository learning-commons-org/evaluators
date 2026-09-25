"""LLM providers (D10): one protocol, three native-SDK adapters.

:class:`LLMProvider` is what an evaluator calls; :func:`create_provider` builds the
built-in adapter for a :class:`ProviderConfig`. Each adapter owns its vendor's
structured-output mechanism, and a caller may inject any object satisfying the protocol.
"""

from learning_commons_evaluators.providers.base import (
    LLMProvider,
    LLMResponse,
    Message,
    Provider,
    ProviderConfig,
    TextGenerationResponse,
    TokenUsage,
    provider_context,
    provider_label,
)
from learning_commons_evaluators.providers.factory import create_provider
from learning_commons_evaluators.providers.retry import call_with_resampling

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "Message",
    "Provider",
    "ProviderConfig",
    "TextGenerationResponse",
    "TokenUsage",
    "call_with_resampling",
    "create_provider",
    "provider_context",
    "provider_label",
]
