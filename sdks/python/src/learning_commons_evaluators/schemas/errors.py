"""Custom error types for the Evaluators SDK.

Design notes for maintainers
----------------------------

This module is a Python-idiomatic port of the TypeScript SDK's error hierarchy:

* The class is the identity. We do *not* maintain ``self.name`` / ``self.code``
  / ``self.message`` string mirrors of the class — those are JS-isms. Callers
  discriminate with ``isinstance``. ``str(err)`` returns the message.

* Retryability is a single, attribute-based signal. ``err.retryable`` is the
  source of truth. There is no parallel ``RetryableError`` marker class to
  inherit from. Subclasses set a class-level default; callers may override per
  instance for the cases where it varies (e.g. a DNS-failed ``NetworkError``).

* Messages on SDK errors are short and controlled. We deliberately do **not**
  echo raw provider error strings into ``str(err)`` because they may contain
  prompt content, user text, or fragments of API keys. The original provider
  exception is preserved via ``raise … from`` (``__cause__``) and structured
  details (``status_code``, ``response_body``, ``request_id``, ``provider``,
  ``model``) are exposed as attributes for callers that want to introspect.

* :func:`wrap_provider_error` prefers structured attributes (``.status_code``,
  ``.response``) from provider SDK exceptions over regex on message strings.
  String parsing is the fallback when nothing structured is available.
"""

from __future__ import annotations

import asyncio
import builtins
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from learning_commons_evaluators.schemas.config import LLMProvider


class EvaluatorError(Exception):
    """Base class for every error raised by this SDK.

    All SDK errors carry a ``retryable`` boolean. The default is ``False``
    (subclasses for transient API failures override it). Callers that wrap an
    evaluator call in retry logic can check ``isinstance(err, EvaluatorError)``
    and then consult ``err.retryable`` rather than learning the full hierarchy.
    """

    #: Whether the error condition is plausibly transient. Subclasses override.
    retryable: bool = False

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ConfigurationError(EvaluatorError):
    """The SDK is misconfigured.

    Examples: missing provider config for the requested LLM provider, an
    unknown model ID, a malformed settings file. These are developer errors
    and are not retryable.
    """

    retryable = False


class InputValidationError(EvaluatorError):
    """Evaluator input failed validation.

    Raised before any LLM call when an :class:`InputField` rejects its value.
    Renamed from ``ValidationError`` to avoid the collision with
    :class:`pydantic.ValidationError`. Not retryable.
    """

    retryable = False


class APIError(EvaluatorError):
    """Base class for failures originating in the LLM provider call.

    Carries structured debug attributes alongside the sanitized message:

    Attributes:
        status_code: HTTP status code from the provider, when one was returned.
        retryable: ``True`` for transient failures (5xx, rate-limit, timeout,
            network). Subclasses set sensible defaults; the constructor accepts
            an override for cases like a non-retryable DNS failure.
        provider: Which configured LLM provider raised the error, when known.
        model: Model ID requested when the error occurred, when known.
        response_body: Decoded response body from the provider, when available.
            May contain echoed prompt text — treat as sensitive in logs.
        request_id: Provider request ID for support escalation.

    The original provider exception is preserved as ``self.__cause__`` when
    callers use ``raise wrap_provider_error(e) from e`` (which is what the SDK
    base evaluator does).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool | None = None,
        provider: LLMProvider | None = None,
        model: str | None = None,
        response_body: Any | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        # Honour subclass class-level default unless caller explicitly overrides.
        if retryable is not None:
            self.retryable = retryable
        self.provider = provider
        self.model = model
        self.response_body = response_body
        self.request_id = request_id


class AuthenticationError(APIError):
    """Provider rejected the request because of credentials (HTTP 401/403).

    Not retryable. The error message is deliberately generic ("Authentication
    failed") rather than the provider's raw message, which may contain a
    fragment of the API key.
    """

    retryable = False

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=status_code, **kwargs)


class RateLimitError(APIError):
    """Provider returned HTTP 429.

    Always retryable; honour ``retry_after`` (seconds) when present.
    """

    retryable = True

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: float | None = None,
        status_code: int | None = 429,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=status_code, **kwargs)
        #: Suggested delay before retry, in **seconds**. ``None`` if the
        #: provider did not return a Retry-After header.
        self.retry_after = retry_after


class NetworkError(APIError):
    """A network-level failure prevented the request from completing.

    Connection refused, DNS resolution failure, broken TLS, etc. Retryable by
    default but pass ``retryable=False`` for cases that won't improve on retry
    (e.g. a permanently bad hostname).
    """

    retryable = True


class RequestTimeoutError(APIError):
    """The request to the provider exceeded the configured timeout.

    Retryable. Renamed from ``EvaluatorTimeoutError`` — the ``Evaluator``
    prefix was a TypeScript-port leftover and the Python builtin
    ``TimeoutError`` makes the unqualified name a poor choice.
    """

    retryable = True

    def __init__(
        self,
        message: str = "Request timed out",
        *,
        status_code: int | None = 408,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, status_code=status_code, **kwargs)


class OutputValidationError(APIError):
    """The LLM response did not satisfy the expected output schema.

    Sits under :class:`APIError` because the failure originated in a provider
    response (not in user-supplied input), but the request itself completed —
    so ``status_code`` is typically ``None``.

    Retryable by default: LLMs are nondeterministic, and a parse failure on
    one call may resolve on the next without changing the prompt. Override
    ``retryable=False`` if your prompt/schema combination is systematically
    incompatible.

    The original :class:`pydantic.ValidationError` is preserved on
    ``__cause__`` when raised via ``raise … from e``. The :attr:`validation_errors`
    attribute exposes the field-level details from Pydantic's ``errors()`` API
    with raw input values stripped — safe for inclusion in logs and telemetry.
    """

    retryable = True

    def __init__(
        self,
        message: str = "Model output failed schema validation",
        *,
        validation_errors: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        #: Per-field validation failures. Each entry has ``loc``, ``type``,
        #: and ``msg`` keys (from :meth:`pydantic.ValidationError.errors`).
        #: Raw input values are deliberately omitted to avoid leaking LLM
        #: output (which may echo user prompts) into telemetry.
        self.validation_errors = validation_errors


def sanitize_pydantic_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip raw input values from a list of :meth:`pydantic.ValidationError.errors` entries.

    Pydantic's per-error dicts include an ``input`` key containing the raw
    value that failed validation. For LLM outputs that value may echo prompt
    content, so we drop it before the error reaches logs or telemetry. The
    remaining keys (``loc``, ``type``, ``msg``, ``ctx`` if present) describe
    the schema and the failure mode but not the offending content.
    """
    return [{key: value for key, value in error.items() if key != "input"} for error in errors]


def format_error_for_metadata(error: BaseException) -> str:
    """Render an exception as a string safe for ``EvaluationMetadata.error_details``.

    SDK errors (:class:`EvaluatorError` subclasses) already carry sanitized
    messages, so include both the class name and the message for debuggability.
    Any other exception is rendered as just its class name — the message may
    contain raw values (e.g. an :class:`AttributeError` echoing a field name
    from user input) and isn't safe to put in telemetry.
    """
    if isinstance(error, EvaluatorError):
        return f"{type(error).__name__}: {error}"
    return f"Unexpected error: {type(error).__name__}"


# --- Provider-error wrapping --------------------------------------------------

# Status codes we consider transient even without a more specific subclass match.
_RETRYABLE_STATUS_MIN = 500

# Exception class-name suffixes used as a soft signal when isinstance checks
# against provider SDKs aren't possible (e.g. those SDKs aren't installed in
# the caller's environment). The provider SDKs follow consistent naming.
_TIMEOUT_NAME_HINTS = ("TimeoutError", "APITimeoutError", "ReadTimeout", "ConnectTimeout")
_NETWORK_NAME_HINTS = ("ConnectionError", "APIConnectionError", "ConnectError", "NetworkError")


def _provider_status_code(error: Exception) -> int | None:
    """Best-effort extraction of an HTTP status code from a provider exception.

    Prefers the structured attribute that openai-python and anthropic-python
    both expose (``.status_code``). Falls back to ``.status`` (used by some
    httpx-based clients) and finally to a regex on the message — narrowed to
    HTTP-shaped 4xx/5xx codes near the start of the message to reduce false
    positives like model names or token counts.
    """
    for attr in ("status_code", "status"):
        value = getattr(error, attr, None)
        if isinstance(value, int):
            return value
    match = re.search(r"\b(4\d{2}|5\d{2})\b", str(error)[:80])
    if match:
        return int(match.group(1))
    return None


def _provider_response_body(error: Exception) -> Any | None:
    """Pull the decoded response body off the provider exception when available."""
    body = getattr(error, "body", None)
    if body is not None:
        return body
    response = getattr(error, "response", None)
    if response is None:
        return None
    # httpx.Response and similar objects: try .json() then fall back to .text.
    json_fn = getattr(response, "json", None)
    if callable(json_fn):
        try:
            return json_fn()
        except Exception:  # noqa: BLE001 — body is best-effort debug data
            pass
    return getattr(response, "text", None)


def _provider_request_id(error: Exception) -> str | None:
    """Pull a request ID off the provider exception when available."""
    request_id = getattr(error, "request_id", None)
    if request_id:
        return str(request_id)
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    try:
        value = headers.get("x-request-id") or headers.get("request-id")
    except Exception:  # noqa: BLE001 — non-mapping headers shouldn't crash wrapping
        return None
    return str(value) if value else None


def _extract_retry_after(error: Exception) -> float | None:
    """Return Retry-After in **seconds** from a provider exception, if present.

    Reads ``response.headers['retry-after']`` when present (per RFC 7231 this
    may be an integer number of seconds or an HTTP-date; only the integer form
    is currently handled, which matches every provider we use). Falls back to
    a ``retry-after: N`` substring in the message.
    """
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is not None:
        try:
            raw = headers.get("retry-after") or headers.get("Retry-After")
        except Exception:  # noqa: BLE001
            raw = None
        if raw is not None:
            try:
                return float(raw)
            except (TypeError, ValueError):
                # HTTP-date form is not currently parsed — providers we
                # integrate with always return seconds.
                pass
    message = str(error)
    match = re.search(r"retry[- ]after[:\s]+(\d+)", message, re.I)
    if match:
        return float(match.group(1))
    return None


def _is_model_not_found(error: Exception, status_code: int | None) -> bool:
    """Detect "model not found" errors from a 404 or model-shaped 400."""
    if status_code == 404:
        return True
    if status_code == 400:
        return bool(re.search(r"\bmodel\b.*(not found|does not exist|invalid)", str(error), re.I))
    return False


def _is_timeout(error: Exception) -> bool:
    """Detect timeout errors by exception class regardless of which SDK raised."""
    if isinstance(error, (asyncio.TimeoutError, builtins.TimeoutError)):
        return True
    name = type(error).__name__
    return any(hint in name for hint in _TIMEOUT_NAME_HINTS)


def _is_network(error: Exception) -> bool:
    """Detect network-level failures by exception class."""
    if isinstance(error, ConnectionError):
        return True
    name = type(error).__name__
    return any(hint in name for hint in _NETWORK_NAME_HINTS)


def wrap_provider_error(
    error: Exception,
    *,
    default_message: str = "API request failed",
    provider: LLMProvider | None = None,
    model: str | None = None,
) -> EvaluatorError:
    """Translate a provider exception into the appropriate SDK error subclass.

    Routing precedence (most specific first):

    1. Asyncio / builtin / SDK timeout exception types → :class:`RequestTimeoutError`
    2. Built-in / SDK connection-error exception types → :class:`NetworkError`
    3. HTTP 404 (and model-shaped 400) → :class:`ConfigurationError` (model not found)
    4. HTTP 401 / 403 → :class:`AuthenticationError`
    5. HTTP 429 → :class:`RateLimitError`
    6. HTTP 5xx → retryable :class:`APIError`
    7. Anything else → non-retryable :class:`APIError`

    SDK error messages are sanitized — we do not interpolate the provider's
    raw message into ``str(err)``. Structured detail is available on the
    exception's attributes (``status_code``, ``response_body``, ``request_id``,
    ``provider``, ``model``) and the original exception is reachable via
    ``__cause__`` when callers use ``raise wrap_provider_error(e) from e``.

    Args:
        error: The provider exception to wrap. Must be a regular ``Exception``
            (callers should not pass ``KeyboardInterrupt``/``SystemExit``).
        default_message: Used only when no more specific message can be
            constructed (e.g. an unidentified, status-less exception).
        provider: The configured LLM provider that raised, when the caller
            knows it. Surfaced as ``err.provider`` to disambiguate multi-
            provider runs.
        model: The model ID that was being invoked, when known. Surfaced as
            ``err.model`` and folded into the message for
            :class:`ConfigurationError` results.

    Returns:
        An :class:`EvaluatorError` subclass. Always a new instance — never the
        original ``error``.
    """
    status_code = _provider_status_code(error)
    response_body = _provider_response_body(error)
    request_id = _provider_request_id(error)
    common: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "response_body": response_body,
        "request_id": request_id,
    }

    if _is_timeout(error):
        return RequestTimeoutError(status_code=status_code, **common)

    if _is_network(error):
        return NetworkError(**common)

    if _is_model_not_found(error, status_code):
        model_suffix = f" (model: {model!r})" if model else ""
        return ConfigurationError(
            f"Model not found or invalid{model_suffix}. "
            "Check the model ID configured for this provider."
        )

    if status_code in (401, 403):
        return AuthenticationError(status_code=status_code, **common)

    if status_code == 429:
        return RateLimitError(retry_after=_extract_retry_after(error), **common)

    if status_code is not None:
        return APIError(
            f"API request failed (HTTP {status_code})",
            status_code=status_code,
            retryable=status_code >= _RETRYABLE_STATUS_MIN,
            **common,
        )

    return APIError(default_message, retryable=False, **common)


__all__ = [
    "APIError",
    "AuthenticationError",
    "ConfigurationError",
    "EvaluatorError",
    "InputValidationError",
    "NetworkError",
    "OutputValidationError",
    "RateLimitError",
    "RequestTimeoutError",
    "format_error_for_metadata",
    "sanitize_pydantic_errors",
    "wrap_provider_error",
]
