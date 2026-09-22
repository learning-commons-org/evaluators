from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.lesson import Lesson
from typing import cast



def _get_kwargs(
    lesson_id: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/lessons/{lesson_id}".format(lesson_id=quote(str(lesson_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | Lesson | None:
    if response.status_code == 200:
        response_200 = Lesson.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | Lesson]:
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

) -> Response[Error | Lesson]:
    """ Lesson by ID

     Fetches detailed information about a specific lesson.

    A lesson represents a focused instructional session within a larger curriculum structure, such as a
    lesson grouping or course, designed to achieve specific learning objectives. It typically includes
    activities, discussions, and assessments, and is intended to be completed within a defined
    timeframe, such as a class period or session.

    Use this endpoint when you need to:
    - Get complete metadata for a specific lesson
    - Retrieve lesson details including timing, audience, and educational use
    - Access curriculum-specific labeling information
    - Understand a lesson's place in the course structure

    Args:
        lesson_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | Lesson]
     """


    kwargs = _get_kwargs(
        lesson_id=lesson_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    lesson_id: str,
    *,
    client: AuthenticatedClient | Client,

) -> Error | Lesson | None:
    """ Lesson by ID

     Fetches detailed information about a specific lesson.

    A lesson represents a focused instructional session within a larger curriculum structure, such as a
    lesson grouping or course, designed to achieve specific learning objectives. It typically includes
    activities, discussions, and assessments, and is intended to be completed within a defined
    timeframe, such as a class period or session.

    Use this endpoint when you need to:
    - Get complete metadata for a specific lesson
    - Retrieve lesson details including timing, audience, and educational use
    - Access curriculum-specific labeling information
    - Understand a lesson's place in the course structure

    Args:
        lesson_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | Lesson
     """


    return sync_detailed(
        lesson_id=lesson_id,
client=client,

    ).parsed

async def asyncio_detailed(
    lesson_id: str,
    *,
    client: AuthenticatedClient | Client,

) -> Response[Error | Lesson]:
    """ Lesson by ID

     Fetches detailed information about a specific lesson.

    A lesson represents a focused instructional session within a larger curriculum structure, such as a
    lesson grouping or course, designed to achieve specific learning objectives. It typically includes
    activities, discussions, and assessments, and is intended to be completed within a defined
    timeframe, such as a class period or session.

    Use this endpoint when you need to:
    - Get complete metadata for a specific lesson
    - Retrieve lesson details including timing, audience, and educational use
    - Access curriculum-specific labeling information
    - Understand a lesson's place in the course structure

    Args:
        lesson_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | Lesson]
     """


    kwargs = _get_kwargs(
        lesson_id=lesson_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    lesson_id: str,
    *,
    client: AuthenticatedClient | Client,

) -> Error | Lesson | None:
    """ Lesson by ID

     Fetches detailed information about a specific lesson.

    A lesson represents a focused instructional session within a larger curriculum structure, such as a
    lesson grouping or course, designed to achieve specific learning objectives. It typically includes
    activities, discussions, and assessments, and is intended to be completed within a defined
    timeframe, such as a class period or session.

    Use this endpoint when you need to:
    - Get complete metadata for a specific lesson
    - Retrieve lesson details including timing, audience, and educational use
    - Access curriculum-specific labeling information
    - Understand a lesson's place in the course structure

    Args:
        lesson_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | Lesson
     """


    return (await asyncio_detailed(
        lesson_id=lesson_id,
client=client,

    )).parsed
