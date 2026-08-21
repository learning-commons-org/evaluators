"""Wire types aligned with ``sdks/typescript/src/telemetry/types.ts``.

Hand-maintained; keep in sync with the TypeScript SDK until a shared schema exists.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

__all__ = [
    "EvaluationTelemetryStatus",
    "TelemetryEvent",
    "TelemetryMetadataPayload",
    "TelemetryStageDetail",
    "TelemetryTokenUsage",
]

# Mirrors TS ``EvaluationStatus``
EvaluationTelemetryStatus = Literal["success", "error"]


class TelemetryTokenUsage(BaseModel):
    """Mirrors TS ``TokenUsage``."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int
    output_tokens: int


class TelemetryStageDetail(BaseModel):
    """Mirrors TS ``StageDetail``."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    provider: str
    latency_ms: float
    token_usage: TelemetryTokenUsage | None = None
    schema_validation_failed: bool | None = None


class TelemetryMetadataPayload(BaseModel):
    """Mirrors TS ``TelemetryMetadata``."""

    model_config = ConfigDict(extra="forbid")

    stage_details: list[TelemetryStageDetail] | None = None


class TelemetryEvent(BaseModel):
    """Mirrors TS ``TelemetryEvent`` (JSON field names match the TS interface)."""

    model_config = ConfigDict(extra="forbid")

    timestamp: str
    sdk_version: str
    evaluator_type: str
    grade: str | None = None
    status: EvaluationTelemetryStatus
    error_code: str | None = None
    latency_ms: float
    text_length_chars: int
    provider: str
    token_usage: TelemetryTokenUsage | None = None
    metadata: TelemetryMetadataPayload | None = None
    input_text: str | None = None
