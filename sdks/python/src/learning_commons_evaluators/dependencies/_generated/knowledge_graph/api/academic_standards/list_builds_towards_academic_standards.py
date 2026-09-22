from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.list_builds_towards_academic_standards_response_200 import ListBuildsTowardsAcademicStandardsResponse200
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
        "url": "/academic-standards/{case_identifier_uuid}/builds-towards".format(case_identifier_uuid=quote(str(case_identifier_uuid), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListBuildsTowardsAcademicStandardsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListBuildsTowardsAcademicStandardsResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListBuildsTowardsAcademicStandardsResponse200]:
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

) -> Response[Error | ListBuildsTowardsAcademicStandardsResponse200]:
    """ Standards a standard builds towards

     Fetches the StandardsFrameworkItems that the specified academic standard builds **towards** via the
    "buildsTowards" relationship - the standards it is a prerequisite of.

    These are the next logical learning steps or more advanced concepts that students can progress to
    after working with the given academic standard (the given standard `buildsTowards` each of them).
    Proficiency in the given academic standard supports the likelihood of success in these standards.

    Use this endpoint when you need to:
    - Identify next steps in a learning progression after students master an academic standard
    - Design curriculum sequences that build on foundational skills
    - Map forward through learning pathways to understand where academic standards lead
    - Plan long-term instructional trajectories for students

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
        Response[Error | ListBuildsTowardsAcademicStandardsResponse200]
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

) -> Error | ListBuildsTowardsAcademicStandardsResponse200 | None:
    """ Standards a standard builds towards

     Fetches the StandardsFrameworkItems that the specified academic standard builds **towards** via the
    "buildsTowards" relationship - the standards it is a prerequisite of.

    These are the next logical learning steps or more advanced concepts that students can progress to
    after working with the given academic standard (the given standard `buildsTowards` each of them).
    Proficiency in the given academic standard supports the likelihood of success in these standards.

    Use this endpoint when you need to:
    - Identify next steps in a learning progression after students master an academic standard
    - Design curriculum sequences that build on foundational skills
    - Map forward through learning pathways to understand where academic standards lead
    - Plan long-term instructional trajectories for students

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
        Error | ListBuildsTowardsAcademicStandardsResponse200
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

) -> Response[Error | ListBuildsTowardsAcademicStandardsResponse200]:
    """ Standards a standard builds towards

     Fetches the StandardsFrameworkItems that the specified academic standard builds **towards** via the
    "buildsTowards" relationship - the standards it is a prerequisite of.

    These are the next logical learning steps or more advanced concepts that students can progress to
    after working with the given academic standard (the given standard `buildsTowards` each of them).
    Proficiency in the given academic standard supports the likelihood of success in these standards.

    Use this endpoint when you need to:
    - Identify next steps in a learning progression after students master an academic standard
    - Design curriculum sequences that build on foundational skills
    - Map forward through learning pathways to understand where academic standards lead
    - Plan long-term instructional trajectories for students

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
        Response[Error | ListBuildsTowardsAcademicStandardsResponse200]
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

) -> Error | ListBuildsTowardsAcademicStandardsResponse200 | None:
    """ Standards a standard builds towards

     Fetches the StandardsFrameworkItems that the specified academic standard builds **towards** via the
    "buildsTowards" relationship - the standards it is a prerequisite of.

    These are the next logical learning steps or more advanced concepts that students can progress to
    after working with the given academic standard (the given standard `buildsTowards` each of them).
    Proficiency in the given academic standard supports the likelihood of success in these standards.

    Use this endpoint when you need to:
    - Identify next steps in a learning progression after students master an academic standard
    - Design curriculum sequences that build on foundational skills
    - Map forward through learning pathways to understand where academic standards lead
    - Plan long-term instructional trajectories for students

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
        Error | ListBuildsTowardsAcademicStandardsResponse200
     """


    return (await asyncio_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
