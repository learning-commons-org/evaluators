from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.academic_subject_enum import AcademicSubjectENUM
from ...models.adoption_status_enum import AdoptionStatusENUM
from ...models.error import Error
from ...models.jurisdiction_enum import JurisdictionENUM
from ...models.list_frameworks_response_200 import ListFrameworksResponse200
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    adoption_status: AdoptionStatusENUM | Unset = UNSET,
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_jurisdiction: str | Unset = UNSET
    if not isinstance(jurisdiction, Unset):
        json_jurisdiction = jurisdiction.value

    params["jurisdiction"] = json_jurisdiction

    json_academic_subject: str | Unset = UNSET
    if not isinstance(academic_subject, Unset):
        json_academic_subject = academic_subject.value

    params["academicSubject"] = json_academic_subject

    json_adoption_status: str | Unset = UNSET
    if not isinstance(adoption_status, Unset):
        json_adoption_status = adoption_status.value

    params["adoptionStatus"] = json_adoption_status

    params["includeNonCurrent"] = include_non_current

    params["limit"] = limit

    params["cursor"] = cursor


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/standards-frameworks",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListFrameworksResponse200 | None:
    if response.status_code == 200:
        response_200 = ListFrameworksResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListFrameworksResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    adoption_status: AdoptionStatusENUM | Unset = UNSET,
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListFrameworksResponse200]:
    """ Standards frameworks

     Fetches a list of StandardsFramework objects representing complete academic standards documents.
    Each standards framework represents a complete standards document published by an official body like
    a state department of education.
    This endpoint allows you to discover available standards frameworks and retrieve metadata about
    standards documents from different jurisdictions, subjects, and adoption statuses.

    Use this endpoint when you need to:
    - Discover available standards frameworks to query academic standards from
    - Find standards framework UUIDs needed for the GET /academic-standards endpoint
    - Browse standards frameworks by subject, jurisdiction, or adoption status
    - Get standards framework metadata (title, adoption status, modification dates)

    **Related topics:**
    - [Understanding StandardsFramework vs StandardsFrameworkItem](/knowledge-graph/schema-
    reference/standards)
    - [Framework adoption statuses](/knowledge-graph/schema-reference/enums-and-
    formats#adoptionstatusenum)

    Args:
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        adoption_status (AdoptionStatusENUM | Unset): Adoption status of a standards framework
        include_non_current (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListFrameworksResponse200]
     """


    kwargs = _get_kwargs(
        jurisdiction=jurisdiction,
academic_subject=academic_subject,
adoption_status=adoption_status,
include_non_current=include_non_current,
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
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    adoption_status: AdoptionStatusENUM | Unset = UNSET,
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListFrameworksResponse200 | None:
    """ Standards frameworks

     Fetches a list of StandardsFramework objects representing complete academic standards documents.
    Each standards framework represents a complete standards document published by an official body like
    a state department of education.
    This endpoint allows you to discover available standards frameworks and retrieve metadata about
    standards documents from different jurisdictions, subjects, and adoption statuses.

    Use this endpoint when you need to:
    - Discover available standards frameworks to query academic standards from
    - Find standards framework UUIDs needed for the GET /academic-standards endpoint
    - Browse standards frameworks by subject, jurisdiction, or adoption status
    - Get standards framework metadata (title, adoption status, modification dates)

    **Related topics:**
    - [Understanding StandardsFramework vs StandardsFrameworkItem](/knowledge-graph/schema-
    reference/standards)
    - [Framework adoption statuses](/knowledge-graph/schema-reference/enums-and-
    formats#adoptionstatusenum)

    Args:
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        adoption_status (AdoptionStatusENUM | Unset): Adoption status of a standards framework
        include_non_current (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListFrameworksResponse200
     """


    return sync_detailed(
        client=client,
jurisdiction=jurisdiction,
academic_subject=academic_subject,
adoption_status=adoption_status,
include_non_current=include_non_current,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    adoption_status: AdoptionStatusENUM | Unset = UNSET,
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListFrameworksResponse200]:
    """ Standards frameworks

     Fetches a list of StandardsFramework objects representing complete academic standards documents.
    Each standards framework represents a complete standards document published by an official body like
    a state department of education.
    This endpoint allows you to discover available standards frameworks and retrieve metadata about
    standards documents from different jurisdictions, subjects, and adoption statuses.

    Use this endpoint when you need to:
    - Discover available standards frameworks to query academic standards from
    - Find standards framework UUIDs needed for the GET /academic-standards endpoint
    - Browse standards frameworks by subject, jurisdiction, or adoption status
    - Get standards framework metadata (title, adoption status, modification dates)

    **Related topics:**
    - [Understanding StandardsFramework vs StandardsFrameworkItem](/knowledge-graph/schema-
    reference/standards)
    - [Framework adoption statuses](/knowledge-graph/schema-reference/enums-and-
    formats#adoptionstatusenum)

    Args:
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        adoption_status (AdoptionStatusENUM | Unset): Adoption status of a standards framework
        include_non_current (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListFrameworksResponse200]
     """


    kwargs = _get_kwargs(
        jurisdiction=jurisdiction,
academic_subject=academic_subject,
adoption_status=adoption_status,
include_non_current=include_non_current,
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
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    adoption_status: AdoptionStatusENUM | Unset = UNSET,
    include_non_current: bool | Unset = False,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListFrameworksResponse200 | None:
    """ Standards frameworks

     Fetches a list of StandardsFramework objects representing complete academic standards documents.
    Each standards framework represents a complete standards document published by an official body like
    a state department of education.
    This endpoint allows you to discover available standards frameworks and retrieve metadata about
    standards documents from different jurisdictions, subjects, and adoption statuses.

    Use this endpoint when you need to:
    - Discover available standards frameworks to query academic standards from
    - Find standards framework UUIDs needed for the GET /academic-standards endpoint
    - Browse standards frameworks by subject, jurisdiction, or adoption status
    - Get standards framework metadata (title, adoption status, modification dates)

    **Related topics:**
    - [Understanding StandardsFramework vs StandardsFrameworkItem](/knowledge-graph/schema-
    reference/standards)
    - [Framework adoption statuses](/knowledge-graph/schema-reference/enums-and-
    formats#adoptionstatusenum)

    Args:
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        adoption_status (AdoptionStatusENUM | Unset): Adoption status of a standards framework
        include_non_current (bool | Unset):  Default: False.
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListFrameworksResponse200
     """


    return (await asyncio_detailed(
        client=client,
jurisdiction=jurisdiction,
academic_subject=academic_subject,
adoption_status=adoption_status,
include_non_current=include_non_current,
limit=limit,
cursor=cursor,

    )).parsed
