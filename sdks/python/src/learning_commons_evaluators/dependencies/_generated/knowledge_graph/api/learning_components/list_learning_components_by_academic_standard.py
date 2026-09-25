from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.list_learning_components_by_academic_standard_response_200 import ListLearningComponentsByAcademicStandardResponse200
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    case_identifier_uuid: UUID,
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
        "url": "/academic-standards/{case_identifier_uuid}/learning-components".format(case_identifier_uuid=quote(str(case_identifier_uuid), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListLearningComponentsByAcademicStandardResponse200 | None:
    if response.status_code == 200:
        response_200 = ListLearningComponentsByAcademicStandardResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListLearningComponentsByAcademicStandardResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    case_identifier_uuid: UUID,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListLearningComponentsByAcademicStandardResponse200]:
    """ Learning components for a standard

     Fetches a list of LearningComponents that support a specific StandardsFrameworkItem.

    This endpoint retrieves all learning components that are aligned to a given academic standard
    through the "supports" relationship. Learning components break down broad academic standards into
    granular, teachable skills, making them actionable for lesson planning and assessment design.

    Use this endpoint when you need to:
    - Find the specific skills that compose a given academic standard
    - Identify granular learning targets for instruction aligned to an academic standard
    - Map learning components to your curriculum or assessment items
    - Understand how a broad academic standard breaks down into teachable units

    **Note:** Learning component alignments are currently available primarily for Mathematics academic
    standards. Academic standards in other subjects or certain special categories (e.g., Standards for
    Mathematical Practice, Pre-K, advanced math) may not have LC alignments.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the supports relationship](/knowledge-graph/schema-reference/learning-
    components#supports)
    - [LC alignment methodology](/knowledge-graph/schema-reference/learning-components#creation-of-lcs)
    - [Available LC coverage by state](/knowledge-graph/schema-reference/learning-components#current-lc-
    mappings)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListLearningComponentsByAcademicStandardResponse200]
     """


    kwargs = _get_kwargs(
        case_identifier_uuid=case_identifier_uuid,
limit=limit,
cursor=cursor,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    case_identifier_uuid: UUID,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListLearningComponentsByAcademicStandardResponse200 | None:
    """ Learning components for a standard

     Fetches a list of LearningComponents that support a specific StandardsFrameworkItem.

    This endpoint retrieves all learning components that are aligned to a given academic standard
    through the "supports" relationship. Learning components break down broad academic standards into
    granular, teachable skills, making them actionable for lesson planning and assessment design.

    Use this endpoint when you need to:
    - Find the specific skills that compose a given academic standard
    - Identify granular learning targets for instruction aligned to an academic standard
    - Map learning components to your curriculum or assessment items
    - Understand how a broad academic standard breaks down into teachable units

    **Note:** Learning component alignments are currently available primarily for Mathematics academic
    standards. Academic standards in other subjects or certain special categories (e.g., Standards for
    Mathematical Practice, Pre-K, advanced math) may not have LC alignments.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the supports relationship](/knowledge-graph/schema-reference/learning-
    components#supports)
    - [LC alignment methodology](/knowledge-graph/schema-reference/learning-components#creation-of-lcs)
    - [Available LC coverage by state](/knowledge-graph/schema-reference/learning-components#current-lc-
    mappings)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListLearningComponentsByAcademicStandardResponse200
     """


    return sync_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    case_identifier_uuid: UUID,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListLearningComponentsByAcademicStandardResponse200]:
    """ Learning components for a standard

     Fetches a list of LearningComponents that support a specific StandardsFrameworkItem.

    This endpoint retrieves all learning components that are aligned to a given academic standard
    through the "supports" relationship. Learning components break down broad academic standards into
    granular, teachable skills, making them actionable for lesson planning and assessment design.

    Use this endpoint when you need to:
    - Find the specific skills that compose a given academic standard
    - Identify granular learning targets for instruction aligned to an academic standard
    - Map learning components to your curriculum or assessment items
    - Understand how a broad academic standard breaks down into teachable units

    **Note:** Learning component alignments are currently available primarily for Mathematics academic
    standards. Academic standards in other subjects or certain special categories (e.g., Standards for
    Mathematical Practice, Pre-K, advanced math) may not have LC alignments.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the supports relationship](/knowledge-graph/schema-reference/learning-
    components#supports)
    - [LC alignment methodology](/knowledge-graph/schema-reference/learning-components#creation-of-lcs)
    - [Available LC coverage by state](/knowledge-graph/schema-reference/learning-components#current-lc-
    mappings)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListLearningComponentsByAcademicStandardResponse200]
     """


    kwargs = _get_kwargs(
        case_identifier_uuid=case_identifier_uuid,
limit=limit,
cursor=cursor,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    case_identifier_uuid: UUID,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListLearningComponentsByAcademicStandardResponse200 | None:
    """ Learning components for a standard

     Fetches a list of LearningComponents that support a specific StandardsFrameworkItem.

    This endpoint retrieves all learning components that are aligned to a given academic standard
    through the "supports" relationship. Learning components break down broad academic standards into
    granular, teachable skills, making them actionable for lesson planning and assessment design.

    Use this endpoint when you need to:
    - Find the specific skills that compose a given academic standard
    - Identify granular learning targets for instruction aligned to an academic standard
    - Map learning components to your curriculum or assessment items
    - Understand how a broad academic standard breaks down into teachable units

    **Note:** Learning component alignments are currently available primarily for Mathematics academic
    standards. Academic standards in other subjects or certain special categories (e.g., Standards for
    Mathematical Practice, Pre-K, advanced math) may not have LC alignments.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the supports relationship](/knowledge-graph/schema-reference/learning-
    components#supports)
    - [LC alignment methodology](/knowledge-graph/schema-reference/learning-components#creation-of-lcs)
    - [Available LC coverage by state](/knowledge-graph/schema-reference/learning-components#current-lc-
    mappings)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListLearningComponentsByAcademicStandardResponse200
     """


    return (await asyncio_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
