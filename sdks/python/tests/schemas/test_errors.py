"""Tests for the error hierarchy and wrap_provider_error().

Each wrap_provider_error test targets a specific branch in the function so
that every routing decision is covered independently.
"""

import pytest

from learning_commons_evaluators.schemas.errors import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    EvaluatorError,
    EvaluatorTimeoutError,
    NetworkError,
    RateLimitError,
    ValidationError,
    wrap_provider_error,
)


class TestErrorHierarchy:
    """Verify that every error type carries the right code, name, and retryable flag."""

    @pytest.mark.parametrize(
        "exc,expected_code,expected_retryable",
        [
            (ValidationError("bad"), "VALIDATION_ERROR", None),
            (ConfigurationError("missing"), "CONFIGURATION_ERROR", None),
            (AuthenticationError("denied", 401), "AUTHENTICATION_ERROR", False),
            (RateLimitError("slow down"), "RATE_LIMIT_ERROR", True),
            (NetworkError("no route"), "NETWORK_ERROR", True),
            (EvaluatorTimeoutError(), "TIMEOUT_ERROR", True),
        ],
    )
    def test_error_code_and_retryable(self, exc, expected_code, expected_retryable):
        assert exc.code == expected_code
        if expected_retryable is not None:
            assert exc.retryable is expected_retryable

    def test_evaluator_error_stores_message(self):
        err = EvaluatorError("something broke", code="ERR")
        assert str(err) == "something broke"
        assert err.message == "something broke"
        assert err.code == "ERR"

    def test_api_error_status_code_and_retryable(self):
        err = APIError("server error", status_code=500, retryable=True)
        assert err.status_code == 500
        assert err.retryable is True

    def test_rate_limit_error_carries_retry_after(self):
        err = RateLimitError("too fast", retry_after=60_000)
        assert err.status_code == 429
        assert err.retry_after == 60_000


class TestWrapProviderError:
    """One test per routing branch in wrap_provider_error()."""

    def test_401_with_api_key_text_returns_authentication_error(self):
        wrapped = wrap_provider_error(Exception("401 Invalid API key"))
        assert isinstance(wrapped, AuthenticationError)
        assert wrapped.status_code == 401

    def test_401_without_api_key_text_uses_fallback_message(self):
        """When the 401 message doesn't mention 'api key', wrap should still use AuthenticationError
        with the generic 'Invalid API key' fallback rather than the raw message."""
        wrapped = wrap_provider_error(Exception("401 Unauthorized"))
        assert isinstance(wrapped, AuthenticationError)
        assert wrapped.status_code == 401
        assert "Invalid API key" in str(wrapped)

    def test_403_returns_authentication_error(self):
        wrapped = wrap_provider_error(Exception("403 Forbidden"))
        assert isinstance(wrapped, AuthenticationError)
        assert wrapped.status_code == 403

    def test_429_returns_rate_limit_error(self):
        wrapped = wrap_provider_error(Exception("429 rate limit exceeded"))
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.status_code == 429

    def test_429_with_retry_after_header_parses_delay(self):
        """Retry-After value in the message should be extracted and converted to ms."""
        wrapped = wrap_provider_error(Exception("429 rate limit exceeded. Retry-After: 5"))
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.retry_after == 5000  # 5 seconds → 5000 ms

    def test_429_without_retry_after_sets_none(self):
        wrapped = wrap_provider_error(Exception("429 rate limit exceeded"))
        assert isinstance(wrapped, RateLimitError)
        assert wrapped.retry_after is None

    @pytest.mark.parametrize(
        "message",
        [
            "ECONNREFUSED 127.0.0.1:443",
            "ENOTFOUND api.example.com",
            "ETIMEDOUT after 30s",
            "Connection failed",
            "Network error",
        ],
    )
    def test_network_keywords_return_network_error(self, message):
        wrapped = wrap_provider_error(Exception(message))
        assert isinstance(wrapped, NetworkError)

    @pytest.mark.parametrize(
        "message",
        [
            "request timed out",
            "Connection timed out after 10 seconds",
        ],
    )
    def test_timeout_phrases_return_timeout_error(self, message):
        wrapped = wrap_provider_error(Exception(message))
        assert isinstance(wrapped, EvaluatorTimeoutError)

    def test_500_returns_retryable_api_error(self):
        wrapped = wrap_provider_error(Exception("500 Internal Server Error"))
        assert isinstance(wrapped, APIError)
        assert wrapped.status_code == 500
        assert wrapped.retryable is True

    def test_unknown_exception_returns_non_retryable_api_error(self):
        wrapped = wrap_provider_error(Exception("something completely unexpected"))
        assert isinstance(wrapped, APIError)
        assert wrapped.status_code is None
        assert wrapped.retryable is False

    def test_empty_message_uses_default_message(self):
        wrapped = wrap_provider_error(Exception(""), default_message="fallback message")
        assert "fallback message" in str(wrapped)
