from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.academic_subject_enum import AcademicSubjectENUM
from ...models.error import Error
from ...models.learning_component_search_result import LearningComponentSearchResult
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    query: str,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["query"] = query

    json_academic_subject: str | Unset = UNSET
    if not isinstance(academic_subject, Unset):
        json_academic_subject = academic_subject.value

    params["academicSubject"] = json_academic_subject

    params["limit"] = limit


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/learning-components/search",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | list[LearningComponentSearchResult] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = LearningComponentSearchResult.from_dict(response_200_item_data)



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | list[LearningComponentSearchResult]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    query: str,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Response[Error | list[LearningComponentSearchResult]]:
    """ Search learning components

     <Warning>This endpoint is for free-text semantic search across learning component descriptions. To
    retrieve learning components for a specific standard, use [Components for a standard](/api-
    reference/learning-components/learning-components-for-a-standard) instead.</Warning>

    Searches for LearningComponents using semantic search against learning component descriptions.

    Results are ranked by relevance to the query text and include a `score` reflecting vector
    similarity. Use the optional `academicSubject` filter to narrow results to a specific subject area.

    Use this endpoint when you need to:
    - Find learning components relevant to a specific skill or concept
    - Discover granular instructional targets related to a teaching goal
    - Search for LCs to map to your own content or assessments

    **Related topics:**
    - [Understanding Learning components](/knowledge-graph/schema-reference/learning-components)
    - [Available LC coverage by subject and state](/knowledge-graph/schema-reference/learning-
    components#current-lc-mappings)

    Args:
        query (str):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | list[LearningComponentSearchResult]]
     """


    kwargs = _get_kwargs(
        query=query,
academic_subject=academic_subject,
limit=limit,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    query: str,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Error | list[LearningComponentSearchResult] | None:
    """ Search learning components

     <Warning>This endpoint is for free-text semantic search across learning component descriptions. To
    retrieve learning components for a specific standard, use [Components for a standard](/api-
    reference/learning-components/learning-components-for-a-standard) instead.</Warning>

    Searches for LearningComponents using semantic search against learning component descriptions.

    Results are ranked by relevance to the query text and include a `score` reflecting vector
    similarity. Use the optional `academicSubject` filter to narrow results to a specific subject area.

    Use this endpoint when you need to:
    - Find learning components relevant to a specific skill or concept
    - Discover granular instructional targets related to a teaching goal
    - Search for LCs to map to your own content or assessments

    **Related topics:**
    - [Understanding Learning components](/knowledge-graph/schema-reference/learning-components)
    - [Available LC coverage by subject and state](/knowledge-graph/schema-reference/learning-
    components#current-lc-mappings)

    Args:
        query (str):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | list[LearningComponentSearchResult]
     """


    return sync_detailed(
        client=client,
query=query,
academic_subject=academic_subject,
limit=limit,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    query: str,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Response[Error | list[LearningComponentSearchResult]]:
    """ Search learning components

     <Warning>This endpoint is for free-text semantic search across learning component descriptions. To
    retrieve learning components for a specific standard, use [Components for a standard](/api-
    reference/learning-components/learning-components-for-a-standard) instead.</Warning>

    Searches for LearningComponents using semantic search against learning component descriptions.

    Results are ranked by relevance to the query text and include a `score` reflecting vector
    similarity. Use the optional `academicSubject` filter to narrow results to a specific subject area.

    Use this endpoint when you need to:
    - Find learning components relevant to a specific skill or concept
    - Discover granular instructional targets related to a teaching goal
    - Search for LCs to map to your own content or assessments

    **Related topics:**
    - [Understanding Learning components](/knowledge-graph/schema-reference/learning-components)
    - [Available LC coverage by subject and state](/knowledge-graph/schema-reference/learning-
    components#current-lc-mappings)

    Args:
        query (str):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | list[LearningComponentSearchResult]]
     """


    kwargs = _get_kwargs(
        query=query,
academic_subject=academic_subject,
limit=limit,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    query: str,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Error | list[LearningComponentSearchResult] | None:
    """ Search learning components

     <Warning>This endpoint is for free-text semantic search across learning component descriptions. To
    retrieve learning components for a specific standard, use [Components for a standard](/api-
    reference/learning-components/learning-components-for-a-standard) instead.</Warning>

    Searches for LearningComponents using semantic search against learning component descriptions.

    Results are ranked by relevance to the query text and include a `score` reflecting vector
    similarity. Use the optional `academicSubject` filter to narrow results to a specific subject area.

    Use this endpoint when you need to:
    - Find learning components relevant to a specific skill or concept
    - Discover granular instructional targets related to a teaching goal
    - Search for LCs to map to your own content or assessments

    **Related topics:**
    - [Understanding Learning components](/knowledge-graph/schema-reference/learning-components)
    - [Available LC coverage by subject and state](/knowledge-graph/schema-reference/learning-
    components#current-lc-mappings)

    Args:
        query (str):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | list[LearningComponentSearchResult]
     """


    return (await asyncio_detailed(
        client=client,
query=query,
academic_subject=academic_subject,
limit=limit,

    )).parsed
