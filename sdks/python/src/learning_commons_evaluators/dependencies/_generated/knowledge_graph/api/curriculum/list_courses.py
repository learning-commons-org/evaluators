from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.curriculum_id_enum import CurriculumIdENUM
from ...models.error import Error
from ...models.list_courses_response_200 import ListCoursesResponse200
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    curriculum_id: CurriculumIdENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_curriculum_id = curriculum_id.value
    params["curriculumId"] = json_curriculum_id

    params["limit"] = limit

    params["cursor"] = cursor


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/courses",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListCoursesResponse200 | None:
    if response.status_code == 200:
        response_200 = ListCoursesResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListCoursesResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    curriculum_id: CurriculumIdENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListCoursesResponse200]:
    """ Courses in a curriculum

     Fetches a list of Course objects for a specific curriculum.

    A Course consists of a structured sequence of instructional content and activities designed to teach
    specific skills, knowledge, or competencies over a defined period. It typically encompasses multiple
    lesson groupings, lessons, and activities and aligns with curriculum standards and intended learning
    objectives for a particular grade level or subject area.

    Use this endpoint when you need to:
    - Discover available courses within a curriculum
    - Get course metadata (name, description, grade levels, subject)
    - Find course identifiers needed for other curriculum endpoints

    Args:
        curriculum_id (CurriculumIdENUM): Unique identifier for the resource in Knowledge Graph
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListCoursesResponse200]
     """


    kwargs = _get_kwargs(
        curriculum_id=curriculum_id,
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
    curriculum_id: CurriculumIdENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListCoursesResponse200 | None:
    """ Courses in a curriculum

     Fetches a list of Course objects for a specific curriculum.

    A Course consists of a structured sequence of instructional content and activities designed to teach
    specific skills, knowledge, or competencies over a defined period. It typically encompasses multiple
    lesson groupings, lessons, and activities and aligns with curriculum standards and intended learning
    objectives for a particular grade level or subject area.

    Use this endpoint when you need to:
    - Discover available courses within a curriculum
    - Get course metadata (name, description, grade levels, subject)
    - Find course identifiers needed for other curriculum endpoints

    Args:
        curriculum_id (CurriculumIdENUM): Unique identifier for the resource in Knowledge Graph
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListCoursesResponse200
     """


    return sync_detailed(
        client=client,
curriculum_id=curriculum_id,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    curriculum_id: CurriculumIdENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListCoursesResponse200]:
    """ Courses in a curriculum

     Fetches a list of Course objects for a specific curriculum.

    A Course consists of a structured sequence of instructional content and activities designed to teach
    specific skills, knowledge, or competencies over a defined period. It typically encompasses multiple
    lesson groupings, lessons, and activities and aligns with curriculum standards and intended learning
    objectives for a particular grade level or subject area.

    Use this endpoint when you need to:
    - Discover available courses within a curriculum
    - Get course metadata (name, description, grade levels, subject)
    - Find course identifiers needed for other curriculum endpoints

    Args:
        curriculum_id (CurriculumIdENUM): Unique identifier for the resource in Knowledge Graph
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListCoursesResponse200]
     """


    kwargs = _get_kwargs(
        curriculum_id=curriculum_id,
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
    curriculum_id: CurriculumIdENUM,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListCoursesResponse200 | None:
    """ Courses in a curriculum

     Fetches a list of Course objects for a specific curriculum.

    A Course consists of a structured sequence of instructional content and activities designed to teach
    specific skills, knowledge, or competencies over a defined period. It typically encompasses multiple
    lesson groupings, lessons, and activities and aligns with curriculum standards and intended learning
    objectives for a particular grade level or subject area.

    Use this endpoint when you need to:
    - Discover available courses within a curriculum
    - Get course metadata (name, description, grade levels, subject)
    - Find course identifiers needed for other curriculum endpoints

    Args:
        curriculum_id (CurriculumIdENUM): Unique identifier for the resource in Knowledge Graph
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListCoursesResponse200
     """


    return (await asyncio_detailed(
        client=client,
curriculum_id=curriculum_id,
limit=limit,
cursor=cursor,

    )).parsed
