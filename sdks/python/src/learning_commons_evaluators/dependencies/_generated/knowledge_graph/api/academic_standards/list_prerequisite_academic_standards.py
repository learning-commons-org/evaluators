from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.list_prerequisite_academic_standards_response_200 import ListPrerequisiteAcademicStandardsResponse200
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
        "url": "/academic-standards/{case_identifier_uuid}/prerequisites".format(case_identifier_uuid=quote(str(case_identifier_uuid), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListPrerequisiteAcademicStandardsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListPrerequisiteAcademicStandardsResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListPrerequisiteAcademicStandardsResponse200]:
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

) -> Response[Error | ListPrerequisiteAcademicStandardsResponse200]:
    """ Prerequisites for a standard

     Fetches the prerequisite StandardsFrameworkItems for the specified academic standard - the
    foundational standards it builds **from** via the "buildsTowards" relationship.

    These are the foundational skills or concepts that contribute to mastery of the given academic
    standard (each prerequisite `buildsTowards` the given standard). The relationship is directional but
    does not require strict prerequisite order - students don't need to fully master prerequisites
    before engaging with the given academic standard.

    Use this endpoint when you need to:
    - Identify foundational academic standards students should be familiar with before tackling a target
    academic standard
    - Trace backward through a learning progression to understand dependencies
    - Design remediation or review activities based on prerequisite skills
    - Map out a coherent learning pathway for students

    **Note:** Learning progression data is currently based on Student Achievement Partners' Coherence
    Map for Common Core State Standards (CCSS) for Mathematics. Coverage for other subjects and
    frameworks may be limited.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the buildsTowards relationship](/knowledge-graph/schema-reference/learning-
    progressions#buildstowards)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListPrerequisiteAcademicStandardsResponse200]
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

) -> Error | ListPrerequisiteAcademicStandardsResponse200 | None:
    """ Prerequisites for a standard

     Fetches the prerequisite StandardsFrameworkItems for the specified academic standard - the
    foundational standards it builds **from** via the "buildsTowards" relationship.

    These are the foundational skills or concepts that contribute to mastery of the given academic
    standard (each prerequisite `buildsTowards` the given standard). The relationship is directional but
    does not require strict prerequisite order - students don't need to fully master prerequisites
    before engaging with the given academic standard.

    Use this endpoint when you need to:
    - Identify foundational academic standards students should be familiar with before tackling a target
    academic standard
    - Trace backward through a learning progression to understand dependencies
    - Design remediation or review activities based on prerequisite skills
    - Map out a coherent learning pathway for students

    **Note:** Learning progression data is currently based on Student Achievement Partners' Coherence
    Map for Common Core State Standards (CCSS) for Mathematics. Coverage for other subjects and
    frameworks may be limited.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the buildsTowards relationship](/knowledge-graph/schema-reference/learning-
    progressions#buildstowards)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListPrerequisiteAcademicStandardsResponse200
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

) -> Response[Error | ListPrerequisiteAcademicStandardsResponse200]:
    """ Prerequisites for a standard

     Fetches the prerequisite StandardsFrameworkItems for the specified academic standard - the
    foundational standards it builds **from** via the "buildsTowards" relationship.

    These are the foundational skills or concepts that contribute to mastery of the given academic
    standard (each prerequisite `buildsTowards` the given standard). The relationship is directional but
    does not require strict prerequisite order - students don't need to fully master prerequisites
    before engaging with the given academic standard.

    Use this endpoint when you need to:
    - Identify foundational academic standards students should be familiar with before tackling a target
    academic standard
    - Trace backward through a learning progression to understand dependencies
    - Design remediation or review activities based on prerequisite skills
    - Map out a coherent learning pathway for students

    **Note:** Learning progression data is currently based on Student Achievement Partners' Coherence
    Map for Common Core State Standards (CCSS) for Mathematics. Coverage for other subjects and
    frameworks may be limited.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the buildsTowards relationship](/knowledge-graph/schema-reference/learning-
    progressions#buildstowards)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListPrerequisiteAcademicStandardsResponse200]
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

) -> Error | ListPrerequisiteAcademicStandardsResponse200 | None:
    """ Prerequisites for a standard

     Fetches the prerequisite StandardsFrameworkItems for the specified academic standard - the
    foundational standards it builds **from** via the "buildsTowards" relationship.

    These are the foundational skills or concepts that contribute to mastery of the given academic
    standard (each prerequisite `buildsTowards` the given standard). The relationship is directional but
    does not require strict prerequisite order - students don't need to fully master prerequisites
    before engaging with the given academic standard.

    Use this endpoint when you need to:
    - Identify foundational academic standards students should be familiar with before tackling a target
    academic standard
    - Trace backward through a learning progression to understand dependencies
    - Design remediation or review activities based on prerequisite skills
    - Map out a coherent learning pathway for students

    **Note:** Learning progression data is currently based on Student Achievement Partners' Coherence
    Map for Common Core State Standards (CCSS) for Mathematics. Coverage for other subjects and
    frameworks may be limited.

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Understanding the buildsTowards relationship](/knowledge-graph/schema-reference/learning-
    progressions#buildstowards)

    Args:
        case_identifier_uuid (UUID):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListPrerequisiteAcademicStandardsResponse200
     """


    return (await asyncio_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
