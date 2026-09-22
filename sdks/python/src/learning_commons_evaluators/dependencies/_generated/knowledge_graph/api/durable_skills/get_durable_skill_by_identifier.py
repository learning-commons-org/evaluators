from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.durable_skill import DurableSkill
from ...models.error import Error
from typing import cast



def _get_kwargs(
    identifier: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/durable-skills/{identifier}".format(identifier=quote(str(identifier), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> DurableSkill | Error | None:
    if response.status_code == 200:
        response_200 = DurableSkill.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[DurableSkill | Error]:
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

) -> Response[DurableSkill | Error]:
    """ Durable skill by ID

     Fetches a single DurableSkill by its Knowledge Graph identifier.

    Use this endpoint when you need to:
    - Retrieve the full details of a specific durable skill
    - Resolve an identifier returned by GET /durable-skills or the search endpoint

    Framework identifiers are not valid here — use GET /durable-skills-frameworks for frameworks.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        identifier (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DurableSkill | Error]
     """


    kwargs = _get_kwargs(
        identifier=identifier,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    identifier: str,
    *,
    client: AuthenticatedClient | Client,

) -> DurableSkill | Error | None:
    """ Durable skill by ID

     Fetches a single DurableSkill by its Knowledge Graph identifier.

    Use this endpoint when you need to:
    - Retrieve the full details of a specific durable skill
    - Resolve an identifier returned by GET /durable-skills or the search endpoint

    Framework identifiers are not valid here — use GET /durable-skills-frameworks for frameworks.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        identifier (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DurableSkill | Error
     """


    return sync_detailed(
        identifier=identifier,
client=client,

    ).parsed

async def asyncio_detailed(
    identifier: str,
    *,
    client: AuthenticatedClient | Client,

) -> Response[DurableSkill | Error]:
    """ Durable skill by ID

     Fetches a single DurableSkill by its Knowledge Graph identifier.

    Use this endpoint when you need to:
    - Retrieve the full details of a specific durable skill
    - Resolve an identifier returned by GET /durable-skills or the search endpoint

    Framework identifiers are not valid here — use GET /durable-skills-frameworks for frameworks.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        identifier (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DurableSkill | Error]
     """


    kwargs = _get_kwargs(
        identifier=identifier,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    identifier: str,
    *,
    client: AuthenticatedClient | Client,

) -> DurableSkill | Error | None:
    """ Durable skill by ID

     Fetches a single DurableSkill by its Knowledge Graph identifier.

    Use this endpoint when you need to:
    - Retrieve the full details of a specific durable skill
    - Resolve an identifier returned by GET /durable-skills or the search endpoint

    Framework identifiers are not valid here — use GET /durable-skills-frameworks for frameworks.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        identifier (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DurableSkill | Error
     """


    return (await asyncio_detailed(
        identifier=identifier,
client=client,

    )).parsed
