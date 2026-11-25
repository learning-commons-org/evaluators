"""The telemetry event, exactly as the collector reads it.

The event's types and its wire serialization are generated from
``evals/telemetry/event.schema.json`` — the single source of truth the TypeScript SDK
generates from too — into :mod:`._event_generated`. Field names, types, wire order, and
which fields may be omitted all come from that schema, so the two SDKs put the same bytes
on the wire by construction rather than by keeping two hand-written mirrors in step. To add
a field, edit the schema and regenerate; nothing here changes.

What an event may not carry is the text being evaluated. There is no option to include it in
either SDK, so an event reports ``text_length_chars`` and nothing of the text itself.
"""

from __future__ import annotations

from typing import Final

from learning_commons_evaluators.telemetry._event_generated import (
    SCHEMA_VERSION,
    EvaluationStatus,
    SdkLanguage,
    StageDetail,
    TelemetryEvent,
    TelemetryMetadata,
)

# ``TokenUsage`` is also the provider layer's name for what one call reports
# (:class:`~learning_commons_evaluators.providers.base.TokenUsage`); the event's counterpart
# keeps the name it has always had here.
from learning_commons_evaluators.telemetry._event_generated import (
    TokenUsage as EventTokenUsage,
)

#: The ``sdk_language`` every event from this SDK carries.
SDK_LANGUAGE: Final[SdkLanguage] = "python"

__all__ = [
    "SCHEMA_VERSION",
    "SDK_LANGUAGE",
    "EvaluationStatus",
    "EventTokenUsage",
    "SdkLanguage",
    "StageDetail",
    "TelemetryEvent",
    "TelemetryMetadata",
]
