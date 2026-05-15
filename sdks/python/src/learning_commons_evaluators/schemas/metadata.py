"""Evaluation metadata schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator

from learning_commons_evaluators._version import __version__ as sdk_version
from learning_commons_evaluators.schemas.config import LLMProvider, PromptSettings
from learning_commons_evaluators.schemas.input_specs import AnyInputSpec


class EvaluatorMaturity(Enum):
    alpha = "alpha"
    beta = "beta"
    rc = "rc"
    ga = "ga"


class Status(Enum):
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"


# Input metadata is the recommended way to represent an input in logs and metadata.
InputMetadata = dict[str, Any]


class EvaluatorMetadata(BaseModel):
    """Evaluator metadata: id, version, name, description; maturity (alpha, beta, rc, ga); sdk_version."""

    id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    maturity: EvaluatorMaturity
    sdk_version: str = f"learning-commons-evaluators-python-{sdk_version}"
    inputs: dict[str, AnyInputSpec] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce_toml_inputs(cls, data: Any) -> Any:
        """Turn ``[[evaluator_metadata.inputs]]`` list rows into ``inputs`` keyed by field name."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if "inputs" not in out:
            return out
        raw = out["inputs"]
        if isinstance(raw, list):
            adapter: TypeAdapter[Any] = TypeAdapter(AnyInputSpec)
            parsed: dict[str, AnyInputSpec] = {}
            for item in raw:
                if not (isinstance(item, dict) and "name" in item):
                    continue
                parsed[str(item["name"])] = adapter.validate_python(item)
            out["inputs"] = parsed
        elif raw is None:
            out["inputs"] = {}
        return out

    @field_validator("id", "version", "name", "description", mode="before")
    @classmethod
    def _strip_required_strings(cls, v: Any) -> Any:
        if v is None:
            return v
        return str(v).strip()

    @field_validator("maturity", mode="before")
    @classmethod
    def _normalize_maturity(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower()
        return v


class TokenUsage(BaseModel):
    """Token usage for a some step of an evaluation: provider type, model, and token counts."""

    provider_type: LLMProvider
    model: str
    input_tokens: int
    output_tokens: int


# Well-known keys for :attr:`StepMetadata.extras` (e.g. prompt / LLM steps).
PROMPT_STEP_EXTRA_PROMPT_SETTINGS = "prompt_settings"
PROMPT_STEP_EXTRA_TOKEN_USAGE = "token_usage"


class StepMetadata(BaseModel):
    """Metadata common to every evaluation step.

    Use :attr:`extras` for step-specific payloads (prompt settings, token usage, etc.).
    See :data:`PROMPT_STEP_EXTRA_PROMPT_SETTINGS` and :data:`PROMPT_STEP_EXTRA_TOKEN_USAGE` for
    standard keys used by :meth:`BaseEvaluator.execute_prompt_chain_step`.
    """

    step_id: str
    status: Status = Status.processing
    error_details: str = ""
    processing_time_ms: float = 0
    extras: dict[str, Any] = Field(default_factory=dict)


def prompt_settings_to_extras_value(settings: PromptSettings) -> dict[str, Any]:
    """JSON-friendly dict for the value at :data:`PROMPT_STEP_EXTRA_PROMPT_SETTINGS` in :attr:`StepMetadata.extras`."""
    return {
        "provider_type": settings.provider_type.value,
        "model": settings.model,
        "temperature": settings.temperature,
    }


class EvaluationMetadata(BaseModel):
    """Metadata for an evaluation run."""

    model_config = {"arbitrary_types_allowed": True}

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evaluator_metadata: EvaluatorMetadata
    evaluation_settings: Any
    input_metadata: InputMetadata
    status: Status = Status.processing
    error_details: str | None = None
    total_token_usage: dict[LLMProvider, TokenUsage] = Field(default_factory=dict)
    processing_time_ms: float = 0
    step_details: dict[str, StepMetadata] = Field(default_factory=dict)
