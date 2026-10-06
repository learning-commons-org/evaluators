"""The fire-and-forget path from an evaluation to the telemetry collector.

Telemetry must never fail an evaluation, delay one, or change its result, so an evaluation
does not send anything: it queues an event and returns. One background daemon thread does
the sending, shared by every evaluator in the process, which is what makes the guarantee
hold for synchronous callers too — an event queued by :meth:`BaseEvaluator.evaluate_sync`
outlives the event loop that ``asyncio.run`` closes underneath it.

Everything that can go wrong is bounded rather than raised: requests time out after
:data:`TIMEOUT_SECONDS`, a full queue drops events instead of blocking, and a failed send
costs at most a warning in the logs. Disabled telemetry reaches none of this — no event is
built, no thread starts, and no HTTP client exists.
"""

from __future__ import annotations

import atexit
import json
import queue
import threading
from dataclasses import dataclass

import httpx

from learning_commons_evaluators.logger import Logger
from learning_commons_evaluators.telemetry.types import TelemetryEvent

#: The collector both SDKs post to.
COLLECTOR_ENDPOINT = "https://api.learningcommons.org/evaluators-telemetry/v1/events"

#: How long one request may take, matching the TypeScript SDK's abort signal.
TIMEOUT_SECONDS = 5.0

#: Events waiting to be sent. A caller evaluating faster than the collector accepts loses
#: events rather than memory; telemetry is a sample, not a ledger.
QUEUE_CAPACITY = 100


@dataclass(frozen=True)
class TelemetryClientConfig:
    """What the client needs to send an event, assembled once per evaluator."""

    endpoint: str
    #: The persistent id anonymous events are attributed to.
    client_id: str
    enabled: bool
    logger: Logger
    #: Present when the caller opted into identified telemetry.
    learning_commons_api_key: str | None = None


@dataclass(frozen=True)
class _Delivery:
    """One prepared request, waiting on the queue."""

    endpoint: str
    headers: dict[str, str]
    body: str
    logger: Logger


def _http_client(timeout: float) -> httpx.Client:
    return httpx.Client(timeout=timeout)


def _post(http: httpx.Client, delivery: _Delivery) -> None:
    """Send one event. Never raises: a collector having a bad day is not the caller's problem."""
    try:
        response = http.post(delivery.endpoint, headers=delivery.headers, content=delivery.body)
    except httpx.TimeoutException:
        # Expected on a slow network, and not worth a line in a partner's logs on every
        # evaluation. The TypeScript client stays quiet about its own aborts for the same reason.
        return
    except Exception as error:  # noqa: BLE001 — anything at all, and the evaluation is long gone
        delivery.logger.warning("[Telemetry] Error sending event: %s", error)
        return
    if not 200 <= response.status_code < 300:
        delivery.logger.warning(
            "[Telemetry] Failed to send event: %s %s",
            response.status_code,
            response.reason_phrase,
        )


class _Sender:
    """The background thread that posts queued deliveries, and nothing else."""

    def __init__(self, *, capacity: int = QUEUE_CAPACITY, timeout: float = TIMEOUT_SECONDS) -> None:
        self._queue: queue.Queue[_Delivery | None] = queue.Queue(maxsize=capacity)
        self._timeout = timeout
        self._thread: threading.Thread | None = None
        self._starting = threading.Lock()
        #: Deliveries queued but not yet finished, so :meth:`flush` knows when it is done.
        self._pending = 0
        self._idle = threading.Condition()

    # --- the evaluation's side ---------------------------------------------------------

    def submit(self, delivery: _Delivery) -> None:
        """Queue one delivery and return. Never blocks, never raises."""
        self._start()
        with self._idle:
            self._pending += 1
        try:
            self._queue.put_nowait(delivery)
        except queue.Full:
            self._finished()
            delivery.logger.debug("[Telemetry] Dropped an event: the send queue is full.")

    def flush(self, timeout: float | None = None) -> None:
        """Wait, at most *timeout* seconds, for the queue to drain."""
        with self._idle:
            self._idle.wait_for(lambda: self._pending == 0, timeout=timeout)

    def close(self, timeout: float | None = None) -> None:
        """Drain, then stop the thread. For the tests; a live process just lets it idle."""
        self.flush(timeout)
        with self._starting:
            thread = self._thread
            self._thread = None
        if thread is not None and thread.is_alive():
            self._queue.put(None)
            thread.join(timeout)

    # --- the sender's side -------------------------------------------------------------

    def _start(self) -> None:
        with self._starting:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._run, name="learning-commons-telemetry", daemon=True
            )
            self._thread.start()

    def _run(self) -> None:
        http: httpx.Client | None = None
        try:
            while True:
                delivery = self._queue.get()
                if delivery is None:
                    return
                try:
                    if http is None:
                        # Built on first use and kept for the thread's life, so every event
                        # after the first reuses the connection.
                        http = _http_client(self._timeout)
                    _post(http, delivery)
                except Exception as error:  # noqa: BLE001 — no transport, so no telemetry
                    # Only the transport can fail here; sending itself never raises. Logged
                    # per event and the thread stays up, so a flush is never left waiting on
                    # a delivery nobody will finish.
                    delivery.logger.warning("[Telemetry] Error sending event: %s", error)
                finally:
                    self._finished()
        finally:
            if http is not None:
                http.close()

    def _finished(self) -> None:
        with self._idle:
            self._pending -= 1
            self._idle.notify_all()


#: Created on the first event, so telemetry that is off costs a process nothing.
_sender_lock = threading.Lock()
_sender_instance: _Sender | None = None


def sender() -> _Sender:
    global _sender_instance
    with _sender_lock:
        if _sender_instance is None:
            _sender_instance = _Sender()
        return _sender_instance


def flush(timeout: float | None = TIMEOUT_SECONDS) -> None:
    """Wait, briefly, for queued events to be sent.

    Returns at once when nothing is queued, which is also the case when telemetry has never
    been used in this process.
    """
    with _sender_lock:
        current = _sender_instance
    if current is not None:
        current.flush(timeout)


# A short-lived script would otherwise exit before its last event left the queue. Costs
# nothing when no event was ever queued, and is bounded by the request timeout, so it
# cannot hang an exit.
atexit.register(flush, TIMEOUT_SECONDS)


@dataclass(frozen=True)
class TelemetryClient:
    """Queues one event per evaluation, on behalf of one evaluator.

    Holding no connection and no state of its own, it is as cheap as the config it wraps;
    the thread and the HTTP client behind it are the process's, not the evaluator's.
    """

    config: TelemetryClientConfig

    def send(self, event: TelemetryEvent) -> None:
        """Queue *event* for delivery. Returns at once, and never raises."""
        if not self.config.enabled:
            return
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Client-ID": self.config.client_id,
            }
            # Identified telemetry is opt-in: an absent key stays absent rather than
            # becoming an empty header.
            if self.config.learning_commons_api_key:
                headers["X-API-Key"] = self.config.learning_commons_api_key
            body = json.dumps(event.payload(), separators=(",", ":"), ensure_ascii=False)
            sender().submit(_Delivery(self.config.endpoint, headers, body, self.config.logger))
        except Exception as error:  # noqa: BLE001 — a telemetry bug must not fail an evaluation
            self.config.logger.warning("[Telemetry] Error preparing event: %s", error)


__all__ = [
    "COLLECTOR_ENDPOINT",
    "QUEUE_CAPACITY",
    "TIMEOUT_SECONDS",
    "TelemetryClient",
    "TelemetryClientConfig",
    "flush",
]
