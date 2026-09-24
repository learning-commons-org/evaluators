"""Map Python evaluation context to TypeScript-shaped :class:`~learning_commons_evaluators.schemas.ts_telemetry.TelemetryEvent`.

Information intentionally dropped or simplified when adapting:

- Full :class:`~learning_commons_evaluators.schemas.metadata.EvaluatorMetadata` (name,
  version, description, maturity, input specs) is not sent; only ``evaluator_metadata.id``
  becomes ``evaluator_type`` and ``evaluator_metadata.sdk_version`` maps to ``sdk_version``.
- The entire ``input_metadata`` dict is not reproduced; ``grade`` and ``text_length_chars``
  are inferred from common shapes when possible.
- :class:`~learning_commons_evaluators.schemas.metadata.Status` ``processing`` is mapped to
  ``status`` ``"error"`` (non-terminal) the same as failures, since TS only allows
  success/error.
- ``error_code`` is derived from ``error_details`` text, not a structured error taxonomy.
- :attr:`~learning_commons_evaluators.schemas.metadata.EvaluationMetadata.evaluation_settings`
  is omitted.
- Per-step ``StepMetadata.error_details`` and most of ``extras`` beyond prompt settings /
  token usage are not mapped to ``stage_details``.
"""

from __future__ import annotations

from typing import Any

from learning_commons_evaluators.schemas.config import EvaluatorConfig, LLMProvider
from learning_commons_evaluators.schemas.evaluator import EvaluationInput
from learning_commons_evaluators.schemas.metadata import (
    PROMPT_STEP_EXTRA_PROMPT_SETTINGS,
    PROMPT_STEP_EXTRA_TOKEN_USAGE,
    EvaluationMetadata,
    Status,
    StepMetadata,
)
from learning_commons_evaluators.schemas.metadata import (
    TokenUsage as EvaluationTokenUsage,
)
from learning_commons_evaluators.schemas.ts_telemetry import (
    EvaluationTelemetryStatus,
    TelemetryEvent,
    TelemetryMetadataPayload,
    TelemetryStageDetail,
    TelemetryTokenUsage,
)
from learning_commons_evaluators.telemetry.utils import iso_utc_z


def _map_status(status: Status) -> EvaluationTelemetryStatus:
    if status is Status.succeeded:
        return "success"
    return "error"


def _grade_from_input_metadata(input_metadata: dict[str, Any]) -> str | None:
    gl = input_metadata.get("grade_level")
    if gl is None:
        return None
    if isinstance(gl, dict) and "grade" in gl:
        return str(gl["grade"])
    if isinstance(gl, (int, float, str)):
        return str(gl)
    return None


def _extract_primary_input_text(inp: EvaluationInput | None) -> str | None:
    if inp is None:
        return None
    field = getattr(inp, "text", None)
    if field is None:
        return None
    value = getattr(field, "value", None)
    return value if isinstance(value, str) else None


def _text_length_chars(
    input_metadata: dict[str, Any],
    input_text: str | None,
    inp: EvaluationInput | None,
) -> int:
    if input_text is not None:
        return len(input_text)
    text_meta = input_metadata.get("text")
    if isinstance(text_meta, dict):
        for key in ("textLength", "length", "charCount"):
            v = text_meta.get(key)
            if isinstance(v, int):
                return v
    extracted = _extract_primary_input_text(inp)
    if extracted is not None:
        return len(extracted)
    return 0


def _error_code(error_details: str | None) -> str | None:
    if not error_details:
        return None
    line = error_details.strip().split("\n", 1)[0].strip()
    return line[:512] if line else None


def _provider_label(usage: EvaluationTokenUsage) -> str:
    return f"{usage.provider_type.value}:{usage.model}"


def _aggregate_provider(total: dict[LLMProvider, EvaluationTokenUsage]) -> str:
    if not total:
        return "unknown"
    parts = [_provider_label(u) for u in total.values()]
    return " + ".join(sorted(parts))


def _aggregate_token_usage(
    total: dict[LLMProvider, EvaluationTokenUsage],
) -> TelemetryTokenUsage | None:
    if not total:
        return None
    it = sum(u.input_tokens for u in total.values())
    ot = sum(u.output_tokens for u in total.values())
    return TelemetryTokenUsage(input_tokens=it, output_tokens=ot)


def _provider_from_step_extras(step: StepMetadata) -> str:
    raw = step.extras.get(PROMPT_STEP_EXTRA_PROMPT_SETTINGS)
    if isinstance(raw, dict):
        pt = raw.get("provider_type")
        model = raw.get("model")
        if isinstance(pt, str) and isinstance(model, str):
            return f"{pt}:{model}"
    return "unknown"


def _token_usage_from_step_extras(step: StepMetadata) -> TelemetryTokenUsage | None:
    raw = step.extras.get(PROMPT_STEP_EXTRA_TOKEN_USAGE)
    if not isinstance(raw, dict):
        return None
    try:
        it = int(raw["input_tokens"])
        ot = int(raw["output_tokens"])
    except (KeyError, TypeError, ValueError):
        return None
    return TelemetryTokenUsage(input_tokens=it, output_tokens=ot)


def _stage_details(evaluation_metadata: EvaluationMetadata) -> list[TelemetryStageDetail] | None:
    if not evaluation_metadata.step_details:
        return None
    details: list[TelemetryStageDetail] = []
    for step_id, step in evaluation_metadata.step_details.items():
        details.append(
            TelemetryStageDetail(
                stage=step_id,
                provider=_provider_from_step_extras(step),
                latency_ms=step.processing_time_ms,
                token_usage=_token_usage_from_step_extras(step),
            )
        )
    return details or None


def evaluation_to_typescript_telemetry_event(
    evaluation_metadata: EvaluationMetadata,
    inp: EvaluationInput | None,
    config: EvaluatorConfig,
) -> TelemetryEvent:
    """Build a TS-shaped :class:`TelemetryEvent` from Python evaluation state."""
    input_text: str | None = None
    if config.telemetry.send_full_input_with_telemetry and inp is not None:
        input_text = _extract_primary_input_text(inp)

    meta = evaluation_metadata.input_metadata
    grade = _grade_from_input_metadata(meta)
    status = _map_status(evaluation_metadata.status)
    stages = _stage_details(evaluation_metadata)
    metadata_payload = (
        TelemetryMetadataPayload(stage_details=stages) if stages is not None else None
    )

    return TelemetryEvent(
        timestamp=iso_utc_z(evaluation_metadata.timestamp),
        sdk_version=evaluation_metadata.evaluator_metadata.sdk_version,
        evaluator_type=evaluation_metadata.evaluator_metadata.id,
        grade=grade,
        status=status,
        error_code=_error_code(evaluation_metadata.error_details) if status == "error" else None,
        latency_ms=evaluation_metadata.processing_time_ms,
        text_length_chars=_text_length_chars(meta, input_text, inp),
        provider=_aggregate_provider(evaluation_metadata.total_token_usage),
        token_usage=_aggregate_token_usage(evaluation_metadata.total_token_usage),
        metadata=metadata_payload,
        input_text=input_text,
    )
