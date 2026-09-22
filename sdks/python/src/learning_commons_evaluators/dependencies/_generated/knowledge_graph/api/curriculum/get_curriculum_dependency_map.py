from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.curriculum_id_enum import CurriculumIdENUM
from ...models.dependency_map_response import DependencyMapResponse
from ...models.error import Error
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    curriculum_id: CurriculumIdENUM,
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
        "url": "/curriculums/{curriculum_id}/dependency-map".format(curriculum_id=quote(str(curriculum_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> DependencyMapResponse | Error | None:
    if response.status_code == 200:
        response_200 = DependencyMapResponse.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[DependencyMapResponse | Error]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    curriculum_id: CurriculumIdENUM,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[DependencyMapResponse | Error]:
    """ Dependency map for a curriculum

     Returns the dependency relationships between lesson groupings within a curriculum.

    Dependencies represent prerequisite relationships between lesson groupings (units, sections,
    modules).
    A dependency from source → target means the target is a prerequisite — it should be taught before
    the source.

    Use this endpoint when you need to:
    - Visualize the dependency graph for a curriculum
    - Understand prerequisite relationships between units or sections
    - Build a dependency-aware course planner or sequencing tool

    Args:
        curriculum_id (CurriculumIdENUM): Unique identifier for the resource in Knowledge Graph
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DependencyMapResponse | Error]
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
    curriculum_id: CurriculumIdENUM,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> DependencyMapResponse | Error | None:
    """ Dependency map for a curriculum

     Returns the dependency relationships between lesson groupings within a curriculum.

    Dependencies represent prerequisite relationships between lesson groupings (units, sections,
    modules).
    A dependency from source → target means the target is a prerequisite — it should be taught before
    the source.

    Use this endpoint when you need to:
    - Visualize the dependency graph for a curriculum
    - Understand prerequisite relationships between units or sections
    - Build a dependency-aware course planner or sequencing tool

    Args:
        curriculum_id (CurriculumIdENUM): Unique identifier for the resource in Knowledge Graph
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DependencyMapResponse | Error
     """


    return sync_detailed(
        curriculum_id=curriculum_id,
client=client,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    curriculum_id: CurriculumIdENUM,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[DependencyMapResponse | Error]:
    """ Dependency map for a curriculum

     Returns the dependency relationships between lesson groupings within a curriculum.

    Dependencies represent prerequisite relationships between lesson groupings (units, sections,
    modules).
    A dependency from source → target means the target is a prerequisite — it should be taught before
    the source.

    Use this endpoint when you need to:
    - Visualize the dependency graph for a curriculum
    - Understand prerequisite relationships between units or sections
    - Build a dependency-aware course planner or sequencing tool

    Args:
        curriculum_id (CurriculumIdENUM): Unique identifier for the resource in Knowledge Graph
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DependencyMapResponse | Error]
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
    curriculum_id: CurriculumIdENUM,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> DependencyMapResponse | Error | None:
    """ Dependency map for a curriculum

     Returns the dependency relationships between lesson groupings within a curriculum.

    Dependencies represent prerequisite relationships between lesson groupings (units, sections,
    modules).
    A dependency from source → target means the target is a prerequisite — it should be taught before
    the source.

    Use this endpoint when you need to:
    - Visualize the dependency graph for a curriculum
    - Understand prerequisite relationships between units or sections
    - Build a dependency-aware course planner or sequencing tool

    Args:
        curriculum_id (CurriculumIdENUM): Unique identifier for the resource in Knowledge Graph
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DependencyMapResponse | Error
     """


    return (await asyncio_detailed(
        curriculum_id=curriculum_id,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
