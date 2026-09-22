from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.lesson_grouping import LessonGrouping
from typing import cast



def _get_kwargs(
    grouping_id: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/lesson-groupings/{grouping_id}".format(grouping_id=quote(str(grouping_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | LessonGrouping | None:
    if response.status_code == 200:
        response_200 = LessonGrouping.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | LessonGrouping]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    grouping_id: str,
    *,
    client: AuthenticatedClient | Client,

) -> Response[Error | LessonGrouping]:
    """ Lesson grouping by ID

     Fetches detailed information about a specific lesson grouping.

    Set of related lessons within a curriculum; naming and organizational level may vary across
    curricula (e.g., unit, module, chapter, section, theme). The `groupName` property indicates the
    specific type used by the curriculum.

    Lesson groupings can be nested (e.g., units containing sections, chapters containing modules) as
    indicated by the `groupLevel` property, where 0 represents the top level.

    Use this endpoint when you need to:
    - Get complete metadata for a specific lesson grouping
    - Retrieve organizational details (group name, level, position)
    - Access curriculum-specific labeling and structure information
    - Understand a lesson grouping's place in the course hierarchy

    Args:
        grouping_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | LessonGrouping]
     """


    kwargs = _get_kwargs(
        grouping_id=grouping_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    grouping_id: str,
    *,
    client: AuthenticatedClient | Client,

) -> Error | LessonGrouping | None:
    """ Lesson grouping by ID

     Fetches detailed information about a specific lesson grouping.

    Set of related lessons within a curriculum; naming and organizational level may vary across
    curricula (e.g., unit, module, chapter, section, theme). The `groupName` property indicates the
    specific type used by the curriculum.

    Lesson groupings can be nested (e.g., units containing sections, chapters containing modules) as
    indicated by the `groupLevel` property, where 0 represents the top level.

    Use this endpoint when you need to:
    - Get complete metadata for a specific lesson grouping
    - Retrieve organizational details (group name, level, position)
    - Access curriculum-specific labeling and structure information
    - Understand a lesson grouping's place in the course hierarchy

    Args:
        grouping_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | LessonGrouping
     """


    return sync_detailed(
        grouping_id=grouping_id,
client=client,

    ).parsed

async def asyncio_detailed(
    grouping_id: str,
    *,
    client: AuthenticatedClient | Client,

) -> Response[Error | LessonGrouping]:
    """ Lesson grouping by ID

     Fetches detailed information about a specific lesson grouping.

    Set of related lessons within a curriculum; naming and organizational level may vary across
    curricula (e.g., unit, module, chapter, section, theme). The `groupName` property indicates the
    specific type used by the curriculum.

    Lesson groupings can be nested (e.g., units containing sections, chapters containing modules) as
    indicated by the `groupLevel` property, where 0 represents the top level.

    Use this endpoint when you need to:
    - Get complete metadata for a specific lesson grouping
    - Retrieve organizational details (group name, level, position)
    - Access curriculum-specific labeling and structure information
    - Understand a lesson grouping's place in the course hierarchy

    Args:
        grouping_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | LessonGrouping]
     """


    kwargs = _get_kwargs(
        grouping_id=grouping_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    grouping_id: str,
    *,
    client: AuthenticatedClient | Client,

) -> Error | LessonGrouping | None:
    """ Lesson grouping by ID

     Fetches detailed information about a specific lesson grouping.

    Set of related lessons within a curriculum; naming and organizational level may vary across
    curricula (e.g., unit, module, chapter, section, theme). The `groupName` property indicates the
    specific type used by the curriculum.

    Lesson groupings can be nested (e.g., units containing sections, chapters containing modules) as
    indicated by the `groupLevel` property, where 0 represents the top level.

    Use this endpoint when you need to:
    - Get complete metadata for a specific lesson grouping
    - Retrieve organizational details (group name, level, position)
    - Access curriculum-specific labeling and structure information
    - Understand a lesson grouping's place in the course hierarchy

    Args:
        grouping_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | LessonGrouping
     """


    return (await asyncio_detailed(
        grouping_id=grouping_id,
client=client,

    )).parsed
