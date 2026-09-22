from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.get_lesson_activities_response_200 import GetLessonActivitiesResponse200
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    lesson_id: str,
    *,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["limit"] = limit

    params["cursor"] = cursor


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/lessons/{lesson_id}/activities".format(lesson_id=quote(str(lesson_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | GetLessonActivitiesResponse200 | None:
    if response.status_code == 200:
        response_200 = GetLessonActivitiesResponse200.from_dict(response.json())



        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())



        return response_400

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())



        return response_404

    if response.status_code == 500:
        response_500 = Error.from_dict(response.json())



        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | GetLessonActivitiesResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    lesson_id: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | GetLessonActivitiesResponse200]:
    """ Activities in a lesson

     Fetches a list of activities within a specific lesson.

    An activity represents a discrete instructional task or exercise within a lesson, designed for
    students, teachers, or both. Activities are the building blocks of lessons and typically include
    specific tasks, exercises, discussions, or practice problems that help achieve the lesson's learning
    objectives.

    Use this endpoint when you need to:
    - Get all activities for a specific lesson
    - Navigate the instructional components of a lesson
    - Access activity metadata including timing, grouping, and submission requirements
    - Build lesson plans or instructional sequences

    Args:
        lesson_id (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetLessonActivitiesResponse200]
     """


    kwargs = _get_kwargs(
        lesson_id=lesson_id,
limit=limit,
cursor=cursor,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    lesson_id: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | GetLessonActivitiesResponse200 | None:
    """ Activities in a lesson

     Fetches a list of activities within a specific lesson.

    An activity represents a discrete instructional task or exercise within a lesson, designed for
    students, teachers, or both. Activities are the building blocks of lessons and typically include
    specific tasks, exercises, discussions, or practice problems that help achieve the lesson's learning
    objectives.

    Use this endpoint when you need to:
    - Get all activities for a specific lesson
    - Navigate the instructional components of a lesson
    - Access activity metadata including timing, grouping, and submission requirements
    - Build lesson plans or instructional sequences

    Args:
        lesson_id (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetLessonActivitiesResponse200
     """


    return sync_detailed(
        lesson_id=lesson_id,
client=client,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    lesson_id: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | GetLessonActivitiesResponse200]:
    """ Activities in a lesson

     Fetches a list of activities within a specific lesson.

    An activity represents a discrete instructional task or exercise within a lesson, designed for
    students, teachers, or both. Activities are the building blocks of lessons and typically include
    specific tasks, exercises, discussions, or practice problems that help achieve the lesson's learning
    objectives.

    Use this endpoint when you need to:
    - Get all activities for a specific lesson
    - Navigate the instructional components of a lesson
    - Access activity metadata including timing, grouping, and submission requirements
    - Build lesson plans or instructional sequences

    Args:
        lesson_id (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetLessonActivitiesResponse200]
     """


    kwargs = _get_kwargs(
        lesson_id=lesson_id,
limit=limit,
cursor=cursor,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    lesson_id: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | GetLessonActivitiesResponse200 | None:
    """ Activities in a lesson

     Fetches a list of activities within a specific lesson.

    An activity represents a discrete instructional task or exercise within a lesson, designed for
    students, teachers, or both. Activities are the building blocks of lessons and typically include
    specific tasks, exercises, discussions, or practice problems that help achieve the lesson's learning
    objectives.

    Use this endpoint when you need to:
    - Get all activities for a specific lesson
    - Navigate the instructional components of a lesson
    - Access activity metadata including timing, grouping, and submission requirements
    - Build lesson plans or instructional sequences

    Args:
        lesson_id (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetLessonActivitiesResponse200
     """


    return (await asyncio_detailed(
        lesson_id=lesson_id,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
