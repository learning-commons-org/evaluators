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


def check_reasoning_effort(provider: Provider, effort: str) -> None:
    """Refuse, before any call, a declared effort the installed vendor SDK cannot send.

    Only google-genai's floor predates its effort parameter. The openai and anthropic
    adapters send theirs as plain request data, which every supported release passes
    through, so there is nothing to check for them.

    :raises ConfigurationError: naming the vendor SDK release to upgrade to.
    """
    if provider is Provider.GOOGLE:
        from learning_commons_evaluators.providers.google_genai import (
            check_reasoning_effort as check_google,
        )

        check_google(effort)


__all__ = ["check_reasoning_effort", "create_provider"]
