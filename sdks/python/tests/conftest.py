"""Telemetry stays in the process while the suite runs.

Evaluators emit telemetry by default, so without this every test that evaluates would post
to the collector. The sink below replaces the sender's HTTP client for every test and is
also what the telemetry tests read: :meth:`EventSink.events` waits for the background sender
to drain and returns what it posted.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest

from learning_commons_evaluators.telemetry import client as telemetry_client


@dataclass
class SinkResponse:
    """What the sink answers with; set ``status_code`` to test the rejection path."""

    status_code: int = 204
    reason_phrase: str = "No Content"


@dataclass
class EventSink:
    """Stands in for the sender's HTTP client, recording every request it is handed."""

    response: SinkResponse = field(default_factory=SinkResponse)
    #: Raised instead of answering, for the failure paths.
    failure: BaseException | None = None
    posts: list[dict[str, Any]] = field(default_factory=list)

    def post(self, url: str, *, headers: dict[str, str], content: str) -> SinkResponse:
        self.posts.append({"url": url, "headers": headers, "body": content})
        if self.failure is not None:
            raise self.failure
        return self.response

    def close(self) -> None:
        return None

    def requests(self, timeout: float = 5.0) -> list[dict[str, Any]]:
        """Every request the sender has made, once it has drained.

        Waiting is this fixture's job rather than the caller's: an evaluation queues its
        event and returns without waiting, which is the behaviour under test everywhere else.
        """
        telemetry_client.flush(timeout)
        return list(self.posts)

    def events(self, timeout: float = 5.0) -> list[dict[str, Any]]:
        """Every event sent so far, as the collector would parse it."""
        return [json.loads(request["body"]) for request in self.requests(timeout)]


@pytest.fixture(autouse=True)
def event_sink(monkeypatch: pytest.MonkeyPatch) -> Iterator[EventSink]:
    """Route this test's telemetry into an in-process sink instead of the network."""
    sink = EventSink()
    monkeypatch.setattr(telemetry_client, "_http_client", lambda timeout: sink)
    # A fresh sender per test, so it picks up the sink above and no event crosses tests.
    monkeypatch.setattr(telemetry_client, "_sender_instance", None)
    yield sink
    running = telemetry_client._sender_instance
    if running is not None:
        running.close(timeout=5.0)
