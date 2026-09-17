"""The client's contract is almost entirely negative.

It must never throw into an evaluation, never make one wait, and never fill a partner's logs
with failures that are expected. What it does on the happy path — the endpoint, the headers,
the bytes — is the collector's interface, shared with the TypeScript SDK, so it is asserted
exactly rather than loosely.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

import httpx
import pytest

from learning_commons_evaluators.logger import get_logger
from learning_commons_evaluators.telemetry import client as telemetry_client
from learning_commons_evaluators.telemetry.client import (
    TIMEOUT_SECONDS,
    TelemetryClient,
    TelemetryClientConfig,
    _Delivery,
    _http_client,
    _Sender,
)
from learning_commons_evaluators.telemetry.types import (
    EventTokenUsage,
    StageDetail,
    TelemetryEvent,
)
from tests.conftest import EventSink, SinkResponse

#: A complete event, so a field added to the type shows up here rather than going untested.
EVENT = TelemetryEvent(
    timestamp="2026-09-17T00:00:00.000Z",
    sdk_version="learning-commons-evaluators-python-1.0.0",
    evaluator_type="student_facing_text.ela_reading.purpose_clarity",
    status="success",
    latency_ms=1234,
    text_length_chars=512,
    provider="google:gemini-3-flash-preview",
    grade="5",
    token_usage=EventTokenUsage(input_tokens=250, output_tokens=120),
    stage_details=(
        StageDetail(
            stage="evaluate_purpose_clarity",
            provider="google:gemini-3-flash-preview",
            latency_ms=900,
            token_usage=EventTokenUsage(input_tokens=250, output_tokens=120),
        ),
    ),
)

ENDPOINT = "https://telemetry.example/v1/events"


def make_client(**overrides: Any) -> TelemetryClient:
    config: dict[str, Any] = {
        "endpoint": ENDPOINT,
        "client_id": "client-abc",
        "enabled": True,
        "logger": get_logger("telemetry-test"),
    }
    return TelemetryClient(TelemetryClientConfig(**{**config, **overrides}))


@pytest.fixture(autouse=True)
def _log_everything(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="learning_commons_evaluators")


class TestWhatReachesTheCollector:
    def test_posts_the_event_as_json_to_the_configured_endpoint(
        self, event_sink: EventSink, caplog: pytest.LogCaptureFixture
    ) -> None:
        make_client().send(EVENT)

        [request] = event_sink.requests()
        assert request["url"] == ENDPOINT
        # Byte for byte: the collector's schema is the wire format, so a field silently
        # dropped or renamed in transit is the failure this catches.
        assert request["body"] == json.dumps(
            EVENT.payload(), separators=(",", ":"), ensure_ascii=False
        )
        assert json.loads(request["body"]) == EVENT.payload()
        # A successful send is silent; a warning here would fire on every evaluation.
        assert caplog.records == []

    def test_identifies_the_client_and_declares_the_content_type(
        self, event_sink: EventSink
    ) -> None:
        make_client().send(EVENT)

        assert event_sink.requests()[0]["headers"] == {
            "Content-Type": "application/json",
            "X-Client-ID": "client-abc",
        }

    def test_sends_no_api_key_header_when_none_is_configured(self, event_sink: EventSink) -> None:
        # Identified telemetry is opt-in, so an absent key must stay absent rather than
        # becoming an empty header.
        make_client().send(EVENT)

        assert "X-API-Key" not in event_sink.requests()[0]["headers"]

    def test_attaches_the_api_key_when_one_is_configured(self, event_sink: EventSink) -> None:
        make_client(learning_commons_api_key="partner-key").send(EVENT)

        assert event_sink.requests()[0]["headers"]["X-API-Key"] == "partner-key"

    def test_gives_up_rather_than_hanging_on_a_slow_network(
        self, monkeypatch: pytest.MonkeyPatch, event_sink: EventSink
    ) -> None:
        # Without a bound, a stalled collector would keep a process alive.
        timeouts: list[float] = []

        def record(timeout: float) -> EventSink:
            timeouts.append(timeout)
            return event_sink

        monkeypatch.setattr(telemetry_client, "_http_client", record)
        make_client().send(EVENT)
        event_sink.requests()

        assert timeouts == [TIMEOUT_SECONDS]

    def test_the_real_transport_carries_the_request_timeout(self) -> None:
        # The sink stands in for this everywhere else — bound directly here, before the
        # fixture's patch — so the real transport is built once.
        with _http_client(TIMEOUT_SECONDS) as http:
            assert http.timeout.read == TIMEOUT_SECONDS
            assert http.timeout.connect == TIMEOUT_SECONDS

    def test_does_nothing_at_all_when_telemetry_is_disabled(
        self, event_sink: EventSink, caplog: pytest.LogCaptureFixture
    ) -> None:
        make_client(enabled=False).send(EVENT)

        assert event_sink.posts == []
        assert telemetry_client._sender_instance is None
        assert caplog.records == []


class TestNothingReachesTheCaller:
    def test_send_returns_before_the_request_is_made(self, event_sink: EventSink) -> None:
        # The promise the whole module exists for: an evaluation does not wait for telemetry.
        released = threading.Event()
        posting = threading.Event()
        original = event_sink.post

        def block(*args: Any, **kwargs: Any) -> SinkResponse:
            posting.set()
            released.wait(5.0)
            return original(*args, **kwargs)

        event_sink.post = block  # type: ignore[method-assign]
        make_client().send(EVENT)

        assert posting.wait(5.0), "the sender never picked the event up"
        assert event_sink.posts == [], "send waited for the request it queued"
        released.set()
        assert len(event_sink.requests()) == 1

    def test_warns_with_the_status_when_the_collector_rejects_the_event(
        self, event_sink: EventSink, caplog: pytest.LogCaptureFixture
    ) -> None:
        event_sink.response = SinkResponse(status_code=503, reason_phrase="Service Unavailable")

        make_client().send(EVENT)
        event_sink.requests()

        assert "503 Service Unavailable" in caplog.text

    def test_logs_rather_than_raising_when_the_request_fails_outright(
        self, event_sink: EventSink, caplog: pytest.LogCaptureFixture
    ) -> None:
        event_sink.failure = httpx.ConnectError("getaddrinfo ENOTFOUND")

        make_client().send(EVENT)
        event_sink.requests()

        assert "getaddrinfo ENOTFOUND" in caplog.text

    def test_stays_quiet_about_an_expected_timeout(
        self, event_sink: EventSink, caplog: pytest.LogCaptureFixture
    ) -> None:
        # A slow network is not a defect worth a line in a partner's logs on every evaluation.
        event_sink.failure = httpx.ReadTimeout("timed out")

        make_client().send(EVENT)
        event_sink.requests()

        assert [record for record in caplog.records if record.levelno >= logging.WARNING] == []

    def test_an_event_that_cannot_be_prepared_is_logged_rather_than_raised(
        self, event_sink: EventSink, caplog: pytest.LogCaptureFixture
    ) -> None:
        class Unserialisable:
            def payload(self) -> dict[str, Any]:
                raise TypeError("not JSON")

        make_client().send(Unserialisable())  # type: ignore[arg-type]

        assert event_sink.posts == []
        assert "Error preparing event" in caplog.text

    def test_a_transport_that_cannot_be_built_drops_the_queue_rather_than_stalling_a_flush(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        def no_transport(timeout: float) -> Any:
            raise RuntimeError("no sockets here")

        monkeypatch.setattr(telemetry_client, "_http_client", no_transport)
        make_client().send(EVENT)

        # A flush that never returned would hang an interpreter exit.
        telemetry_client.flush(5.0)
        assert "no sockets here" in caplog.text


class TestABacklogIsDroppedNotQueuedForever:
    def test_a_full_queue_drops_the_event(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Telemetry is a sample, not a ledger: a caller evaluating faster than the collector
        # accepts must lose events rather than memory, and must never be made to wait.
        sender = _Sender(capacity=1)
        delivery = _Delivery(ENDPOINT, {}, "{}", get_logger("telemetry-test"))
        # Nothing drains the queue, so the second submit meets a full one.
        monkeypatch.setattr(sender, "_start", lambda: None)

        sender.submit(delivery)
        sender.submit(delivery)

        assert "Dropped an event" in caplog.text
