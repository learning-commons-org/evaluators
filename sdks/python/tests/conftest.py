"""Shared pytest fixtures for the learning_commons_evaluators test suite."""

import pytest

from learning_commons_evaluators import create_config_no_telemetry
from learning_commons_evaluators.schemas.config import LlmProvider, PromptSettings
from learning_commons_evaluators.schemas.conventionality import (
    ConventionalityEvaluationSettings,
)
from learning_commons_evaluators.schemas.metadata import (
    EvaluationMetadata,
    EvaluatorMaturity,
    EvaluatorMetadata,
)


@pytest.fixture
def evaluator_metadata():
    """Minimal EvaluatorMetadata suitable for use in tests."""
    return EvaluatorMetadata(
        id="test-evaluator",
        version="0.1",
        name="Test Evaluator",
        description="Used in unit tests.",
        maturity=EvaluatorMaturity.beta,
    )


@pytest.fixture
def prompt_settings_google():
    """PromptSettings configured for Google, usable in multiple test modules."""
    return PromptSettings(
        provider_type=LlmProvider.GOOGLE,
        model="gemini-2.0-flash",
        temperature=0.0,
    )


@pytest.fixture
def evaluation_metadata(evaluator_metadata, prompt_settings_google):
    """EvaluationMetadata with sensible defaults for unit tests."""
    return EvaluationMetadata(
        evaluator_metadata=evaluator_metadata,
        evaluation_settings=ConventionalityEvaluationSettings(
            prompt_settings_step_conventionality_evaluation=prompt_settings_google,
        ),
        input_metadata={},
    )


@pytest.fixture
def config():
    """EvaluatorConfig with no telemetry, suitable for unit tests."""
    return create_config_no_telemetry()
