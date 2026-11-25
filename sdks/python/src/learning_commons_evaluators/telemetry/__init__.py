"""Telemetry: one event per evaluation, sent fire-and-forget to the Learning Commons collector.

The event format is generated from the schema both SDKs share (:mod:`.types`); the emit path is
in :class:`~learning_commons_evaluators.evaluators.base.BaseEvaluator`, so every evaluator
reports without code of its own. Nothing here is public API: callers configure telemetry
through :class:`~learning_commons_evaluators.config.TelemetryOptions` and never build an
event themselves.
"""

from __future__ import annotations

from learning_commons_evaluators.telemetry.client import (
    COLLECTOR_ENDPOINT,
    QUEUE_CAPACITY,
    TIMEOUT_SECONDS,
    TelemetryClient,
    TelemetryClientConfig,
    flush,
)
from learning_commons_evaluators.telemetry.run import TelemetryRun
from learning_commons_evaluators.telemetry.types import (
    SCHEMA_VERSION,
    SDK_LANGUAGE,
    EvaluationStatus,
    EventTokenUsage,
    SdkLanguage,
    StageDetail,
    TelemetryEvent,
    TelemetryMetadata,
)
from learning_commons_evaluators.telemetry.utils import (
    SDK_IDENTIFIER,
    client_id,
    config_file,
    sdk_version,
    utc_timestamp,
)

__all__ = [
    "COLLECTOR_ENDPOINT",
    "QUEUE_CAPACITY",
    "SCHEMA_VERSION",
    "SDK_IDENTIFIER",
    "SDK_LANGUAGE",
    "TIMEOUT_SECONDS",
    "EvaluationStatus",
    "EventTokenUsage",
    "SdkLanguage",
    "StageDetail",
    "TelemetryClient",
    "TelemetryClientConfig",
    "TelemetryEvent",
    "TelemetryMetadata",
    "TelemetryRun",
    "client_id",
    "config_file",
    "flush",
    "sdk_version",
    "utc_timestamp",
]
