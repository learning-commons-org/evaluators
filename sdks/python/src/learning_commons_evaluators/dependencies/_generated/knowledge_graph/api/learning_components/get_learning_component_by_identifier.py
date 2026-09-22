from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.learning_component import LearningComponent
from typing import cast



def _get_kwargs(
    identifier: str,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/learning-components/{identifier}".format(identifier=quote(str(identifier), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | LearningComponent | None:
    if response.status_code == 200:
        response_200 = LearningComponent.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | LearningComponent]:
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

) -> Response[Error | LearningComponent]:
    """ Learning component by ID

     Fetches a single LearningComponent by its unique identifier.

    A LearningComponent represents a single, well-defined skill or concept that students are expected to
    learn. Learning components are granular units of learning that break down broad state standards into
    teachable and measurable parts at the level of a lesson, activity, or assessment question.

    Use this endpoint when you need to:
    - Display the full details of a specific learning component
    - Retrieve the skill description and metadata for a known learning component
    - Access attribution information for learning components used in your application

    Learning components(LCs) are developed through expert-driven processes with input from experienced
    educators. Currently, LCs are available for mathematics standards across multiple states, with more
    subjects and states being added over time.

    **Related topics:**
    - [Understanding learning components](/knowledge-graph/schema-reference/learning-components)
    - [LC creation and alignment process](/knowledge-graph/schema-reference/learning-
    components#creation-of-lcs)
    - [Available LC mappings by state](/knowledge-graph/schema-reference/learning-components#current-lc-
    mappings)

    Args:
        identifier (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | LearningComponent]
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

) -> Error | LearningComponent | None:
    """ Learning component by ID

     Fetches a single LearningComponent by its unique identifier.

    A LearningComponent represents a single, well-defined skill or concept that students are expected to
    learn. Learning components are granular units of learning that break down broad state standards into
    teachable and measurable parts at the level of a lesson, activity, or assessment question.

    Use this endpoint when you need to:
    - Display the full details of a specific learning component
    - Retrieve the skill description and metadata for a known learning component
    - Access attribution information for learning components used in your application

    Learning components(LCs) are developed through expert-driven processes with input from experienced
    educators. Currently, LCs are available for mathematics standards across multiple states, with more
    subjects and states being added over time.

    **Related topics:**
    - [Understanding learning components](/knowledge-graph/schema-reference/learning-components)
    - [LC creation and alignment process](/knowledge-graph/schema-reference/learning-
    components#creation-of-lcs)
    - [Available LC mappings by state](/knowledge-graph/schema-reference/learning-components#current-lc-
    mappings)

    Args:
        identifier (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | LearningComponent
     """


    return sync_detailed(
        identifier=identifier,
client=client,

    ).parsed

async def asyncio_detailed(
    identifier: str,
    *,
    client: AuthenticatedClient | Client,

) -> Response[Error | LearningComponent]:
    """ Learning component by ID

     Fetches a single LearningComponent by its unique identifier.

    A LearningComponent represents a single, well-defined skill or concept that students are expected to
    learn. Learning components are granular units of learning that break down broad state standards into
    teachable and measurable parts at the level of a lesson, activity, or assessment question.

    Use this endpoint when you need to:
    - Display the full details of a specific learning component
    - Retrieve the skill description and metadata for a known learning component
    - Access attribution information for learning components used in your application

    Learning components(LCs) are developed through expert-driven processes with input from experienced
    educators. Currently, LCs are available for mathematics standards across multiple states, with more
    subjects and states being added over time.

    **Related topics:**
    - [Understanding learning components](/knowledge-graph/schema-reference/learning-components)
    - [LC creation and alignment process](/knowledge-graph/schema-reference/learning-
    components#creation-of-lcs)
    - [Available LC mappings by state](/knowledge-graph/schema-reference/learning-components#current-lc-
    mappings)

    Args:
        identifier (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | LearningComponent]
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

) -> Error | LearningComponent | None:
    """ Learning component by ID

     Fetches a single LearningComponent by its unique identifier.

    A LearningComponent represents a single, well-defined skill or concept that students are expected to
    learn. Learning components are granular units of learning that break down broad state standards into
    teachable and measurable parts at the level of a lesson, activity, or assessment question.

    Use this endpoint when you need to:
    - Display the full details of a specific learning component
    - Retrieve the skill description and metadata for a known learning component
    - Access attribution information for learning components used in your application

    Learning components(LCs) are developed through expert-driven processes with input from experienced
    educators. Currently, LCs are available for mathematics standards across multiple states, with more
    subjects and states being added over time.

    **Related topics:**
    - [Understanding learning components](/knowledge-graph/schema-reference/learning-components)
    - [LC creation and alignment process](/knowledge-graph/schema-reference/learning-
    components#creation-of-lcs)
    - [Available LC mappings by state](/knowledge-graph/schema-reference/learning-components#current-lc-
    mappings)

    Args:
        identifier (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | LearningComponent
     """


    return (await asyncio_detailed(
        identifier=identifier,
client=client,

    )).parsed
