"""Tests for the error hierarchy and wrap_provider_error().

Covers two surfaces:

1. The hierarchy itself — every subclass advertises the right ``retryable``
   default, message defaults are sanitized, and structured attributes (status
   code, retry-after, response body, request id, provider, model) round-trip.

2. ``wrap_provider_error`` — one test per routing branch, plus tests that the
   function prefers structured attributes (``.status_code``, ``.response``) over
   regex on the message and that raw provider messages do not leak into the
   wrapped error's ``str()``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from learning_commons_evaluators.schemas.config import LLMProvider
from learning_commons_evaluators.schemas.errors import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    EvaluatorError,
    InputValidationError,
    NetworkError,
    OutputValidationError,
    RateLimitError,
    RequestTimeoutError,
    format_error_for_metadata,
    sanitize_pydantic_errors,
    wrap_provider_error,
)

# --- Hierarchy ---------------------------------------------------------------


class TestErrorHierarchy:
    """The class is the identity. Each subclass exposes the right retryable default."""

    @pytest.mark.parametrize(
        "exc,expected_retryable",
        [
            (InputValidationError("bad"), False),
            (ConfigurationError("missing"), False),
            (AuthenticationError(status_code=401), False),
            (RateLimitError(), True),
            (NetworkError(), True),
            (RequestTimeoutError(), True),
            (OutputValidationError(), True),
        ],
    )
    def test_retryable_default(self, exc: EvaluatorError, expected_retryable: bool) -> None:
        assert exc.retryable is expected_retryable

    def test_every_subclass_is_an_evaluator_error(self) -> None:
        for exc in (
            InputValidationError("x"),
            ConfigurationError("x"),
            APIError("x"),
            AuthenticationError(),
            RateLimitError(),
            NetworkError(),
            RequestTimeoutError(),
            OutputValidationError(),
        ):
            assert isinstance(exc, EvaluatorError)

    def test_api_error_subclasses_are_api_errors(self) -> None:
        for exc in (
            AuthenticationError(),
            RateLimitError(),
            NetworkError(),
            RequestTimeoutError(),
            OutputValidationError(),
        ):
            assert isinstance(exc, APIError)

    def test_output_validation_error_carries_validation_errors(self) -> None:
        details = [{"loc": ("vocabulary_complexity",), "type": "missing", "msg": "Field required"}]
        err = OutputValidationError(validation_errors=details)
        assert err.validation_errors == details
        # No input snippets leak into the SDK error's string form.
        assert str(err) == "Model output failed schema validation"

    def test_evaluator_error_str_returns_message(self) -> None:
        err = EvaluatorError("something broke")
        assert str(err) == "something broke"

    def test_api_error_structured_attributes(self) -> None:
        err = APIError(
            "server error",
            status_code=500,
            retryable=True,
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
            response_body={"error": "explode"},
            request_id="req_abc",
        )
        assert err.status_code == 500
        assert err.retryable is True
        assert err.provider is LLMProvider.OPENAI
        assert err.model == "gpt-4o"
        assert err.response_body == {"error": "explode"}
        assert err.request_id == "req_abc"

    def test_rate_limit_error_retry_after_is_seconds(self) -> None:
        """Retry-After is exposed in **seconds** (not milliseconds like the TS SDK)."""
        err = RateLimitError(retry_after=60.0)
        assert err.status_code == 429
        assert err.retry_after == 60.0

    def test_network_error_retryable_overridable(self) -> None:
        """Permanently bad hostnames should be flaggable as non-retryable."""
        err = NetworkError("DNS resolution failed permanently", retryable=False)
        assert err.retryable is False

    def test_authentication_error_default_message_is_generic(self) -> None:
        """Default message must not contain anything from the original provider error."""
        err = AuthenticationError(status_code=401)
        assert str(err) == "Authentication failed"


# --- Helpers for fake provider exceptions ------------------------------------


class _FakeHeaders:
    def __init__(self, headers: dict[str, str]) -> None:
        self._headers = headers

    def get(self, key: str, default: Any = None) -> Any:
        return self._headers.get(key.lower(), self._headers.get(key, default))


class _FakeResponse:
    def __init__(self, headers: dict[str, str] | None = None, body: Any = None) -> None:
        self.headers = _FakeHeaders(headers or {})
        self._body = body

    def json(self) -> Any:
        return self._body


class _FakeProviderError(Exception):
    """Stand-in for openai/anthropic API errors: exposes ``status_code`` / ``response``."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response: _FakeResponse | None = None,
        body: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response
        self.body = body


# --- wrap_provider_error: routing branches ----------------------------------


class TestWrapProviderError:
    """One test per routing branch, plus attribute-vs-regex preferences."""

    def test_status_code_read_from_attribute_not_message(self) -> None:
        """Should prefer the structured .status_code attribute over message regex."""
        err = _FakeProviderError("something opaque", status_code=429)
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.status_code == 429

    def test_404_routes_to_configuration_error_with_model_in_message(self) -> None:
        """Model-not-found is a developer mistake, not an API error."""
        err = _FakeProviderError("not found", status_code=404)
        wrapped = wrap_provider_error(err, provider=LLMProvider.OPENAI, model="gpt-bogus")
        assert isinstance(wrapped, ConfigurationError)
        assert "gpt-bogus" in str(wrapped)

    def test_400_model_message_routes_to_configuration_error(self) -> None:
        err = _FakeProviderError("model 'gpt-bogus' does not exist", status_code=400)
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, ConfigurationError)

    def test_401_routes_to_authentication_error_with_sanitized_message(self) -> None:
        err = _FakeProviderError("401: api key sk-...REDACTED is invalid", status_code=401)
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, AuthenticationError)
        assert wrapped.status_code == 401
        # Original raw message must not leak into the SDK error's string form.
        assert "sk-" not in str(wrapped)
        assert str(wrapped) == "Authentication failed"

    def test_403_routes_to_authentication_error(self) -> None:
        err = _FakeProviderError("forbidden", status_code=403)
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, AuthenticationError)
        assert wrapped.status_code == 403

    def test_429_with_retry_after_header_is_in_seconds(self) -> None:
        """Retry-After header takes precedence over message regex and is in seconds."""
        err = _FakeProviderError(
            "429 rate limit",
            status_code=429,
            response=_FakeResponse(headers={"retry-after": "12"}),
        )
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.retry_after == 12.0

    def test_429_falls_back_to_message_regex_for_retry_after(self) -> None:
        err = _FakeProviderError("429 rate limit. Retry-After: 5", status_code=429)
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.retry_after == 5.0

    def test_429_without_retry_after_sets_none(self) -> None:
        err = _FakeProviderError("429 rate limit", status_code=429)
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.retry_after is None

    def test_builtin_connection_error_routes_to_network_error(self) -> None:
        wrapped = wrap_provider_error(ConnectionError("connection refused"))
        assert isinstance(wrapped, NetworkError)

    def test_provider_named_connection_error_routes_to_network_error(self) -> None:
        """Detect by class name when isinstance against the SDK class isn't possible."""

        class APIConnectionError(Exception):
            pass

        wrapped = wrap_provider_error(APIConnectionError("connect failed"))
        assert isinstance(wrapped, NetworkError)

    def test_builtin_timeout_error_routes_to_timeout(self) -> None:
        wrapped = wrap_provider_error(TimeoutError("timed out"))
        assert isinstance(wrapped, RequestTimeoutError)

    def test_asyncio_timeout_error_routes_to_timeout(self) -> None:
        wrapped = wrap_provider_error(asyncio.TimeoutError())
        assert isinstance(wrapped, RequestTimeoutError)

    def test_provider_named_timeout_error_routes_to_timeout(self) -> None:
        class APITimeoutError(Exception):
            pass

        wrapped = wrap_provider_error(APITimeoutError("timed out"))
        assert isinstance(wrapped, RequestTimeoutError)

    def test_500_returns_retryable_api_error(self) -> None:
        err = _FakeProviderError("internal server error", status_code=500)
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, APIError)
        assert wrapped.status_code == 500
        assert wrapped.retryable is True

    def test_502_returns_retryable_api_error(self) -> None:
        err = _FakeProviderError("bad gateway", status_code=502)
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, APIError)
        assert wrapped.retryable is True

    def test_unknown_exception_returns_non_retryable_api_error(self) -> None:
        wrapped = wrap_provider_error(Exception("something completely unexpected"))
        assert isinstance(wrapped, APIError)
        assert wrapped.status_code is None
        assert wrapped.retryable is False

    def test_default_message_is_used_when_no_signal(self) -> None:
        wrapped = wrap_provider_error(Exception(""), default_message="fallback message")
        assert "fallback message" in str(wrapped)

    def test_provider_and_model_threaded_through(self) -> None:
        err = _FakeProviderError("429", status_code=429)
        wrapped = wrap_provider_error(err, provider=LLMProvider.ANTHROPIC, model="claude-x")
        assert isinstance(wrapped, APIError)
        assert wrapped.provider is LLMProvider.ANTHROPIC
        assert wrapped.model == "claude-x"

    def test_response_body_and_request_id_extracted(self) -> None:
        err = _FakeProviderError(
            "429",
            status_code=429,
            response=_FakeResponse(
                headers={"x-request-id": "req_xyz"},
                body={"error": "rate_limited"},
            ),
        )
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, APIError)
        assert wrapped.request_id == "req_xyz"
        assert wrapped.response_body == {"error": "rate_limited"}

    def test_body_attribute_preferred_over_response_json(self) -> None:
        """When the SDK already has a decoded body attribute, use it directly."""
        err = _FakeProviderError(
            "429",
            status_code=429,
            body={"error": "from_body_attr"},
            response=_FakeResponse(body={"error": "from_response_json"}),
        )
        wrapped = wrap_provider_error(err)
        assert isinstance(wrapped, APIError)
        assert wrapped.response_body == {"error": "from_body_attr"}

    def test_original_exception_preserved_via_cause(self) -> None:
        """`raise wrap_provider_error(e) from e` keeps __cause__ for debugging."""
        original = _FakeProviderError("opaque inner error", status_code=500)
        try:
            try:
                raise original
            except Exception as e:
                raise wrap_provider_error(e) from e
        except APIError as wrapped:
            assert wrapped.__cause__ is original

    def test_message_regex_fallback_when_no_status_code_attr(self) -> None:
        """When the exception has no .status_code, fall back to bounded regex on message."""
        wrapped = wrap_provider_error(Exception("503 Service Unavailable"))
        assert isinstance(wrapped, APIError)
        assert wrapped.status_code == 503
        assert wrapped.retryable is True


# --- sanitize_pydantic_errors ------------------------------------------------


class TestSanitizePydanticErrors:
    def test_strips_input_key_only(self) -> None:
        """Drop the raw ``input`` value but keep loc/type/msg/ctx for debugging."""
        raw = [
            {
                "loc": ("vocabulary_complexity",),
                "type": "missing",
                "msg": "Field required",
                "input": {"label": "only"},  # potentially echoes LLM output
                "ctx": {"some": "context"},
            }
        ]
        sanitized = sanitize_pydantic_errors(raw)
        assert sanitized == [
            {
                "loc": ("vocabulary_complexity",),
                "type": "missing",
                "msg": "Field required",
                "ctx": {"some": "context"},
            }
        ]

    def test_handles_empty_list(self) -> None:
        assert sanitize_pydantic_errors([]) == []


# --- format_error_for_metadata -----------------------------------------------


class TestFormatErrorForMetadata:
    def test_sdk_error_includes_class_name_and_sanitized_message(self) -> None:
        err = RateLimitError()
        assert format_error_for_metadata(err) == "RateLimitError: Rate limit exceeded"

    def test_non_sdk_error_drops_message(self) -> None:
        """Arbitrary exception messages may contain user data — only the class name is recorded."""
        formatted = format_error_for_metadata(ValueError("something sensitive: sk-XYZ"))
        assert "sk-XYZ" not in formatted
        assert "something sensitive" not in formatted
        assert "ValueError" in formatted

    def test_returns_string(self) -> None:
        assert isinstance(format_error_for_metadata(EvaluatorError("x")), str)
        assert isinstance(format_error_for_metadata(Exception("y")), str)
