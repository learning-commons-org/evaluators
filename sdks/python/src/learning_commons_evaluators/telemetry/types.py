"""The telemetry event, exactly as the collector reads it.

Events from both SDKs land in one collector and are aggregated together, so the wire format
here is the TypeScript SDK's ``TelemetryEvent`` (``src/telemetry/types.ts``) field for
field: same names, same types, same omissions. A field added on one side only would split
the aggregate it feeds, so the two move together — the next change is the migration that
takes the SDK spec's telemetry schema out of Draft.

What an event may not carry is the text being evaluated. There is no option to include it in
either SDK, so an event reports ``text_length_chars`` and nothing of the text itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

#: What an evaluation did, from the collector's point of view.
EvaluationStatus = Literal["success", "error"]


@dataclass(frozen=True)
class EventTokenUsage:
    """Token counts as an event reports them, summed over the steps that completed."""

    input_tokens: int
    output_tokens: int

    def payload(self) -> dict[str, int]:
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens}


@dataclass(frozen=True)
class StageDetail:
    """One step of an evaluation: what ran, on which model, for how long, at what cost.

    The TypeScript type also declares ``schema_validation_failed``, which nothing sets; it
    is left out here rather than sent as a constant the collector would have to ignore.
    """

    stage: str
    provider: str
    latency_ms: int
    token_usage: EventTokenUsage | None = None

    def payload(self) -> dict[str, Any]:
        stage: dict[str, Any] = {
            "stage": self.stage,
            "provider": self.provider,
            "latency_ms": self.latency_ms,
        }
        if self.token_usage is not None:
            stage["token_usage"] = self.token_usage.payload()
        return stage


@dataclass(frozen=True)
class TelemetryEvent:
    """One evaluation, reported once, whether it succeeded or failed."""

    timestamp: str
    #: This SDK's identifier and version; see :func:`~.utils.sdk_version`.
    sdk_version: str
    #: The evaluator's current dotted registry id.
    evaluator_type: str
    status: EvaluationStatus
    #: Wall-clock duration of the whole evaluation, including a failed one.
    latency_ms: int
    text_length_chars: int
    #: ``provider:model`` for the model that answered, or that was being called when the
    #: evaluation failed.
    provider: str
    #: The grade evaluated, empty for an evaluator that takes none. The wire field stays
    #: ``grade`` until the telemetry schema is renamed; the collector reads that name today.
    grade: str = ""
    #: The error's class name, on a failed evaluation only.
    error_code: str | None = None
    token_usage: EventTokenUsage | None = None
    #: One entry per completed step; empty when none completed.
    stage_details: tuple[StageDetail, ...] = ()
    #: ``True`` when the caller configured a ``model_override``, otherwise absent.
    model_override: bool | None = None

    def payload(self) -> dict[str, Any]:
        """The event as the collector receives it.

        Keys are built in the TypeScript SDK's declaration order, and an absent optional
        field is omitted rather than sent as ``null`` — which is what ``JSON.stringify``
        does with ``undefined`` there, so the two SDKs put the same bytes on the wire.
        """
        event: dict[str, Any] = {
            "timestamp": self.timestamp,
            "sdk_version": self.sdk_version,
            "evaluator_type": self.evaluator_type,
            "grade": self.grade,
            "status": self.status,
        }
        if self.error_code is not None:
            event["error_code"] = self.error_code
        event["latency_ms"] = self.latency_ms
        event["text_length_chars"] = self.text_length_chars
        event["provider"] = self.provider
        if self.token_usage is not None:
            event["token_usage"] = self.token_usage.payload()
        if self.stage_details:
            # Nested under ``metadata``, as the TypeScript event nests it, so the collector
            # reads one optional per-stage breakdown rather than two shapes.
            event["metadata"] = {"stage_details": [stage.payload() for stage in self.stage_details]}
        if self.model_override:
            event["model_override"] = True
        return event


__all__ = ["EvaluationStatus", "EventTokenUsage", "StageDetail", "TelemetryEvent"]
