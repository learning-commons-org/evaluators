from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.academic_standard_search_result import AcademicStandardSearchResult
from ...models.academic_subject_enum import AcademicSubjectENUM
from ...models.error import Error
from ...models.grade_level_enum import GradeLevelENUM
from ...models.jurisdiction_enum import JurisdictionENUM
from ...models.normalized_statement_type_enum import NormalizedStatementTypeENUM
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["query"] = query

    params["statementCode"] = statement_code

    json_grade_level: list[str] | Unset = UNSET
    if not isinstance(grade_level, Unset):
        json_grade_level = []
        for grade_level_item_data in grade_level:
            grade_level_item = grade_level_item_data.value
            json_grade_level.append(grade_level_item)


    params["gradeLevel"] = json_grade_level

    json_academic_subject: str | Unset = UNSET
    if not isinstance(academic_subject, Unset):
        json_academic_subject = academic_subject.value

    params["academicSubject"] = json_academic_subject

    json_normalized_statement_type: str | Unset = UNSET
    if not isinstance(normalized_statement_type, Unset):
        json_normalized_statement_type = normalized_statement_type.value

    params["normalizedStatementType"] = json_normalized_statement_type

    json_jurisdiction: str | Unset = UNSET
    if not isinstance(jurisdiction, Unset):
        json_jurisdiction = jurisdiction.value

    params["jurisdiction"] = json_jurisdiction

    params["limit"] = limit


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/academic-standards/search",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | list[AcademicStandardSearchResult] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = AcademicStandardSearchResult.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())



        return response_400

    if response.status_code == 422:
        response_422 = Error.from_dict(response.json())



        return response_422

    if response.status_code == 500:
        response_500 = Error.from_dict(response.json())



        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | list[AcademicStandardSearchResult]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Response[Error | list[AcademicStandardSearchResult]]:
    """ Search standards

     Searches for StandardsFrameworkItems using either semantic search or exact statement code match
    across all standards frameworks.

    This endpoint supports two mutually exclusive search modes:

    - **Semantic search** (`query`): Full-text semantic search against the standard's description.
    Results are ranked by relevance and include a `score` reflecting vector similarity.
    - **Code search** (`statementCode`): Exact statement code match (e.g., "3.NF.A.1"). Case-
    insensitive, no partial matching. All results carry a `score` of 1.0.

    **Exactly one of `query` or `statementCode` must be provided.** Providing both or neither returns a
    400 error.

    Results can be narrowed further using the optional filters and support cursor-based pagination.

    Use this endpoint when you need to:
    - Find academic standards relevant to a concept or learning goal (semantic search)
    - Look up an academic standard by its exact statement code
    - Find all standards frameworks that include a specific statement code
    - Filter search results by grade level, subject, or statement type

    **Note:** Not all academic standards have statement codes - some organizational groupings may have
    null codes and won't appear in code search results.

    **Related topics:**
    - [Understanding statement codes](/knowledge-graph/schema-
    reference/standards#standardsframeworkitem)

    Args:
        query (str | Unset):
        statement_code (str | Unset):
        grade_level (list[GradeLevelENUM] | Unset):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | list[AcademicStandardSearchResult]]
     """


    kwargs = _get_kwargs(
        query=query,
statement_code=statement_code,
grade_level=grade_level,
academic_subject=academic_subject,
normalized_statement_type=normalized_statement_type,
jurisdiction=jurisdiction,
limit=limit,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Error | list[AcademicStandardSearchResult] | None:
    """ Search standards

     Searches for StandardsFrameworkItems using either semantic search or exact statement code match
    across all standards frameworks.

    This endpoint supports two mutually exclusive search modes:

    - **Semantic search** (`query`): Full-text semantic search against the standard's description.
    Results are ranked by relevance and include a `score` reflecting vector similarity.
    - **Code search** (`statementCode`): Exact statement code match (e.g., "3.NF.A.1"). Case-
    insensitive, no partial matching. All results carry a `score` of 1.0.

    **Exactly one of `query` or `statementCode` must be provided.** Providing both or neither returns a
    400 error.

    Results can be narrowed further using the optional filters and support cursor-based pagination.

    Use this endpoint when you need to:
    - Find academic standards relevant to a concept or learning goal (semantic search)
    - Look up an academic standard by its exact statement code
    - Find all standards frameworks that include a specific statement code
    - Filter search results by grade level, subject, or statement type

    **Note:** Not all academic standards have statement codes - some organizational groupings may have
    null codes and won't appear in code search results.

    **Related topics:**
    - [Understanding statement codes](/knowledge-graph/schema-
    reference/standards#standardsframeworkitem)

    Args:
        query (str | Unset):
        statement_code (str | Unset):
        grade_level (list[GradeLevelENUM] | Unset):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | list[AcademicStandardSearchResult]
     """


    return sync_detailed(
        client=client,
query=query,
statement_code=statement_code,
grade_level=grade_level,
academic_subject=academic_subject,
normalized_statement_type=normalized_statement_type,
jurisdiction=jurisdiction,
limit=limit,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Response[Error | list[AcademicStandardSearchResult]]:
    """ Search standards

     Searches for StandardsFrameworkItems using either semantic search or exact statement code match
    across all standards frameworks.

    This endpoint supports two mutually exclusive search modes:

    - **Semantic search** (`query`): Full-text semantic search against the standard's description.
    Results are ranked by relevance and include a `score` reflecting vector similarity.
    - **Code search** (`statementCode`): Exact statement code match (e.g., "3.NF.A.1"). Case-
    insensitive, no partial matching. All results carry a `score` of 1.0.

    **Exactly one of `query` or `statementCode` must be provided.** Providing both or neither returns a
    400 error.

    Results can be narrowed further using the optional filters and support cursor-based pagination.

    Use this endpoint when you need to:
    - Find academic standards relevant to a concept or learning goal (semantic search)
    - Look up an academic standard by its exact statement code
    - Find all standards frameworks that include a specific statement code
    - Filter search results by grade level, subject, or statement type

    **Note:** Not all academic standards have statement codes - some organizational groupings may have
    null codes and won't appear in code search results.

    **Related topics:**
    - [Understanding statement codes](/knowledge-graph/schema-
    reference/standards#standardsframeworkitem)

    Args:
        query (str | Unset):
        statement_code (str | Unset):
        grade_level (list[GradeLevelENUM] | Unset):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | list[AcademicStandardSearchResult]]
     """


    kwargs = _get_kwargs(
        query=query,
statement_code=statement_code,
grade_level=grade_level,
academic_subject=academic_subject,
normalized_statement_type=normalized_statement_type,
jurisdiction=jurisdiction,
limit=limit,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Error | list[AcademicStandardSearchResult] | None:
    """ Search standards

     Searches for StandardsFrameworkItems using either semantic search or exact statement code match
    across all standards frameworks.

    This endpoint supports two mutually exclusive search modes:

    - **Semantic search** (`query`): Full-text semantic search against the standard's description.
    Results are ranked by relevance and include a `score` reflecting vector similarity.
    - **Code search** (`statementCode`): Exact statement code match (e.g., "3.NF.A.1"). Case-
    insensitive, no partial matching. All results carry a `score` of 1.0.

    **Exactly one of `query` or `statementCode` must be provided.** Providing both or neither returns a
    400 error.

    Results can be narrowed further using the optional filters and support cursor-based pagination.

    Use this endpoint when you need to:
    - Find academic standards relevant to a concept or learning goal (semantic search)
    - Look up an academic standard by its exact statement code
    - Find all standards frameworks that include a specific statement code
    - Filter search results by grade level, subject, or statement type

    **Note:** Not all academic standards have statement codes - some organizational groupings may have
    null codes and won't appear in code search results.

    **Related topics:**
    - [Understanding statement codes](/knowledge-graph/schema-
    reference/standards#standardsframeworkitem)

    Args:
        query (str | Unset):
        statement_code (str | Unset):
        grade_level (list[GradeLevelENUM] | Unset):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | list[AcademicStandardSearchResult]
     """


    return (await asyncio_detailed(
        client=client,
query=query,
statement_code=statement_code,
grade_level=grade_level,
academic_subject=academic_subject,
normalized_statement_type=normalized_statement_type,
jurisdiction=jurisdiction,
limit=limit,

    )).parsed
