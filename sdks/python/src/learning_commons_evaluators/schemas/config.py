"""
Evaluator configuration and metadata.

Prompt provider configs (base, Google, OpenAI, Anthropic), EvaluatorConfig, and evaluator
metadata live here. Evaluator config is created via factory methods (create_config,
create_config_no_telemetry, create_config_telemetry_with_full_input).
"""

from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, ConfigDict

from learning_commons_evaluators.logger import Logger, get_logger

# --- Prompt provider configs (for LLM calls in prompt steps) ---


# TODO: rename to LLMProvider
class LlmProvider(str, Enum):
    """LLM provider identifier. Subclass of str so it compares and serializes as the provider name."""

    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI = "openai"


# TODO: rename to LLMProviderConfig and subclasses to GoogleLLMProviderConfig, OpenAILLMProviderConfig, AnthropicLLMProviderConfig.
@dataclass(frozen=True)
class PromptProviderConfig:
    """Base type for prompt provider configuration."""

    api_key: str
    type: LlmProvider
    # TODO: verify base_url functionality before enabling
    # base_url: str | None = (
    #     None  # Optional; for OpenAI-compatible endpoints (e.g. Azure, proxy). Used only when type is OPENAI.
    # )


@dataclass(frozen=True)
class GooglePromptProviderConfig(PromptProviderConfig):
    """Google (Gemini) prompt provider config. Takes an API key."""

    type: LlmProvider = LlmProvider.GOOGLE


@dataclass(frozen=True)
class OpenAIPromptProviderConfig(PromptProviderConfig):
    """OpenAI prompt provider config. Takes an API key. Optional base_url for custom endpoints."""

    type: LlmProvider = LlmProvider.OPENAI


@dataclass(frozen=True)
class AnthropicPromptProviderConfig(PromptProviderConfig):
    """Anthropic (Claude) prompt provider config. Takes an API key."""

    type: LlmProvider = LlmProvider.ANTHROPIC


@dataclass(frozen=True)
class PromptSettings:
    """Settings for a prompt step: provider, model, temperature."""

    provider_type: LlmProvider
    model: str
    temperature: float


class EvaluationSettings(BaseModel):
    """Base model for evaluation run settings (e.g. model, temperature).

    Concrete evaluators subclass this and declare evaluation settings fields as needed.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)


@dataclass(frozen=True)
class TelemetryConfig:
    """Config for telemetry."""

    telemetry_partner_id: str | None = None
    send_full_input_with_telemetry: bool = False

# --- Evaluator config ---


@dataclass(frozen=True)
class EvaluatorConfig:
    """
    Config for creating an evaluator: prompt provider configs, logger, telemetry.

    Logger defaults to the SDK package logger (``learning_commons_evaluators``), so
    log records propagate like typical library loggers. Pass ``logger=`` to use a
    different logger (for example ``create_silent_logger()`` from
    ``learning_commons_evaluators.logger`` to discard SDK messages). Accepts any
    standard ``logging.Logger`` instance.
    Create via create_config, create_config_no_telemetry, or
    create_config_telemetry_with_full_input, then pass the config to the evaluator constructor.
    """

    google_prompt_provider_config: GooglePromptProviderConfig | None = None
    openai_prompt_provider_config: OpenAIPromptProviderConfig | None = None
    anthropic_prompt_provider_config: AnthropicPromptProviderConfig | None = None
    logger: Logger = field(default_factory=get_logger)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)


def create_config(
    *,
    google_prompt_provider_config: GooglePromptProviderConfig | None = None,
    openai_prompt_provider_config: OpenAIPromptProviderConfig | None = None,
    anthropic_prompt_provider_config: AnthropicPromptProviderConfig | None = None,
    logger: Logger | None = None,
    telemetry_partner_id: str,
    send_full_input_with_telemetry: bool = False,
) -> EvaluatorConfig:
    """Create evaluator config with telemetry. telemetry_partner_id is required."""
    return EvaluatorConfig(
        google_prompt_provider_config=google_prompt_provider_config,
        openai_prompt_provider_config=openai_prompt_provider_config,
        anthropic_prompt_provider_config=anthropic_prompt_provider_config,
        logger=get_logger() if logger is None else logger,
        telemetry=TelemetryConfig(telemetry_partner_id=telemetry_partner_id, send_full_input_with_telemetry=send_full_input_with_telemetry),
    )


def create_config_no_telemetry(
    *,
    google_prompt_provider_config: GooglePromptProviderConfig | None = None,
    openai_prompt_provider_config: OpenAIPromptProviderConfig | None = None,
    anthropic_prompt_provider_config: AnthropicPromptProviderConfig | None = None,
    logger: Logger | None = None,
) -> EvaluatorConfig:
    """Create evaluator config with telemetry disabled."""
    return EvaluatorConfig(
        google_prompt_provider_config=google_prompt_provider_config,
        openai_prompt_provider_config=openai_prompt_provider_config,
        anthropic_prompt_provider_config=anthropic_prompt_provider_config,
        logger=get_logger() if logger is None else logger,
        telemetry=TelemetryConfig(telemetry_partner_id=None, send_full_input_with_telemetry=False),
    )


def create_config_telemetry_with_full_input(
    *,
    google_prompt_provider_config: GooglePromptProviderConfig | None = None,
    openai_prompt_provider_config: OpenAIPromptProviderConfig | None = None,
    anthropic_prompt_provider_config: AnthropicPromptProviderConfig | None = None,
    logger: Logger | None = None,
    telemetry_partner_id: str,
) -> EvaluatorConfig:
    """Create evaluator config with telemetry and full input sent with telemetry."""
    return EvaluatorConfig(
        google_prompt_provider_config=google_prompt_provider_config,
        openai_prompt_provider_config=openai_prompt_provider_config,
        anthropic_prompt_provider_config=anthropic_prompt_provider_config,
        logger=get_logger() if logger is None else logger,
        telemetry=TelemetryConfig(telemetry_partner_id=telemetry_partner_id, send_full_input_with_telemetry=True),
    )
