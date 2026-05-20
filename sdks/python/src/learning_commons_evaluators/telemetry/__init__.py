"""Telemetry: schedule and send evaluation events (fire-and-forget HTTP POST)."""

from __future__ import annotations

import asyncio
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx

from learning_commons_evaluators.schemas.config import EvaluatorConfig
from learning_commons_evaluators.schemas.evaluator import EvaluationInput
from learning_commons_evaluators.schemas.metadata import EvaluationMetadata
from learning_commons_evaluators.telemetry.adapter import evaluation_to_typescript_telemetry_event
from learning_commons_evaluators.telemetry.utils import client_id_from_seed, iso_utc_z

__all__ = [
    "evaluation_to_typescript_telemetry_event",
    "schedule_send_telemetry",
    "send_telemetry",
    "should_send_telemetry",
]

_TELEMETRY_EXECUTOR: ThreadPoolExecutor | None = None
_TELEMETRY_EXECUTOR_LOCK = threading.Lock()


def _get_telemetry_executor() -> ThreadPoolExecutor:
    global _TELEMETRY_EXECUTOR
    with _TELEMETRY_EXECUTOR_LOCK:
        if _TELEMETRY_EXECUTOR is None:
            _TELEMETRY_EXECUTOR = ThreadPoolExecutor(
                max_workers=2,
                thread_name_prefix="lc-telemetry",
            )
    return _TELEMETRY_EXECUTOR


def should_send_telemetry(config: EvaluatorConfig) -> bool:
    """Return True when telemetry is configured with a non-empty partner / client id."""
    partner_id = config.telemetry.telemetry_partner_id
    return bool(partner_id and partner_id.strip())


def _is_uuid(value: str | None) -> bool:
    if value is None:
        return False
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


async def send_telemetry(
    evaluation_metadata: EvaluationMetadata,
    inp: EvaluationInput | None,
    config: EvaluatorConfig,
) -> None:
    """POST a TypeScript-shaped telemetry JSON payload. Never raises to callers (logs failures)."""
    if not should_send_telemetry(config):
        return

    try:
        partner_id = config.telemetry.telemetry_partner_id
        assert (
            partner_id is not None
        )  # for mypy: ``should_send_telemetry`` guarantees non-empty after strip.
        telemetry_partner_id = partner_id.strip()

        event = evaluation_to_typescript_telemetry_event(evaluation_metadata, inp, config)
        # TS SDK sets timestamp at send time (`new Date().toISOString()`), not evaluation start.
        event = event.model_copy(update={"timestamp": iso_utc_z(datetime.now(timezone.utc))})
        payload = event.model_dump(mode="json", exclude_none=True)

        api_key = telemetry_partner_id if not _is_uuid(telemetry_partner_id) else None
        client_id = (
            telemetry_partner_id
            if _is_uuid(telemetry_partner_id)
            else client_id_from_seed(telemetry_partner_id, config.client_id_seed)
        )

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Client-ID": client_id,
        }
        if api_key is not None:
            headers["X-API-Key"] = api_key

        timeout = httpx.Timeout(5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(config.telemetry.endpoint, json=payload, headers=headers)
            if response.is_error:
                # Log status only; response bodies may echo input text or other sensitive data.
                config.logger.warning(
                    "telemetry send failed: HTTP %s",
                    response.status_code,
                )
    except Exception as e:
        # Log exception type only; ``str(e)`` may include payload fields (e.g. input_text).
        config.logger.warning(
            "telemetry send failed: %s",
            type(e).__qualname__,
        )


def schedule_send_telemetry(
    evaluation_metadata: EvaluationMetadata,
    inp: EvaluationInput | None,
    config: EvaluatorConfig,
) -> None:
    """Fire-and-forget: run :func:`send_telemetry` on a shared worker when telemetry is enabled."""
    if not should_send_telemetry(config):
        return

    def _run() -> None:
        asyncio.run(send_telemetry(evaluation_metadata, inp, config))

    _get_telemetry_executor().submit(_run)
