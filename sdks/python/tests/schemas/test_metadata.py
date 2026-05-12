"""Unit tests for schemas/metadata.py.

Covers: EvaluatorMaturity, Status, EvaluatorMetadata, TokenUsage,
StepMetadata, EvaluationMetadata, and prompt_settings_to_extras_value.
"""

from datetime import timezone

import pytest

from learning_commons_evaluators.schemas.config import LlmProvider, PromptSettings
from learning_commons_evaluators.schemas.metadata import (
    PROMPT_STEP_EXTRA_PROMPT_SETTINGS,
    PROMPT_STEP_EXTRA_TOKEN_USAGE,
    EvaluatorMaturity,
    EvaluatorMetadata,
    Status,
    StepMetadata,
    TokenUsage,
    prompt_settings_to_extras_value,
)


class TestEnums:
    @pytest.mark.parametrize(
        "member,value",
        [
            (EvaluatorMaturity.alpha, "alpha"),
            (EvaluatorMaturity.beta, "beta"),
            (EvaluatorMaturity.rc, "rc"),
            (EvaluatorMaturity.ga, "ga"),
        ],
    )
    def test_evaluator_maturity_values(self, member, value):
        assert member.value == value

    @pytest.mark.parametrize(
        "member,value",
        [
            (Status.processing, "processing"),
            (Status.succeeded, "succeeded"),
            (Status.failed, "failed"),
        ],
    )
    def test_status_values(self, member, value):
        assert member.value == value


class TestEvaluatorMetadata:
    def test_fields_and_sdk_version(self):
        meta = EvaluatorMetadata(
            id="my-evaluator",
            version="1.0",
            name="My Evaluator",
            description="Does stuff.",
            maturity=EvaluatorMaturity.ga,
        )
        assert meta.id == "my-evaluator"
        assert meta.name == "My Evaluator"
        assert meta.maturity == EvaluatorMaturity.ga
        # sdk_version is auto-populated from the installed package version.
        assert "learning-commons-evaluators-python" in meta.sdk_version


class TestTokenUsage:
    def test_fields(self):
        usage = TokenUsage(
            provider_type=LlmProvider.GOOGLE,
            model="gemini-2.0-flash",
            input_tokens=100,
            output_tokens=50,
        )
        assert usage.provider_type == LlmProvider.GOOGLE
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50

    def test_zero_tokens_are_valid(self):
        usage = TokenUsage(
            provider_type=LlmProvider.OPENAI,
            model="gpt-4o-mini",
            input_tokens=0,
            output_tokens=0,
        )
        assert usage.input_tokens == 0


class TestStepMetadata:
    def test_defaults(self):
        step = StepMetadata(step_id="main")
        assert step.status == Status.processing
        assert step.error_details == ""
        assert step.processing_time_ms == 0
        assert step.extras == {}

    def test_extras_dict_is_mutable(self):
        step = StepMetadata(step_id="step1", extras={"a": 1})
        step.extras["b"] = 2
        assert step.extras == {"a": 1, "b": 2}

    def test_well_known_extra_key_constants(self):
        assert PROMPT_STEP_EXTRA_PROMPT_SETTINGS == "prompt_settings"
        assert PROMPT_STEP_EXTRA_TOKEN_USAGE == "token_usage"


class TestPromptSettingsToExtrasValue:
    def test_produces_json_serialisable_dict(self):
        """provider_type must be a plain string (not the enum) so the dict is JSON-safe."""
        settings = PromptSettings(
            provider_type=LlmProvider.ANTHROPIC,
            model="claude-3-haiku",
            temperature=0.5,
        )
        extras = prompt_settings_to_extras_value(settings)
        assert isinstance(extras["provider_type"], str)
        assert extras["provider_type"] == "anthropic"
        assert extras["model"] == "claude-3-haiku"
        assert extras["temperature"] == 0.5


class TestEvaluationMetadata:
    def test_timestamp_is_utc(self, evaluation_metadata):
        assert evaluation_metadata.timestamp.tzinfo == timezone.utc

    def test_defaults(self, evaluation_metadata):
        assert evaluation_metadata.status == Status.processing
        assert evaluation_metadata.step_details == {}
        assert evaluation_metadata.total_token_usage == {}
        assert evaluation_metadata.error_details is None
        assert evaluation_metadata.input_metadata == {}

    def test_status_can_be_mutated(self, evaluation_metadata):
        evaluation_metadata.status = Status.succeeded
        assert evaluation_metadata.status == Status.succeeded

    def test_step_details_can_be_populated(self, evaluation_metadata):
        step = StepMetadata(step_id="main", status=Status.succeeded)
        evaluation_metadata.step_details["main"] = step
        assert evaluation_metadata.step_details["main"].status == Status.succeeded
