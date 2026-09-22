from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.list_durable_skills_frameworks_response_200 import ListDurableSkillsFrameworksResponse200
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["includeNonCurrent"] = include_non_current

    params["limit"] = limit

    params["cursor"] = cursor


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/durable-skills-frameworks",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListDurableSkillsFrameworksResponse200 | None:
    if response.status_code == 200:
        response_200 = ListDurableSkillsFrameworksResponse200.from_dict(response.json())



        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())



        return response_400

    if response.status_code == 500:
        response_500 = Error.from_dict(response.json())



        return response_500

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListDurableSkillsFrameworksResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListDurableSkillsFrameworksResponse200]:
    """ Durable skills frameworks

     Fetches the list of DurableSkillsFramework objects available in the knowledge graph.

    Durable skills frameworks describe transferable competencies — collaboration, communication,
    critical thinking and similar — rather than subject-area academic content. They are published
    outside the CASE Network, so they carry no CASE identifiers and are addressed by their Knowledge
    Graph `identifier`.

    Use this endpoint when you need to:
    - Discover which durable skills frameworks are available
    - Find the framework `identifier` required by GET /durable-skills
    - Get framework metadata (name, description, publisher, modification dates)

    Retired frameworks are excluded by default. Set `includeNonCurrent=true` to include them.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        include_non_current (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListDurableSkillsFrameworksResponse200]
     """


    kwargs = _get_kwargs(
        include_non_current=include_non_current,
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
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListDurableSkillsFrameworksResponse200 | None:
    """ Durable skills frameworks

     Fetches the list of DurableSkillsFramework objects available in the knowledge graph.

    Durable skills frameworks describe transferable competencies — collaboration, communication,
    critical thinking and similar — rather than subject-area academic content. They are published
    outside the CASE Network, so they carry no CASE identifiers and are addressed by their Knowledge
    Graph `identifier`.

    Use this endpoint when you need to:
    - Discover which durable skills frameworks are available
    - Find the framework `identifier` required by GET /durable-skills
    - Get framework metadata (name, description, publisher, modification dates)

    Retired frameworks are excluded by default. Set `includeNonCurrent=true` to include them.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        include_non_current (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListDurableSkillsFrameworksResponse200
     """


    return sync_detailed(
        client=client,
include_non_current=include_non_current,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListDurableSkillsFrameworksResponse200]:
    """ Durable skills frameworks

     Fetches the list of DurableSkillsFramework objects available in the knowledge graph.

    Durable skills frameworks describe transferable competencies — collaboration, communication,
    critical thinking and similar — rather than subject-area academic content. They are published
    outside the CASE Network, so they carry no CASE identifiers and are addressed by their Knowledge
    Graph `identifier`.

    Use this endpoint when you need to:
    - Discover which durable skills frameworks are available
    - Find the framework `identifier` required by GET /durable-skills
    - Get framework metadata (name, description, publisher, modification dates)

    Retired frameworks are excluded by default. Set `includeNonCurrent=true` to include them.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        include_non_current (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListDurableSkillsFrameworksResponse200]
     """


    kwargs = _get_kwargs(
        include_non_current=include_non_current,
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
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListDurableSkillsFrameworksResponse200 | None:
    """ Durable skills frameworks

     Fetches the list of DurableSkillsFramework objects available in the knowledge graph.

    Durable skills frameworks describe transferable competencies — collaboration, communication,
    critical thinking and similar — rather than subject-area academic content. They are published
    outside the CASE Network, so they carry no CASE identifiers and are addressed by their Knowledge
    Graph `identifier`.

    Use this endpoint when you need to:
    - Discover which durable skills frameworks are available
    - Find the framework `identifier` required by GET /durable-skills
    - Get framework metadata (name, description, publisher, modification dates)

    Retired frameworks are excluded by default. Set `includeNonCurrent=true` to include them.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        include_non_current (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListDurableSkillsFrameworksResponse200
     """


    return (await asyncio_detailed(
        client=client,
include_non_current=include_non_current,
limit=limit,
cursor=cursor,

    )).parsed
