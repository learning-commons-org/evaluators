"""The generated event module against the schema it is generated from.

``scripts/check.py telemetry-schema`` already fails CI when the module drifts from the
schema text; these tests pin the *behaviour* the schema promises — wire order, omission,
and the version constant — so a generator change that renders the wrong rules fails here.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from learning_commons_evaluators.telemetry import _event_generated as generated
from learning_commons_evaluators.telemetry.types import (
    SCHEMA_VERSION,
    SDK_LANGUAGE,
    EventTokenUsage,
    StageDetail,
    TelemetryEvent,
    TelemetryMetadata,
)

SCHEMA_PATH = Path(__file__).resolve().parents[5] / "evals" / "telemetry" / "event.schema.json"
SCHEMA: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

USAGE = EventTokenUsage(input_tokens=250, output_tokens=120)

#: Every field set, so every key the schema declares is on the wire.
FULL = TelemetryEvent(
    timestamp="2026-11-24T00:00:00.000Z",
    sdk_version="learning-commons-evaluators-python-1.0.0",
    sdk_language=SDK_LANGUAGE,
    evaluator_type="text_complexity.ela_reading.sentence_structure",
    grade="5",
    status="error",
    error_code="RateLimitError",
    latency_ms=10,
    text_length_chars=159,
    provider="openai:gpt-4o",
    token_usage=USAGE,
    metadata=TelemetryMetadata(
        stage_details=(
            StageDetail(
                stage="analysis",
                provider="openai:gpt-4o",
                latency_ms=5,
                token_usage=USAGE,
                schema_validation_failed=False,
            ),
        )
    ),
    model_override=True,
)

#: Only what the schema requires.
MINIMAL = TelemetryEvent(
    timestamp="2026-11-24T00:00:00.000Z",
    sdk_version="learning-commons-evaluators-python-1.0.0",
    sdk_language=SDK_LANGUAGE,
    evaluator_type="feedback.writing.actionability",
    grade="",
    status="success",
    latency_ms=10,
    text_length_chars=0,
    provider="google:gemini-3-flash-preview",
)


def properties(name: str | None = None) -> list[str]:
    node = SCHEMA if name is None else SCHEMA["$defs"][name]
    return list(node["properties"])


def test_schema_version_is_the_schemas() -> None:
    assert SCHEMA["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert MINIMAL.payload()["schema_version"] == SCHEMA_VERSION


def test_this_sdk_names_itself() -> None:
    assert SDK_LANGUAGE == "python"
    assert SDK_LANGUAGE in SCHEMA["$defs"]["SdkLanguage"]["enum"]


@pytest.mark.parametrize(
    ("cls", "schema_name"),
    [
        (TelemetryEvent, None),
        (EventTokenUsage, "TokenUsage"),
        (StageDetail, "StageDetail"),
        (TelemetryMetadata, "TelemetryMetadata"),
    ],
)
def test_every_class_declares_exactly_the_schemas_properties(
    cls: type, schema_name: str | None
) -> None:
    assert [f.name for f in dataclasses.fields(cls)] == properties(schema_name)


def test_a_full_event_writes_every_key_in_schema_order() -> None:
    wire = FULL.payload()

    assert list(wire) == properties()
    assert list(wire["token_usage"]) == properties("TokenUsage")
    assert list(wire["metadata"]) == properties("TelemetryMetadata")
    assert list(wire["metadata"]["stage_details"][0]) == properties("StageDetail")


def test_a_minimal_event_writes_only_the_required_keys() -> None:
    # Unset optionals are omitted, never written as null.
    assert list(MINIMAL.payload()) == [p for p in properties() if p in SCHEMA["required"]]


def test_a_false_optional_is_written_not_omitted() -> None:
    # Omission is for unset (None) only; False is a value.
    stage = StageDetail(stage="s", provider="p", latency_ms=1, schema_validation_failed=False)

    assert stage.payload()["schema_validation_failed"] is False


def test_every_public_name_is_exported() -> None:
    assert set(generated.__all__) == {
        "SCHEMA_VERSION",
        *SCHEMA["$defs"],
        SCHEMA["title"],
    }
