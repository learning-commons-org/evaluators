"""The error mapping check (SDK spec §6.5): every signal row maps to the expected class.

The cases are the TypeScript SDK's ``wrap-provider-error.test.ts`` re-expressed over the
signals Python surfaces — the native SDKs' status errors, ``httpx`` transport errors,
pydantic validation errors, and standard-library exceptions — so both SDKs classify
identically.
"""

from __future__ import annotations

import asyncio
import errno
import json
import socket
import ssl
from typing import Any

import anthropic
import httpx
import httpx2
import openai
import pytest
from google.genai import errors as genai_errors
from pydantic import BaseModel, ValidationError

from learning_commons_evaluators.errors import (
    AuthenticationError,
    ConfigurationError,
    DependencyError,
    EvaluatorError,
    InputValidationError,
    LLMOutputProcessingError,
    LLMProviderError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
    wrap_provider_error,
)

CONTEXT: dict[str, Any] = {"dependency": "openai", "model": "gpt-4o-2024-11-20"}

# google-genai transports over httpx 0.x; openai and anthropic over httpx 2, which is
# published as the separate ``httpx2`` package. Each SDK's errors are built with its own.
_REQUEST = httpx.Request("POST", "https://api.example.com/v1/responses")
_REQUEST2 = httpx2.Request("POST", "https://api.example.com/v1/responses")


def _response(
    status: int, headers: dict[str, str] | None = None, body: Any = None, text: str | None = None
) -> httpx2.Response:
    if text is not None:
        return httpx2.Response(status, headers=headers or {}, text=text, request=_REQUEST2)
    return httpx2.Response(
        status, headers=headers or {}, json=body if body is not None else {}, request=_REQUEST2
    )


def openai_error(
    status: int,
    message: str = "boom",
    headers: dict[str, str] | None = None,
    body: Any = None,
) -> openai.APIStatusError:
    """What the openai SDK raises for a non-2xx: status, headers and decoded body attached."""
    return openai.APIStatusError(message, response=_response(status, headers, body), body=body)


def anthropic_error(status: int, message: str = "boom") -> anthropic.APIStatusError:
    return anthropic.APIStatusError(message, response=_response(status), body=None)


def google_error(status: int, message: str = "boom") -> genai_errors.APIError:
    body = {"error": {"code": status, "message": message, "status": "SOME_STATUS"}}
    cls = genai_errors.ClientError if status < 500 else genai_errors.ServerError
    return cls(status, body, httpx.Response(status, json=body, request=_REQUEST))


class _Payload(BaseModel):
    score: int


def pydantic_failure() -> ValidationError:
    try:
        _Payload.model_validate({"score": "not a number"})
    except ValidationError as e:
        return e
    raise AssertionError("expected a ValidationError")


def json_failure() -> json.JSONDecodeError:
    try:
        json.loads('{"a":')
    except json.JSONDecodeError as e:
        return e
    raise AssertionError("expected a JSONDecodeError")


def chained(outer: BaseException, cause: BaseException) -> BaseException:
    """``raise outer from cause``, as an object."""
    outer.__cause__ = cause
    return outer


class TestStatusCodeClassification:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (404, ConfigurationError),
            (401, AuthenticationError),
            (403, AuthenticationError),
            (429, RateLimitError),
            (408, RequestTimeoutError),
            (500, LLMProviderError),
            (503, LLMProviderError),
            (400, LLMProviderError),
        ],
    )
    def test_maps_openai_status(self, status: int, expected: type) -> None:
        assert isinstance(wrap_provider_error(openai_error(status), **CONTEXT), expected)

    @pytest.mark.parametrize(
        ("status", "expected"),
        [(401, AuthenticationError), (404, ConfigurationError), (529, LLMProviderError)],
    )
    def test_maps_anthropic_status(self, status: int, expected: type) -> None:
        wrapped = wrap_provider_error(anthropic_error(status), dependency="anthropic")
        assert isinstance(wrapped, expected)
        if status == 529:
            # Anthropic's "overloaded" is a 5xx, so the catch-all retries it.
            assert wrapped.retryable is True

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (404, ConfigurationError),
            (403, AuthenticationError),
            (429, RateLimitError),
            (503, LLMProviderError),
        ],
    )
    def test_maps_google_status_from_code(self, status: int, expected: type) -> None:
        # google-genai's APIError carries the HTTP status as ``code`` and a string ``status``
        # like "NOT_FOUND", which must never be read as a code.
        wrapped = wrap_provider_error(google_error(status), dependency="google")
        assert isinstance(wrapped, expected)
        if isinstance(wrapped, DependencyError):
            assert wrapped.status_code == status

    def test_reads_status_from_an_httpx_status_error(self) -> None:
        response = httpx.Response(401, request=_REQUEST)
        err = httpx.HTTPStatusError("nope", request=_REQUEST, response=response)
        assert isinstance(wrap_provider_error(err, **CONTEXT), AuthenticationError)

    def test_reads_status_code_from_a_plain_attribute(self) -> None:
        err = Exception("nope")
        err.status_code = 401  # type: ignore[attr-defined]
        assert isinstance(wrap_provider_error(err, **CONTEXT), AuthenticationError)

    def test_reads_status_from_the_status_alias(self) -> None:
        err = Exception("nope")
        err.status = 429  # type: ignore[attr-defined]
        assert isinstance(wrap_provider_error(err, **CONTEXT), RateLimitError)

    def test_finds_a_loose_status_nested_in_the_cause_chain(self) -> None:
        # The shape a bring-your-own provider produces: it wraps its vendor SDK's error
        # rather than re-raising it, so the status is one link down.
        vendor = Exception("429 Too Many Requests")
        vendor.status = 429  # type: ignore[attr-defined]
        wrapped = wrap_provider_error(chained(Exception("gateway call failed"), vendor), **CONTEXT)
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.retryable is True

    def test_follows_implicit_context_when_no_explicit_cause(self) -> None:
        # ``raise Wrapper()`` inside an ``except`` links via __context__; Python's own
        # traceback shows that chain, so classification follows it too.
        try:
            try:
                raise openai_error(429)
            except openai.APIStatusError:
                raise RuntimeError("wrapped without from")  # noqa: B904
        except RuntimeError as e:
            assert isinstance(wrap_provider_error(e, **CONTEXT), RateLimitError)

    def test_prefers_the_outermost_status_over_a_deeper_one(self) -> None:
        inner = Exception("inner")
        inner.status = 500  # type: ignore[attr-defined]
        outer = Exception("outer")
        outer.status_code = 401  # type: ignore[attr-defined]
        assert isinstance(
            wrap_provider_error(chained(outer, inner), **CONTEXT), AuthenticationError
        )

    def test_ignores_a_non_numeric_status(self) -> None:
        err = Exception("nope")
        err.status = "429"  # type: ignore[attr-defined]
        wrapped = wrap_provider_error(err, **CONTEXT)
        assert isinstance(wrapped, LLMProviderError)
        assert wrapped.status_code is None

    def test_ignores_a_boolean_status(self) -> None:
        err = Exception("nope")
        err.status_code = True  # type: ignore[attr-defined]
        assert wrap_provider_error(err, **CONTEXT).status_code is None  # type: ignore[attr-defined]

    def test_falls_back_to_the_catch_all_without_a_status(self) -> None:
        wrapped = wrap_provider_error(Exception("something opaque"), **CONTEXT)
        assert isinstance(wrapped, LLMProviderError)
        assert wrapped.status_code is None
        assert wrapped.retryable is False

    def test_substitutes_a_default_message_only_when_the_provider_gave_none(self) -> None:
        assert str(wrap_provider_error(Exception(""), **CONTEXT)) == "API request failed"
        assert (
            str(wrap_provider_error(Exception("upstream detail"), **CONTEXT)) == "upstream detail"
        )

    def test_returns_an_evaluator_error_unchanged(self) -> None:
        original = InputValidationError("text is required.")
        assert wrap_provider_error(original, **CONTEXT) is original


class TestMessageTextNeverReclassifies:
    def test_does_not_promote_a_400_with_model_not_found_prose(self) -> None:
        err = openai_error(400, "model 'gpt-fake-99' does not exist or you do not have access")
        wrapped = wrap_provider_error(err, **CONTEXT)
        assert isinstance(wrapped, LLMProviderError)

    @pytest.mark.parametrize(
        "message",
        [
            "ECONNREFUSED connecting to api.example.com",
            "[Errno 111] Connection refused",
            "Could not resolve host: api.example.com",
            "the request timed out after 30s",
            "503 Service Unavailable",
        ],
    )
    def test_does_not_classify_by_prose(self, message: str) -> None:
        wrapped = wrap_provider_error(Exception(message), **CONTEXT)
        assert isinstance(wrapped, LLMProviderError)
        assert wrapped.status_code is None
        assert not isinstance(wrapped, (NetworkError, RequestTimeoutError))


class TestDiagnosticAttribution:
    def test_attaches_dependency_status_model_and_cause(self) -> None:
        original = openai_error(500, "upstream exploded")
        wrapped = wrap_provider_error(original, **CONTEXT)
        assert isinstance(wrapped, DependencyError)
        assert wrapped.dependency == "openai"
        assert wrapped.status_code == 500
        assert wrapped.model == "gpt-4o-2024-11-20"
        assert wrapped.__cause__ is original

    def test_carries_the_upstream_message(self) -> None:
        wrapped = wrap_provider_error(openai_error(401, "key revoked on 2026-01-01"), **CONTEXT)
        assert str(wrapped) == "key revoked on 2026-01-01"

    def test_defaults_model_and_request_id_to_none(self) -> None:
        wrapped = wrap_provider_error(Exception("x"), dependency="google")
        assert isinstance(wrapped, DependencyError)
        assert wrapped.model is None
        assert wrapped.request_id is None

    def test_configuration_error_path_keeps_cause_and_detail(self) -> None:
        original = openai_error(404, "no such model")
        wrapped = wrap_provider_error(original, **CONTEXT)
        assert wrapped.__cause__ is original
        assert "no such model" in str(wrapped)
        assert "Check the model ID" in str(wrapped)

    def test_raise_from_keeps_the_same_cause(self) -> None:
        original = openai_error(500)
        try:
            try:
                raise original
            except Exception as e:
                raise wrap_provider_error(e, **CONTEXT) from e
        except LLMProviderError as wrapped:
            assert wrapped.__cause__ is original


class TestRetryabilityEndToEnd:
    def test_keeps_a_5xx_retryable(self) -> None:
        assert wrap_provider_error(openai_error(503), **CONTEXT).retryable is True

    def test_keeps_a_429_retryable(self) -> None:
        assert wrap_provider_error(openai_error(429), **CONTEXT).retryable is True

    def test_keeps_a_400_non_retryable(self) -> None:
        assert wrap_provider_error(openai_error(400), **CONTEXT).retryable is False

    def test_keeps_auth_failures_non_retryable(self) -> None:
        assert wrap_provider_error(openai_error(401), **CONTEXT).retryable is False


class TestTransportFailures:
    @pytest.mark.parametrize(
        "error",
        [
            httpx.ConnectError("refused", request=_REQUEST),
            httpx.ReadError("reset", request=_REQUEST),
            httpx.ProxyError("proxy", request=_REQUEST),
            httpx2.ConnectError("refused", request=_REQUEST2),
            httpx2.ProxyError("proxy", request=_REQUEST2),
            ConnectionRefusedError("refused"),
            ConnectionResetError("reset"),
            BrokenPipeError("pipe"),
            socket.gaierror(8, "nodename nor servname provided"),
            ssl.SSLError("tls handshake failed"),
            OSError(errno.EHOSTUNREACH, "host unreachable"),
            OSError(errno.ENETUNREACH, "network unreachable"),
            openai.APIConnectionError(request=_REQUEST2),
            anthropic.APIConnectionError(request=_REQUEST2),
        ],
    )
    def test_typed_connection_failures_are_retryable_network_errors(
        self, error: BaseException
    ) -> None:
        wrapped = wrap_provider_error(error, **CONTEXT)
        assert isinstance(wrapped, NetworkError)
        assert wrapped.retryable is True

    @pytest.mark.parametrize(
        "error",
        [
            httpx.ReadTimeout("slow", request=_REQUEST),
            httpx.ConnectTimeout("slow", request=_REQUEST),
            httpx.PoolTimeout("slow", request=_REQUEST),
            httpx2.ReadTimeout("slow", request=_REQUEST2),
            TimeoutError("timed out"),
            asyncio.TimeoutError(),
            OSError(errno.ETIMEDOUT, "timed out"),
            openai.APITimeoutError(request=_REQUEST2),
            anthropic.APITimeoutError(request=_REQUEST2),
        ],
    )
    def test_typed_timeouts_are_retryable_timeout_errors(self, error: BaseException) -> None:
        wrapped = wrap_provider_error(error, **CONTEXT)
        assert isinstance(wrapped, RequestTimeoutError)
        assert wrapped.retryable is True

    def test_maps_a_408_to_a_timeout(self) -> None:
        assert isinstance(wrap_provider_error(openai_error(408), **CONTEXT), RequestTimeoutError)

    def test_finds_a_transport_failure_nested_in_the_cause_chain(self) -> None:
        nested = chained(Exception("fetch failed"), httpx.ConnectError("inner", request=_REQUEST))
        assert isinstance(wrap_provider_error(nested, **CONTEXT), NetworkError)

    @pytest.mark.parametrize("code", [errno.EACCES, errno.ENOENT])
    def test_an_unrelated_errno_falls_to_the_catch_all(self, code: int) -> None:
        wrapped = wrap_provider_error(OSError(code, "nope"), **CONTEXT)
        assert isinstance(wrapped, LLMProviderError)

    def test_an_httpx_protocol_error_is_not_guessed_at(self) -> None:
        # Not connection-level in the typed sense; it stays in the catch-all rather than
        # being promoted on a hunch.
        err = httpx.RemoteProtocolError("peer closed connection", request=_REQUEST)
        assert isinstance(wrap_provider_error(err, **CONTEXT), LLMProviderError)


class TestOutputProcessingFailures:
    def test_maps_a_pydantic_validation_failure(self) -> None:
        wrapped = wrap_provider_error(pydantic_failure(), **CONTEXT)
        assert isinstance(wrapped, LLMOutputProcessingError)
        assert not isinstance(wrapped, DependencyError)
        # Sampling variance, so it resamples immediately rather than backing off.
        assert wrapped.retryable is True

    def test_carries_sanitized_validation_errors(self) -> None:
        wrapped = wrap_provider_error(pydantic_failure(), **CONTEXT)
        assert isinstance(wrapped, LLMOutputProcessingError)
        assert wrapped.validation_errors is not None
        assert wrapped.validation_errors[0]["loc"] == ("score",)
        assert "type" in wrapped.validation_errors[0]
        for entry in wrapped.validation_errors:
            assert "input" not in entry
            assert "msg" not in entry

    def test_maps_unparseable_json(self) -> None:
        wrapped = wrap_provider_error(json_failure(), **CONTEXT)
        assert isinstance(wrapped, LLMOutputProcessingError)
        assert wrapped.validation_errors is None

    def test_yields_to_an_http_error_status(self) -> None:
        # A 5xx whose body is an HTML error page surfaces as a parse failure nested under
        # the status error. That is the service failing, not the model, and resampling it
        # immediately would hammer a server that is already down.
        wrapped = wrap_provider_error(
            chained(openai_error(500, "server"), json_failure()), **CONTEXT
        )
        assert isinstance(wrapped, LLMProviderError)
        assert wrapped.retryable is True

    def test_still_claims_a_parse_failure_on_a_successful_response(self) -> None:
        wrapped = wrap_provider_error(chained(openai_error(200, "ok"), json_failure()), **CONTEXT)
        assert isinstance(wrapped, LLMOutputProcessingError)

    @pytest.mark.parametrize(("status", "is_parse_failure"), [(400, False), (399, True)])
    def test_400_is_the_first_failing_status(self, status: int, is_parse_failure: bool) -> None:
        wrapped = wrap_provider_error(chained(openai_error(status), json_failure()), **CONTEXT)
        assert isinstance(wrapped, LLMOutputProcessingError) is is_parse_failure


class TestUpstreamVerdictWidensOnly:
    def _with_verdict(self, status: int, retry: bool) -> openai.APIStatusError:
        return openai_error(status, headers={"x-should-retry": "true" if retry else "false"})

    def test_honours_an_upstream_true_on_a_status_we_would_not_retry(self) -> None:
        # 409 Conflict: the vendor SDKs retry it, "iff 5xx" alone would not.
        assert wrap_provider_error(self._with_verdict(409, True), **CONTEXT).retryable is True

    def test_keeps_the_5xx_floor_when_upstream_says_otherwise(self) -> None:
        assert wrap_provider_error(self._with_verdict(500, False), **CONTEXT).retryable is True

    def test_never_makes_an_auth_failure_retryable(self) -> None:
        wrapped = wrap_provider_error(self._with_verdict(403, True), **CONTEXT)
        assert isinstance(wrapped, AuthenticationError)
        assert wrapped.retryable is False

    def test_never_stops_a_rate_limit_from_retrying(self) -> None:
        wrapped = wrap_provider_error(self._with_verdict(429, False), **CONTEXT)
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.retryable is True


class TestStructuredDiagnostics:
    def _rate_limited(self, headers: dict[str, str]) -> RateLimitError:
        wrapped = wrap_provider_error(openai_error(429, headers=headers), **CONTEXT)
        assert isinstance(wrapped, RateLimitError)
        return wrapped

    def test_reads_retry_after_seconds_as_ms(self) -> None:
        assert self._rate_limited({"retry-after": "3"}).retry_after_ms == 3000

    def test_reads_retry_after_ms(self) -> None:
        assert self._rate_limited({"retry-after-ms": "1500"}).retry_after_ms == 1500

    def test_leaves_retry_after_none_without_a_hint(self) -> None:
        assert self._rate_limited({}).retry_after_ms is None

    def test_ignores_an_http_date(self) -> None:
        assert (
            self._rate_limited({"retry-after": "Wed, 21 Oct 2026 07:28:00 GMT"}).retry_after_ms
            is None
        )

    def test_prefers_seconds_over_ms_when_both_present(self) -> None:
        assert (
            self._rate_limited({"retry-after": "2", "retry-after-ms": "9999"}).retry_after_ms
            == 2000
        )

    def test_rounds_fractional_seconds(self) -> None:
        assert self._rate_limited({"retry-after": "0.25"}).retry_after_ms == 250

    @pytest.mark.parametrize("value", ["0", "", "-5", "soon"])
    def test_rejects_an_unusable_delay(self, value: str) -> None:
        assert self._rate_limited({"retry-after": value}).retry_after_ms is None

    def test_falls_through_to_ms_when_seconds_are_unusable(self) -> None:
        assert (
            self._rate_limited({"retry-after": "0", "retry-after-ms": "1500"}).retry_after_ms
            == 1500
        )

    def test_caps_an_implausible_delay_at_one_hour(self) -> None:
        assert self._rate_limited({"retry-after": "99999"}).retry_after_ms == 3_600_000

    @pytest.mark.parametrize(
        ("header", "value"),
        [("x-request-id", "req_x"), ("request-id", "req_plain"), ("x-amzn-requestid", "req_amzn")],
    )
    def test_reads_request_id_headers(self, header: str, value: str) -> None:
        wrapped = wrap_provider_error(openai_error(500, headers={header: value}), **CONTEXT)
        assert isinstance(wrapped, DependencyError)
        assert wrapped.request_id == value

    def test_prefers_x_request_id_over_the_fallbacks(self) -> None:
        wrapped = wrap_provider_error(
            openai_error(500, headers={"x-amzn-requestid": "req_amzn", "x-request-id": "req_x"}),
            **CONTEXT,
        )
        assert isinstance(wrapped, DependencyError)
        assert wrapped.request_id == "req_x"

    def test_request_id_is_none_without_a_known_header(self) -> None:
        wrapped = wrap_provider_error(openai_error(500, headers={"x-other": "nope"}), **CONTEXT)
        assert isinstance(wrapped, DependencyError)
        assert wrapped.request_id is None

    def test_reads_request_id_off_the_exception_when_there_are_no_headers(self) -> None:
        err = Exception("x")
        err.status_code = 500  # type: ignore[attr-defined]
        err.request_id = "req_attr"  # type: ignore[attr-defined]
        wrapped = wrap_provider_error(err, **CONTEXT)
        assert isinstance(wrapped, DependencyError)
        assert wrapped.request_id == "req_attr"

    def test_anthropic_request_id_comes_through(self) -> None:
        response = _response(500, headers={"request-id": "req_anth"})
        err = anthropic.APIStatusError("boom", response=response, body=None)
        wrapped = wrap_provider_error(err, dependency="anthropic")
        assert isinstance(wrapped, DependencyError)
        assert wrapped.request_id == "req_anth"


class TestRejectedModelIsTheCallersConfiguration:
    # Verbatim from a live OpenAI 400 for a model id that does not exist.
    OPENAI_BODY = {
        "error": {
            "message": "The requested model 'gpt-this-model-does-not-exist-9999' does not exist.",
            "type": "invalid_request_error",
            "param": "model",
            "code": "model_not_found",
        }
    }

    def test_classifies_a_400_model_not_found_from_the_decoded_body(self) -> None:
        wrapped = wrap_provider_error(openai_error(400, body=self.OPENAI_BODY), **CONTEXT)
        assert isinstance(wrapped, ConfigurationError)
        assert "Check the model ID" in str(wrapped)

    def test_classifies_it_from_the_response_json_when_the_body_is_missing(self) -> None:
        err = openai.APIStatusError(
            "bad model", response=_response(400, body=self.OPENAI_BODY), body=None
        )
        assert isinstance(wrap_provider_error(err, **CONTEXT), ConfigurationError)

    def test_still_classifies_a_404_as_google_and_anthropic_send(self) -> None:
        assert isinstance(
            wrap_provider_error(google_error(404), dependency="google"), ConfigurationError
        )

    def test_leaves_an_unrelated_400_as_a_provider_fault(self) -> None:
        body = {
            "error": {"message": "Invalid value", "param": "temperature", "code": "invalid_value"}
        }
        wrapped = wrap_provider_error(openai_error(400, body=body), **CONTEXT)
        assert isinstance(wrapped, LLMProviderError)

    def test_leaves_a_400_with_no_verdict_alone(self) -> None:
        assert isinstance(
            wrap_provider_error(openai_error(400, "Bad Request"), **CONTEXT), LLMProviderError
        )

    def test_classifies_on_the_code_alone(self) -> None:
        body = {"error": {"message": "no such model", "code": "model_not_found"}}
        assert isinstance(
            wrap_provider_error(openai_error(400, body=body), **CONTEXT), ConfigurationError
        )

    def test_classifies_on_the_param_alone(self) -> None:
        body = {"error": {"message": "invalid model id", "param": "model", "code": "invalid_value"}}
        assert isinstance(
            wrap_provider_error(openai_error(400, body=body), **CONTEXT), ConfigurationError
        )

    def test_ignores_a_non_string_param(self) -> None:
        body = {"error": {"message": "bad request", "param": 0}}
        assert not isinstance(
            wrap_provider_error(openai_error(400, body=body), **CONTEXT), ConfigurationError
        )

    def test_finds_the_verdict_further_down_the_cause_chain(self) -> None:
        wrapper = chained(
            Exception("Failed to generate object"), openai_error(400, body=self.OPENAI_BODY)
        )
        assert isinstance(wrap_provider_error(wrapper, **CONTEXT), ConfigurationError)

    def test_survives_a_body_that_is_not_json(self) -> None:
        response = _response(400, text="<html>502 Bad Gateway</html>")
        err = openai.APIStatusError("bad gateway", response=response, body=None)
        assert isinstance(wrap_provider_error(err, **CONTEXT), LLMProviderError)

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (401, AuthenticationError),
            (403, AuthenticationError),
            (429, RateLimitError),
            (408, RequestTimeoutError),
            (500, LLMProviderError),
        ],
    )
    def test_a_status_with_a_definite_policy_keeps_it(self, status: int, expected: type) -> None:
        wrapped = wrap_provider_error(openai_error(status, body=self.OPENAI_BODY), **CONTEXT)
        assert isinstance(wrapped, expected)
        assert not isinstance(wrapped, ConfigurationError)


class TestHostileInputs:
    def test_terminates_on_a_self_referencing_cause_chain(self) -> None:
        loop = Exception("round and round")
        loop.__cause__ = loop
        assert isinstance(wrap_provider_error(loop, **CONTEXT), LLMProviderError)

    def test_survives_headers_that_are_not_a_mapping(self) -> None:
        class _Response:
            status_code = 429
            headers = object()

        err = Exception("rate limited")
        err.response = _Response()  # type: ignore[attr-defined]
        wrapped = wrap_provider_error(err, **CONTEXT)
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.retry_after_ms is None

    def test_result_is_always_an_evaluator_error(self) -> None:
        assert isinstance(wrap_provider_error(Exception(), **CONTEXT), EvaluatorError)
