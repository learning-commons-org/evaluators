"""Telemetry helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def iso_utc_z(dt: datetime) -> str:
    """Format *dt* as an ISO 8601 UTC string with a ``Z`` suffix (TS wire format)."""
    s = dt.astimezone(timezone.utc).isoformat()
    return s.replace("+00:00", "Z")


def client_id_from_seed(learning_commons_api_key: str, client_id_seed: uuid.UUID) -> str:
    """Return a deterministic UUID string for this API key within the given namespace.

    ``client_id_seed`` is used as the RFC 4122 UUIDv5 *namespace*; the stripped API key is
    the *name*. The same :class:`~learning_commons_evaluators.schemas.config.EvaluatorConfig`
    (same seed + same telemetry partner API key) always yields the same ``X-Client-ID``.
    """
    return str(uuid.uuid5(client_id_seed, learning_commons_api_key.strip()))
