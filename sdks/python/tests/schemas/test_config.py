"""Tests for EvaluatorConfig, PromptProviderConfig subclasses, and factory functions."""

from dataclasses import FrozenInstanceError

import pytest

from learning_commons_evaluators.logger import SDK_LOGGER_NAME, get_logger
from learning_commons_evaluators.schemas.config import (
    AnthropicPromptProviderConfig,
    GooglePromptProviderConfig,
    LlmProvider,
    OpenAIPromptProviderConfig,
    TelemetryConfig,
    create_config,
    create_config_no_telemetry,
    create_config_telemetry_with_full_input,
)


class TestLlmProvider:
    @pytest.mark.parametrize(
        "member,value",
        [
            (LlmProvider.ANTHROPIC, "anthropic"),
            (LlmProvider.GOOGLE, "google"),
            (LlmProvider.OPENAI, "openai"),
        ],
    )
    def test_provider_value(self, member, value):
        assert member.value == value


class TestPromptProviderConfigs:
    @pytest.mark.parametrize(
        "cls,expected_type",
        [
            (GooglePromptProviderConfig, LlmProvider.GOOGLE),
            (OpenAIPromptProviderConfig, LlmProvider.OPENAI),
            (AnthropicPromptProviderConfig, LlmProvider.ANTHROPIC),
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
            google_prompt_provider_config=GooglePromptProviderConfig(api_key="gk"),
            openai_prompt_provider_config=OpenAIPromptProviderConfig(api_key="ok"),
        )
        assert config.google_prompt_provider_config.api_key == "gk"
        assert config.openai_prompt_provider_config.api_key == "ok"

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
