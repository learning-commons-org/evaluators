"""The Knowledge Graph client, driven through a mock transport — no live calls.

Every test builds a real ``KnowledgeGraphClient`` over ``httpx.MockTransport``, so the
generated request building and response parsing run for real and only the socket is faked.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from http import HTTPStatus
from typing import Any, cast
from uuid import UUID

import httpx
import pytest

from learning_commons_evaluators.config import EvaluatorConfig
from learning_commons_evaluators.dependencies._generated.knowledge_graph.models.grade_level_enum import (
    GradeLevelENUM,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.models.jurisdiction_enum import (
    JurisdictionENUM,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.models.standards_framework_item import (
    StandardsFrameworkItem,
)
from learning_commons_evaluators.dependencies._generated.knowledge_graph.types import Response
from learning_commons_evaluators.dependencies.knowledge_graph import (
    DEFAULT_BASE_URL,
    STANDARD_SEARCH_LIMIT,
    AcademicStandard,
    KnowledgeGraphClient,
    LearningComponent,
    _academic_standard,
    _body_excerpt,
    _parsed,
    normalize_statement_code,
)
from learning_commons_evaluators.errors import (
    AuthenticationError,
    ConfigurationError,
    InputValidationError,
    KnowledgeGraphError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
    StandardNotFoundError,
)
from learning_commons_evaluators.schemas.kg_taxonomy import (
    AcademicSubject,
    GradeLevel,
    Jurisdiction,
)

_UUID = "fa29b90a-2795-4bf5-b6bc-3ac4a695e9e2"
_OTHER_UUID = "6c8e2b11-4a7d-4f0e-9b3c-2d5e8f1a0c47"

#: Attribution fields the Knowledge Graph requires on every resource; noise for our
#: purposes, but the generated models reject a body without them.
_ATTRIBUTION = {
    "author": "1EdTech",
    "provider": "Learning Commons",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "attributionStatement": "Knowledge Graph is provided by Learning Commons.",
}

_SEARCH_HIT = {
    **_ATTRIBUTION,
    "caseIdentifierUUID": _UUID,
    "statementCode": "3.MD.C.7.d",
    "description": "Find the area of a rectangle.",
    "jurisdiction": "Multi-State",
    "score": 1.0,
}

_STANDARD = {
    **_ATTRIBUTION,
    "identifier": "kg-std-1",
    "caseIdentifierUUID": _UUID,
    "hasChildren": False,
    "statementCode": "3.MD.C.7.d",
    "description": "Find the area of a rectangle.",
    "notes": "Optional usage guidance.",
    "jurisdiction": "Multi-State",
    "academicSubject": "Mathematics",
    "gradeLevel": ["3"],
}

_ERROR_BODY = {
    "error": "not_authorized",
    "message": "API key is not valid",
    "requestId": "req-42",
}


Handler = Callable[[httpx.Request], httpx.Response]


def _client(handler: Handler, *, max_retries: int = 0) -> KnowledgeGraphClient:
    # MockTransport serves async requests too, so one handler drives the whole client.
    return KnowledgeGraphClient(
        "test-key",
        max_retries=max_retries,
        httpx_args={"transport": httpx.MockTransport(handler)},
    )


def _answering(*responses: httpx.Response) -> tuple[Handler, list[httpx.Request]]:
    """A handler that replays ``responses`` in order, plus the log of what it was asked."""
    remaining = list(responses)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return remaining.pop(0) if len(remaining) > 1 else remaining[0]

    return handler, seen


def _lc(identifier: str, description: str | None = None, **overrides: object) -> dict[str, object]:
    """One learning-component row as the service sends it, attribution and all."""
    row: dict[str, object] = {**_ATTRIBUTION, "identifier": identifier}
    if description is not None:
        row["description"] = description
    return {**row, **overrides}


def _lc_page(*, items: list[dict[str, object]], next_cursor: str | None) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "data": items,
            "pagination": {
                "limit": 100,
                "hasMore": next_cursor is not None,
                "nextCursor": next_cursor,
            },
        },
    )


@pytest.fixture(autouse=True)
def _no_backoff_sleep(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[float]]:
    """Make the retry loop's waits instant, and record what they would have been."""
    import learning_commons_evaluators.dependencies.knowledge_graph as kg

    slept: list[float] = []

    async def fake_sleep(delay: float) -> None:
        slept.append(delay)

    monkeypatch.setattr(kg.asyncio, "sleep", fake_sleep)
    yield slept


# --- Wire conversion ----------------------------------------------------------------


def test_a_taxonomy_value_the_sdk_does_not_know_is_dropped_not_fatal() -> None:
    """Drift tolerance in the mapping layer, for the window `check-kg-client` warns about.

    The generated models accept every value the *vendored spec* declares, and the spec can
    gain a jurisdiction before ``schemas/kg_taxonomy.py`` does — ``make check-kg-client``
    warns about exactly that rather than failing. Until someone catches up, the standard
    is still perfectly usable with that one descriptive field left unset.
    """
    item = StandardsFrameworkItem(
        identifier="kg-std-1",
        case_identifier_uuid=UUID(_UUID),
        author="1EdTech",
        provider="Learning Commons",
        license_="https://creativecommons.org/licenses/by/4.0/",
        attribution_statement="Knowledge Graph is provided by Learning Commons.",
        has_children=False,
        description="Find the area of a rectangle.",
        # Stands in for a value a newer spec has and the SDK's enum does not.
        jurisdiction=cast(JurisdictionENUM, "Atlantis"),
        grade_level=cast(list[GradeLevelENUM], ["3", "Freshman"]),
    )
    standard = _academic_standard(item)
    assert standard.jurisdiction is None
    assert standard.grade_level == (GradeLevel.GRADE_3,)
    assert standard.description == "Find the area of a rectangle."


def test_an_empty_failure_body_contributes_no_message() -> None:
    assert _body_excerpt("   \n  ") is None


def test_a_success_body_of_the_wrong_type_is_reported_not_returned() -> None:
    """Defence for a spec that stops documenting 200 for an endpoint.

    The generated parser answers ``None`` for a status it does not know, and returning
    that would surface as an ``AttributeError`` somewhere downstream instead of as an
    error the taxonomy names.
    """
    response: Response[Any] = Response(
        status_code=HTTPStatus.OK, content=b"{}", headers={}, parsed=None
    )
    with pytest.raises(KnowledgeGraphError, match="unexpected response body"):
        _parsed(response, expected=StandardsFrameworkItem, resource="a standard")


# --- Statement code normalization ---------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("3.md.c.7.d", "3.MD.C.7.D"),
        ("  3.MD.C.7.d  ", "3.MD.C.7.D"),
        ("CCSS.MATH   3.MD", "CCSS.MATH 3.MD"),
        ("CCSS\tMATH\nNBT", "CCSS MATH NBT"),
    ],
)
def test_normalize_statement_code(raw: str, expected: str) -> None:
    assert normalize_statement_code(raw) == expected


# --- Construction -------------------------------------------------------------------


def test_empty_api_key_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="learning_commons_api_key"):
        KnowledgeGraphClient("   ")


def test_negative_max_retries_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="max_retries"):
        KnowledgeGraphClient("k", max_retries=-1)


def test_non_positive_timeout_is_a_configuration_error() -> None:
    with pytest.raises(ConfigurationError, match="must be positive"):
        KnowledgeGraphClient("k", timeout=0)


def test_numeric_timeout_becomes_an_httpx_timeout() -> None:
    client = KnowledgeGraphClient("k", timeout=2.5)
    assert client._client._timeout == httpx.Timeout(2.5)


def test_none_timeout_disables_timeouts() -> None:
    assert KnowledgeGraphClient("k", timeout=None)._client._timeout is None


def test_from_config_reads_the_key_and_retry_budget() -> None:
    config = EvaluatorConfig(learning_commons_api_key="from-config", max_retries=4)
    client = KnowledgeGraphClient.from_config(config)
    assert client._max_retries == 4
    assert client._client.token == "from-config"
    assert client._client._base_url == DEFAULT_BASE_URL


def test_from_config_without_the_key_names_the_canonical_credential() -> None:
    with pytest.raises(
        ConfigurationError, match="Missing required credential: learning_commons_api_key"
    ):
        KnowledgeGraphClient.from_config(EvaluatorConfig(google_api_key="g"))


def test_from_config_passes_overrides_to_the_constructor() -> None:
    client = KnowledgeGraphClient.from_config(
        EvaluatorConfig(learning_commons_api_key="k"), base_url="https://kg.test/v0"
    )
    assert client._client._base_url == "https://kg.test/v0"


def test_from_config_lets_an_override_win_over_the_config() -> None:
    # max_retries is read from the config *and* is a constructor argument, so overriding
    # it must not collide with the one from_config supplies.
    config = EvaluatorConfig(learning_commons_api_key="k", max_retries=2)
    assert KnowledgeGraphClient.from_config(config, max_retries=5)._max_retries == 5


# --- Lifecycle ----------------------------------------------------------------------


async def test_aclose_closes_a_pool_the_client_built() -> None:
    client = _client(lambda _: httpx.Response(200, json=[]))
    pool = client._client.get_async_httpx_client()
    await client.aclose()
    assert pool.is_closed


async def test_aclose_is_idempotent() -> None:
    client = _client(lambda _: httpx.Response(200, json=[]))
    await client.aclose()
    await client.aclose()


def test_a_pre_built_pool_cannot_be_handed_in() -> None:
    # Deliberate: stamping the key onto a shared pool would send it to every host that
    # pool talks to, and the error hook would turn their non-200s into KG errors.
    with pytest.raises(TypeError, match="httpx_client"):
        KnowledgeGraphClient("k", httpx_client=httpx.AsyncClient())  # type: ignore[call-arg]


async def test_context_manager_closes_on_exit() -> None:
    client = _client(lambda _: httpx.Response(200, json=[]))
    async with client as entered:
        assert entered is client
    assert client._client.get_async_httpx_client().is_closed


def test_a_colliding_httpx_arg_fails_at_construction_not_mid_request() -> None:
    # The pool is built eagerly, so an argument the generated client already sets is a
    # TypeError naming it — rather than surfacing on the first request as an unreadable
    # response body, which is what the body-failure net would otherwise make of it.
    with pytest.raises(TypeError, match="base_url"):
        KnowledgeGraphClient("k", httpx_args={"base_url": "https://elsewhere.test"})


def test_verify_is_forwarded_to_the_pool() -> None:
    # `verify` is named on the constructor because the generated client sets it itself;
    # passing it through httpx_args would collide.
    client = KnowledgeGraphClient("k", verify=False)
    assert client._client.get_async_httpx_client() is not None


# --- search_standards ---------------------------------------------------------------


async def test_search_sends_the_normalized_code_and_the_documented_limit() -> None:
    handler, seen = _answering(httpx.Response(200, json=[_SEARCH_HIT]))
    matches = await _client(handler).search_standards(" 3.md.c.7.d ")

    request = seen[0]
    assert request.headers["x-api-key"] == "test-key"
    assert request.url.path.endswith("/academic-standards/search")
    assert request.url.params["statementCode"] == "3.MD.C.7.D"
    assert request.url.params["jurisdiction"] == "Multi-State"
    assert request.url.params["limit"] == str(STANDARD_SEARCH_LIMIT)
    # academicSubject is optional and was not asked for, so it is not sent at all.
    assert "academicSubject" not in request.url.params

    assert len(matches) == 1
    assert matches[0].case_identifier_uuid == _UUID
    # The Knowledge Graph's own spelling survives; the uppercased key is kept separately.
    assert matches[0].statement_code == "3.MD.C.7.d"
    assert matches[0].normalized_code == "3.MD.C.7.D"
    assert matches[0].description == "Find the area of a rectangle."
    assert matches[0].jurisdiction is Jurisdiction.MULTI_STATE


async def test_search_passes_jurisdiction_and_subject_through() -> None:
    handler, seen = _answering(httpx.Response(200, json=[_SEARCH_HIT]))
    await _client(handler).search_standards(
        "3.MD.C.7.d",
        jurisdiction=Jurisdiction.TEXAS,
        academic_subject=AcademicSubject.MATHEMATICS,
    )
    assert seen[0].url.params["jurisdiction"] == "Texas"
    assert seen[0].url.params["academicSubject"] == "Mathematics"


async def test_search_keeps_every_candidate_in_service_order() -> None:
    second = {**_SEARCH_HIT, "caseIdentifierUUID": _OTHER_UUID, "score": 0.4}
    handler, _ = _answering(httpx.Response(200, json=[_SEARCH_HIT, second]))
    matches = await _client(handler).search_standards("3.MD.C.7.d")
    assert [m.case_identifier_uuid for m in matches] == [_UUID, _OTHER_UUID]


async def test_search_falls_back_to_the_normalized_code_when_the_service_omits_one() -> None:
    handler, _ = _answering(httpx.Response(200, json=[{**_SEARCH_HIT, "statementCode": None}]))
    (match,) = await _client(handler).search_standards("3.md.c.7.d")
    assert match.statement_code == "3.MD.C.7.D"


async def test_search_with_no_hits_raises_standard_not_found() -> None:
    handler, _ = _answering(httpx.Response(200, json=[]))
    with pytest.raises(StandardNotFoundError) as caught:
        await _client(handler).search_standards("no.such.code", jurisdiction=Jurisdiction.OHIO)

    error = caught.value
    # The caller's fault domain, so not retryable and reported as an input failure.
    assert isinstance(error, InputValidationError)
    assert error.retryable is False
    assert error.statement_code == "NO.SUCH.CODE"
    assert "Ohio" in str(error)


@pytest.mark.parametrize("code", ["", "   ", "\t\n"])
async def test_search_rejects_a_blank_statement_code_without_a_request(code: str) -> None:
    # A blank code would come back as a 400, which the taxonomy attributes to the service;
    # it is the caller's input, so it is caught here and costs no request.
    handler, seen = _answering(httpx.Response(200, json=[_SEARCH_HIT]))
    with pytest.raises(InputValidationError, match="must not be blank"):
        await _client(handler).search_standards(code)
    assert seen == []


@pytest.mark.parametrize("limit", [0, -1, 51, 1000])
async def test_search_rejects_a_limit_outside_the_declared_range(limit: int) -> None:
    handler, seen = _answering(httpx.Response(200, json=[_SEARCH_HIT]))
    with pytest.raises(InputValidationError, match="limit must be between 1 and 50"):
        await _client(handler).search_standards("3.MD.C.7.d", limit=limit)
    assert seen == []


async def test_search_accepts_the_edges_of_the_declared_limit_range() -> None:
    handler, seen = _answering(httpx.Response(200, json=[_SEARCH_HIT]))
    await _client(handler).search_standards("3.MD.C.7.d", limit=1)
    await _client(handler).search_standards("3.MD.C.7.d", limit=50)
    assert [r.url.params["limit"] for r in seen] == ["1", "50"]


async def test_search_rejects_an_unknown_jurisdiction_without_a_request() -> None:
    handler, seen = _answering(httpx.Response(200, json=[_SEARCH_HIT]))
    with pytest.raises(InputValidationError, match="jurisdiction"):
        await _client(handler).search_standards("3.MD.C.7.d", jurisdiction="Atlantis")
    assert seen == []


async def test_search_rejects_an_unknown_academic_subject_without_a_request() -> None:
    handler, seen = _answering(httpx.Response(200, json=[_SEARCH_HIT]))
    with pytest.raises(InputValidationError, match="academic subject"):
        await _client(handler).search_standards("3.MD.C.7.d", academic_subject="Alchemy")
    assert seen == []


# --- get_academic_standard ----------------------------------------------------------


async def test_get_academic_standard_maps_every_field() -> None:
    handler, seen = _answering(httpx.Response(200, json=_STANDARD))
    standard = await _client(handler).get_academic_standard(_UUID)

    assert seen[0].url.path.endswith(f"/academic-standards/{_UUID}")
    assert standard == AcademicStandard(
        case_identifier_uuid=_UUID,
        statement_code="3.MD.C.7.d",
        description="Find the area of a rectangle.",
        notes="Optional usage guidance.",
        jurisdiction=Jurisdiction.MULTI_STATE,
        academic_subject=AcademicSubject.MATHEMATICS,
        grade_level=(GradeLevel.GRADE_3,),
    )


async def test_get_academic_standard_tolerates_a_sparse_record() -> None:
    sparse = {
        **_ATTRIBUTION,
        "identifier": "kg-std-2",
        "caseIdentifierUUID": _UUID,
        "hasChildren": False,
    }
    handler, _ = _answering(httpx.Response(200, json=sparse))
    standard = await _client(handler).get_academic_standard(_UUID)
    assert standard.statement_code is None
    assert standard.description is None
    assert standard.jurisdiction is None
    assert standard.grade_level == ()


async def test_a_taxonomy_value_newer_than_the_vendored_spec_is_reported_not_guessed() -> None:
    # The generated models validate enums strictly, so a jurisdiction the service has
    # added and we have not regenerated for makes the whole standard unreadable rather
    # than arriving with one field missing. That is the cost of D9's generated client, and
    # `make check-kg-client` is what warns before it bites: it prints a warning for every
    # value the vendored spec has that schemas/kg_taxonomy.py does not.
    body = {**_STANDARD, "jurisdiction": "Atlantis"}
    handler, _ = _answering(httpx.Response(200, json=body))
    with pytest.raises(KnowledgeGraphError, match="unexpected response body"):
        await _client(handler).get_academic_standard(_UUID)


async def test_a_missing_required_field_is_reported_as_an_unreadable_body() -> None:
    incomplete = {k: v for k, v in _STANDARD.items() if k != "hasChildren"}
    handler, _ = _answering(httpx.Response(200, json=incomplete))
    with pytest.raises(KnowledgeGraphError, match="unexpected response body") as caught:
        await _client(handler).get_academic_standard(_UUID)
    # Not retryable: replaying the request returns the same bytes.
    assert caught.value.retryable is False


async def test_malformed_uuid_is_rejected_without_a_request() -> None:
    handler, seen = _answering(httpx.Response(200, json=_STANDARD))
    with pytest.raises(InputValidationError, match="Invalid academic-standard UUID"):
        await _client(handler).get_academic_standard("not-a-uuid")
    assert seen == []


# --- learning components ------------------------------------------------------------


async def test_learning_components_follow_the_cursor_to_the_last_page() -> None:
    first = _lc_page(
        items=[_lc("lc-1", "Decompose a rectilinear figure")],
        next_cursor="page-2",
    )
    second = _lc_page(
        items=[_lc("lc-2", "Find the area of a rectilinear figure")],
        next_cursor=None,
    )
    handler, seen = _answering(first, second)
    components = await _client(handler).get_learning_components(_UUID)

    assert components == [
        LearningComponent("lc-1", "Decompose a rectilinear figure"),
        LearningComponent("lc-2", "Find the area of a rectilinear figure"),
    ]
    assert len(seen) == 2
    assert seen[0].url.params["limit"] == "100"
    assert "cursor" not in seen[0].url.params
    assert seen[1].url.params["cursor"] == "page-2"


async def test_undescribed_components_are_counted_not_returned() -> None:
    # `description` is optional in the spec, so a row without one is a fact about the
    # standard rather than a broken response: alignment is judged from that text, so the
    # row cannot be evaluated, but it is counted so that "nothing authored against this
    # standard" stays distinguishable from "authored, but with no text to judge".
    handler, _ = _answering(
        _lc_page(items=[_lc("lc-1", "Usable"), _lc("lc-2"), _lc("lc-3", "")], next_cursor=None)
    )
    result = await _client(handler).get_learning_component_set(_UUID)

    assert result.components == (LearningComponent("lc-1", "Usable"),)
    assert result.undescribed_count == 2


async def test_a_row_missing_a_required_field_fails_like_any_other_malformed_body() -> None:
    """The spec requires `identifier`, so a row without one is a broken response.

    It used to be dropped silently, because the generator types these rows as a free-form
    object and the wrapper read them loosely. Dropping a learning component changes the
    judgement an evaluator reaches without telling anyone, which is worse than failing.
    """
    handler, _ = _answering(
        _lc_page(items=[{**_ATTRIBUTION, "description": "no identifier"}], next_cursor=None)
    )
    with pytest.raises(KnowledgeGraphError, match="unexpected response body"):
        await _client(handler).get_learning_components(_UUID)


async def test_rows_are_parsed_through_the_model_the_spec_declares() -> None:
    # The generator loses the allOf override and types these rows as an empty object, so
    # the wrapper re-parses them; this pins that the declared field types come back.
    handler, _ = _answering(_lc_page(items=[_lc("lc-1", "Usable")], next_cursor=None))
    (component,) = await _client(handler).get_learning_components(_UUID)
    assert (component.identifier, component.description) == ("lc-1", "Usable")


async def test_a_standard_with_no_components_is_an_empty_set_not_an_error() -> None:
    handler, _ = _answering(_lc_page(items=[], next_cursor=None))
    result = await _client(handler).get_learning_component_set(_UUID)
    assert result.components == ()
    assert result.undescribed_count == 0


async def test_has_more_without_a_cursor_fails_rather_than_truncating() -> None:
    page = httpx.Response(
        200, json={"data": [], "pagination": {"limit": 100, "hasMore": True, "nextCursor": None}}
    )
    handler, _ = _answering(page)
    with pytest.raises(KnowledgeGraphError, match="nextCursor is missing"):
        await _client(handler).get_learning_components(_UUID)


async def test_a_repeated_cursor_fails_rather_than_looping_forever() -> None:
    handler, _ = _answering(_lc_page(items=[], next_cursor="same"))
    with pytest.raises(KnowledgeGraphError, match="repeated"):
        await _client(handler).get_learning_components(_UUID)


async def test_a_fresh_cursor_per_page_is_stopped_by_the_page_ceiling() -> None:
    pages = iter(range(10_000))

    def handler(_: httpx.Request) -> httpx.Response:
        return _lc_page(items=[], next_cursor=f"cursor-{next(pages)}")

    with pytest.raises(KnowledgeGraphError, match="exceeded 200 pages"):
        await _client(handler).get_learning_components(_UUID)


# --- Failure mapping ----------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_failures_name_the_credential_to_fix(status: int) -> None:
    handler, _ = _answering(
        httpx.Response(status, json=_ERROR_BODY, headers={"x-request-id": "req-42"})
    )
    with pytest.raises(AuthenticationError) as caught:
        await _client(handler).get_academic_standard(_UUID)

    error = caught.value
    assert error.dependency == "knowledge-graph"
    assert error.status_code == status
    assert error.request_id == "req-42"
    assert error.retryable is False
    assert "learning_commons_api_key" in str(error)


async def test_rate_limit_carries_retry_after_in_milliseconds() -> None:
    handler, _ = _answering(httpx.Response(429, json=_ERROR_BODY, headers={"retry-after": "2.5"}))
    with pytest.raises(RateLimitError) as caught:
        await _client(handler).get_academic_standard(_UUID)

    assert caught.value.dependency == "knowledge-graph"
    assert caught.value.retry_after_ms == 2500
    assert caught.value.retryable is True


@pytest.mark.parametrize("header", ["not-a-number", "0", "-1"])
async def test_an_unusable_retry_after_is_ignored(header: str) -> None:
    handler, _ = _answering(httpx.Response(429, json=_ERROR_BODY, headers={"retry-after": header}))
    with pytest.raises(RateLimitError) as caught:
        await _client(handler).get_academic_standard(_UUID)
    assert caught.value.retry_after_ms is None


async def test_a_408_is_a_request_timeout() -> None:
    handler, _ = _answering(httpx.Response(408, json=_ERROR_BODY))
    with pytest.raises(RequestTimeoutError):
        await _client(handler).get_academic_standard(_UUID)


async def test_a_404_is_the_callers_identifier_not_a_service_fault() -> None:
    handler, _ = _answering(httpx.Response(404, json=_ERROR_BODY))
    with pytest.raises(InputValidationError) as caught:
        await _client(handler).get_academic_standard(_UUID)
    assert _UUID in str(caught.value)
    assert caught.value.retryable is False


@pytest.mark.parametrize(
    ("status", "retryable"), [(400, False), (422, False), (500, True), (503, True)]
)
async def test_everything_else_is_a_knowledge_graph_error_retryable_iff_5xx(
    status: int, retryable: bool
) -> None:
    handler, _ = _answering(httpx.Response(status, json=_ERROR_BODY))
    with pytest.raises(KnowledgeGraphError) as caught:
        await _client(handler, max_retries=0).get_academic_standard(_UUID)

    error = caught.value
    assert error.dependency == "knowledge-graph"
    assert error.status_code == status
    assert error.retryable is retryable
    # The service's own message is carried for diagnosis, never used to classify.
    assert "API key is not valid" in str(error)


async def test_a_failure_body_that_is_not_the_error_shape_still_classifies() -> None:
    # A proxy's HTML page in front of a 503. Classified by the status, so it stays
    # retryable, and the body is quoted so the page is recognizable in a log.
    handler, _ = _answering(httpx.Response(503, text="<html>gateway timeout</html>"))
    with pytest.raises(KnowledgeGraphError) as caught:
        await _client(handler, max_retries=0).get_academic_standard(_UUID)

    assert caught.value.status_code == 503
    assert caught.value.retryable is True
    assert caught.value.request_id is None
    assert "gateway timeout" in str(caught.value)


async def test_a_long_failure_body_is_truncated_in_the_message() -> None:
    handler, _ = _answering(httpx.Response(500, text="x" * 5_000))
    with pytest.raises(KnowledgeGraphError) as caught:
        await _client(handler).get_academic_standard(_UUID)
    assert len(str(caught.value)) < 500
    assert str(caught.value).endswith("…")


async def test_a_transport_timeout_is_a_request_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(RequestTimeoutError) as caught:
        await _client(handler).get_academic_standard(_UUID)
    assert caught.value.dependency == "knowledge-graph"
    assert isinstance(caught.value.__cause__, httpx.ReadTimeout)


async def test_a_connection_failure_is_a_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(NetworkError) as caught:
        await _client(handler).get_academic_standard(_UUID)
    assert caught.value.dependency == "knowledge-graph"
    assert caught.value.retryable is True


async def test_a_200_that_is_not_json_is_a_knowledge_graph_error() -> None:
    handler, _ = _answering(httpx.Response(200, text="not json"))
    with pytest.raises(KnowledgeGraphError, match="invalid JSON") as caught:
        await _client(handler).get_academic_standard(_UUID)
    assert caught.value.retryable is False


async def test_a_200_with_the_wrong_shape_is_a_knowledge_graph_error() -> None:
    # A well-formed JSON document that is not what the endpoint promised: the generated
    # parser returns None rather than the model, and the wrapper has to say so.
    handler, _ = _answering(httpx.Response(200, json=[{"unexpected": True}]))
    with pytest.raises(KnowledgeGraphError, match="unexpected response body"):
        await _client(handler).get_academic_standard(_UUID)


async def test_an_unroutable_request_is_reported_rather_than_retried() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.UnsupportedProtocol("gopher", request=request)

    with pytest.raises(KnowledgeGraphError) as caught:
        await _client(handler).get_academic_standard(_UUID)
    assert caught.value.retryable is False


# --- Backoff ------------------------------------------------------------------------


async def test_a_retryable_failure_is_retried_up_to_the_budget(
    _no_backoff_sleep: list[float],
) -> None:
    handler, seen = _answering(
        httpx.Response(503, json=_ERROR_BODY),
        httpx.Response(503, json=_ERROR_BODY),
        httpx.Response(200, json=_STANDARD),
    )
    standard = await _client(handler, max_retries=2).get_academic_standard(_UUID)

    assert standard.case_identifier_uuid == _UUID
    assert len(seen) == 3
    assert len(_no_backoff_sleep) == 2


async def test_backoff_gives_up_after_the_budget_and_raises_the_last_failure(
    _no_backoff_sleep: list[float],
) -> None:
    handler, seen = _answering(httpx.Response(500, json=_ERROR_BODY))
    with pytest.raises(KnowledgeGraphError):
        await _client(handler, max_retries=2).get_academic_standard(_UUID)

    # 1 + max_retries attempts, and no wait after the last one.
    assert len(seen) == 3
    assert len(_no_backoff_sleep) == 2


async def test_a_non_retryable_failure_is_not_retried(_no_backoff_sleep: list[float]) -> None:
    handler, seen = _answering(httpx.Response(400, json=_ERROR_BODY))
    with pytest.raises(KnowledgeGraphError):
        await _client(handler, max_retries=5).get_academic_standard(_UUID)
    assert len(seen) == 1
    assert _no_backoff_sleep == []


async def test_retries_are_off_by_default(_no_backoff_sleep: list[float]) -> None:
    handler, seen = _answering(httpx.Response(503, json=_ERROR_BODY))
    with pytest.raises(KnowledgeGraphError):
        await _client(handler).get_academic_standard(_UUID)
    assert len(seen) == 1


async def test_backoff_honours_retry_after_over_its_own_schedule(
    _no_backoff_sleep: list[float],
) -> None:
    handler, _ = _answering(
        httpx.Response(429, json=_ERROR_BODY, headers={"retry-after": "3"}),
        httpx.Response(200, json=_STANDARD),
    )
    await _client(handler, max_retries=1).get_academic_standard(_UUID)
    assert _no_backoff_sleep == [3.0]


async def test_backoff_without_a_hint_stays_inside_the_ceiling(
    _no_backoff_sleep: list[float],
) -> None:
    handler, _ = _answering(httpx.Response(503, json=_ERROR_BODY))
    with pytest.raises(KnowledgeGraphError):
        await _client(handler, max_retries=8).get_academic_standard(_UUID)
    assert len(_no_backoff_sleep) == 8
    assert all(0 <= delay <= 8.0 for delay in _no_backoff_sleep)


async def test_a_retry_after_far_in_the_future_is_capped(
    _no_backoff_sleep: list[float],
) -> None:
    handler, _ = _answering(
        httpx.Response(429, json=_ERROR_BODY, headers={"retry-after": "3600"}),
        httpx.Response(200, json=_STANDARD),
    )
    await _client(handler, max_retries=1).get_academic_standard(_UUID)
    assert _no_backoff_sleep == [8.0]


async def test_each_page_of_a_walk_retries_itself(_no_backoff_sleep: list[float]) -> None:
    # The blip is on page two; the walk resumes there rather than starting over.
    handler, seen = _answering(
        _lc_page(items=[_lc("lc-1", "One")], next_cursor="page-2"),
        httpx.Response(503, json=_ERROR_BODY),
        _lc_page(items=[_lc("lc-2", "Two")], next_cursor=None),
    )
    components = await _client(handler, max_retries=1).get_learning_components(_UUID)

    assert [c.identifier for c in components] == ["lc-1", "lc-2"]
    assert [request.url.params.get("cursor") for request in seen] == [None, "page-2", "page-2"]
