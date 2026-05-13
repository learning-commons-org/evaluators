"""Tests for EvaluatorConfig, LLMProviderConfig subclasses, and factory functions."""

import uuid
from dataclasses import FrozenInstanceError

import pytest

from learning_commons_evaluators.logger import SDK_LOGGER_NAME, get_logger
from learning_commons_evaluators.schemas.config import (
    DEFAULT_TELEMETRY_EVENTS_ENDPOINT,
    AnthropicLLMProviderConfig,
    GoogleLLMProviderConfig,
    LLMProvider,
    OpenAILLMProviderConfig,
    TelemetryConfig,
    create_config,
    create_config_anonymous_telemetry,
    create_config_anonymous_telemetry_with_full_input,
    create_config_no_telemetry,
    create_config_telemetry_with_full_input,
    create_config_with_telemetry_config,
)


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
        assert config.telemetry.endpoint == DEFAULT_TELEMETRY_EVENTS_ENDPOINT
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
        assert config.telemetry.endpoint == DEFAULT_TELEMETRY_EVENTS_ENDPOINT
        assert config.telemetry.send_full_input_with_telemetry is False

    def test_create_config_telemetry_with_full_input_sets_flag(self):
        config = create_config_telemetry_with_full_input(telemetry_partner_id="tid")
        assert config.telemetry.telemetry_partner_id == "tid"
        assert config.telemetry.send_full_input_with_telemetry is True

    def test_create_config_with_telemetry_config_uses_given_telemetry_config(self):
        telemetry = TelemetryConfig(
            endpoint="https://example.com/events",
            telemetry_partner_id="partner-1",
            send_full_input_with_telemetry=True,
        )
        config = create_config_with_telemetry_config(telemetry_config=telemetry)
        assert config.telemetry is telemetry
        assert config.telemetry.endpoint == "https://example.com/events"
        assert config.telemetry.telemetry_partner_id == "partner-1"
        assert config.telemetry.send_full_input_with_telemetry is True

    def test_create_config_with_telemetry_config_accepts_providers(self):
        config = create_config_with_telemetry_config(
            google_llm_provider_config=GoogleLLMProviderConfig(api_key="gk"),
            telemetry_config=TelemetryConfig(telemetry_partner_id="p"),
        )
        assert config.google_llm_provider_config.api_key == "gk"

    def test_create_config_with_telemetry_config_preserves_logger(self):
        custom = get_logger("custom_with_telemetry")
        telemetry = TelemetryConfig(telemetry_partner_id="p")
        config = create_config_with_telemetry_config(logger=custom, telemetry_config=telemetry)
        assert config.logger is custom

    def test_create_config_anonymous_telemetry_uuid_partner_id(self):
        config = create_config_anonymous_telemetry()
        pid = config.telemetry.telemetry_partner_id
        assert pid is not None
        uuid.UUID(pid)
        assert config.telemetry.send_full_input_with_telemetry is False
        assert config.telemetry.endpoint == DEFAULT_TELEMETRY_EVENTS_ENDPOINT

    def test_create_config_anonymous_telemetry_distinct_partner_ids(self):
        a = create_config_anonymous_telemetry()
        b = create_config_anonymous_telemetry()
        assert a.telemetry.telemetry_partner_id != b.telemetry.telemetry_partner_id

    def test_create_config_anonymous_telemetry_accepts_providers(self):
        config = create_config_anonymous_telemetry(
            openai_llm_provider_config=OpenAILLMProviderConfig(api_key="ok"),
        )
        assert config.openai_llm_provider_config.api_key == "ok"

    def test_create_config_anonymous_telemetry_with_full_input(self):
        config = create_config_anonymous_telemetry_with_full_input()
        pid = config.telemetry.telemetry_partner_id
        assert pid is not None
        uuid.UUID(pid)
        assert config.telemetry.send_full_input_with_telemetry is True
        assert config.telemetry.endpoint == DEFAULT_TELEMETRY_EVENTS_ENDPOINT

    def test_create_config_anonymous_telemetry_with_full_input_distinct_partner_ids(self):
        a = create_config_anonymous_telemetry_with_full_input()
        b = create_config_anonymous_telemetry_with_full_input()
        assert a.telemetry.telemetry_partner_id != b.telemetry.telemetry_partner_id

    def test_explicit_logger_is_preserved(self):
        custom = get_logger("custom_test")
        config = create_config_no_telemetry(logger=custom)
        assert config.logger is custom

    def test_config_is_frozen(self):
        """EvaluatorConfig is a frozen dataclass; mutation must raise."""
        config = create_config_no_telemetry()
        with pytest.raises(FrozenInstanceError):
            config.telemetry = TelemetryConfig(
                telemetry_partner_id="x",
                send_full_input_with_telemetry=False,
            )
