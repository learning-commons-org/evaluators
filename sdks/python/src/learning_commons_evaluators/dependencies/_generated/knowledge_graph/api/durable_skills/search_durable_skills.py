from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.durable_skill_search_result import DurableSkillSearchResult
from ...models.error import Error
from ...models.normalized_statement_type_enum import NormalizedStatementTypeENUM
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    params["query"] = query

    params["statementCode"] = statement_code

    json_normalized_statement_type: str | Unset = UNSET
    if not isinstance(normalized_statement_type, Unset):
        json_normalized_statement_type = normalized_statement_type.value

    params["normalizedStatementType"] = json_normalized_statement_type

    params["limit"] = limit


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/durable-skills/search",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | list[DurableSkillSearchResult] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = DurableSkillSearchResult.from_dict(response_200_item_data)



            response_200.append(response_200_item)

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | list[DurableSkillSearchResult]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Response[Error | list[DurableSkillSearchResult]]:
    """ Search durable skills

     Searches for DurableSkill objects by semantic similarity or by exact statement code.

    Provide exactly one of `query` or `statementCode`. Semantic search ranks results by relevance to the
    query text and returns a `score` reflecting vector similarity. Statement code search performs an
    exact, case-insensitive match and returns a score of 1.0.

    Use this endpoint when you need to:
    - Find durable skills relevant to a teaching goal or observed behaviour
    - Look up a specific skill by the code used in framework documentation
    - Discover skills to map to your own content or assessments

    Semantic search covers all durable skills frameworks.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        query (str | Unset):
        statement_code (str | Unset):
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | list[DurableSkillSearchResult]]
     """


    kwargs = _get_kwargs(
        query=query,
statement_code=statement_code,
normalized_statement_type=normalized_statement_type,
limit=limit,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Error | list[DurableSkillSearchResult] | None:
    """ Search durable skills

     Searches for DurableSkill objects by semantic similarity or by exact statement code.

    Provide exactly one of `query` or `statementCode`. Semantic search ranks results by relevance to the
    query text and returns a `score` reflecting vector similarity. Statement code search performs an
    exact, case-insensitive match and returns a score of 1.0.

    Use this endpoint when you need to:
    - Find durable skills relevant to a teaching goal or observed behaviour
    - Look up a specific skill by the code used in framework documentation
    - Discover skills to map to your own content or assessments

    Semantic search covers all durable skills frameworks.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        query (str | Unset):
        statement_code (str | Unset):
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | list[DurableSkillSearchResult]
     """


    return sync_detailed(
        client=client,
query=query,
statement_code=statement_code,
normalized_statement_type=normalized_statement_type,
limit=limit,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Response[Error | list[DurableSkillSearchResult]]:
    """ Search durable skills

     Searches for DurableSkill objects by semantic similarity or by exact statement code.

    Provide exactly one of `query` or `statementCode`. Semantic search ranks results by relevance to the
    query text and returns a `score` reflecting vector similarity. Statement code search performs an
    exact, case-insensitive match and returns a score of 1.0.

    Use this endpoint when you need to:
    - Find durable skills relevant to a teaching goal or observed behaviour
    - Look up a specific skill by the code used in framework documentation
    - Discover skills to map to your own content or assessments

    Semantic search covers all durable skills frameworks.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        query (str | Unset):
        statement_code (str | Unset):
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | list[DurableSkillSearchResult]]
     """


    kwargs = _get_kwargs(
        query=query,
statement_code=statement_code,
normalized_statement_type=normalized_statement_type,
limit=limit,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    query: str | Unset = UNSET,
    statement_code: str | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 5,

) -> Error | list[DurableSkillSearchResult] | None:
    """ Search durable skills

     Searches for DurableSkill objects by semantic similarity or by exact statement code.

    Provide exactly one of `query` or `statementCode`. Semantic search ranks results by relevance to the
    query text and returns a `score` reflecting vector similarity. Statement code search performs an
    exact, case-insensitive match and returns a score of 1.0.

    Use this endpoint when you need to:
    - Find durable skills relevant to a teaching goal or observed behaviour
    - Look up a specific skill by the code used in framework documentation
    - Discover skills to map to your own content or assessments

    Semantic search covers all durable skills frameworks.

    **Related topics:**
    - [XQ Competencies](/knowledge-graph/datasets/standards/xq-competencies)
    - [Carnegie Skills Progressions](/knowledge-graph/datasets/standards/carnegie-skills-progressions)

    Args:
        query (str | Unset):
        statement_code (str | Unset):
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 5.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | list[DurableSkillSearchResult]
     """


    return (await asyncio_detailed(
        client=client,
query=query,
statement_code=statement_code,
normalized_statement_type=normalized_statement_type,
limit=limit,

    )).parsed
