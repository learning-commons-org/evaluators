from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.list_durable_skills_response_200 import ListDurableSkillsResponse200
from ...models.normalized_statement_type_enum import NormalizedStatementTypeENUM
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    framework_identifier: str,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["frameworkIdentifier"] = framework_identifier

    json_normalized_statement_type: str | Unset = UNSET
    if not isinstance(normalized_statement_type, Unset):
        json_normalized_statement_type = normalized_statement_type.value

    params["normalizedStatementType"] = json_normalized_statement_type

    params["limit"] = limit

    params["cursor"] = cursor


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/durable-skills",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListDurableSkillsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListDurableSkillsResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListDurableSkillsResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    framework_identifier: str,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListDurableSkillsResponse200]:
    """ Durable skills in a framework

     Fetches a list of DurableSkill objects within a specific durable skills framework.

    Returns every item in the framework's hierarchy, from top-level skills through to the most granular
    progression levels. Use `normalizedStatementType` to retrieve only skill statements and exclude the
    organizational groupings that structure them.

    Use this endpoint when you need to:
    - Retrieve the full contents of a durable skills framework
    - Export a framework's skills for mapping to your own content
    - Browse a framework's structure before navigating it with /durable-skills/{identifier}/children

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        framework_identifier (str):
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListDurableSkillsResponse200]
     """


    kwargs = _get_kwargs(
        framework_identifier=framework_identifier,
normalized_statement_type=normalized_statement_type,
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
    framework_identifier: str,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListDurableSkillsResponse200 | None:
    """ Durable skills in a framework

     Fetches a list of DurableSkill objects within a specific durable skills framework.

    Returns every item in the framework's hierarchy, from top-level skills through to the most granular
    progression levels. Use `normalizedStatementType` to retrieve only skill statements and exclude the
    organizational groupings that structure them.

    Use this endpoint when you need to:
    - Retrieve the full contents of a durable skills framework
    - Export a framework's skills for mapping to your own content
    - Browse a framework's structure before navigating it with /durable-skills/{identifier}/children

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        framework_identifier (str):
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListDurableSkillsResponse200
     """


    return sync_detailed(
        client=client,
framework_identifier=framework_identifier,
normalized_statement_type=normalized_statement_type,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    framework_identifier: str,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListDurableSkillsResponse200]:
    """ Durable skills in a framework

     Fetches a list of DurableSkill objects within a specific durable skills framework.

    Returns every item in the framework's hierarchy, from top-level skills through to the most granular
    progression levels. Use `normalizedStatementType` to retrieve only skill statements and exclude the
    organizational groupings that structure them.

    Use this endpoint when you need to:
    - Retrieve the full contents of a durable skills framework
    - Export a framework's skills for mapping to your own content
    - Browse a framework's structure before navigating it with /durable-skills/{identifier}/children

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        framework_identifier (str):
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListDurableSkillsResponse200]
     """


    kwargs = _get_kwargs(
        framework_identifier=framework_identifier,
normalized_statement_type=normalized_statement_type,
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
    framework_identifier: str,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListDurableSkillsResponse200 | None:
    """ Durable skills in a framework

     Fetches a list of DurableSkill objects within a specific durable skills framework.

    Returns every item in the framework's hierarchy, from top-level skills through to the most granular
    progression levels. Use `normalizedStatementType` to retrieve only skill statements and exclude the
    organizational groupings that structure them.

    Use this endpoint when you need to:
    - Retrieve the full contents of a durable skills framework
    - Export a framework's skills for mapping to your own content
    - Browse a framework's structure before navigating it with /durable-skills/{identifier}/children

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        framework_identifier (str):
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListDurableSkillsResponse200
     """


    return (await asyncio_detailed(
        client=client,
framework_identifier=framework_identifier,
normalized_statement_type=normalized_statement_type,
limit=limit,
cursor=cursor,

    )).parsed
