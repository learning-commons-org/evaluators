from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.academic_subject_enum import AcademicSubjectENUM
from ...models.error import Error
from ...models.grade_level_enum import GradeLevelENUM
from ...models.list_academic_standards_response_200 import ListAcademicStandardsResponse200
from ...models.normalized_statement_type_enum import NormalizedStatementTypeENUM
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    *,
    standards_framework_case_identifier_uuid: UUID,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_standards_framework_case_identifier_uuid = str(standards_framework_case_identifier_uuid)
    params["standardsFrameworkCaseIdentifierUUID"] = json_standards_framework_case_identifier_uuid

    json_grade_level: list[str] | Unset = UNSET
    if not isinstance(grade_level, Unset):
        json_grade_level = []
        for grade_level_item_data in grade_level:
            grade_level_item = grade_level_item_data.value
            json_grade_level.append(grade_level_item)


    params["gradeLevel"] = json_grade_level

    json_academic_subject: str | Unset = UNSET
    if not isinstance(academic_subject, Unset):
        json_academic_subject = academic_subject.value

    params["academicSubject"] = json_academic_subject

    json_normalized_statement_type: str | Unset = UNSET
    if not isinstance(normalized_statement_type, Unset):
        json_normalized_statement_type = normalized_statement_type.value

    params["normalizedStatementType"] = json_normalized_statement_type

    params["limit"] = limit

    params["cursor"] = cursor


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/academic-standards",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListAcademicStandardsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListAcademicStandardsResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListAcademicStandardsResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    standards_framework_case_identifier_uuid: UUID,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListAcademicStandardsResponse200]:
    """ Standards in a framework

     Fetches a list of StandardsFrameworkItems for a specific standards framework.

    This endpoint retrieves academic standards from a single standards framework identified by its CASE
    Network UUID. You can further filter the results by grade level or classification type. This is
    useful when you need to work with academic standards from a specific state or jurisdiction.

    Use this endpoint when you need to:
    - Get all academic standards within a specific standards framework
    - Find academic standards for a particular grade level within a standards framework
    - Filter academic standards by subject area (e.g., only Mathematics academic standards)
    - Filter academic standards by their normalized classification (e.g., only instructional academic
    standards, not organizational groupings)
    - Retrieve a subset of a standards framework's academic standards for display or processing

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned and navigate through large result sets.

    **Related topics:**
    - [Understanding StandardsFrameworkItem classifications](/knowledge-graph/schema-reference/enums-
    and-formats#normalizedstatementtypeenum)

    Args:
        standards_framework_case_identifier_uuid (UUID):
        grade_level (list[GradeLevelENUM] | Unset):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListAcademicStandardsResponse200]
     """


    kwargs = _get_kwargs(
        standards_framework_case_identifier_uuid=standards_framework_case_identifier_uuid,
grade_level=grade_level,
academic_subject=academic_subject,
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
    standards_framework_case_identifier_uuid: UUID,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListAcademicStandardsResponse200 | None:
    """ Standards in a framework

     Fetches a list of StandardsFrameworkItems for a specific standards framework.

    This endpoint retrieves academic standards from a single standards framework identified by its CASE
    Network UUID. You can further filter the results by grade level or classification type. This is
    useful when you need to work with academic standards from a specific state or jurisdiction.

    Use this endpoint when you need to:
    - Get all academic standards within a specific standards framework
    - Find academic standards for a particular grade level within a standards framework
    - Filter academic standards by subject area (e.g., only Mathematics academic standards)
    - Filter academic standards by their normalized classification (e.g., only instructional academic
    standards, not organizational groupings)
    - Retrieve a subset of a standards framework's academic standards for display or processing

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned and navigate through large result sets.

    **Related topics:**
    - [Understanding StandardsFrameworkItem classifications](/knowledge-graph/schema-reference/enums-
    and-formats#normalizedstatementtypeenum)

    Args:
        standards_framework_case_identifier_uuid (UUID):
        grade_level (list[GradeLevelENUM] | Unset):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListAcademicStandardsResponse200
     """


    return sync_detailed(
        client=client,
standards_framework_case_identifier_uuid=standards_framework_case_identifier_uuid,
grade_level=grade_level,
academic_subject=academic_subject,
normalized_statement_type=normalized_statement_type,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    standards_framework_case_identifier_uuid: UUID,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListAcademicStandardsResponse200]:
    """ Standards in a framework

     Fetches a list of StandardsFrameworkItems for a specific standards framework.

    This endpoint retrieves academic standards from a single standards framework identified by its CASE
    Network UUID. You can further filter the results by grade level or classification type. This is
    useful when you need to work with academic standards from a specific state or jurisdiction.

    Use this endpoint when you need to:
    - Get all academic standards within a specific standards framework
    - Find academic standards for a particular grade level within a standards framework
    - Filter academic standards by subject area (e.g., only Mathematics academic standards)
    - Filter academic standards by their normalized classification (e.g., only instructional academic
    standards, not organizational groupings)
    - Retrieve a subset of a standards framework's academic standards for display or processing

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned and navigate through large result sets.

    **Related topics:**
    - [Understanding StandardsFrameworkItem classifications](/knowledge-graph/schema-reference/enums-
    and-formats#normalizedstatementtypeenum)

    Args:
        standards_framework_case_identifier_uuid (UUID):
        grade_level (list[GradeLevelENUM] | Unset):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListAcademicStandardsResponse200]
     """


    kwargs = _get_kwargs(
        standards_framework_case_identifier_uuid=standards_framework_case_identifier_uuid,
grade_level=grade_level,
academic_subject=academic_subject,
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
    standards_framework_case_identifier_uuid: UUID,
    grade_level: list[GradeLevelENUM] | Unset = UNSET,
    academic_subject: AcademicSubjectENUM | Unset = UNSET,
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListAcademicStandardsResponse200 | None:
    """ Standards in a framework

     Fetches a list of StandardsFrameworkItems for a specific standards framework.

    This endpoint retrieves academic standards from a single standards framework identified by its CASE
    Network UUID. You can further filter the results by grade level or classification type. This is
    useful when you need to work with academic standards from a specific state or jurisdiction.

    Use this endpoint when you need to:
    - Get all academic standards within a specific standards framework
    - Find academic standards for a particular grade level within a standards framework
    - Filter academic standards by subject area (e.g., only Mathematics academic standards)
    - Filter academic standards by their normalized classification (e.g., only instructional academic
    standards, not organizational groupings)
    - Retrieve a subset of a standards framework's academic standards for display or processing

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned and navigate through large result sets.

    **Related topics:**
    - [Understanding StandardsFrameworkItem classifications](/knowledge-graph/schema-reference/enums-
    and-formats#normalizedstatementtypeenum)

    Args:
        standards_framework_case_identifier_uuid (UUID):
        grade_level (list[GradeLevelENUM] | Unset):
        academic_subject (AcademicSubjectENUM | Unset): Academic subject area
        normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that
            has been standardized across standards frameworks for cross-state queries and
            categorization
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListAcademicStandardsResponse200
     """


    return (await asyncio_detailed(
        client=client,
standards_framework_case_identifier_uuid=standards_framework_case_identifier_uuid,
grade_level=grade_level,
academic_subject=academic_subject,
normalized_statement_type=normalized_statement_type,
limit=limit,
cursor=cursor,

    )).parsed
