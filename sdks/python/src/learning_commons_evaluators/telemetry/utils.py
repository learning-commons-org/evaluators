"""Where an event's source information comes from: this SDK's identity and the client id.

Both are process-wide facts rather than per-evaluation ones, so both are computed once and
cached. The client id is shared state on disk: the TypeScript SDK writes the same file, so a
host running both SDKs reports one client rather than two.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from learning_commons_evaluators.version import __version__

#: Which SDK an event came from. The TypeScript SDK sends a bare version in ``sdk_version``,
#: so this prefix is what distinguishes the two in the collector, and it is the identifier
#: the 0.2.0 Python SDK already recorded as ``EvaluatorMetadata.sdk_version``. A separate
#: source field would be a field TypeScript does not send, which would split aggregates;
#: adding one belongs to the migration that takes the telemetry schema out of Draft.
SDK_IDENTIFIER = "learning-commons-evaluators-python"

#: Read from disk at most once per process, as the TypeScript SDK's cache does.
_client_id: str | None = None


def sdk_version() -> str:
    """The event's ``sdk_version``: this SDK's identifier and its version."""
    return f"{SDK_IDENTIFIER}-{__version__}"


def utc_timestamp() -> str:
    """Now, as the event carries it: ``2026-09-17T18:04:05.123Z``.

    Millisecond precision and a ``Z`` suffix, which is what JavaScript's
    ``Date.toISOString`` produces and therefore what the collector already parses.
    """
    now = datetime.now(UTC)
    return f"{now:%Y-%m-%dT%H:%M:%S}.{now.microsecond // 1000:03d}Z"


def utf16_length(text: str) -> int:
    """The length JavaScript's ``String.length`` reports for ``text``.

    Both SDKs' events reach one collector and are summed together, so
    ``text_length_chars`` has to mean the same count in each. JavaScript counts UTF-16 code
    units, where Python's ``len`` counts code points: an emoji is 2 there and 1 here. The
    TypeScript event is the oracle, so this follows it.

    The field's name overstates what either SDK measures — a non-BMP character is one
    character and two code units — but renaming it is a change to the shared wire format,
    and a silent disagreement between the SDKs is worse than an imprecise name.
    """
    return len(text.encode("utf-16-le")) // 2


def config_file() -> Path:
    """The file holding the client id, at the path the TypeScript SDK uses."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home())
    else:
        base = Path.home() / ".config"
    return base / "learning-commons" / "config.json"


def client_id() -> str:
    """The persistent id anonymous events are attributed to.

    Read from the shared config file, generated and saved there on first use. The key is
    ``telemetry.clientId`` — JavaScript's spelling, because the file is the TypeScript
    SDK's too and both SDKs must find the same id.

    A filesystem that cannot be read or written (a read-only container, a serverless
    sandbox) is not a failure: the id is then per-process, and telemetry stays anonymous
    either way.
    """
    # TODO(DSCR-2250): this is an unsynchronized check/read/generate/write, and
    # ``_write_config`` below is not atomic. Two threads racing on first use can cache
    # different ids, and two processes can tear the file — which ``_read_config`` then
    # discards, silently churning the id it exists to persist. Deferred rather than fixed
    # piecemeal: the TypeScript SDK writes the same shared file the same way
    # (``sdks/typescript/src/telemetry/utils.ts``), so the fix belongs in both at once.
    global _client_id
    if _client_id is not None:
        return _client_id

    path = config_file()
    stored = _read_config(path)
    saved = stored.get("telemetry")
    if isinstance(saved, dict) and isinstance(saved.get("clientId"), str) and saved["clientId"]:
        _client_id = saved["clientId"]
        return _client_id

    _client_id = str(uuid.uuid4())
    # Merged into whatever the file already holds rather than replacing it: the file is
    # shared, and a key this SDK does not know about is not ours to drop.
    stored["telemetry"] = {**(saved if isinstance(saved, dict) else {}), "clientId": _client_id}
    _write_config(path, stored)
    return _client_id


def _read_config(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — missing, unreadable, or not JSON: start fresh
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _write_config(path: Path, config: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except Exception:  # noqa: BLE001 — an id we could not save is still a usable id
        return


__all__ = ["SDK_IDENTIFIER", "client_id", "config_file", "sdk_version", "utc_timestamp"]
