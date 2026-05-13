"""Custom error types for the Evaluators SDK."""

import re


# TODO: rename name and message, and remove Evaluator prefix where appropriate
class EvaluatorError(Exception):
    """Base error class for all evaluator errors."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.name = "EvaluatorError"


class EvaluatorRetryableError(EvaluatorError):
    """Base for errors that may be retried (possibly with backoff). All other evaluator errors are non-retryable."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message, code)
        self.name = "EvaluatorRetryableError"


class ConfigurationError(EvaluatorError):
    """Configuration error - e.g. missing API keys. Non-retryable."""

    def __init__(self, message: str):
        super().__init__(message, "CONFIGURATION_ERROR")
        self.name = "ConfigurationError"


class ValidationError(EvaluatorError):
    """Validation error - invalid input. Non-retryable."""

    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")
        self.name = "ValidationError"


class APIError(EvaluatorError):
    """Base API error - LLM API calls failed. Use subclasses or set retryable explicitly."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retryable: bool = False,
        code: str | None = None,
    ):
        super().__init__(message, code)
        self.status_code = status_code
        self.retryable = retryable
        self.name = "APIError"


class AuthenticationError(APIError):
    """Invalid or missing API keys (401/403). Non-retryable."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, status_code, False, "AUTHENTICATION_ERROR")
        self.name = "AuthenticationError"


class RateLimitError(APIError, EvaluatorRetryableError):
    """Rate limit exceeded (429). Should be retried with backoff."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message, 429, True, "RATE_LIMIT_ERROR")
        self.retry_after = retry_after  # milliseconds
        self.name = "RateLimitError"


class NetworkError(APIError, EvaluatorRetryableError):
    """Network failure. May be retryable."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message, None, retryable, "NETWORK_ERROR")
        self.name = "NetworkError"


class EvaluatorTimeoutError(APIError, EvaluatorRetryableError):
    """Request timed out. Should be retried with caution."""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, 408, True, "TIMEOUT_ERROR")
        self.name = "EvaluatorTimeoutError"


# TODO: OpenAI & Anthropic may return a status_code in the response.
def _parse_provider_error(error: BaseException) -> tuple[str, int | None, str | None]:
    message = str(error)
    status_code = None
    code = getattr(error, "name", None) or type(error).__name__
    if code == "Error":
        code = None
    match = re.search(r"\b(4\d{2}|5\d{2})\b", message)
    if match:
        status_code = int(match.group(1))
    return message, status_code, code


def wrap_provider_error(
    error: BaseException, default_message: str = "API request failed"
) -> APIError:
    """Wrap a provider error into the appropriate SDK error type."""
    message, status_code, code = _parse_provider_error(error)
    msg = message or default_message

    if status_code in (401, 403):
        return AuthenticationError(
            msg if "API key" in msg or "api key" in msg.lower() else "Invalid API key",
            status_code,
        )
    if status_code == 429:
        retry_match = re.search(r"retry[- ]after[:\s]+(\d+)", msg, re.I)
        retry_after = int(retry_match.group(1)) * 1000 if retry_match else None
        return RateLimitError(
            msg if "rate limit" in msg.lower() else "Rate limit exceeded",
            retry_after,
        )
    # Timeouts before generic "Connection" — many stacks use "Connection timed out"
    if "timeout" in msg.lower() or "timed out" in msg.lower():
        return EvaluatorTimeoutError(msg)
    # TODO: confirm if these apply to Python too. Based on TypeScript SDK implementation.
    if any(
        x in msg
        for x in (
            "ECONNREFUSED",
            "ENOTFOUND",
            "ETIMEDOUT",
            "network",
            "Network",
            "Connection",
        )
    ):
        return NetworkError(msg)
    return APIError(
        msg,
        status_code,
        bool(status_code and status_code >= 500),
        code,
    )
