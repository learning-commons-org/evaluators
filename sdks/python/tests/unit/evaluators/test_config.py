"""The flat config (§3) and what BaseEvaluator checks at construction."""

from __future__ import annotations

import logging

import pytest

from learning_commons_evaluators import (
    ConfigurationError,
    EvaluatorConfig,
    GradeLevelAppropriatenessEvaluator,
    ModelOverride,
    Provider,
    PurposeClarityEvaluator,
    TelemetryOptions,
    ToneAppropriatenessEvaluator,
)
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from tests.unit.conftest import ProviderFactory


class TestEvaluatorConfig:
    def test_credentials_are_read_by_canonical_key(self) -> None:
        config = EvaluatorConfig(openai_api_key="o", learning_commons_api_key="lc")
        assert config.credential("openai_api_key") == "o"
        assert config.credential("learning_commons_api_key") == "lc"
        assert config.credential("google_api_key") is None
        assert config.api_key_for(Provider.OPENAI) == "o"

    def test_telemetry_shorthands_normalise(self) -> None:
        assert EvaluatorConfig().telemetry_options == TelemetryOptions()
        assert EvaluatorConfig(telemetry=False).telemetry_options.enabled is False
        granular = TelemetryOptions(record_raw_inputs=True, learning_commons_api_key="t")
        assert EvaluatorConfig(telemetry=granular).telemetry_options is granular

    def test_defaults(self) -> None:
        config = EvaluatorConfig()
        assert config.max_retries == 2
        assert config.model_override is None


class TestConstruction:
    def test_accepts_a_config_object_or_keyword_fields(self, providers: ProviderFactory) -> None:
        by_object = PurposeClarityEvaluator(EvaluatorConfig(google_api_key="k", max_retries=0))
        by_fields = PurposeClarityEvaluator(google_api_key="k", max_retries=0)
        assert by_object.config == by_fields.config

    def test_rejects_both_forms_at_once(self, providers: ProviderFactory) -> None:
        with pytest.raises(TypeError, match="not both"):
            PurposeClarityEvaluator(EvaluatorConfig(google_api_key="k"), openai_api_key="o")

    def test_an_unknown_field_is_a_configuration_error(self, providers: ProviderFactory) -> None:
        with pytest.raises(ConfigurationError, match="Unknown configuration field.*google_api_key"):
            PurposeClarityEvaluator(googleApiKey="k")

    @pytest.mark.parametrize(
        ("evaluator", "key"),
        [
            (GradeLevelAppropriatenessEvaluator, "google_api_key"),
            (PurposeClarityEvaluator, "google_api_key"),
            (ToneAppropriatenessEvaluator, "openai_api_key"),
        ],
    )
    def test_the_provider_key_is_derived_from_the_contract(
        self, providers: ProviderFactory, evaluator: type[BaseEvaluator], key: str
    ) -> None:
        with pytest.raises(
            ConfigurationError,
            match=f"Missing required credential: {key}. Required by {evaluator.metadata.name}.",
        ):
            evaluator()

    @pytest.mark.parametrize("value", ["", "   "])
    def test_an_empty_key_is_missing(self, providers: ProviderFactory, value: str) -> None:
        with pytest.raises(ConfigurationError, match="Missing required credential: google_api_key"):
            PurposeClarityEvaluator(google_api_key=value)

    def test_keys_for_other_providers_are_not_required(self, providers: ProviderFactory) -> None:
        # A Google evaluator does not need an OpenAI key, and extra keys are simply unused.
        PurposeClarityEvaluator(google_api_key="k", anthropic_api_key="a")
        assert providers.last.config.api_key == "k"

    def test_the_provider_is_built_from_the_contract_step(self, providers: ProviderFactory) -> None:
        PurposeClarityEvaluator(google_api_key="k", max_retries=5)
        config = providers.last.config
        assert (config.type, config.model, config.max_retries) == (
            Provider.GOOGLE,
            "gemini-3-flash-preview",
            5,
        )


class TestModelOverride:
    def test_replaces_the_provider_and_its_key_requirement(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        override = ModelOverride(provider=Provider.ANTHROPIC, model="claude-haiku-4-5-20251001")
        with caplog.at_level(logging.WARNING, logger="learning_commons_evaluators"):
            evaluator = PurposeClarityEvaluator(anthropic_api_key="a", model_override=override)
        config = providers.last.config
        assert (config.type, config.model, config.api_key) == (
            Provider.ANTHROPIC,
            "claude-haiku-4-5-20251001",
            "a",
        )
        assert evaluator.provider.label == "anthropic:claude-haiku-4-5-20251001"
        assert evaluator.providers_in_use == (Provider.ANTHROPIC,)
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "anthropic:claude-haiku-4-5-20251001" in warnings[0].getMessage()

    def test_demands_the_override_providers_key(self, providers: ProviderFactory) -> None:
        override = ModelOverride(provider=Provider.OPENAI, model="gpt-4o-2024-11-20")
        with pytest.raises(ConfigurationError, match="Missing required credential: openai_api_key"):
            PurposeClarityEvaluator(google_api_key="k", model_override=override)

    def test_accepts_the_provider_as_its_canonical_string(self, providers: ProviderFactory) -> None:
        override = ModelOverride(provider="openai", model="gpt-4o-2024-11-20")  # type: ignore[arg-type]
        evaluator = PurposeClarityEvaluator(openai_api_key="o", model_override=override)
        assert evaluator.provider.label == "openai:gpt-4o-2024-11-20"

    def test_rejects_an_unknown_provider(self, providers: ProviderFactory) -> None:
        override = ModelOverride(provider="cohere", model="m")  # type: ignore[arg-type]
        with pytest.raises(
            ConfigurationError, match='Invalid provider "cohere".*openai, google, anthropic'
        ):
            PurposeClarityEvaluator(google_api_key="k", model_override=override)

    @pytest.mark.parametrize("model", ["", "  "])
    def test_rejects_an_empty_model(self, providers: ProviderFactory, model: str) -> None:
        override = ModelOverride(provider=Provider.GOOGLE, model=model)
        with pytest.raises(ConfigurationError, match="model_override.model is required"):
            PurposeClarityEvaluator(google_api_key="k", model_override=override)

    def test_no_warning_without_an_override(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="learning_commons_evaluators"):
            PurposeClarityEvaluator(google_api_key="k")
        assert not [r for r in caplog.records if r.levelno == logging.WARNING]
