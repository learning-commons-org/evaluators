"""Building the right adapter for a provider config."""

from __future__ import annotations

from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.providers.base import LLMProvider, Provider, ProviderConfig


def create_provider(config: ProviderConfig) -> LLMProvider:
    """The built-in adapter for ``config.type``.

    Adapters import their vendor SDK on construction, so a program that only ever uses one
    provider never loads the other two.

    :raises ConfigurationError: for an unknown provider, an empty model, or a missing key.
    """
    if config.type is Provider.OPENAI:
        from learning_commons_evaluators.providers.openai_sdk import OpenAIProvider

        return OpenAIProvider(config)
    if config.type is Provider.ANTHROPIC:
        from learning_commons_evaluators.providers.anthropic_sdk import AnthropicProvider

        return AnthropicProvider(config)
    if config.type is Provider.GOOGLE:
        from learning_commons_evaluators.providers.google_genai import GoogleProvider

        return GoogleProvider(config)
    supported = ", ".join(p.value for p in Provider)
    raise ConfigurationError(
        f"Unsupported provider {getattr(config.type, 'value', config.type)!r}. "
        f"Supported: {supported}."
    )


__all__ = ["create_provider"]
