"""Every adapter builds a vendor client per call and closes it, whatever the call does.

The fakes stand in for the vendor SDK classes the adapters build from, and are bound to
the event loop they first run on, as a real client's connection pool is: used from another
loop, they fail the way the real ones do. A client the caller injects is the caller's, so
it is reused and left open.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from learning_commons_evaluators.providers import Provider, ProviderConfig
from learning_commons_evaluators.providers.anthropic_sdk import AnthropicProvider
from learning_commons_evaluators.providers.google_genai import GoogleProvider
from learning_commons_evaluators.providers.openai_sdk import OpenAIProvider


class _Verdict(BaseModel):
    score: int


MESSAGES = [{"role": "user", "content": "Grade this."}]


class _FakeClient:
    """A vendor client whose one endpoint answers with ``result`` or raises ``error``."""

    result: Any = None
    error: Exception | None = None

    def __init__(self, **_options: Any) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.calls = 0
        self.closed = False

    async def _call(self, **_request: Any) -> Any:
        loop = asyncio.get_running_loop()
        if self.loop is None:
            self.loop = loop
        elif self.loop is not loop:
            raise RuntimeError("Event loop is closed")
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class _FakeOpenAI(_FakeClient):
    result = SimpleNamespace(output_parsed=_Verdict(score=1), output_text="t", usage=None)

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self.responses = SimpleNamespace(parse=self._call, create=self._call)

    async def __aenter__(self) -> _FakeOpenAI:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        self.closed = True


class _FakeAnthropic(_FakeOpenAI):
    result = SimpleNamespace(
        parsed_output=_Verdict(score=1),
        content=[SimpleNamespace(type="text", text="t")],
        usage=None,
        stop_reason="end_turn",
    )

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self.messages = SimpleNamespace(parse=self._call, create=self._call)


class _FakeGoogle(_FakeClient):
    result = SimpleNamespace(
        parsed=_Verdict(score=1), text='{"score": 1}', usage_metadata=None, candidates=[]
    )

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self.async_closed = False

        async def aclose() -> None:
            self.async_closed = True

        self.aio = SimpleNamespace(
            models=SimpleNamespace(generate_content=self._call), aclose=aclose
        )

    def close(self) -> None:
        self.closed = True


@dataclass(frozen=True)
class _Vendor:
    provider: Provider
    adapter: Callable[..., Any]
    module: str
    attribute: str
    fake: type[_FakeClient]
    #: Every client the adapter built, in order; filled by the ``vendor`` fixture.
    built: list[_FakeClient] = field(default_factory=list)

    def all_closed(self, client: _FakeClient) -> bool:
        # A Google client has an async and a sync half, and both must be closed.
        return client.closed and getattr(client, "async_closed", True)


VENDORS = [
    _Vendor(Provider.OPENAI, OpenAIProvider, "openai", "AsyncOpenAI", _FakeOpenAI),
    _Vendor(Provider.ANTHROPIC, AnthropicProvider, "anthropic", "AsyncAnthropic", _FakeAnthropic),
    _Vendor(Provider.GOOGLE, GoogleProvider, "google.genai", "Client", _FakeGoogle),
]


async def _structured(adapter: Any) -> Any:
    return await adapter.generate_structured(MESSAGES, _Verdict)


async def _text(adapter: Any) -> Any:
    return await adapter.generate_text(MESSAGES)


CALLS = [pytest.param(_structured, id="structured"), pytest.param(_text, id="text")]


@pytest.fixture(params=VENDORS, ids=lambda v: v.provider.value)
def vendor(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> _Vendor:
    """Patch the vendor class with a fake that records every instance built."""
    spec: _Vendor = request.param
    built: list[_FakeClient] = []

    def recording(**options: Any) -> _FakeClient:
        client = spec.fake(**options)
        built.append(client)
        return client

    monkeypatch.setattr(f"{spec.module}.{spec.attribute}", recording)
    return replace(spec, built=built)


def _adapter(vendor: _Vendor, client: Any = None) -> Any:
    config = ProviderConfig(type=vendor.provider, model="m", api_key="k")
    return vendor.adapter(config) if client is None else vendor.adapter(config, client=client)


@pytest.mark.parametrize("call", CALLS)
async def test_each_call_builds_its_own_client_and_closes_it(vendor: _Vendor, call: Any) -> None:
    adapter = _adapter(vendor)
    assert vendor.built == []  # nothing is opened until a call needs it
    await call(adapter)
    await call(adapter)
    assert [c.calls for c in vendor.built] == [1, 1]
    assert all(vendor.all_closed(c) for c in vendor.built)


@pytest.mark.parametrize("call", CALLS)
async def test_the_client_is_closed_when_the_call_fails(
    vendor: _Vendor, call: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(vendor.fake, "error", ConnectionError("down"))
    with pytest.raises(Exception, match="down"):
        await call(_adapter(vendor))
    (client,) = vendor.built
    assert vendor.all_closed(client)


@pytest.mark.parametrize("call", CALLS)
def test_calls_on_separate_event_loops_each_succeed(vendor: _Vendor, call: Any) -> None:
    # What ``evaluate_sync`` does: every evaluation runs its own ``asyncio.run``. A client
    # kept from the first loop would fail the second call with "Event loop is closed".
    adapter = _adapter(vendor)
    for _ in range(3):
        asyncio.run(call(adapter))
    assert len(vendor.built) == 3


@pytest.mark.parametrize("call", CALLS)
async def test_an_injected_client_is_reused_and_left_open(vendor: _Vendor, call: Any) -> None:
    injected = vendor.fake()
    adapter = _adapter(vendor, client=injected)
    await call(adapter)
    await call(adapter)
    assert injected.calls == 2
    assert not injected.closed
    assert not getattr(injected, "async_closed", False)
    assert vendor.built == []
