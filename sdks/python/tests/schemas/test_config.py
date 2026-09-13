"""Tests for EvaluatorConfig, LLMProviderConfig subclasses, and factory functions."""

from dataclasses import FrozenInstanceError

import pytest

from learning_commons_evaluators.logger import SDK_LOGGER_NAME, get_logger
from learning_commons_evaluators.schemas.config import (
    AnthropicLLMProviderConfig,
    EvaluationSettings,
    GoogleLLMProviderConfig,
    LLMProvider,
    OpenAILLMProviderConfig,
    PromptSettings,
    TelemetryConfig,
    create_config,
    create_config_no_telemetry,
    create_config_telemetry_with_full_input,
)
from learning_commons_evaluators.schemas.errors import ConfigurationError


class TestLLMProvider:
    @pytest.mark.parametrize(
        "member,value",
        [
            (LLMProvider.ANTHROPIC, "anthropic"),
            (LLMProvider.GOOGLE, "google"),
            (LLMProvider.OPENAI, "openai"),
        ],
    )
    def test_provider_value(self, member, value):
        assert member.value == value


class TestLLMProviderConfigs:
    @pytest.mark.parametrize(
        "cls,expected_type",
        [
            (GoogleLLMProviderConfig, LLMProvider.GOOGLE),
            (OpenAILLMProviderConfig, LLMProvider.OPENAI),
            (AnthropicLLMProviderConfig, LLMProvider.ANTHROPIC),
        ],
    )
    def test_provider_config_default_type(self, cls, expected_type):
        cfg = cls(api_key="test-key")
        assert cfg.type == expected_type
        assert cfg.api_key == "test-key"


class TestEvaluatorConfigFactory:
    def test_create_config_no_telemetry_defaults(self):
        config = create_config_no_telemetry()
        assert config.telemetry.telemetry_partner_id is None
        assert config.telemetry.send_full_input_with_telemetry is False
        assert config.logger.name == SDK_LOGGER_NAME

    def test_create_config_no_telemetry_accepts_providers(self):
        config = create_config_no_telemetry(
            google_llm_provider_config=GoogleLLMProviderConfig(api_key="gk"),
            openai_llm_provider_config=OpenAILLMProviderConfig(api_key="ok"),
        )
        assert config.google_llm_provider_config.api_key == "gk"
        assert config.openai_llm_provider_config.api_key == "ok"

    def test_create_config_sets_telemetry_partner_id(self):
        config = create_config(telemetry_partner_id="tid-123")
        assert config.telemetry.telemetry_partner_id == "tid-123"
        assert config.telemetry.send_full_input_with_telemetry is False

    def test_create_config_telemetry_with_full_input_sets_flag(self):
        config = create_config_telemetry_with_full_input(telemetry_partner_id="tid")
        assert config.telemetry.telemetry_partner_id == "tid"
        assert config.telemetry.send_full_input_with_telemetry is True

    def test_explicit_logger_is_preserved(self):
        custom = get_logger("custom_test")
        config = create_config_no_telemetry(logger=custom)
        assert config.logger is custom

    def test_config_is_frozen(self):
        """EvaluatorConfig is a frozen dataclass; mutation must raise."""
        config = create_config_no_telemetry()
        with pytest.raises(FrozenInstanceError):
            config.telemetry = TelemetryConfig(
                telemetry_partner_id="x", send_full_input_with_telemetry=False
            )


class _SettingsWithPrompt(EvaluationSettings):
    prompt_settings_main: PromptSettings


class _SettingsWithTwoPrompts(EvaluationSettings):
    prompt_settings_a: PromptSettings
    prompt_settings_b: PromptSettings


class TestValidateSupportsEvaluationSettings:
    def test_no_prompt_settings_is_no_op(self):
        config = create_config_no_telemetry()
        config.validate_supports_evaluation_settings(EvaluationSettings())

    def test_missing_google_raises(self):
        config = create_config_no_telemetry()
        settings = _SettingsWithPrompt(
            prompt_settings_main=PromptSettings(
                provider_type=LLMProvider.GOOGLE,
                model="gemini-2.0-flash",
                temperature=0.0,
            )
        )
        with pytest.raises(ConfigurationError, match="Google provider config is not set"):
            config.validate_supports_evaluation_settings(settings)

    def test_google_configured_passes(self):
        config = create_config_no_telemetry(
            google_llm_provider_config=GoogleLLMProviderConfig(api_key="gk"),
        )
        settings = _SettingsWithPrompt(
            prompt_settings_main=PromptSettings(
                provider_type=LLMProvider.GOOGLE,
                model="gemini-2.0-flash",
                temperature=0.0,
            )
        )
        config.validate_supports_evaluation_settings(settings)

    def test_duplicate_provider_in_settings_requires_one_config(self):
        config = create_config_no_telemetry(
            openai_llm_provider_config=OpenAILLMProviderConfig(api_key="ok"),
        )
        settings = _SettingsWithTwoPrompts(
            prompt_settings_a=PromptSettings(
                provider_type=LLMProvider.OPENAI,
                model="gpt-4o",
                temperature=0.0,
            ),
            prompt_settings_b=PromptSettings(
                provider_type=LLMProvider.OPENAI,
                model="gpt-4.1",
                temperature=0.0,
            ),
        )
        config.validate_supports_evaluation_settings(settings)

    def test_multiple_missing_providers_lists_all(self):
        config = create_config_no_telemetry()
        settings = _SettingsWithTwoPrompts(
            prompt_settings_a=PromptSettings(
                provider_type=LLMProvider.GOOGLE,
                model="gemini-2.0-flash",
                temperature=0.0,
            ),
            prompt_settings_b=PromptSettings(
                provider_type=LLMProvider.OPENAI,
                model="gpt-4o",
                temperature=0.0,
            ),
        )
        with pytest.raises(ConfigurationError) as exc_info:
            config.validate_supports_evaluation_settings(settings)
        msg = str(exc_info.value)
        assert "Google provider config is not set" in msg
        assert "OpenAI provider config is not set" in msg
