"""Telemetry: schedule and send evaluation events (fire-and-forget HTTP POST)."""

from __future__ import annotations

import asyncio
import threading
import uuid

import httpx

from learning_commons_evaluators.schemas.config import EvaluatorConfig
from learning_commons_evaluators.schemas.evaluator import EvaluationInput
from learning_commons_evaluators.schemas.metadata import EvaluationMetadata
from learning_commons_evaluators.telemetry.adapter import evaluation_to_typescript_telemetry_event
from learning_commons_evaluators.telemetry.utils import client_id_from_seed

__all__ = [
    "evaluation_to_typescript_telemetry_event",
    "schedule_send_telemetry",
    "send_telemetry",
    "should_send_telemetry",
]


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

    partner_id = config.telemetry.telemetry_partner_id
    assert (
        partner_id is not None
    )  # for mypy: ``should_send_telemetry`` guarantees non-empty after strip.
    telemetry_partner_id = partner_id.strip()

    event = evaluation_to_typescript_telemetry_event(evaluation_metadata, inp, config)
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

    try:
        timeout = httpx.Timeout(5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(config.telemetry.endpoint, json=payload, headers=headers)
            if response.is_error:
                config.logger.warning(
                    "telemetry send failed: %s %s",
                    response.status_code,
                    response.text[:500],
                )
    except httpx.RequestError as e:
        config.logger.warning("telemetry send failed: %s", e)


def schedule_send_telemetry(
    evaluation_metadata: EvaluationMetadata,
    inp: EvaluationInput | None,
    config: EvaluatorConfig,
) -> None:
    """Fire-and-forget: run :func:`send_telemetry` on a daemon thread when telemetry is enabled."""
    if not should_send_telemetry(config):
        return

    def _run() -> None:
        asyncio.run(send_telemetry(evaluation_metadata, inp, config))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
