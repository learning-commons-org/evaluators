"""Building adapters from a ``ProviderConfig``; no network is touched."""

from __future__ import annotations

import pytest

from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.providers import Provider, ProviderConfig, create_provider
from learning_commons_evaluators.providers.anthropic_sdk import AnthropicProvider
from learning_commons_evaluators.providers.google_genai import GoogleProvider
from learning_commons_evaluators.providers.openai_sdk import OpenAIProvider


@pytest.mark.parametrize(
    ("provider", "cls", "model"),
    [
        (Provider.OPENAI, OpenAIProvider, "gpt-4o-2024-11-20"),
        (Provider.ANTHROPIC, AnthropicProvider, "claude-haiku-4-5-20251001"),
        (Provider.GOOGLE, GoogleProvider, "gemini-3.6-flash"),
    ],
)
def test_builds_the_adapter_for_each_provider(provider: Provider, cls: type, model: str) -> None:
    adapter = create_provider(ProviderConfig(type=provider, model=model, api_key="test-key"))
    assert isinstance(adapter, cls)
    assert adapter.label == f"{provider.value}:{model}"


@pytest.mark.parametrize("provider", list(Provider))
def test_a_missing_key_is_a_configuration_error_with_the_canonical_message(
    provider: Provider,
) -> None:
    with pytest.raises(
        ConfigurationError, match=f"Missing required credential: {provider.value}_api_key"
    ):
        create_provider(ProviderConfig(type=provider, model="m"))


@pytest.mark.parametrize("key", ["", "   "])
def test_an_empty_key_counts_as_missing(key: str) -> None:
    # The spec's definition of missing (§3.1) includes the language's empty value; left to
    # the vendor SDK, an empty key would fall back to an implicit environment read.
    with pytest.raises(ConfigurationError, match="Missing required credential"):
        create_provider(ProviderConfig(type=Provider.OPENAI, model="m", api_key=key))


@pytest.mark.parametrize("model", ["", "  "])
def test_an_empty_model_is_a_configuration_error(model: str) -> None:
    with pytest.raises(ConfigurationError, match="model is required"):
        create_provider(ProviderConfig(type=Provider.GOOGLE, model=model, api_key="k"))


def test_an_unknown_provider_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="Unsupported provider"):
        create_provider(ProviderConfig(type="bedrock", model="m", api_key="k"))  # type: ignore[arg-type]


def test_an_adapter_rejects_a_config_for_another_provider() -> None:
    with pytest.raises(ConfigurationError, match="received a config for provider 'google'"):
        OpenAIProvider(ProviderConfig(type=Provider.GOOGLE, model="m", api_key="k"))


def test_max_retries_reaches_the_vendor_client() -> None:
    openai_adapter = OpenAIProvider(
        ProviderConfig(type=Provider.OPENAI, model="m", api_key="k", max_retries=3)
    )
    assert openai_adapter._client.max_retries == 3
    anthropic_adapter = AnthropicProvider(
        ProviderConfig(type=Provider.ANTHROPIC, model="m", api_key="k", max_retries=0)
    )
    assert anthropic_adapter._client.max_retries == 0
