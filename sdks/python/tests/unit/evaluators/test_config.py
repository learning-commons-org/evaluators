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
    VocabularyComplexityEvaluator,
)
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.providers import ProviderConfig
from tests.unit.conftest import FakeProvider, ProviderFactory, sample_for
from tests.unit.evaluators.test_single_step import contract as demo_contract
from tests.unit.evaluators.test_single_step import define as define_demo


def _needs_learning_commons_key() -> type[BaseEvaluator]:
    """The demo evaluator, with a non-LLM credential declared on its step.

    Declared on the step rather than on a preprocessing entry because the single-step base
    only admits ``computation`` preprocessing; ``Contract.required_credentials`` aggregates
    both, so this exercises the same path the math contract will.
    """
    step = demo_contract().steps[0].model_dump(by_alias=True)
    step["required_credentials"] = ["learning_commons_api_key"]
    return define_demo(steps=[step])


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
        granular = TelemetryOptions(learning_commons_api_key="t")
        assert EvaluatorConfig(telemetry=granular).telemetry_options is granular

    def test_defaults(self) -> None:
        config = EvaluatorConfig()
        assert config.max_retries == 2
        assert config.model_override is None

    def test_a_field_added_later_does_not_shift_the_existing_positions(self) -> None:
        # Positional construction is part of the public dataclass; a new field goes last.
        config = EvaluatorConfig(None, "o", None, None, None, 0, False)
        assert (config.openai_api_key, config.max_retries, config.telemetry) == ("o", 0, False)
        assert config.llm_provider is None


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

    def test_a_credential_no_provider_implies_is_still_required(
        self, providers: ProviderFactory
    ) -> None:
        """A key the contract names directly, rather than one derived from its providers.

        The only registry contract with one is Math Standards Alignment, which declares
        ``learning_commons_api_key`` for its Knowledge Graph calls and has no evaluator
        class until Phase 5b — so until now nothing exercised this half of
        ``_validate_credentials`` and deleting it would have broken no test.
        """
        with pytest.raises(
            ConfigurationError,
            match=(
                "Missing required credential: learning_commons_api_key. "
                "Required by Thing Evaluator."
            ),
        ):
            _needs_learning_commons_key()(google_api_key="k")

    def test_that_credential_is_satisfied_when_supplied(self, providers: ProviderFactory) -> None:
        evaluator = _needs_learning_commons_key()(google_api_key="k", learning_commons_api_key="lc")
        assert evaluator.metadata.required_credentials == ("learning_commons_api_key",)

    @pytest.mark.parametrize("value", ["", "   "])
    def test_a_blank_contract_credential_counts_as_missing(
        self, providers: ProviderFactory, value: str
    ) -> None:
        with pytest.raises(ConfigurationError, match="learning_commons_api_key"):
            _needs_learning_commons_key()(google_api_key="k", learning_commons_api_key=value)

    def test_a_model_override_does_not_excuse_it(self, providers: ProviderFactory) -> None:
        """An override replaces the provider key, not a key for a service still being called.

        Swapping the model says nothing about the Knowledge Graph, so the evaluator still
        needs its key — and the override must not become a way to skip the check.
        """
        with pytest.raises(ConfigurationError, match="learning_commons_api_key"):
            _needs_learning_commons_key()(
                openai_api_key="o",
                model_override=ModelOverride(Provider.OPENAI, "gpt-4o-2024-11-20"),
            )

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


class TestVendorSDKs:
    """A built-in adapter's vendor SDK is checked at construction, like its key."""

    @pytest.fixture
    def installed(self, monkeypatch: pytest.MonkeyPatch) -> set[Provider]:
        """The providers whose SDK counts as installed; none until a test adds some."""
        present: set[Provider] = set()
        monkeypatch.setattr(
            "learning_commons_evaluators.evaluators.base.sdk_installed", present.__contains__
        )
        return present

    def test_a_missing_sdk_names_the_evaluator_and_the_extra(
        self, providers: ProviderFactory, installed: set[Provider]
    ) -> None:
        with pytest.raises(ConfigurationError) as exc_info:
            PurposeClarityEvaluator(google_api_key="k")
        assert str(exc_info.value) == (
            "Purpose Clarity Evaluator needs the google-genai package, which is not installed. "
            'Install it with: pip install "learning-commons-evaluators[google]"'
        )

    def test_every_missing_sdk_is_named_at_once(
        self, providers: ProviderFactory, installed: set[Provider]
    ) -> None:
        with pytest.raises(ConfigurationError, match=r"\[openai,google\]"):
            VocabularyComplexityEvaluator(openai_api_key="o", google_api_key="g")
        installed.add(Provider.OPENAI)
        with pytest.raises(ConfigurationError, match=r"needs the google-genai package.*\[google\]"):
            VocabularyComplexityEvaluator(openai_api_key="o", google_api_key="g")

    def test_it_is_checked_before_the_keys(
        self, providers: ProviderFactory, installed: set[Provider]
    ) -> None:
        # Installing comes before configuring, so the first error is the one to fix first.
        with pytest.raises(ConfigurationError, match="google-genai"):
            PurposeClarityEvaluator()

    def test_an_override_needs_its_own_providers_sdk_instead(
        self, providers: ProviderFactory, installed: set[Provider]
    ) -> None:
        override = ModelOverride(provider=Provider.ANTHROPIC, model="claude-haiku-4-5-20251001")
        with pytest.raises(ConfigurationError, match=r"\[anthropic\]"):
            PurposeClarityEvaluator(anthropic_api_key="a", model_override=override)
        installed.add(Provider.ANTHROPIC)
        PurposeClarityEvaluator(anthropic_api_key="a", model_override=override)

    def test_an_injected_provider_needs_none(
        self, providers: ProviderFactory, installed: set[Provider]
    ) -> None:
        injected = FakeProvider(ProviderConfig(type=Provider.OPENAI, model="m"), sample_for)
        VocabularyComplexityEvaluator(llm_provider=injected)
