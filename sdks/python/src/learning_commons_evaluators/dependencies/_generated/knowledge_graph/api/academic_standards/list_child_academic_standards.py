from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.list_child_academic_standards_response_200 import ListChildAcademicStandardsResponse200
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
        "url": "/academic-standards/{case_identifier_uuid}/children".format(case_identifier_uuid=quote(str(case_identifier_uuid), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListChildAcademicStandardsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListChildAcademicStandardsResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListChildAcademicStandardsResponse200]:
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

) -> Response[Error | ListChildAcademicStandardsResponse200]:
    """ Children of a standard

     Fetches StandardsFrameworkItems that are direct children of the specified academic standard through
    the "hasChild" relationship.

    This endpoint retrieves academic standards that are hierarchically organized under the given
    academic standard. This allows you to navigate down the standards framework hierarchy from domains
    to clusters to individual academic standards, or from any parent grouping to its children.

    Use this endpoint when you need to:
    - Navigate down the standards framework hierarchy (e.g., from domain to academic standards)
    - Get all academic standards within a specific grouping or cluster
    - Build tree visualizations of standards framework structures
    - Explore the organizational structure of a standards document

    **Note:** This returns direct children only, not all descendants. To get all descendants, you'll
    need to traverse multiple levels.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the hasChild relationship](/knowledge-graph/schema-reference/standards#haschild)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListChildAcademicStandardsResponse200]
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

) -> Error | ListChildAcademicStandardsResponse200 | None:
    """ Children of a standard

     Fetches StandardsFrameworkItems that are direct children of the specified academic standard through
    the "hasChild" relationship.

    This endpoint retrieves academic standards that are hierarchically organized under the given
    academic standard. This allows you to navigate down the standards framework hierarchy from domains
    to clusters to individual academic standards, or from any parent grouping to its children.

    Use this endpoint when you need to:
    - Navigate down the standards framework hierarchy (e.g., from domain to academic standards)
    - Get all academic standards within a specific grouping or cluster
    - Build tree visualizations of standards framework structures
    - Explore the organizational structure of a standards document

    **Note:** This returns direct children only, not all descendants. To get all descendants, you'll
    need to traverse multiple levels.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the hasChild relationship](/knowledge-graph/schema-reference/standards#haschild)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListChildAcademicStandardsResponse200
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

) -> Response[Error | ListChildAcademicStandardsResponse200]:
    """ Children of a standard

     Fetches StandardsFrameworkItems that are direct children of the specified academic standard through
    the "hasChild" relationship.

    This endpoint retrieves academic standards that are hierarchically organized under the given
    academic standard. This allows you to navigate down the standards framework hierarchy from domains
    to clusters to individual academic standards, or from any parent grouping to its children.

    Use this endpoint when you need to:
    - Navigate down the standards framework hierarchy (e.g., from domain to academic standards)
    - Get all academic standards within a specific grouping or cluster
    - Build tree visualizations of standards framework structures
    - Explore the organizational structure of a standards document

    **Note:** This returns direct children only, not all descendants. To get all descendants, you'll
    need to traverse multiple levels.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the hasChild relationship](/knowledge-graph/schema-reference/standards#haschild)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListChildAcademicStandardsResponse200]
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

) -> Error | ListChildAcademicStandardsResponse200 | None:
    """ Children of a standard

     Fetches StandardsFrameworkItems that are direct children of the specified academic standard through
    the "hasChild" relationship.

    This endpoint retrieves academic standards that are hierarchically organized under the given
    academic standard. This allows you to navigate down the standards framework hierarchy from domains
    to clusters to individual academic standards, or from any parent grouping to its children.

    Use this endpoint when you need to:
    - Navigate down the standards framework hierarchy (e.g., from domain to academic standards)
    - Get all academic standards within a specific grouping or cluster
    - Build tree visualizations of standards framework structures
    - Explore the organizational structure of a standards document

    **Note:** This returns direct children only, not all descendants. To get all descendants, you'll
    need to traverse multiple levels.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the hasChild relationship](/knowledge-graph/schema-reference/standards#haschild)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListChildAcademicStandardsResponse200
     """


    return (await asyncio_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
