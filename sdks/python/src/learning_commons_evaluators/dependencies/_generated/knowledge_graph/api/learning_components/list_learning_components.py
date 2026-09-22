from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.academic_subject_enum import AcademicSubjectENUM
from ...models.error import Error
from ...models.list_learning_components_response_200 import ListLearningComponentsResponse200
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    academic_subject: AcademicSubjectENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_academic_subject = academic_subject.value
    params["academicSubject"] = json_academic_subject

    params["limit"] = limit

    params["cursor"] = cursor


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/learning-components",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListLearningComponentsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListLearningComponentsResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListLearningComponentsResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    academic_subject: AcademicSubjectENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListLearningComponentsResponse200]:
    """ Learning components by subject

     Fetches a list of LearningComponents filtered by academic subject.

    This endpoint retrieves learning components for a specific subject area. Learning components are
    granular skills that break down broad standards into teachable units. Learning components are
    available for Mathematics and English Language Arts, with additional subjects being developed.

    Use this endpoint when you need to:
    - Get all learning components available for a specific subject
    - Browse the complete set of skills/concepts for curriculum planning
    - Retrieve LCs for mapping to your own content or assessments
    - Export learning component data for analysis or integration

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned and navigate through large result sets.

    **Related topics:**
    - [Understanding Learning components](/knowledge-graph/schema-reference/learning-components)
    - [Available LC coverage by subject and state](/knowledge-graph/schema-reference/learning-
    components#current-lc-mappings)

    Args:
        academic_subject (AcademicSubjectENUM): Academic subject area
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListLearningComponentsResponse200]
     """


    kwargs = _get_kwargs(
        academic_subject=academic_subject,
limit=limit,
cursor=cursor,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    academic_subject: AcademicSubjectENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListLearningComponentsResponse200 | None:
    """ Learning components by subject

     Fetches a list of LearningComponents filtered by academic subject.

    This endpoint retrieves learning components for a specific subject area. Learning components are
    granular skills that break down broad standards into teachable units. Learning components are
    available for Mathematics and English Language Arts, with additional subjects being developed.

    Use this endpoint when you need to:
    - Get all learning components available for a specific subject
    - Browse the complete set of skills/concepts for curriculum planning
    - Retrieve LCs for mapping to your own content or assessments
    - Export learning component data for analysis or integration

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned and navigate through large result sets.

    **Related topics:**
    - [Understanding Learning components](/knowledge-graph/schema-reference/learning-components)
    - [Available LC coverage by subject and state](/knowledge-graph/schema-reference/learning-
    components#current-lc-mappings)

    Args:
        academic_subject (AcademicSubjectENUM): Academic subject area
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListLearningComponentsResponse200
     """


    return sync_detailed(
        client=client,
academic_subject=academic_subject,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    academic_subject: AcademicSubjectENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListLearningComponentsResponse200]:
    """ Learning components by subject

     Fetches a list of LearningComponents filtered by academic subject.

    This endpoint retrieves learning components for a specific subject area. Learning components are
    granular skills that break down broad standards into teachable units. Learning components are
    available for Mathematics and English Language Arts, with additional subjects being developed.

    Use this endpoint when you need to:
    - Get all learning components available for a specific subject
    - Browse the complete set of skills/concepts for curriculum planning
    - Retrieve LCs for mapping to your own content or assessments
    - Export learning component data for analysis or integration

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned and navigate through large result sets.

    **Related topics:**
    - [Understanding Learning components](/knowledge-graph/schema-reference/learning-components)
    - [Available LC coverage by subject and state](/knowledge-graph/schema-reference/learning-
    components#current-lc-mappings)

    Args:
        academic_subject (AcademicSubjectENUM): Academic subject area
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListLearningComponentsResponse200]
     """


    kwargs = _get_kwargs(
        academic_subject=academic_subject,
limit=limit,
cursor=cursor,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    academic_subject: AcademicSubjectENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListLearningComponentsResponse200 | None:
    """ Learning components by subject

     Fetches a list of LearningComponents filtered by academic subject.

    This endpoint retrieves learning components for a specific subject area. Learning components are
    granular skills that break down broad standards into teachable units. Learning components are
    available for Mathematics and English Language Arts, with additional subjects being developed.

    Use this endpoint when you need to:
    - Get all learning components available for a specific subject
    - Browse the complete set of skills/concepts for curriculum planning
    - Retrieve LCs for mapping to your own content or assessments
    - Export learning component data for analysis or integration

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned and navigate through large result sets.

    **Related topics:**
    - [Understanding Learning components](/knowledge-graph/schema-reference/learning-components)
    - [Available LC coverage by subject and state](/knowledge-graph/schema-reference/learning-
    components#current-lc-mappings)

    Args:
        academic_subject (AcademicSubjectENUM): Academic subject area
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListLearningComponentsResponse200
     """


    return (await asyncio_detailed(
        client=client,
academic_subject=academic_subject,
limit=limit,
cursor=cursor,

    )).parsed
