"""Canonical error taxonomy (SDK spec §6), transliterated from the TypeScript SDK's ``errors.ts``.

Errors classify by **fault domain** — who must act — not by mechanism: the caller
(:class:`ConfigurationError`, :class:`InputValidationError`), our own evaluation logic
(:class:`EvaluationError`), or an external system (:class:`DependencyError`).

``retryable`` is data, not hierarchy: callers read the flag rather than memorizing which
classes retry. Strategy follows the category — dependency failures back off, evaluation
failures resample immediately (§6.3).

Python idiom where it does not change the contract: the class is the identity (there is no
``name`` mirror; use ``type(err).__name__``), ``str(err)`` is the message, and the original
exception travels on ``__cause__``. Everything else — class names, fields, retryability
rules, and the classification order in :func:`wrap_provider_error` — is the spec's.
"""

from __future__ import annotations

import asyncio
import contextlib
import errno
import json
import math
import socket
import ssl
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

import httpx
from pydantic import ValidationError as PydanticValidationError
from typing_extensions import Unpack

# Canonical ID of an external system, for ``DependencyError.dependency``.
#
# Closed on purpose: an integration we add must be named here rather than landing in a
# catch-all. ``custom`` is not that catch-all — it means the caller injected their own
# ``llm_provider``, so the vendor is theirs to know, not ours. A ``model_override`` still
# reports its real vendor, since it is one of ours.
#
# Named per service, so ``knowledge-graph`` rather than ``learning-commons``: the one
# Learning Commons key authorizes several services, and a failure needs to name the one
# that failed. Further Learning Commons services get their own IDs.
DependencyId = Literal["openai", "google", "anthropic", "knowledge-graph", "custom"]

# The subset of ``DependencyId`` that can appear as an LLM provider label's prefix.
# ``knowledge-graph`` never does — that client raises its own errors — and ``custom`` is
# the fallback for a label none of these match, not a match itself.
PROVIDER_DEPENDENCIES: frozenset[str] = frozenset({"openai", "google", "anthropic"})


class DependencyErrorOptions(TypedDict, total=False):
    """Keyword options shared by every :class:`DependencyError` subclass."""

    status_code: int | None
    request_id: str | None
    #: Model in use, when the dependency is an LLM provider.
    model: str | None
    #: Overrides the class default; a 5xx forces ``True``.
    retryable: bool
    cause: BaseException | None


class EvaluatorError(Exception):
    """Abstract base for every error the SDK raises.

    Not instantiable directly (§6.1): raise a concrete subclass. Exists so callers can
    catch the whole family and branch on category.
    """

    retryable: bool

    def __init__(self, message: str, retryable: bool, cause: BaseException | None = None) -> None:
        if type(self) in _ABSTRACT_CLASSES:
            raise TypeError(
                f"{type(self).__name__} is abstract; raise one of its concrete subclasses."
            )
        super().__init__(message)
        self.retryable = retryable
        if cause is not None:
            self.__cause__ = cause


class ConfigurationError(EvaluatorError):
    """Caller: missing or invalid key, unknown provider or model, malformed settings."""

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        super().__init__(message, False, cause)


class InputValidationError(EvaluatorError):
    """Caller: text or grade failed validation.

    Also covers caller-supplied identifiers a dependency rejects — fault domain decides,
    not subsystem.
    """

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        super().__init__(message, False, cause)


class StandardNotFoundError(InputValidationError):
    """A caller-supplied standards code that does not exist in the jurisdiction."""

    def __init__(
        self, message: str, statement_code: str, cause: BaseException | None = None
    ) -> None:
        super().__init__(message, cause)
        self.statement_code = statement_code


class EvaluationError(EvaluatorError):
    """Abstract: our own evaluation logic failed after the dependency call succeeded."""


class LLMOutputProcessingError(EvaluationError):
    """Model response failed parsing, normalization, or its output schema.

    Retryable immediately: the failure is sampling variance, so backing off only adds
    latency. ``validation_errors`` carries per-field failures as schema locations and error
    types (see :func:`sanitize_pydantic_errors`); ``None`` when the failure was not a
    field-level one.
    """

    def __init__(
        self,
        message: str,
        validation_errors: list[dict[str, Any]] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, True, cause)
        self.validation_errors = validation_errors


class DependencyError(EvaluatorError):
    """Abstract: an external system failed. Which system is data (``dependency``), not a class."""

    def __init__(
        self,
        message: str,
        class_retryable: bool,
        *,
        dependency: DependencyId,
        **options: Unpack[DependencyErrorOptions],
    ) -> None:
        status_code = options.get("status_code")
        is_5xx = status_code is not None and status_code >= 500
        explicit = options.get("retryable")
        super().__init__(
            message,
            explicit if explicit is not None else (is_5xx or class_retryable),
            options.get("cause"),
        )
        self.dependency: DependencyId = dependency
        self.status_code: int | None = status_code
        self.request_id: str | None = options.get("request_id")
        self.model: str | None = options.get("model")


class AuthenticationError(DependencyError):
    """401 or 403 from the dependency. Never retryable by default."""

    def __init__(
        self, message: str, *, dependency: DependencyId, **options: Unpack[DependencyErrorOptions]
    ) -> None:
        super().__init__(message, False, dependency=dependency, **options)


class RateLimitError(DependencyError):
    """429 from the dependency. Retryable with backoff, honouring ``retry_after_ms``."""

    def __init__(
        self,
        message: str,
        *,
        dependency: DependencyId,
        retry_after_ms: int | None = None,
        **options: Unpack[DependencyErrorOptions],
    ) -> None:
        # A present-but-None status must not clobber the 429 this class implies.
        if options.get("status_code") is None:
            options["status_code"] = 429
        super().__init__(message, True, dependency=dependency, **options)
        self.retry_after_ms: int | None = retry_after_ms


class NetworkError(DependencyError):
    """Connection-level failure: DNS, refused, reset, TLS. Retryable with backoff."""

    def __init__(
        self, message: str, *, dependency: DependencyId, **options: Unpack[DependencyErrorOptions]
    ) -> None:
        super().__init__(message, True, dependency=dependency, **options)


class RequestTimeoutError(DependencyError):
    """The request to the dependency exceeded its timeout. Retryable with backoff.

    Named to avoid shadowing the builtin ``TimeoutError``.
    """

    def __init__(
        self, message: str, *, dependency: DependencyId, **options: Unpack[DependencyErrorOptions]
    ) -> None:
        super().__init__(message, True, dependency=dependency, **options)


class LLMProviderError(DependencyError):
    """Catch-all for LLM-provider failures not mapped above. Retryable iff 5xx."""

    def __init__(
        self, message: str, *, dependency: DependencyId, **options: Unpack[DependencyErrorOptions]
    ) -> None:
        super().__init__(message, False, dependency=dependency, **options)


class KnowledgeGraphError(DependencyError):
    """Catch-all for Knowledge Graph failures not mapped above. Retryable iff 5xx."""

    def __init__(self, message: str, **options: Unpack[DependencyErrorOptions]) -> None:
        super().__init__(message, False, dependency="knowledge-graph", **options)


_ABSTRACT_CLASSES: frozenset[type] = frozenset({EvaluatorError, EvaluationError, DependencyError})


# --- Sanitizing pydantic detail ----------------------------------------------------------


def _is_safe_ctx_value(value: Any) -> bool:
    """True if a pydantic ``ctx`` value is safe to expose in logs and telemetry.

    Pydantic puts constraint metadata in ``ctx`` (e.g. ``{"min_length": 3}``) but custom
    validators can attach arbitrary strings there. Only non-string JSON primitives, and
    lists or tuples of those, are kept.
    """
    if value is None or isinstance(value, (bool, int, float)):
        return True
    if isinstance(value, (tuple, list)):
        return all(_is_safe_ctx_value(item) for item in value)
    return False


def sanitize_pydantic_errors(errors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Reduce :meth:`pydantic.ValidationError.errors` entries to schema locations and error types.

    ``input`` (the rejected value, which for model output may echo prompt content) and
    ``msg`` (which custom validators often interpolate the value into) are dropped; ``ctx``
    keeps only numeric and boolean constraint metadata. ``loc``, ``type``, and ``url`` are
    retained. This is the shape ``LLMOutputProcessingError.validation_errors`` carries and
    what telemetry may report (§6.4).
    """
    sanitized: list[dict[str, Any]] = []
    for error in errors:
        clean: dict[str, Any] = {
            key: value for key, value in error.items() if key not in {"input", "ctx", "msg"}
        }
        ctx = error.get("ctx")
        if isinstance(ctx, Mapping):
            safe_ctx = {k: v for k, v in ctx.items() if _is_safe_ctx_value(v)}
            if safe_ctx:
                clean["ctx"] = safe_ctx
        sanitized.append(clean)
    return sanitized


# --- Provider-error wrapping --------------------------------------------------------------

# Header names providers use for the request ID, in preference order.
_REQUEST_ID_HEADERS = ("x-request-id", "request-id", "x-amzn-requestid")

# Beyond this, a ``Retry-After`` is more likely malformed than meant.
_MAX_RETRY_AFTER_MS = 60 * 60 * 1000

# How far to follow ``__cause__`` / ``__context__`` before giving up.
_MAX_CHAIN_DEPTH = 10

# Connection-level failures, by errno rather than message text (the Python analogue of the
# Node errno codes the TypeScript SDK reads). ``ConnectionError`` and its builtin subclasses
# already cover refused, reset, aborted, and broken pipe.
_NETWORK_ERRNOS = frozenset(
    {errno.EHOSTUNREACH, errno.ENETUNREACH, errno.ECONNREFUSED, errno.ECONNRESET, errno.EPIPE}
)
_TIMEOUT_ERRNOS = frozenset({errno.ETIMEDOUT})


@dataclass(frozen=True)
class _ProviderSignals:
    message: str
    status_code: int | None
    request_id: str | None
    #: The provider's own retryability verdict, when it gave one.
    retryable: bool | None
    retry_after_ms: int | None


def _cause_chain(error: BaseException) -> Iterator[BaseException]:
    """Walk the cause chain so a wrapped provider error is still classifiable.

    Follows ``__cause__`` (``raise ... from``) and, when that is unset and not suppressed,
    ``__context__`` (an exception raised while handling another), which is how Python's own
    traceback display links them. Bounded and cycle-safe.
    """
    seen: set[int] = set()
    current: BaseException | None = error
    depth = 0
    while current is not None and depth < _MAX_CHAIN_DEPTH and id(current) not in seen:
        seen.add(id(current))
        yield current
        depth += 1
        if current.__cause__ is not None:
            current = current.__cause__
        elif not current.__suppress_context__:
            current = current.__context__
        else:
            current = None


def _sdk_class(module: str, name: str) -> type | None:
    """A native SDK's exception class, only if that SDK is already imported.

    An SDK that was never imported cannot have raised the error being classified, so
    looking it up in ``sys.modules`` is both sufficient and free — the taxonomy stays light
    and never imports a provider SDK on its own.
    """
    mod = sys.modules.get(module)
    cls = getattr(mod, name, None) if mod is not None else None
    return cls if isinstance(cls, type) else None


def _is_instance_of(link: BaseException, module: str, name: str) -> bool:
    cls = _sdk_class(module, name)
    return cls is not None and isinstance(link, cls)


def _as_int(value: Any) -> int | None:
    """An ``int`` status, excluding ``bool`` (a subclass of ``int``) and numeric strings."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _status_code_of(link: BaseException) -> int | None:
    """The HTTP status one link carries, from the structured places the SDKs put it.

    openai and anthropic status errors expose ``status_code``; google-genai's ``APIError``
    exposes ``code``; ``httpx.HTTPStatusError`` keeps it on ``response``; a bring-your-own
    provider may use the loose ``status`` name. Restricted to ints so a google ``status``
    string like ``"NOT_FOUND"`` is never read as a code.
    """
    status = _as_int(getattr(link, "status_code", None))
    if status is not None:
        return status
    if _is_instance_of(link, "google.genai.errors", "APIError"):
        status = _as_int(getattr(link, "code", None))
        if status is not None:
            return status
    response = getattr(link, "response", None)
    if response is not None:
        status = _as_int(getattr(response, "status_code", None))
        if status is not None:
            return status
    return _as_int(getattr(link, "status", None))


def _headers_of(link: BaseException) -> Any | None:
    response = getattr(link, "response", None)
    headers = getattr(response, "headers", None) if response is not None else None
    return headers if headers is not None and hasattr(headers, "get") else None


def _lookup_header(headers: Any, name: str) -> str | None:
    """Header names are case-insensitive; a custom transport may not normalise them."""
    try:
        direct = headers.get(name)
    except Exception:  # noqa: BLE001 — a non-mapping must not break classification
        return None
    if direct is not None:
        return str(direct)
    items = getattr(headers, "items", None)
    if not callable(items):
        return None
    try:
        for key, value in items():
            if str(key).lower() == name:
                return str(value)
    except Exception:  # noqa: BLE001
        return None
    return None


def _usable_delay_ms(value: float) -> int | None:
    """A delay is only usable if it is a positive, finite, plausible number of milliseconds.

    A zero delay reads as "retry now", which is worse than having no hint at all — so
    anything non-positive, and anything past the ceiling, is discarded.
    """
    if not math.isfinite(value) or value <= 0:
        return None
    return min(round(value), _MAX_RETRY_AFTER_MS)


def _parse_number(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        # ``Retry-After`` may also be an HTTP-date, which is not a delay we can use.
        return None


def _read_retry_after_ms(headers: Any | None) -> int | None:
    if headers is None:
        return None
    seconds = _parse_number(_lookup_header(headers, "retry-after"))
    if seconds is not None:
        from_seconds = _usable_delay_ms(seconds * 1000)
        if from_seconds is not None:
            return from_seconds
    ms = _parse_number(_lookup_header(headers, "retry-after-ms"))
    return None if ms is None else _usable_delay_ms(ms)


def _read_request_id(link: BaseException, headers: Any | None) -> str | None:
    if headers is not None:
        for name in _REQUEST_ID_HEADERS:
            value = _lookup_header(headers, name)
            if value:
                return value
    # openai and anthropic also copy the header onto the exception itself.
    attr = getattr(link, "request_id", None)
    return attr if isinstance(attr, str) and attr else None


def _read_upstream_verdict(headers: Any | None) -> bool | None:
    """The provider's own retryability verdict, when it gave one.

    openai and anthropic honour an ``x-should-retry`` header from their servers; it is
    the one structured verdict Python SDK exceptions carry.
    """
    if headers is None:
        return None
    raw = _lookup_header(headers, "x-should-retry")
    if raw is None:
        return None
    lowered = raw.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def _read_provider_signals(error: BaseException) -> _ProviderSignals:
    """Read structured fields off whatever was raised.

    Message text is carried for diagnosis but never used to classify. The outermost link
    carrying a status wins, so a wrapper that re-labelled a failure is believed over the
    error it wrapped.
    """
    message = str(error)
    for link in _cause_chain(error):
        status = _status_code_of(link)
        if status is None:
            continue
        headers = _headers_of(link)
        return _ProviderSignals(
            message=message,
            status_code=status,
            request_id=_read_request_id(link, headers),
            retryable=_read_upstream_verdict(headers),
            retry_after_ms=_read_retry_after_ms(headers),
        )
    return _ProviderSignals(
        message=message, status_code=None, request_id=None, retryable=None, retry_after_ms=None
    )


def _provider_error_bodies(link: BaseException) -> list[Any]:
    """Every parsed JSON error body reachable from one link of the cause chain.

    openai and anthropic expose the decoded body as ``body``; google-genai as ``details``;
    an ``httpx.HTTPStatusError`` only as the response, whose body may or may not be JSON —
    so every candidate is read rather than trusting one.
    """
    bodies: list[Any] = []
    for attr in ("body", "details"):
        value = getattr(link, attr, None)
        if value is not None:
            bodies.append(value)
    # Duck-typed: openai and anthropic transport over httpx 2 (the ``httpx2`` package),
    # google-genai over httpx 0.x or ``requests``; every one exposes ``json()``.
    response = getattr(link, "response", None)
    json_of = getattr(response, "json", None)
    if callable(json_of):
        # A non-JSON body carries no verdict; the status code is all there is.
        with contextlib.suppress(Exception):
            bodies.append(json_of())
    return bodies


def _is_model_rejection(error: BaseException) -> bool:
    """Whether the provider blamed the model id itself, rather than failing to serve it.

    OpenAI-shaped bodies carry ``{"error": {"param", "code"}}``. ``param == "model"``
    covers a malformed id as well as an unknown one — both are the caller's choice of
    model, so the same fault domain. Compared against string literals, which excludes
    non-string values without narrowing them first.
    """
    for link in _cause_chain(error):
        for body in _provider_error_bodies(link):
            verdict = body.get("error") if isinstance(body, Mapping) else None
            if not isinstance(verdict, Mapping):
                continue
            if verdict.get("param") == "model" or verdict.get("code") == "model_not_found":
                return True
    return False


def _is_output_processing_failure(error: BaseException) -> bool:
    """Schema and parse failures are the model's fault, not the dependency's."""
    return any(
        isinstance(link, (PydanticValidationError, json.JSONDecodeError))
        for link in _cause_chain(error)
    )


def _validation_errors_of(error: BaseException) -> list[dict[str, Any]] | None:
    for link in _cause_chain(error):
        if isinstance(link, PydanticValidationError):
            return sanitize_pydantic_errors(link.errors())
    return None


def _find_transport_failure(error: BaseException) -> Literal["network", "timeout"] | None:
    """Typed connection-level and timeout failures, searched along the cause chain.

    Timeouts are checked before network failures on each link because the SDKs' timeout
    classes subclass their connection-error classes. Deliberate cancellation
    (``asyncio.CancelledError``) is a ``BaseException`` and never reaches here.

    Both httpx generations are covered: google-genai transports over ``httpx`` 0.x, while
    openai and anthropic transport over httpx 2, published as the separate ``httpx2``
    package (looked up only if loaded, like the SDK classes).
    """
    for link in _cause_chain(error):
        if isinstance(link, (TimeoutError, asyncio.TimeoutError, httpx.TimeoutException)):
            return "timeout"
        if any(_is_instance_of(link, module, name) for module, name in _TIMEOUT_SDK_CLASSES):
            return "timeout"
        if isinstance(link, OSError) and link.errno in _TIMEOUT_ERRNOS:
            return "timeout"

        if isinstance(
            link,
            (
                ConnectionError,
                socket.gaierror,
                socket.herror,
                ssl.SSLError,
                httpx.NetworkError,
                httpx.ProxyError,
            ),
        ):
            return "network"
        if any(_is_instance_of(link, module, name) for module, name in _NETWORK_SDK_CLASSES):
            return "network"
        if isinstance(link, OSError) and link.errno in _NETWORK_ERRNOS:
            return "network"
    return None


# Typed transport failures from packages this module never imports itself.
_TIMEOUT_SDK_CLASSES = (
    ("httpx2", "TimeoutException"),
    ("openai", "APITimeoutError"),
    ("anthropic", "APITimeoutError"),
)
_NETWORK_SDK_CLASSES = (
    ("httpx2", "NetworkError"),
    ("httpx2", "ProxyError"),
    ("openai", "APIConnectionError"),
    ("anthropic", "APIConnectionError"),
)


def wrap_provider_error(
    error: BaseException, *, dependency: DependencyId, model: str | None = None
) -> EvaluatorError:
    """Map a dependency failure onto the taxonomy.

    Classification uses structured signals only — status codes, typed exceptions from the
    native SDKs, ``httpx`` and the standard library, structured error payloads, and errnos,
    each searched along the cause chain. Message text is never matched: wording is not a
    contract, and the catch-all is safer than a wrong class (§6.5).

    An error that is already an :class:`EvaluatorError` is returned unchanged, so a
    boundary can wrap without first checking what it caught. The returned error carries
    ``error`` as its ``__cause__``; ``raise wrap_provider_error(e, ...) from e`` is the
    idiomatic call and sets the same link.
    """
    if isinstance(error, EvaluatorError):
        return error

    signals = _read_provider_signals(error)
    message, status_code = signals.message, signals.status_code
    options: DependencyErrorOptions = {
        "status_code": status_code,
        "request_id": signals.request_id,
        "model": model,
        "cause": error,
    }

    # A parse failure carrying an HTTP error status is the server erroring, not the model:
    # the body is an error page, not a malformed completion. Treating it as our own output
    # failure would resample immediately against a service that is already failing, so
    # only unparseable *successful* responses count.
    http_failed = status_code is not None and status_code >= 400
    if not http_failed and _is_output_processing_failure(error):
        return LLMOutputProcessingError(message, _validation_errors_of(error), error)

    # A rejected model is the caller's configuration, not a service fault: Google and
    # Anthropic answer 404, OpenAI answers 400 with ``code: model_not_found``. Restricted to
    # those two statuses so a 401/429/5xx that happens to name ``model`` keeps the definite
    # policy its status carries.
    if status_code == 404 or (status_code == 400 and _is_model_rejection(error)):
        return ConfigurationError(
            f"Model not found or invalid: {message}. Check the model ID passed to the provider.",
            error,
        )
    if status_code in (401, 403):
        return AuthenticationError(message, dependency=dependency, **options)
    if status_code == 429:
        return RateLimitError(
            message, dependency=dependency, retry_after_ms=signals.retry_after_ms, **options
        )

    transport = "timeout" if status_code == 408 else _find_transport_failure(error)
    if transport == "timeout":
        return RequestTimeoutError(message, dependency=dependency, **options)
    if transport == "network":
        return NetworkError(message, dependency=dependency, **options)

    # The dependency's own verdict only reaches the catch-all, whose class rule is
    # "retryable iff 5xx" and so genuinely benefits from it. Classes with a definite policy
    # keep theirs — an upstream flag must not make an auth failure retryable. It can only
    # widen: a ``False`` never defeats the 5xx floor.
    if signals.retryable is True:
        options["retryable"] = True
    return LLMProviderError(message or "API request failed", dependency=dependency, **options)


__all__ = [
    "PROVIDER_DEPENDENCIES",
    "AuthenticationError",
    "ConfigurationError",
    "DependencyError",
    "DependencyErrorOptions",
    "DependencyId",
    "EvaluationError",
    "EvaluatorError",
    "InputValidationError",
    "KnowledgeGraphError",
    "LLMOutputProcessingError",
    "LLMProviderError",
    "NetworkError",
    "RateLimitError",
    "RequestTimeoutError",
    "StandardNotFoundError",
    "sanitize_pydantic_errors",
    "wrap_provider_error",
]
