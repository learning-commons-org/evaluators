"""Tests for LangChain provider factory and token usage."""

from unittest.mock import MagicMock

import pytest

from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.providers.langchain import (
    create_provider,
    token_usage_from_aimessage,
)
from learning_commons_evaluators.schemas.config import (
    EvaluatorConfig,
    GoogleLLMProviderConfig,
    LLMProvider,
    OpenAILLMProviderConfig,
    PromptSettings,
)


def _config(**kwargs) -> EvaluatorConfig:
    """Return an EvaluatorConfig with all providers set to None; pass provider kwargs to override."""
    defaults: dict = {
        "google_llm_provider_config": None,
        "openai_llm_provider_config": None,
        "anthropic_llm_provider_config": None,
    }
    defaults.update(kwargs)
    return EvaluatorConfig(**defaults)


# ---------------------------------------------------------------------------
# create_provider
# ---------------------------------------------------------------------------


class TestCreateProvider:
    def test_google_provider_returns_model(self):
        config = _config(
            google_llm_provider_config=GoogleLLMProviderConfig(api_key="test-key")
        )
        settings = PromptSettings(
            provider_type=LLMProvider.GOOGLE, model="gemini-2.0-flash", temperature=0.0
        )
        assert create_provider(settings, config) is not None

    def test_openai_provider_returns_model(self):
        config = _config(
            openai_llm_provider_config=OpenAILLMProviderConfig(api_key="test-key")
        )
        settings = PromptSettings(
            provider_type=LLMProvider.OPENAI, model="gpt-4o-mini", temperature=0.0
        )
        assert create_provider(settings, config) is not None

    def test_raises_when_google_config_missing(self):
        settings = PromptSettings(
            provider_type=LLMProvider.GOOGLE, model="gemini-2.0-flash", temperature=0.0
        )
        with pytest.raises(ConfigurationError, match="Google provider config is not set"):
            create_provider(settings, _config())

    def test_raises_when_openai_config_missing(self):
        settings = PromptSettings(provider_type=LLMProvider.OPENAI, model="gpt-4o", temperature=0.0)
        with pytest.raises(ConfigurationError, match="OpenAI provider config is not set"):
            create_provider(settings, _config())

    def test_raises_when_anthropic_config_missing(self):
        settings = PromptSettings(
            provider_type=LLMProvider.ANTHROPIC, model="claude-3", temperature=0.0
        )
        with pytest.raises(ConfigurationError, match="Anthropic provider config is not set"):
            create_provider(settings, _config())

    def test_raises_configuration_error_for_unrecognized_provider_type(self):
        """Unknown provider_type must surface as ConfigurationError, not ValueError."""
        mock_settings = MagicMock()
        mock_settings.provider_type = object()
        with pytest.raises(ConfigurationError, match="Unsupported LLM provider type"):
            create_provider(
                mock_settings,
                _config(google_llm_provider_config=GoogleLLMProviderConfig(api_key="k")),
            )


# ---------------------------------------------------------------------------
# token_usage_from_aimessage
# ---------------------------------------------------------------------------


class TestTokenUsageFromAIMessage:
    def test_returns_zero_usage_when_no_usage_metadata(self):
        settings = PromptSettings(
            provider_type=LLMProvider.GOOGLE, model="gemini-2.0-flash", temperature=0.0
        )
        usage = token_usage_from_aimessage(object(), settings)
        assert usage.provider_type == LLMProvider.GOOGLE
        assert usage.model == "gemini-2.0-flash"
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0

    def test_uses_usage_metadata_when_present(self):
        settings = PromptSettings(provider_type=LLMProvider.OPENAI, model="gpt-4o", temperature=0.0)
        message = type("Msg", (), {"usage_metadata": {"input_tokens": 100, "output_tokens": 50}})()
        usage = token_usage_from_aimessage(message, settings)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

    def test_falls_back_to_response_metadata_when_usage_metadata_absent(self):
        settings = PromptSettings(provider_type=LLMProvider.GOOGLE, model="gemini", temperature=0.0)
        message = type(
            "Msg",
            (),
            {"response_metadata": {"usage_metadata": {"input_tokens": 10, "output_tokens": 20}}},
        )()
        usage = token_usage_from_aimessage(message, settings)
        assert usage.input_tokens == 10
        assert usage.output_tokens == 20
