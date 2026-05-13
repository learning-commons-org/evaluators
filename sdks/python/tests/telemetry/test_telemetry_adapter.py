"""Tests for :func:`evaluation_to_typescript_telemetry_event`."""

from __future__ import annotations

from learning_commons_evaluators import create_config
from learning_commons_evaluators.schemas.config import LLMProvider, PromptSettings
from learning_commons_evaluators.schemas.metadata import (
    PROMPT_STEP_EXTRA_PROMPT_SETTINGS,
    PROMPT_STEP_EXTRA_TOKEN_USAGE,
    Status,
    StepMetadata,
    TokenUsage,
)
from learning_commons_evaluators.telemetry.adapter import evaluation_to_typescript_telemetry_event


def test_adapter_maps_success_and_aggregate_tokens(evaluation_metadata):
    cfg = create_config(telemetry_partner_id="tid")
    evaluation_metadata.status = Status.succeeded
    evaluation_metadata.input_metadata = {"grade_level": {"grade": 5}}
    evaluation_metadata.total_token_usage[LLMProvider.OPENAI] = TokenUsage(
        provider_type=LLMProvider.OPENAI,
        model="gpt-4o",
        input_tokens=10,
        output_tokens=20,
    )
    evaluation_metadata.total_token_usage[LLMProvider.GOOGLE] = TokenUsage(
        provider_type=LLMProvider.GOOGLE,
        model="gemini-pro",
        input_tokens=5,
        output_tokens=5,
    )

    event = evaluation_to_typescript_telemetry_event(evaluation_metadata, None, cfg)

    assert event.status == "success"
    assert event.evaluator_type == "test-evaluator"
    assert event.grade == "5"
    assert event.provider == "google:gemini-pro + openai:gpt-4o"
    assert event.token_usage is not None
    assert event.token_usage.input_tokens == 15
    assert event.token_usage.output_tokens == 25


def test_adapter_stage_details_from_step_extras(evaluation_metadata):
    cfg = create_config(telemetry_partner_id="tid")
    evaluation_metadata.status = Status.succeeded
    ps = PromptSettings(provider_type=LLMProvider.OPENAI, model="gpt-4o-mini", temperature=0.0)
    evaluation_metadata.step_details["step_a"] = StepMetadata(
        step_id="step_a",
        status=Status.succeeded,
        processing_time_ms=12.5,
        extras={
            PROMPT_STEP_EXTRA_PROMPT_SETTINGS: {
                "provider_type": ps.provider_type.value,
                "model": ps.model,
                "temperature": ps.temperature,
            },
            PROMPT_STEP_EXTRA_TOKEN_USAGE: {
                "provider_type": "openai",
                "model": "gpt-4o-mini",
                "input_tokens": 3,
                "output_tokens": 4,
            },
        },
    )

    event = evaluation_to_typescript_telemetry_event(evaluation_metadata, None, cfg)

    assert event.metadata is not None
    assert event.metadata.stage_details is not None
    assert len(event.metadata.stage_details) == 1
    sd = event.metadata.stage_details[0]
    assert sd.stage == "step_a"
    assert sd.provider == "openai:gpt-4o-mini"
    assert sd.token_usage is not None
    assert sd.token_usage.input_tokens == 3
    assert sd.token_usage.output_tokens == 4
