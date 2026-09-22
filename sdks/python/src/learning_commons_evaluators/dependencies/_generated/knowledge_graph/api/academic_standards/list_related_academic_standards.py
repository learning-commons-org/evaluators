from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.list_related_academic_standards_response_200 import ListRelatedAcademicStandardsResponse200
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
        "url": "/academic-standards/{case_identifier_uuid}/related-standards".format(case_identifier_uuid=quote(str(case_identifier_uuid), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListRelatedAcademicStandardsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListRelatedAcademicStandardsResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListRelatedAcademicStandardsResponse200]:
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

) -> Response[Error | ListRelatedAcademicStandardsResponse200]:
    """ Related standards for a standard

     Fetches StandardsFrameworkItems that are related to the specified academic standard through the
    "relatesTo" relationship.

    This endpoint retrieves academic standards that share meaningful conceptual or skill-based links
    with the given academic standard, without implying a specific sequence or prerequisite order. These
    lateral connections highlight associations that can inform instructional design, identify
    reinforcing concepts, or reveal thematic links across academic standards.

    Use this endpoint when you need to:
    - Find academic standards with related content or skills for integrated instruction
    - Identify opportunities for reinforcing concepts across different academic standards
    - Design cross-curricular or thematic units that connect related academic standards
    - Discover alternative pathways or parallel concepts in curriculum planning

    **Note:** Learning progression data is currently based on Student Achievement Partners' Coherence
    Map for Common Core State Standards (CCSS) for Mathematics. Coverage for other subjects and
    frameworks may be limited.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the relatesTo relationship](/knowledge-graph/schema-reference/learning-
    progressions#relatesto)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListRelatedAcademicStandardsResponse200]
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

) -> Error | ListRelatedAcademicStandardsResponse200 | None:
    """ Related standards for a standard

     Fetches StandardsFrameworkItems that are related to the specified academic standard through the
    "relatesTo" relationship.

    This endpoint retrieves academic standards that share meaningful conceptual or skill-based links
    with the given academic standard, without implying a specific sequence or prerequisite order. These
    lateral connections highlight associations that can inform instructional design, identify
    reinforcing concepts, or reveal thematic links across academic standards.

    Use this endpoint when you need to:
    - Find academic standards with related content or skills for integrated instruction
    - Identify opportunities for reinforcing concepts across different academic standards
    - Design cross-curricular or thematic units that connect related academic standards
    - Discover alternative pathways or parallel concepts in curriculum planning

    **Note:** Learning progression data is currently based on Student Achievement Partners' Coherence
    Map for Common Core State Standards (CCSS) for Mathematics. Coverage for other subjects and
    frameworks may be limited.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the relatesTo relationship](/knowledge-graph/schema-reference/learning-
    progressions#relatesto)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListRelatedAcademicStandardsResponse200
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

) -> Response[Error | ListRelatedAcademicStandardsResponse200]:
    """ Related standards for a standard

     Fetches StandardsFrameworkItems that are related to the specified academic standard through the
    "relatesTo" relationship.

    This endpoint retrieves academic standards that share meaningful conceptual or skill-based links
    with the given academic standard, without implying a specific sequence or prerequisite order. These
    lateral connections highlight associations that can inform instructional design, identify
    reinforcing concepts, or reveal thematic links across academic standards.

    Use this endpoint when you need to:
    - Find academic standards with related content or skills for integrated instruction
    - Identify opportunities for reinforcing concepts across different academic standards
    - Design cross-curricular or thematic units that connect related academic standards
    - Discover alternative pathways or parallel concepts in curriculum planning

    **Note:** Learning progression data is currently based on Student Achievement Partners' Coherence
    Map for Common Core State Standards (CCSS) for Mathematics. Coverage for other subjects and
    frameworks may be limited.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the relatesTo relationship](/knowledge-graph/schema-reference/learning-
    progressions#relatesto)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListRelatedAcademicStandardsResponse200]
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

) -> Error | ListRelatedAcademicStandardsResponse200 | None:
    """ Related standards for a standard

     Fetches StandardsFrameworkItems that are related to the specified academic standard through the
    "relatesTo" relationship.

    This endpoint retrieves academic standards that share meaningful conceptual or skill-based links
    with the given academic standard, without implying a specific sequence or prerequisite order. These
    lateral connections highlight associations that can inform instructional design, identify
    reinforcing concepts, or reveal thematic links across academic standards.

    Use this endpoint when you need to:
    - Find academic standards with related content or skills for integrated instruction
    - Identify opportunities for reinforcing concepts across different academic standards
    - Design cross-curricular or thematic units that connect related academic standards
    - Discover alternative pathways or parallel concepts in curriculum planning

    **Note:** Learning progression data is currently based on Student Achievement Partners' Coherence
    Map for Common Core State Standards (CCSS) for Mathematics. Coverage for other subjects and
    frameworks may be limited.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the relatesTo relationship](/knowledge-graph/schema-reference/learning-
    progressions#relatesto)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListRelatedAcademicStandardsResponse200
     """


    return (await asyncio_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
