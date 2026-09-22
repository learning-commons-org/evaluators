from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.list_assessments_response_200 import ListAssessmentsResponse200
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    course_id: str,
    lesson_id: str | Unset = UNSET,
    lesson_grouping_id: str | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["courseId"] = course_id

    params["lessonId"] = lesson_id

    params["lessonGroupingId"] = lesson_grouping_id

    params["limit"] = limit

    params["cursor"] = cursor


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/assessments",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListAssessmentsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListAssessmentsResponse200.from_dict(response.json())



        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())



        return response_400

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())



        return response_404

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListAssessmentsResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    course_id: str,
    lesson_id: str | Unset = UNSET,
    lesson_grouping_id: str | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListAssessmentsResponse200]:
    """ Assessments in a course

     Fetches assessments for a course with optional filtering by lesson or lesson grouping.

    Assessments can be associated with different levels of the curriculum hierarchy:
    - **Course-level**: All assessments in the course
    - **Lesson grouping-level**: Assessments for a unit, section, or module (e.g., "End-of-Unit
    Assessment")
    - **Lesson-level**: Assessments specific to a lesson

    Use this endpoint when you need to:
    - Get all assessments for a course
    - Find assessments for a specific lesson grouping (unit, section, module)
    - Find assessments for a specific lesson
    - Build assessment reports or tracking systems

    **Note:** You cannot provide both `lessonId` and `lessonGroupingId` in the same request.

    Args:
        course_id (str):
        lesson_id (str | Unset):
        lesson_grouping_id (str | Unset):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListAssessmentsResponse200]
     """


    kwargs = _get_kwargs(
        course_id=course_id,
lesson_id=lesson_id,
lesson_grouping_id=lesson_grouping_id,
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
    course_id: str,
    lesson_id: str | Unset = UNSET,
    lesson_grouping_id: str | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListAssessmentsResponse200 | None:
    """ Assessments in a course

     Fetches assessments for a course with optional filtering by lesson or lesson grouping.

    Assessments can be associated with different levels of the curriculum hierarchy:
    - **Course-level**: All assessments in the course
    - **Lesson grouping-level**: Assessments for a unit, section, or module (e.g., "End-of-Unit
    Assessment")
    - **Lesson-level**: Assessments specific to a lesson

    Use this endpoint when you need to:
    - Get all assessments for a course
    - Find assessments for a specific lesson grouping (unit, section, module)
    - Find assessments for a specific lesson
    - Build assessment reports or tracking systems

    **Note:** You cannot provide both `lessonId` and `lessonGroupingId` in the same request.

    Args:
        course_id (str):
        lesson_id (str | Unset):
        lesson_grouping_id (str | Unset):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListAssessmentsResponse200
     """


    return sync_detailed(
        client=client,
course_id=course_id,
lesson_id=lesson_id,
lesson_grouping_id=lesson_grouping_id,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    course_id: str,
    lesson_id: str | Unset = UNSET,
    lesson_grouping_id: str | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListAssessmentsResponse200]:
    """ Assessments in a course

     Fetches assessments for a course with optional filtering by lesson or lesson grouping.

    Assessments can be associated with different levels of the curriculum hierarchy:
    - **Course-level**: All assessments in the course
    - **Lesson grouping-level**: Assessments for a unit, section, or module (e.g., "End-of-Unit
    Assessment")
    - **Lesson-level**: Assessments specific to a lesson

    Use this endpoint when you need to:
    - Get all assessments for a course
    - Find assessments for a specific lesson grouping (unit, section, module)
    - Find assessments for a specific lesson
    - Build assessment reports or tracking systems

    **Note:** You cannot provide both `lessonId` and `lessonGroupingId` in the same request.

    Args:
        course_id (str):
        lesson_id (str | Unset):
        lesson_grouping_id (str | Unset):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListAssessmentsResponse200]
     """


    kwargs = _get_kwargs(
        course_id=course_id,
lesson_id=lesson_id,
lesson_grouping_id=lesson_grouping_id,
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
    course_id: str,
    lesson_id: str | Unset = UNSET,
    lesson_grouping_id: str | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListAssessmentsResponse200 | None:
    """ Assessments in a course

     Fetches assessments for a course with optional filtering by lesson or lesson grouping.

    Assessments can be associated with different levels of the curriculum hierarchy:
    - **Course-level**: All assessments in the course
    - **Lesson grouping-level**: Assessments for a unit, section, or module (e.g., "End-of-Unit
    Assessment")
    - **Lesson-level**: Assessments specific to a lesson

    Use this endpoint when you need to:
    - Get all assessments for a course
    - Find assessments for a specific lesson grouping (unit, section, module)
    - Find assessments for a specific lesson
    - Build assessment reports or tracking systems

    **Note:** You cannot provide both `lessonId` and `lessonGroupingId` in the same request.

    Args:
        course_id (str):
        lesson_id (str | Unset):
        lesson_grouping_id (str | Unset):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListAssessmentsResponse200
     """


    return (await asyncio_detailed(
        client=client,
course_id=course_id,
lesson_id=lesson_id,
lesson_grouping_id=lesson_grouping_id,
limit=limit,
cursor=cursor,

    )).parsed
