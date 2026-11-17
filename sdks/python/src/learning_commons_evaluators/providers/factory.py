"""Building the right adapter for a provider config."""

from __future__ import annotations

import importlib.util
from collections.abc import Sequence

from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.providers.base import LLMProvider, Provider, ProviderConfig

#: The module each built-in adapter imports, and the distribution that provides it. The
#: extra that installs it is named after the provider: ``pip install "...[google]"``.
_SDKS: dict[Provider, tuple[str, str]] = {
    Provider.OPENAI: ("openai", "openai"),
    Provider.ANTHROPIC: ("anthropic", "anthropic"),
    Provider.GOOGLE: ("google.genai", "google-genai"),
}


def sdk_installed(provider: Provider) -> bool:
    """Whether ``provider``'s vendor SDK is importable, found without importing it."""
    try:
        return importlib.util.find_spec(_SDKS[provider][0]) is not None
    except ModuleNotFoundError:
        # ``google.genai`` is looked up through ``google``, which may be absent itself.
        return False
    except ValueError:
        # A module placed in ``sys.modules`` without a spec, as a stub in tests may be: it
        # is importable, which is what the check is for.
        return True


def missing_sdk_error(providers: Sequence[Provider], needed_by: str) -> ConfigurationError:
    """The error for SDKs that are not installed, naming the extra that installs them."""
    missing = list(dict.fromkeys(providers))
    packages = " and ".join(_SDKS[provider][1] for provider in missing)
    extras = ",".join(provider.value for provider in missing)
    plural = len(missing) > 1
    return ConfigurationError(
        f"{needed_by} needs the {packages} package{'s' if plural else ''}, which "
        f"{'are' if plural else 'is'} not installed. Install {'them' if plural else 'it'} "
        f'with: pip install "learning-commons-evaluators[{extras}]"'
    )


def create_provider(config: ProviderConfig) -> LLMProvider:
    """The built-in adapter for ``config.type``.

    Adapters import their vendor SDK on construction, so a program that only ever uses one
    provider never loads the other two.

    :raises ConfigurationError: for an unknown provider, an empty model, a missing key, or
        a vendor SDK that is not installed.
    """
    if isinstance(config.type, Provider) and not sdk_installed(config.type):
        raise missing_sdk_error([config.type], f"The {config.type.value} provider")
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


__all__ = ["create_provider", "missing_sdk_error", "sdk_installed"]
