"""Shared pytest fixtures for the learning_commons_evaluators test suite."""

import pytest

from learning_commons_evaluators import create_config_no_telemetry
from learning_commons_evaluators.schemas.config import (
    EvaluationSettings,
    GoogleLLMProviderConfig,
    OpenAILLMProviderConfig,
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
def evaluation_metadata(evaluator_metadata):
    """EvaluationMetadata with sensible defaults for unit tests.

    Uses base :class:`EvaluationSettings` so this stays evaluator-agnostic; tests for a
    concrete evaluator should build that evaluator's settings (or a dedicated fixture)
    when they need specific fields.
    """
    return EvaluationMetadata(
        evaluator_metadata=evaluator_metadata,
        evaluation_settings=EvaluationSettings(),
        input_metadata={},
    )


@pytest.fixture
def config():
    """EvaluatorConfig with no telemetry, suitable for unit tests."""
    return create_config_no_telemetry()


@pytest.fixture
def config_with_google():
    """EvaluatorConfig with Google provider set (conventionality and similar evaluators)."""
    return create_config_no_telemetry(
        google_llm_provider_config=GoogleLLMProviderConfig(api_key="test-google-key"),
    )


@pytest.fixture
def config_with_google_and_openai():
    """EvaluatorConfig with Google and OpenAI providers set (vocabulary evaluator)."""
    return create_config_no_telemetry(
        google_llm_provider_config=GoogleLLMProviderConfig(api_key="test-google-key"),
        openai_llm_provider_config=OpenAILLMProviderConfig(api_key="test-openai-key"),
    )
