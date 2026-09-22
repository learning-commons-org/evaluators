from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.get_standard_assessments_response_200 import GetStandardAssessmentsResponse200
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
        "url": "/academic-standards/{case_identifier_uuid}/assessments".format(case_identifier_uuid=quote(str(case_identifier_uuid), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | GetStandardAssessmentsResponse200 | None:
    if response.status_code == 200:
        response_200 = GetStandardAssessmentsResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | GetStandardAssessmentsResponse200]:
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

) -> Response[Error | GetStandardAssessmentsResponse200]:
    """ Assessments for a standard

     Fetches summary information for all assessments that evaluate a specific academic standard.

    Returns assessment summaries (identifier, name) that are aligned to this standard, indicating which
    assessments measure student achievement of this learning expectation.

    Use this endpoint when you need to:
    - Find all assessments that evaluate a specific standard
    - Build standards-based assessment systems
    - Track which standards are assessed
    - Generate assessment coverage reports

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetStandardAssessmentsResponse200]
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

) -> Error | GetStandardAssessmentsResponse200 | None:
    """ Assessments for a standard

     Fetches summary information for all assessments that evaluate a specific academic standard.

    Returns assessment summaries (identifier, name) that are aligned to this standard, indicating which
    assessments measure student achievement of this learning expectation.

    Use this endpoint when you need to:
    - Find all assessments that evaluate a specific standard
    - Build standards-based assessment systems
    - Track which standards are assessed
    - Generate assessment coverage reports

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetStandardAssessmentsResponse200
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

) -> Response[Error | GetStandardAssessmentsResponse200]:
    """ Assessments for a standard

     Fetches summary information for all assessments that evaluate a specific academic standard.

    Returns assessment summaries (identifier, name) that are aligned to this standard, indicating which
    assessments measure student achievement of this learning expectation.

    Use this endpoint when you need to:
    - Find all assessments that evaluate a specific standard
    - Build standards-based assessment systems
    - Track which standards are assessed
    - Generate assessment coverage reports

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetStandardAssessmentsResponse200]
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

) -> Error | GetStandardAssessmentsResponse200 | None:
    """ Assessments for a standard

     Fetches summary information for all assessments that evaluate a specific academic standard.

    Returns assessment summaries (identifier, name) that are aligned to this standard, indicating which
    assessments measure student achievement of this learning expectation.

    Use this endpoint when you need to:
    - Find all assessments that evaluate a specific standard
    - Build standards-based assessment systems
    - Track which standards are assessed
    - Generate assessment coverage reports

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetStandardAssessmentsResponse200
     """


    return (await asyncio_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
