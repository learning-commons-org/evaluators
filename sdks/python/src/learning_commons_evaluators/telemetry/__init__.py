"""Telemetry: one event per evaluation, sent fire-and-forget to the Learning Commons collector.

The event format is the TypeScript SDK's, field for field (:mod:`.types`); the emit path is
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
    EvaluationStatus,
    EventTokenUsage,
    StageDetail,
    TelemetryEvent,
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
    "SDK_IDENTIFIER",
    "TIMEOUT_SECONDS",
    "EvaluationStatus",
    "EventTokenUsage",
    "StageDetail",
    "TelemetryClient",
    "TelemetryClientConfig",
    "TelemetryEvent",
    "TelemetryRun",
    "client_id",
    "config_file",
    "flush",
    "sdk_version",
    "utc_timestamp",
]
