"""
Evaluator configuration and metadata.

LLM provider configs (base, Google, OpenAI, Anthropic), EvaluatorConfig, and evaluator
metadata live here. Evaluator config is created via factory methods (create_config,
create_config_no_telemetry, create_config_telemetry_with_full_input).
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, ConfigDict

from learning_commons_evaluators.logger import Logger, get_logger

DEFAULT_TELEMETRY_EVENTS_ENDPOINT = "https://api.learningcommons.org/evaluators-telemetry/v1/events"

# Shared per process so multiple :class:`EvaluatorConfig` instances derive the same client id.
_PROCESS_CLIENT_ID_SEED = uuid.uuid4()

# --- LLM provider configs (for LLM calls in prompt steps) ---


class LLMProvider(str, Enum):
    """LLM provider identifier. Subclass of str so it compares and serializes as the provider name."""

    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENAI = "openai"


@dataclass(frozen=True)
class LLMProviderConfig:
    """Base type for LLM provider configuration."""

    api_key: str
    type: LLMProvider


@dataclass(frozen=True)
class GoogleLLMProviderConfig(LLMProviderConfig):
    """Google (Gemini) LLM provider config. Takes an API key."""

    type: LLMProvider = LLMProvider.GOOGLE


@dataclass(frozen=True)
class OpenAILLMProviderConfig(LLMProviderConfig):
    """OpenAI LLM provider config. Takes an API key."""

    type: LLMProvider = LLMProvider.OPENAI
    # TODO: verify base_url functionality before enabling
    # base_url: str | None = (
    #     None  # Optional; for OpenAI-compatible endpoints (e.g. Azure, proxy). Used only when type is OPENAI.
    # )


@dataclass(frozen=True)
class AnthropicLLMProviderConfig(LLMProviderConfig):
    """Anthropic (Claude) LLM provider config. Takes an API key."""

    type: LLMProvider = LLMProvider.ANTHROPIC


@dataclass(frozen=True)
class PromptSettings:
    """Settings for a prompt step: provider, model, temperature."""

    provider_type: LLMProvider
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

    endpoint: str = DEFAULT_TELEMETRY_EVENTS_ENDPOINT
    telemetry_partner_id: str | None = None
    send_full_input_with_telemetry: bool = False


# --- Evaluator config ---


@dataclass(frozen=True)
class EvaluatorConfig:
    """
    Config for creating an evaluator: LLM provider configs, logger, telemetry.

    Logger defaults to the SDK package logger (``learning_commons_evaluators``), so
    log records propagate like typical library loggers. Pass ``logger=`` to use a
    different logger (for example ``create_silent_logger()`` from
    ``learning_commons_evaluators.logger`` to discard SDK messages). Accepts any
    standard ``logging.Logger`` instance.
    Create via create_config, create_config_no_telemetry, or
    create_config_telemetry_with_full_input, then pass the config to the evaluator constructor.
    """

    google_llm_provider_config: GoogleLLMProviderConfig | None = None
    openai_llm_provider_config: OpenAILLMProviderConfig | None = None
    anthropic_llm_provider_config: AnthropicLLMProviderConfig | None = None
    logger: Logger = field(default_factory=get_logger)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)

    # Temporary until we finalize the telemetry API key/client id strategy.
    #: UUID v5 namespace for deriving ``X-Client-ID`` when ``telemetry_partner_id`` is an API key.
    #: Defaults to a single per-process seed so all configs in one run share the same derived id.
    client_id_seed: uuid.UUID = field(default=_PROCESS_CLIENT_ID_SEED)


def create_config(
    *,
    google_llm_provider_config: GoogleLLMProviderConfig | None = None,
    openai_llm_provider_config: OpenAILLMProviderConfig | None = None,
    anthropic_llm_provider_config: AnthropicLLMProviderConfig | None = None,
    logger: Logger | None = None,
    telemetry_partner_id: str,
    send_full_input_with_telemetry: bool = False,
) -> EvaluatorConfig:
    """Create evaluator config with telemetry. telemetry_partner_id is required."""
    return EvaluatorConfig(
        google_llm_provider_config=google_llm_provider_config,
        openai_llm_provider_config=openai_llm_provider_config,
        anthropic_llm_provider_config=anthropic_llm_provider_config,
        logger=get_logger() if logger is None else logger,
        telemetry=TelemetryConfig(
            telemetry_partner_id=telemetry_partner_id,
            send_full_input_with_telemetry=send_full_input_with_telemetry,
        ),
    )


def create_config_telemetry_with_full_input(
    *,
    google_llm_provider_config: GoogleLLMProviderConfig | None = None,
    openai_llm_provider_config: OpenAILLMProviderConfig | None = None,
    anthropic_llm_provider_config: AnthropicLLMProviderConfig | None = None,
    logger: Logger | None = None,
    telemetry_partner_id: str,
) -> EvaluatorConfig:
    """Create evaluator config with telemetry and full input sent with telemetry."""
    return EvaluatorConfig(
        google_llm_provider_config=google_llm_provider_config,
        openai_llm_provider_config=openai_llm_provider_config,
        anthropic_llm_provider_config=anthropic_llm_provider_config,
        logger=get_logger() if logger is None else logger,
        telemetry=TelemetryConfig(
            telemetry_partner_id=telemetry_partner_id, send_full_input_with_telemetry=True
        ),
    )


def create_config_anonymous_telemetry(
    *,
    google_llm_provider_config: GoogleLLMProviderConfig | None = None,
    openai_llm_provider_config: OpenAILLMProviderConfig | None = None,
    anthropic_llm_provider_config: AnthropicLLMProviderConfig | None = None,
    logger: Logger | None = None,
    send_full_input_with_telemetry: bool = False,
) -> EvaluatorConfig:
    """Create evaluator config with anonymous telemetry."""
    anonymous_telemetry_id = str(uuid.uuid4())
    return create_config_with_telemetry_config(
        google_llm_provider_config=google_llm_provider_config,
        openai_llm_provider_config=openai_llm_provider_config,
        anthropic_llm_provider_config=anthropic_llm_provider_config,
        logger=logger,
        telemetry_config=TelemetryConfig(
            telemetry_partner_id=anonymous_telemetry_id,
            send_full_input_with_telemetry=send_full_input_with_telemetry,
        ),
    )


def create_config_anonymous_telemetry_with_full_input(
    *,
    google_llm_provider_config: GoogleLLMProviderConfig | None = None,
    openai_llm_provider_config: OpenAILLMProviderConfig | None = None,
    anthropic_llm_provider_config: AnthropicLLMProviderConfig | None = None,
    logger: Logger | None = None,
) -> EvaluatorConfig:
    """Create evaluator config with anonymous telemetry and full input sent with telemetry."""
    return create_config_anonymous_telemetry(
        google_llm_provider_config=google_llm_provider_config,
        openai_llm_provider_config=openai_llm_provider_config,
        anthropic_llm_provider_config=anthropic_llm_provider_config,
        logger=logger,
        send_full_input_with_telemetry=True,
    )


def create_config_with_telemetry_config(
    *,
    google_llm_provider_config: GoogleLLMProviderConfig | None = None,
    openai_llm_provider_config: OpenAILLMProviderConfig | None = None,
    anthropic_llm_provider_config: AnthropicLLMProviderConfig | None = None,
    logger: Logger | None = None,
    telemetry_config: TelemetryConfig,
) -> EvaluatorConfig:
    """Create evaluator config with telemetry. telemetry_config is required."""
    return EvaluatorConfig(
        google_llm_provider_config=google_llm_provider_config,
        openai_llm_provider_config=openai_llm_provider_config,
        anthropic_llm_provider_config=anthropic_llm_provider_config,
        logger=get_logger() if logger is None else logger,
        telemetry=telemetry_config,
    )


def create_config_no_telemetry(
    *,
    google_llm_provider_config: GoogleLLMProviderConfig | None = None,
    openai_llm_provider_config: OpenAILLMProviderConfig | None = None,
    anthropic_llm_provider_config: AnthropicLLMProviderConfig | None = None,
    logger: Logger | None = None,
) -> EvaluatorConfig:
    """Create evaluator config with telemetry disabled."""
    return EvaluatorConfig(
        google_llm_provider_config=google_llm_provider_config,
        openai_llm_provider_config=openai_llm_provider_config,
        anthropic_llm_provider_config=anthropic_llm_provider_config,
        logger=get_logger() if logger is None else logger,
        telemetry=TelemetryConfig(telemetry_partner_id=None, send_full_input_with_telemetry=False),
    )
