"""The resampling half of the retry split: only output failures are retried, immediately."""

from __future__ import annotations

import httpx
import httpx2
import openai
import pytest
from pydantic import BaseModel, ValidationError

from learning_commons_evaluators.errors import (
    AuthenticationError,
    ConfigurationError,
    LLMOutputProcessingError,
    NetworkError,
)
from learning_commons_evaluators.providers import call_with_resampling

_REQUEST = httpx.Request("POST", "https://api.example.com/v1/responses")


class _Payload(BaseModel):
    score: int


def _invalid() -> ValidationError:
    try:
        _Payload.model_validate({"score": "x"})
    except ValidationError as e:
        return e
    raise AssertionError


class _Flaky:
    def __init__(self, failures: list[BaseException], result: str = "ok") -> None:
        self.failures = list(failures)
        self.result = result
        self.calls = 0

    async def __call__(self) -> str:
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return self.result


async def test_resamples_output_processing_failures_up_to_max_retries() -> None:
    call = _Flaky([LLMOutputProcessingError("bad"), LLMOutputProcessingError("bad again")])
    assert await call_with_resampling(call, max_retries=2, dependency="openai") == "ok"
    assert call.calls == 3


async def test_raises_once_the_budget_is_spent() -> None:
    call = _Flaky([LLMOutputProcessingError("1"), LLMOutputProcessingError("2")])
    with pytest.raises(LLMOutputProcessingError, match="2"):
        await call_with_resampling(call, max_retries=1, dependency="openai")
    assert call.calls == 2


async def test_zero_disables_resampling() -> None:
    call = _Flaky([LLMOutputProcessingError("once")])
    with pytest.raises(LLMOutputProcessingError):
        await call_with_resampling(call, max_retries=0, dependency="openai")
    assert call.calls == 1


async def test_classifies_a_raw_schema_failure_and_resamples_it() -> None:
    call = _Flaky([_invalid()])
    assert await call_with_resampling(call, max_retries=1, dependency="google") == "ok"
    assert call.calls == 2


async def test_a_raw_dependency_failure_is_classified_and_raised_at_once() -> None:
    # Backoff for dependency failures belongs to the vendor SDK; by the time one surfaces
    # here its retries are spent, so resampling would only repeat the failure.
    # The openai SDK transports over httpx 2 (the ``httpx2`` package).
    response = httpx2.Response(
        401, request=httpx2.Request("POST", "https://api.example.com/v1/responses")
    )
    raw = openai.APIStatusError("nope", response=response, body=None)
    call = _Flaky([raw, LLMOutputProcessingError("never reached")])
    with pytest.raises(AuthenticationError) as exc_info:
        await call_with_resampling(call, max_retries=3, dependency="openai", model="gpt-4o")
    assert call.calls == 1
    assert exc_info.value.__cause__ is raw
    assert exc_info.value.model == "gpt-4o"


async def test_a_retryable_dependency_failure_is_still_not_resampled() -> None:
    call = _Flaky([httpx.ConnectError("refused", request=_REQUEST)])
    with pytest.raises(NetworkError) as exc_info:
        await call_with_resampling(call, max_retries=3, dependency="anthropic")
    assert exc_info.value.retryable is True
    assert call.calls == 1


async def test_an_evaluator_error_passes_through_as_the_same_object() -> None:
    original = ConfigurationError("bad model")
    call = _Flaky([original])
    with pytest.raises(ConfigurationError) as exc_info:
        await call_with_resampling(call, max_retries=3, dependency="openai")
    assert exc_info.value is original
