from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.list_child_durable_skills_response_200 import ListChildDurableSkillsResponse200
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    identifier: str,
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
        "url": "/durable-skills/{identifier}/children".format(identifier=quote(str(identifier), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListChildDurableSkillsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListChildDurableSkillsResponse200.from_dict(response.json())



        return response_200

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListChildDurableSkillsResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    identifier: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListChildDurableSkillsResponse200]:
    """ Children of a durable skill

     Fetches the direct children of a durable skill through the "hasChild" relationship.

    Durable skills frameworks are hierarchical, and this endpoint walks one level at a time. Check the
    parent's `hasChildren` flag before calling to avoid requests that return empty pages.

    Use this endpoint when you need to:
    - Navigate a framework's hierarchy one level at a time
    - Retrieve the progression levels beneath a skill
    - Build an expandable tree view of a framework

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        identifier (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListChildDurableSkillsResponse200]
     """


    kwargs = _get_kwargs(
        identifier=identifier,
limit=limit,
cursor=cursor,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    identifier: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListChildDurableSkillsResponse200 | None:
    """ Children of a durable skill

     Fetches the direct children of a durable skill through the "hasChild" relationship.

    Durable skills frameworks are hierarchical, and this endpoint walks one level at a time. Check the
    parent's `hasChildren` flag before calling to avoid requests that return empty pages.

    Use this endpoint when you need to:
    - Navigate a framework's hierarchy one level at a time
    - Retrieve the progression levels beneath a skill
    - Build an expandable tree view of a framework

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        identifier (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListChildDurableSkillsResponse200
     """


    return sync_detailed(
        identifier=identifier,
client=client,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    identifier: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListChildDurableSkillsResponse200]:
    """ Children of a durable skill

     Fetches the direct children of a durable skill through the "hasChild" relationship.

    Durable skills frameworks are hierarchical, and this endpoint walks one level at a time. Check the
    parent's `hasChildren` flag before calling to avoid requests that return empty pages.

    Use this endpoint when you need to:
    - Navigate a framework's hierarchy one level at a time
    - Retrieve the progression levels beneath a skill
    - Build an expandable tree view of a framework

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        identifier (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListChildDurableSkillsResponse200]
     """


    kwargs = _get_kwargs(
        identifier=identifier,
limit=limit,
cursor=cursor,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    identifier: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListChildDurableSkillsResponse200 | None:
    """ Children of a durable skill

     Fetches the direct children of a durable skill through the "hasChild" relationship.

    Durable skills frameworks are hierarchical, and this endpoint walks one level at a time. Check the
    parent's `hasChildren` flag before calling to avoid requests that return empty pages.

    Use this endpoint when you need to:
    - Navigate a framework's hierarchy one level at a time
    - Retrieve the progression levels beneath a skill
    - Build an expandable tree view of a framework

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        identifier (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListChildDurableSkillsResponse200
     """


    return (await asyncio_detailed(
        identifier=identifier,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
