"""GENERATED — do not edit directly.

Source: evals/telemetry/event.schema.json
Regenerate: python3 scripts/generate_telemetry_schema.py (from the repo root)

The telemetry event's types and wire serialization. ``payload()`` writes keys in schema
order, omits an unset optional field rather than writing ``null``, and writes no key the
schema does not declare — the same rules as the TypeScript SDK's generated serializer,
so the two SDKs put the same bytes on the wire for the same event.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

#: The ``schema_version`` this SDK's events are built against.
SCHEMA_VERSION: Literal[1] = 1

#: What an evaluation did, from the collector's point of view.
EvaluationStatus = Literal["success", "error"]

#: The SDK an event came from.
SdkLanguage = Literal["python", "typescript"]


@dataclass(frozen=True, kw_only=True)
class TokenUsage:
    """Token counts reported by the model provider."""

    input_tokens: int
    output_tokens: int

    def payload(self) -> dict[str, Any]:
        """This value as it goes on the wire."""
        wire: dict[str, Any] = {}
        wire["input_tokens"] = self.input_tokens
        wire["output_tokens"] = self.output_tokens
        return wire


@dataclass(frozen=True, kw_only=True)
class StageDetail:
    """One step of an evaluation: what ran, on which model, for how long, at what cost."""

    #: Stage name, e.g. `background_knowledge` or `complexity_evaluation`.
    stage: str
    #: `provider:model` for this stage.
    provider: str
    #: This stage's latency in milliseconds, including its retries.
    latency_ms: int
    token_usage: TokenUsage | None = None
    #: Declared but never set by either SDK; to be replaced by `output_failure_kind` (telemetry
    #: Phase B1).
    schema_validation_failed: bool | None = None

    def payload(self) -> dict[str, Any]:
        """This value as it goes on the wire."""
        wire: dict[str, Any] = {}
        wire["stage"] = self.stage
        wire["provider"] = self.provider
        wire["latency_ms"] = self.latency_ms
        if self.token_usage is not None:
            wire["token_usage"] = self.token_usage.payload()
        if self.schema_validation_failed is not None:
            wire["schema_validation_failed"] = self.schema_validation_failed
        return wire


@dataclass(frozen=True, kw_only=True)
class TelemetryMetadata:
    """The only place per-evaluator variation may live. Each property is one named, typed block
    that an evaluator emits only when it has something to report in it; every block is optional.
    """

    #: One entry per completed step, in run order. Emitted by every evaluator that runs model steps
    #: (single-step, multi-step, and Math Standards Alignment).
    stage_details: tuple[StageDetail, ...] | None = None

    def payload(self) -> dict[str, Any]:
        """This value as it goes on the wire."""
        wire: dict[str, Any] = {}
        if self.stage_details is not None:
            wire["stage_details"] = [item.payload() for item in self.stage_details]
        return wire


@dataclass(frozen=True, kw_only=True)
class TelemetryEvent:
    """One evaluation, reported once to the Learning Commons telemetry collector, whether it
    succeeded or failed. This file is the single source of truth for the event both SDKs send:
    their types and wire serialization are generated from it by
    scripts/generate_telemetry_schema.py. Property order here is the order keys are written on
    the wire, and an optional property is omitted rather than sent as null. No property may
    carry the text being evaluated. Per-evaluator variation lives only in the named, typed
    blocks under `metadata`; the rest of the envelope is the same for every evaluator. Changing
    the wire shape means bumping `schema_version` in the same change (the telemetry-schema check
    enforces it).
    """

    #: Version of this schema the event was built against. Bumped in the same change as any
    #: wire-shape change; an event without it predates versioning.
    schema_version: Literal[1] = 1
    #: When the event was emitted (the evaluation's completion), as JavaScript's Date.toISOString
    #: writes it: millisecond precision, Z suffix.
    timestamp: str
    #: The emitting SDK's version. The Python SDK prefixes it with its package identifier; the
    #: TypeScript SDK sends it bare.
    sdk_version: str
    #: Which SDK emitted the event.
    sdk_language: SdkLanguage
    #: The evaluator's current dotted registry id.
    evaluator_type: str
    #: The grade evaluated. Always present: empty string for an evaluator that takes no grade, or
    #: when the evaluation failed before the grade was known.
    grade: str
    status: EvaluationStatus
    #: The error's class name, on a failed evaluation only.
    error_code: str | None = None
    #: Wall-clock duration of the whole evaluation in milliseconds, including a failed one.
    latency_ms: int
    #: Length of the evaluator's primary text input in UTF-16 code units (JavaScript's
    #: String.length); 0 when the inputs were never validated.
    text_length_chars: int
    #: `provider:model` for the model that answered, or that was being called when the evaluation
    #: failed. `provider1+provider2` for an evaluator that reports a combined label.
    provider: str
    #: Token usage summed over the steps that completed. Absent when no step completed.
    token_usage: TokenUsage | None = None
    #: Per-evaluator extension blocks. Absent when no block has anything to report.
    metadata: TelemetryMetadata | None = None
    #: true when the caller configured a model override; absent otherwise.
    model_override: bool | None = None

    def payload(self) -> dict[str, Any]:
        """This value as it goes on the wire."""
        wire: dict[str, Any] = {}
        wire["schema_version"] = self.schema_version
        wire["timestamp"] = self.timestamp
        wire["sdk_version"] = self.sdk_version
        wire["sdk_language"] = self.sdk_language
        wire["evaluator_type"] = self.evaluator_type
        wire["grade"] = self.grade
        wire["status"] = self.status
        if self.error_code is not None:
            wire["error_code"] = self.error_code
        wire["latency_ms"] = self.latency_ms
        wire["text_length_chars"] = self.text_length_chars
        wire["provider"] = self.provider
        if self.token_usage is not None:
            wire["token_usage"] = self.token_usage.payload()
        if self.metadata is not None:
            wire["metadata"] = self.metadata.payload()
        if self.model_override is not None:
            wire["model_override"] = self.model_override
        return wire


__all__ = [
    "EvaluationStatus",
    "SCHEMA_VERSION",
    "SdkLanguage",
    "StageDetail",
    "TelemetryEvent",
    "TelemetryMetadata",
    "TokenUsage",
]
