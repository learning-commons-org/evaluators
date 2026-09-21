"""Client for the Learning Commons Knowledge Graph (D9).

The Knowledge Graph is where academic standards and their learning components come from;
the math standards evaluator reads both to build its prompt. This module is the supported
surface. Underneath it sits ``_generated/knowledge_graph``, produced by ``make
generate-kg-client`` from the vendored OpenAPI spec — import from here, never from there.

Of the generated surface the SDK uses three endpoints:

- ``GET /academic-standards/search`` — :meth:`KnowledgeGraphClient.search_standards`
- ``GET /academic-standards/{uuid}`` — :meth:`KnowledgeGraphClient.get_academic_standard`
- ``GET /academic-standards/{uuid}/learning-components`` —
  :meth:`KnowledgeGraphClient.get_learning_component_set`

Every failure surfaces as the canonical taxonomy (§6.1) attributed to the
``knowledge-graph`` dependency: :class:`~learning_commons_evaluators.errors.AuthenticationError`
for 401/403, :class:`~learning_commons_evaluators.errors.RateLimitError` for 429,
:class:`~learning_commons_evaluators.errors.RequestTimeoutError` and
:class:`~learning_commons_evaluators.errors.NetworkError` for transport failures,
:class:`~learning_commons_evaluators.errors.StandardNotFoundError` when a statement code
the caller supplied matches nothing, and
:class:`~learning_commons_evaluators.errors.KnowledgeGraphError` for everything else,
retryable exactly when the status was 5xx.

The client is async, like the providers, and owns an HTTP connection pool. Use it as an
async context manager, or call :meth:`~KnowledgeGraphClient.aclose` when done::

    async with KnowledgeGraphClient(api_key) as kg:
        standard = await kg.search_standards("3.MD.C.7.d")
        components = await kg.get_learning_components(standard[0].case_identifier_uuid)

Not implemented here, deliberately: the per-code and per-UUID caching and the concurrency
limit the TypeScript client carries. Both exist to make *batch* evaluation cheap, batch is
its own story, and a cache that outlives one evaluation is a correctness decision (how
long may a standard be stale?) rather than a transport one.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
from collections.abc import Awaitable, Callable, Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
from typing import Any, TypeVar
from uuid import UUID

import httpx

from learning_commons_evaluators.config import EvaluatorConfig
from learning_commons_evaluators.dependencies._generated.knowledge_graph.api.academic_standards import (
    get_academic_standard_by_case_identifier_uuid,
    search_academic_standards,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.api.learning_components import (
    list_learning_components_by_academic_standard,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.client import (
    AuthenticatedClient,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.models.academic_standard_search_result import (
    AcademicStandardSearchResult,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.models.academic_subject_enum import (
    AcademicSubjectENUM,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.models.jurisdiction_enum import (
    JurisdictionENUM,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.models.learning_component_summary import (
    LearningComponentSummary,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.models.list_learning_components_by_academic_standard_response_200 import (
    ListLearningComponentsByAcademicStandardResponse200,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.models.standards_framework_item import (
    StandardsFrameworkItem,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.types import (
    UNSET,
    Response,
    Unset,
)
from learning_commons_evaluators.errors import (
    AuthenticationError,
    ConfigurationError,
    EvaluatorError,
    InputValidationError,
    KnowledgeGraphError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
    StandardNotFoundError,
)
from learning_commons_evaluators.logger import get_logger
from learning_commons_evaluators.schemas.kg_taxonomy import (
    DEFAULT_JURISDICTION,
    AcademicSubject,
    GradeLevel,
    Jurisdiction,
)

#: The published API origin, including the version prefix. The TypeScript client uses the
#: same one, so both SDKs read one service.
DEFAULT_BASE_URL = "https://api.learningcommons.org/knowledge-graph/v0"

#: Read budget matches the TypeScript client's 30s. Connect is tighter because a
#: connection that has not been established in 5s is not going to be.
#:
#: Set explicitly because the generated client always forwards its ``timeout`` field, and
#: httpx reads an explicit ``None`` as "no timeout at all" rather than falling back to its
#: own default — leaving it unset would let one stalled request hang a caller forever.
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=5.0)

#: The search endpoint's documented maximum. Sent explicitly because its *default* is 5.
STANDARD_SEARCH_LIMIT = 50

#: Page size for the learning-components walk. The spec allows up to 1000 and defaults to
#: 100; 100 is what the TypeScript client sends, and matching it keeps the two SDKs making
#: the same requests. A standard with more components than this pages, which is tested.
_LEARNING_COMPONENTS_PAGE_SIZE = 100

#: Bounds the search endpoint declares for ``limit``, checked before spending a request.
_SEARCH_LIMIT_RANGE = (1, 50)

#: Generous ceiling on a cursor walk, so a server minting a fresh cursor per page fails
#: loudly instead of paging forever.
_MAX_PAGES = 200

#: Base delay for dependency backoff, doubling per attempt, with full jitter.
_BACKOFF_BASE_S = 0.5
_BACKOFF_MAX_S = 8.0

_WHITESPACE = re.compile(r"\s+")

_EnumT = TypeVar("_EnumT", bound=Enum)

#: What the in-flight request is for, so the response hook can name it in an error. Set
#: per request by :meth:`KnowledgeGraphClient._request`; a context variable rather than an
#: attribute because one client serves concurrent callers and each asyncio task carries
#: its own copy of the context.
_resource: ContextVar[str] = ContextVar("lce_kg_resource", default="the requested resource")

logger = get_logger("dependencies.knowledge_graph")


# --- Domain types -------------------------------------------------------------------


@dataclass(frozen=True)
class AcademicStandard:
    """One academic standard, keyed by its CASE Network UUID.

    The Knowledge Graph declares everything but the UUID optional, so every other field
    may be ``None`` (or empty, for :attr:`grade_level`) on a sparsely authored standard.
    """

    case_identifier_uuid: str
    statement_code: str | None
    description: str | None
    notes: str | None
    jurisdiction: Jurisdiction | None
    academic_subject: AcademicSubject | None
    grade_level: tuple[GradeLevel, ...] = ()


@dataclass(frozen=True)
class StandardMatch:
    """One hit from a statement-code search, in the order the Knowledge Graph ranked them."""

    case_identifier_uuid: str
    #: The Knowledge Graph's own spelling — use this for display and for joins. CCSS
    #: sub-standards are lowercase (``3.MD.C.7.d``), so it differs from
    #: :attr:`normalized_code`. Falls back to the normalized code if the service omits it.
    statement_code: str
    #: The canonical lookup key the search was made with. Dedupe on this.
    normalized_code: str
    description: str | None
    jurisdiction: Jurisdiction | None


@dataclass(frozen=True)
class LearningComponent:
    """One learning component: the unit a question is judged to align with, or not.

    :attr:`description` is always present — the alignment judgment is made from that text,
    so components without one are filtered out at fetch time and counted instead.
    """

    identifier: str
    description: str


@dataclass(frozen=True)
class LearningComponentSet:
    """A standard's learning components, split by whether they can be evaluated.

    Keeping the count rather than dropping it silently is what lets a caller tell a
    standard with nothing authored against it (``components`` and ``undescribed_count``
    both empty) from one whose components exist but carry no text to judge against.
    """

    components: tuple[LearningComponent, ...] = ()
    undescribed_count: int = 0


# --- Statement codes ----------------------------------------------------------------


def normalize_statement_code(statement_code: str) -> str:
    """The canonical lookup form: trimmed, interior whitespace collapsed, uppercased.

    Safe because the Knowledge Graph documents ``statementCode`` search as a
    case-insensitive exact match, and it is what the TypeScript client sends, so the two
    SDKs resolve a given code to the same standard.
    """
    return _WHITESPACE.sub(" ", statement_code.strip()).upper()


# --- Wire conversion ----------------------------------------------------------------


def _text(value: Any) -> str | None:
    """A wire field as text, with ``UNSET``, ``None``, and ``""`` all reading as absent."""
    if value is None or isinstance(value, Unset):
        return None
    text = str(value.value) if isinstance(value, Enum) else str(value)
    return text or None


def _taxonomy(enum_class: type[_EnumT], value: Any) -> _EnumT | None:
    """A wire field as one of our taxonomy enums, or ``None`` if it is not one we know.

    Unknown values are dropped rather than raised on: the service may add a jurisdiction
    before we do (``make check-kg-client`` warns about exactly that), and a standard is
    still perfectly usable when one descriptive field of it is unrecognized.
    """
    text = _text(value)
    if text is None:
        return None
    try:
        return enum_class(text)
    except ValueError:
        logger.debug("Ignoring unknown %s from Knowledge Graph: %r", enum_class.__name__, text)
        return None


def _grade_levels(value: Any) -> tuple[GradeLevel, ...]:
    if value is None or isinstance(value, Unset):
        return ()
    parsed = (_taxonomy(GradeLevel, item) for item in value)
    return tuple(level for level in parsed if level is not None)


def _academic_standard(item: StandardsFrameworkItem) -> AcademicStandard:
    return AcademicStandard(
        case_identifier_uuid=str(item.case_identifier_uuid),
        statement_code=_text(item.statement_code),
        description=_text(item.description),
        notes=_text(item.notes),
        jurisdiction=_taxonomy(Jurisdiction, item.jurisdiction),
        academic_subject=_taxonomy(AcademicSubject, item.academic_subject),
        grade_level=_grade_levels(item.grade_level),
    )


def _standard_match(item: AcademicStandardSearchResult, normalized_code: str) -> StandardMatch:
    return StandardMatch(
        case_identifier_uuid=str(item.case_identifier_uuid),
        statement_code=_text(item.statement_code) or normalized_code,
        normalized_code=normalized_code,
        description=_text(item.description),
        jurisdiction=_taxonomy(Jurisdiction, item.jurisdiction),
    )


def _wire_text(value: Enum | str) -> str:
    """A taxonomy member or a plain string as the wire string.

    Taken from ``.value`` rather than ``str()``: a ``str``-mixin enum still renders as
    ``Jurisdiction.TEXAS`` under ``str()``, which is not what the service is expecting.
    """
    return str(value.value) if isinstance(value, Enum) else str(value)


def _wire_enum(enum_class: type[_EnumT], value: Enum | str, label: str) -> _EnumT:
    """A caller's value as the generated request enum, or a failure naming the field.

    The caller chose the value, so an unknown one is theirs to fix — and catching it here
    means a typo costs no request.
    """
    text = _wire_text(value)
    try:
        return enum_class(text)
    except ValueError as e:
        raise InputValidationError(f"Unknown Knowledge Graph {label}: {text!r}") from e


def _parse_uuid(value: str, label: str) -> UUID:
    try:
        return UUID(value)
    except (AttributeError, TypeError, ValueError) as e:
        raise InputValidationError(f"Invalid {label}: {value!r}") from e


# --- Failure mapping ----------------------------------------------------------------


#: Longest slice of an unparsed error body to quote back. Enough to recognize a gateway
#: page or a proxy's rejection without pasting a megabyte of HTML into a log line.
_MAX_BODY_EXCERPT = 300


@dataclass(frozen=True)
class _WireFailure:
    """What the service said about a failure, however it said it."""

    request_id: str | None = None
    message: str | None = None


def _wire_failure(response: httpx.Response) -> _WireFailure:
    """The request id and message behind a failure response.

    The Knowledge Graph documents one ``Error`` body shape — ``error``, ``message``,
    ``requestId`` — but only for some statuses on some endpoints, and a proxy in front of
    it answers with whatever it likes. So the body is read as that shape when it is one and
    quoted as an excerpt when it is not, and the request id falls back to the
    ``x-request-id`` header, which is on every response. The TypeScript client reads the
    same header, so a request traced from one SDK is traceable from the other.
    """
    header_id = response.headers.get("x-request-id") or None
    body = _error_body(response)
    if body is None:
        return _WireFailure(request_id=header_id, message=_body_excerpt(response.text))
    return _WireFailure(
        request_id=header_id or _text(body.get("requestId")),
        message=_text(body.get("message")) or _body_excerpt(response.text),
    )


def _error_body(response: httpx.Response) -> Mapping[str, Any] | None:
    """The response body as the documented error object, or ``None`` if it is not one."""
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, Mapping) and "message" in body else None


def _body_excerpt(content: str) -> str | None:
    """An unstructured error body as a short, single-line excerpt for the message."""
    text = _WHITESPACE.sub(" ", content).strip()
    if not text:
        return None
    return text if len(text) <= _MAX_BODY_EXCERPT else f"{text[:_MAX_BODY_EXCERPT]}…"


def _retry_after_ms(headers: Mapping[str, str]) -> int | None:
    """``Retry-After`` in milliseconds, if it is a delay we can actually use.

    Only the delta-seconds form is read. The HTTP-date form is also legal, but a clock
    difference makes it a worse hint than our own backoff, and a non-positive delay reads
    as "retry now", which is worse than no hint at all.
    """
    try:
        seconds = float(headers.get("retry-after", ""))
    except (TypeError, ValueError):
        return None
    return round(seconds * 1000) if seconds > 0 else None


async def _raise_for_status(response: httpx.Response) -> None:
    """Turn a failure response into the canonical error for it, before anything parses it.

    An httpx response hook rather than a check after the fact, mirroring the TypeScript
    client's error middleware. Putting it here means the generated parser only ever sees a
    success body, so a 500 whose body is an HTML gateway page is classified by its status
    — retryable — instead of surfacing as whatever the parser tripped over first.

    200 is the only success: every endpoint the SDK calls is a ``GET`` the spec documents
    as answering 200, and it is the only status the generated parsers build a model for,
    so anything else is a failure however 2xx it looks.
    """
    if response.status_code == HTTPStatus.OK:
        return
    # Hooks run before the body is read, and the error message quotes it.
    await response.aread()
    raise _map_status(response)


def _map_status(response: httpx.Response) -> EvaluatorError:
    """One non-200 response as the canonical error for it.

    Classified by status alone, never by message text: wording is not a contract, and the
    catch-all is safer than a wrong class (§6.5).
    """
    status = int(response.status_code)
    resource = _resource.get()
    failure = _wire_failure(response)
    detail = f": {failure.message}" if failure.message else ""
    options: dict[str, Any] = {"status_code": status, "request_id": failure.request_id}

    if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        return AuthenticationError(
            f"Knowledge Graph authentication failed{detail}. "
            "Check the learning_commons_api_key passed in the configuration.",
            dependency="knowledge-graph",
            **options,
        )
    if status == HTTPStatus.TOO_MANY_REQUESTS:
        return RateLimitError(
            f"Knowledge Graph rate limit exceeded{detail}",
            dependency="knowledge-graph",
            retry_after_ms=_retry_after_ms(response.headers),
            **options,
        )
    if status == HTTPStatus.REQUEST_TIMEOUT:
        return RequestTimeoutError(
            f"Knowledge Graph request timed out{detail}",
            dependency="knowledge-graph",
            **options,
        )
    if status == HTTPStatus.NOT_FOUND:
        # The caller named something that does not exist, so this is their fault domain
        # rather than the service's — an identifier is an input like any other (§6.1).
        return InputValidationError(f"Knowledge Graph has no {resource}{detail}")
    # Retryable exactly when 5xx, which DependencyError derives from the status.
    return KnowledgeGraphError(f"Knowledge Graph request failed (HTTP {status}){detail}", **options)


def _map_transport_error(error: Exception) -> EvaluatorError:
    """One raised transport failure as the canonical error for it."""
    if isinstance(error, httpx.TimeoutException):
        return RequestTimeoutError(
            f"Knowledge Graph request timed out: {error}", dependency="knowledge-graph"
        )
    if isinstance(error, (httpx.NetworkError, httpx.ProxyError)):
        return NetworkError(
            f"Knowledge Graph request failed: {error}", dependency="knowledge-graph"
        )
    # Remaining httpx.HTTPError kinds — an unsupported protocol, an invalid URL, too many
    # redirects. Configuration-shaped, and none of them improve on a retry.
    return KnowledgeGraphError(f"Knowledge Graph request failed: {error}")


#: How the generated parser fails on a body that is not the shape the spec promised. It
#: raises bare builtins rather than one type of its own: ``json.JSONDecodeError`` for a
#: body that is not JSON, ``KeyError`` for a missing required field, and the rest for a
#: field of the wrong type. Catching them here is what keeps a service-side mistake a
#: ``KnowledgeGraphError`` instead of an exception nothing in the SDK's contract mentions.
_BODY_FAILURES = (json.JSONDecodeError, KeyError, TypeError, ValueError, AttributeError)


def _map_body_failure(error: Exception, resource: str) -> KnowledgeGraphError:
    """A body the generated parser could not read as the canonical error for it.

    Never retryable: replaying the request returns the same bytes.
    """
    if isinstance(error, json.JSONDecodeError):
        return KnowledgeGraphError(f"Knowledge Graph returned invalid JSON for {resource}")
    return KnowledgeGraphError(
        f"Knowledge Graph returned an unexpected response body for {resource} "
        f"({type(error).__name__}: {error})"
    )


# --- Client -------------------------------------------------------------------------


class KnowledgeGraphClient:
    """Async client for the Learning Commons Knowledge Graph.

    Owns an HTTP connection pool, so close it when you are done — ``async with``, or
    :meth:`aclose`. An evaluator that builds one closes it from its own ``aclose``.

    :param api_key: The Learning Commons key, sent as ``x-api-key``.
    :param base_url: API origin including the ``/knowledge-graph/v0`` prefix.
    :param timeout: A number is seconds for every phase; pass an :class:`httpx.Timeout`
        for per-phase control, or ``None`` to disable timeouts entirely.
    :param max_retries: Extra attempts for retryable failures; total attempts are
        ``1 + max_retries``. ``0`` disables backoff.
    :param verify: TLS verification, as :class:`httpx.AsyncClient` takes it — ``False``, or
        a CA bundle path or :class:`ssl.SSLContext` for a corporate proxy.
    :param httpx_args: Extra keyword arguments for the connection pool, such as a
        ``transport`` or a ``proxy``. The pool is built here rather than lazily, so a
        rejected argument raises :class:`TypeError` now rather than mid-evaluation.
        ``base_url``, ``headers``, ``timeout``, ``verify``, and ``event_hooks`` are this
        client's to set and are named above instead where they are configurable at all.
    :raises ConfigurationError: when ``api_key`` is empty or ``max_retries`` is negative.

    There is deliberately no way to hand in a pre-built ``httpx.AsyncClient``. Doing so
    would mean stamping the Learning Commons key onto a pool that also talks to other
    hosts, and installing an error hook that turns *their* non-200 responses into
    Knowledge Graph errors. Share a :class:`KnowledgeGraphClient` instead — it is safe to
    use from concurrent tasks, and it is what an evaluator holds.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: httpx.Timeout | float | None = DEFAULT_TIMEOUT,
        max_retries: int = 0,
        verify: Any = True,
        httpx_args: Mapping[str, Any] | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ConfigurationError("Missing required credential: learning_commons_api_key.")
        if max_retries < 0:
            raise ConfigurationError(f"max_retries must not be negative, got {max_retries!r}.")

        self._max_retries = max_retries
        self._client = AuthenticatedClient(
            base_url=base_url,
            token=api_key,
            # An empty prefix and a named header make this ``x-api-key: <key>`` rather
            # than the generator's default ``Authorization: Bearer <key>``.
            prefix="",
            auth_header_name="x-api-key",
            timeout=_as_timeout(timeout),
            verify_ssl=verify,
            httpx_args={
                **dict(httpx_args or {}),
                # Every failure becomes an SDK error before the generated parser sees the
                # body; see _raise_for_status.
                "event_hooks": {"response": [_raise_for_status]},
            },
        )
        # Built now, not on the first request: the generated client sets base_url, headers,
        # timeout, verify and event_hooks itself, so an httpx_args key that collides with
        # one of those is a TypeError, and raising it here names the real cause instead of
        # surfacing mid-request as an unreadable response body.
        self._client.get_async_httpx_client()

    @classmethod
    def from_config(cls, config: EvaluatorConfig, **overrides: Any) -> KnowledgeGraphClient:
        """A client built from an evaluator's configuration.

        Reads ``learning_commons_api_key`` and ``max_retries``; ``overrides`` are passed
        through to the constructor, which is how an evaluator points at a non-default host
        or injects a pool.

        :raises ConfigurationError: when ``learning_commons_api_key`` is not set. Raised at
            construction, so the missing key surfaces before any LLM call rather than
            partway through an evaluation.
        """
        api_key = config.learning_commons_api_key
        if api_key is None or not api_key.strip():
            raise ConfigurationError("Missing required credential: learning_commons_api_key.")
        # setdefault, not a keyword: an override of max_retries is exactly what the
        # signature invites, and passing both would be a TypeError.
        overrides.setdefault("max_retries", config.max_retries)
        return cls(api_key, **overrides)

    async def aclose(self) -> None:
        """Release the connection pool. Safe to call more than once.

        Prefer closing from the loop that used the client. httpx tolerates the pool being
        reused and closed across separate ``asyncio.run`` calls — measured, not assumed —
        but an idle keep-alive connection outliving the loop that opened it is not a
        property it documents, so a long-lived client is better off on one loop.
        """
        await self._client.get_async_httpx_client().aclose()

    async def __aenter__(self) -> KnowledgeGraphClient:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    # --- endpoints ---------------------------------------------------------------

    async def search_standards(
        self,
        statement_code: str,
        *,
        jurisdiction: Jurisdiction | str = DEFAULT_JURISDICTION,
        academic_subject: AcademicSubject | str | None = None,
        limit: int = STANDARD_SEARCH_LIMIT,
    ) -> list[StandardMatch]:
        """Every standard whose statement code matches, best match first.

        More than one hit means the code is reused — typically across courses — and the
        caller has to choose; a result of exactly ``limit`` may have been truncated,
        because the search endpoint takes no cursor.

        :raises InputValidationError: for a blank code, a ``limit`` outside 1–50, or a
            jurisdiction or subject the Knowledge Graph does not define — each checked
            before a request is spent.

        :raises StandardNotFoundError: when nothing matches, carrying the normalized code.
            A code that does not exist in the jurisdiction is the caller's input, not a
            service fault, which is why it is an
            :class:`~learning_commons_evaluators.errors.InputValidationError` and not
            retryable.
        """
        normalized = normalize_statement_code(statement_code)
        # Checked here, not by the service. Both would come back as a 400, which the
        # taxonomy attributes to the Knowledge Graph — but an empty code and an
        # out-of-range limit are the caller's, and saying so costs no request. The
        # declared 50-character ceiling on a code is deliberately not enforced: it is the
        # vendored spec's number, and rejecting on it locally would turn a service that
        # relaxed the limit into a client-side failure.
        if not normalized:
            raise InputValidationError(f"statement_code must not be blank, got {statement_code!r}")
        low, high = _SEARCH_LIMIT_RANGE
        if not low <= limit <= high:
            raise InputValidationError(f"limit must be between {low} and {high}, got {limit!r}")
        response = await self._request(
            search_academic_standards.asyncio_detailed,
            resource=f"standard {normalized!r}",
            statement_code=normalized,
            jurisdiction=_wire_enum(JurisdictionENUM, jurisdiction, "jurisdiction"),
            academic_subject=(
                UNSET
                if academic_subject is None
                else _wire_enum(AcademicSubjectENUM, academic_subject, "academic subject")
            ),
            limit=limit,
        )
        results: list[AcademicStandardSearchResult] = _parsed(
            response, expected=list, resource=f"standard {normalized!r}"
        )
        if not results:
            raise StandardNotFoundError(
                f'Standard not found: "{statement_code}" '
                f'in jurisdiction "{_wire_text(jurisdiction)}"',
                normalized,
            )
        return [_standard_match(item, normalized) for item in results]

    async def get_academic_standard(self, case_identifier_uuid: str) -> AcademicStandard:
        """One standard by CASE Network UUID.

        :raises InputValidationError: when the UUID is malformed or names no standard.
        """
        resource = f"academic standard {case_identifier_uuid!r}"
        response = await self._request(
            get_academic_standard_by_case_identifier_uuid.asyncio_detailed,
            resource=resource,
            case_identifier_uuid=_parse_uuid(case_identifier_uuid, "academic-standard UUID"),
        )
        return _academic_standard(
            _parsed(response, expected=StandardsFrameworkItem, resource=resource)
        )

    async def get_learning_components(self, case_identifier_uuid: str) -> list[LearningComponent]:
        """Every evaluable learning component for a standard.

        See :meth:`get_learning_component_set` to tell a standard with no components apart
        from one whose components carry no descriptions.
        """
        return list((await self.get_learning_component_set(case_identifier_uuid)).components)

    async def get_learning_component_set(self, case_identifier_uuid: str) -> LearningComponentSet:
        """Every learning component for a standard, following the cursor to the last page.

        Each page is its own request, so a blip on page 7 of 10 retries page 7 rather than
        restarting the walk.

        :raises InputValidationError: when the UUID is malformed or names no standard.
        :raises KnowledgeGraphError: when the pagination fields contradict each other,
            which would otherwise truncate silently or loop forever.
        """
        uuid = _parse_uuid(case_identifier_uuid, "academic-standard UUID")
        resource = f"academic standard {case_identifier_uuid!r}"
        components: list[LearningComponent] = []
        undescribed = 0
        cursor: str | Unset = UNSET
        seen_cursors: set[str] = set()

        while True:
            response = await self._request(
                list_learning_components_by_academic_standard.asyncio_detailed,
                resource=resource,
                case_identifier_uuid=uuid,
                limit=_LEARNING_COMPONENTS_PAGE_SIZE,
                cursor=cursor,
            )
            body: ListLearningComponentsByAcademicStandardResponse200 = _parsed(
                response,
                expected=ListLearningComponentsByAcademicStandardResponse200,
                resource=resource,
            )
            page, page_undescribed = _learning_components_page(body, case_identifier_uuid)
            components.extend(page)
            undescribed += page_undescribed

            next_cursor = _next_cursor(body, resource)
            if next_cursor is None:
                break
            if next_cursor in seen_cursors:
                raise KnowledgeGraphError(
                    f"Knowledge Graph pagination error: cursor {next_cursor!r} "
                    f"repeated for {resource}"
                )
            seen_cursors.add(next_cursor)
            if len(seen_cursors) > _MAX_PAGES:
                # The repeat check above misses a server minting a fresh cursor per page.
                raise KnowledgeGraphError(
                    f"Knowledge Graph pagination error: exceeded {_MAX_PAGES} pages for {resource}"
                )
            cursor = next_cursor

        return LearningComponentSet(tuple(components), undescribed)

    # --- request plumbing --------------------------------------------------------

    async def _request(
        self,
        endpoint: Callable[..., Awaitable[Response[Any]]],
        *,
        resource: str,
        **kwargs: Any,
    ) -> Response[Any]:
        """The one point every request funnels through, and so where backoff sits.

        Backoff lives here rather than in ``providers/retry.py`` because that module
        delegates dependency backoff to the vendor SDKs (§6.3) and there is no vendor SDK
        beneath this one — the generated client is transport only. The rule is the same
        one the vendors apply: retry what the taxonomy marks ``retryable``, honour
        ``Retry-After`` when the service sent one, and otherwise back off exponentially
        with full jitter.
        """
        token = _resource.set(resource)
        try:
            return await self._attempt_request(endpoint, resource, kwargs)
        finally:
            _resource.reset(token)

    async def _attempt_request(
        self,
        endpoint: Callable[..., Awaitable[Response[Any]]],
        resource: str,
        kwargs: dict[str, Any],
    ) -> Response[Any]:
        for attempt in range(self._max_retries + 1):
            try:
                return await endpoint(client=self._client, **kwargs)
            except EvaluatorError as raised:
                # Raised by the response hook, which has already classified the status.
                error: EvaluatorError = raised
            except httpx.HTTPError as raw:
                error = _map_transport_error(raw)
                error.__cause__ = raw
            except _BODY_FAILURES as raw:
                error = _map_body_failure(raw, resource)
                error.__cause__ = raw

            if not error.retryable or attempt == self._max_retries:
                raise error
            delay = _backoff_delay(attempt, getattr(error, "retry_after_ms", None))
            logger.debug(
                "Retrying Knowledge Graph request for %s after %s (attempt %d of %d, %.2fs)",
                resource,
                type(error).__name__,
                attempt + 1,
                self._max_retries,
                delay,
            )
            await asyncio.sleep(delay)

        # Unreachable: the range always has a last iteration, which returns or raises.
        raise AssertionError("retry loop exited without a result")  # pragma: no cover


# --- Helpers ------------------------------------------------------------------------


def _as_timeout(timeout: httpx.Timeout | float | None) -> httpx.Timeout | None:
    """A caller's timeout as httpx's type; ``None`` passes through as "no timeout"."""
    if timeout is None or isinstance(timeout, httpx.Timeout):
        return timeout
    if timeout <= 0:
        raise ConfigurationError(
            f"Knowledge Graph timeout must be positive, got {timeout!r}; "
            "pass None to disable timeouts."
        )
    return httpx.Timeout(timeout)


def _parsed(response: Response[Any], *, expected: type, resource: str) -> Any:
    """The body of a 200, or a failure for a body that is not the shape the spec promised.

    ``_request`` has already raised for every non-200, so reaching here with the wrong
    type means the service answered 200 with something else.
    """
    if isinstance(response.parsed, expected):
        return response.parsed
    raise KnowledgeGraphError(
        f"Knowledge Graph returned an unexpected response body for {resource} "
        f"(expected {expected.__name__})",
        status_code=int(response.status_code),
    )


def _learning_components_page(
    body: ListLearningComponentsByAcademicStandardResponse200, case_identifier_uuid: str
) -> tuple[list[LearningComponent], int]:
    """One page's evaluable components, plus how many carried no description.

    The rows are re-parsed through :class:`LearningComponentSummary` rather than read
    loosely off ``additional_properties``, and the detour is the generator's fault rather
    than the spec's. The spec declares these rows properly, as an ``allOf`` overriding
    ``PaginatedResponse.data``; openapi-python-client 0.29 does not apply that override —
    it keeps the base's ``{type: object}``, emits the empty ``PaginatedResponseDataItem``,
    and says nothing about having done so. A plain ``$ref`` array resolves correctly,
    which is why standards come back typed and these rows do not.

    Parsing them here puts back what that loses: the declared field types, and a row that
    is missing a field the spec requires failing like every other malformed body instead
    of being silently dropped from a judgement. ``description`` is optional in the spec,
    so a row without one is counted rather than rejected — alignment is judged from that
    text, so such a row cannot be evaluated, but its absence is a fact about the standard
    rather than a broken response.
    """
    components: list[LearningComponent] = []
    undescribed = 0
    for item in body.data:
        # Mapped by hand because this parse happens after ``_request`` has returned, so it
        # is outside the net that turns the generated parser's bare builtins into an
        # error the taxonomy names.
        try:
            row = LearningComponentSummary.from_dict(item.additional_properties)
        except _BODY_FAILURES as raw:
            raise _map_body_failure(raw, f"academic standard {case_identifier_uuid!r}") from raw
        description = _text(row.description)
        if description is None:
            undescribed += 1
            logger.debug(
                "Learning component %s of standard %s has no description; not evaluable",
                row.identifier,
                case_identifier_uuid,
            )
            continue
        components.append(LearningComponent(identifier=row.identifier, description=description))
    return components, undescribed


def _next_cursor(
    body: ListLearningComponentsByAcademicStandardResponse200, resource: str
) -> str | None:
    """The cursor for the next page, or ``None`` when the walk is done."""
    if not body.pagination.has_more:
        return None
    cursor = body.pagination.next_cursor
    if isinstance(cursor, Unset) or not cursor:
        raise KnowledgeGraphError(
            f"Knowledge Graph pagination error: hasMore is true but nextCursor is "
            f"missing for {resource}"
        )
    return cursor


def _backoff_delay(attempt: int, retry_after_ms: int | None) -> float:
    """Seconds to wait before the next attempt (0-indexed).

    ``Retry-After`` wins when the service sent one: it knows when it will be ready and we
    are guessing. Otherwise exponential with full jitter, which spreads a fleet of clients
    that all got rate-limited by the same burst instead of having them return together.
    """
    if retry_after_ms is not None:
        return min(retry_after_ms / 1000, _BACKOFF_MAX_S)
    return random.uniform(0, min(_BACKOFF_BASE_S * 2**attempt, _BACKOFF_MAX_S))  # noqa: S311


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "STANDARD_SEARCH_LIMIT",
    "AcademicStandard",
    "KnowledgeGraphClient",
    "LearningComponent",
    "LearningComponentSet",
    "StandardMatch",
    "normalize_statement_code",
]
