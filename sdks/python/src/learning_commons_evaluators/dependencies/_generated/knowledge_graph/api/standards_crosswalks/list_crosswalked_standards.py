from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.jurisdiction_enum import JurisdictionENUM
from ...models.list_crosswalked_standards_response_200 import ListCrosswalkedStandardsResponse200
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    case_identifier_uuid: UUID,
    *,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    min_jaccard_score: float | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_jurisdiction: str | Unset = UNSET
    if not isinstance(jurisdiction, Unset):
        json_jurisdiction = jurisdiction.value

    params["jurisdiction"] = json_jurisdiction

    params["minJaccardScore"] = min_jaccard_score

    params["limit"] = limit

    params["cursor"] = cursor


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/academic-standards/{case_identifier_uuid}/crosswalks".format(case_identifier_uuid=quote(str(case_identifier_uuid), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ListCrosswalkedStandardsResponse200 | None:
    if response.status_code == 200:
        response_200 = ListCrosswalkedStandardsResponse200.from_dict(response.json())



        return response_200

    if response.status_code == 400:
        response_400 = Error.from_dict(response.json())



        return response_400

    if response.status_code == 404:
        response_404 = Error.from_dict(response.json())



        return response_404

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ListCrosswalkedStandardsResponse200]:
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
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    min_jaccard_score: float | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListCrosswalkedStandardsResponse200]:
    """ Crosswalks for a standard

     Fetches a list of standards that align to a specific standard through shared learning components.

    This endpoint retrieves crosswalk relationships bidirectionally:
    - **State standard → CCSS**: Pass in a state standard to get matching Common Core State Standards
    (CCSS)
    - **CCSS → State standards**: Pass in a Common Core State Standards (CCSS) standard to get matching
    state standards across jurisdictions

    Each crosswalk includes similarity metrics based on measurable overlap of learning components to
    help understand the strength and nature of the alignment.

    Crosswalks provide a scalable way to extend mappings between CCSS and state-specific frameworks
    without independent matching logic. By leveraging the LC superset, crosswalks show where standards
    converge in content coverage.

    Use this endpoint when you need to:
    - Find Common Core State Standards (CCSS) standards that align to a state standard for content
    adaptation
    - Find state standards that align to a Common Core State Standards (CCSS) standard across multiple
    jurisdictions
    - Understand the similarity between standards
    - Map content between Common Core and state frameworks
    - Analyze the degree of overlap between standards

    **Note:** Crosswalks are currently available for Mathematics and English Language Arts (ELA)
    standards in states where LC alignment exists. Math crosswalks cover grades K-12. ELA crosswalks
    cover grades K-2. Crosswalks are evidence-based (require at least one shared learning component).

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Standards crosswalks methodology](/knowledge-graph/schema-reference/standards#understanding-the-
    jaccard-score)

    Args:
        case_identifier_uuid (UUID):
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        min_jaccard_score (float | Unset):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListCrosswalkedStandardsResponse200]
     """


    kwargs = _get_kwargs(
        case_identifier_uuid=case_identifier_uuid,
jurisdiction=jurisdiction,
min_jaccard_score=min_jaccard_score,
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
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    min_jaccard_score: float | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListCrosswalkedStandardsResponse200 | None:
    """ Crosswalks for a standard

     Fetches a list of standards that align to a specific standard through shared learning components.

    This endpoint retrieves crosswalk relationships bidirectionally:
    - **State standard → CCSS**: Pass in a state standard to get matching Common Core State Standards
    (CCSS)
    - **CCSS → State standards**: Pass in a Common Core State Standards (CCSS) standard to get matching
    state standards across jurisdictions

    Each crosswalk includes similarity metrics based on measurable overlap of learning components to
    help understand the strength and nature of the alignment.

    Crosswalks provide a scalable way to extend mappings between CCSS and state-specific frameworks
    without independent matching logic. By leveraging the LC superset, crosswalks show where standards
    converge in content coverage.

    Use this endpoint when you need to:
    - Find Common Core State Standards (CCSS) standards that align to a state standard for content
    adaptation
    - Find state standards that align to a Common Core State Standards (CCSS) standard across multiple
    jurisdictions
    - Understand the similarity between standards
    - Map content between Common Core and state frameworks
    - Analyze the degree of overlap between standards

    **Note:** Crosswalks are currently available for Mathematics and English Language Arts (ELA)
    standards in states where LC alignment exists. Math crosswalks cover grades K-12. ELA crosswalks
    cover grades K-2. Crosswalks are evidence-based (require at least one shared learning component).

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Standards crosswalks methodology](/knowledge-graph/schema-reference/standards#understanding-the-
    jaccard-score)

    Args:
        case_identifier_uuid (UUID):
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        min_jaccard_score (float | Unset):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListCrosswalkedStandardsResponse200
     """


    return sync_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,
jurisdiction=jurisdiction,
min_jaccard_score=min_jaccard_score,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    case_identifier_uuid: UUID,
    *,
    client: AuthenticatedClient | Client,
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    min_jaccard_score: float | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | ListCrosswalkedStandardsResponse200]:
    """ Crosswalks for a standard

     Fetches a list of standards that align to a specific standard through shared learning components.

    This endpoint retrieves crosswalk relationships bidirectionally:
    - **State standard → CCSS**: Pass in a state standard to get matching Common Core State Standards
    (CCSS)
    - **CCSS → State standards**: Pass in a Common Core State Standards (CCSS) standard to get matching
    state standards across jurisdictions

    Each crosswalk includes similarity metrics based on measurable overlap of learning components to
    help understand the strength and nature of the alignment.

    Crosswalks provide a scalable way to extend mappings between CCSS and state-specific frameworks
    without independent matching logic. By leveraging the LC superset, crosswalks show where standards
    converge in content coverage.

    Use this endpoint when you need to:
    - Find Common Core State Standards (CCSS) standards that align to a state standard for content
    adaptation
    - Find state standards that align to a Common Core State Standards (CCSS) standard across multiple
    jurisdictions
    - Understand the similarity between standards
    - Map content between Common Core and state frameworks
    - Analyze the degree of overlap between standards

    **Note:** Crosswalks are currently available for Mathematics and English Language Arts (ELA)
    standards in states where LC alignment exists. Math crosswalks cover grades K-12. ELA crosswalks
    cover grades K-2. Crosswalks are evidence-based (require at least one shared learning component).

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Standards crosswalks methodology](/knowledge-graph/schema-reference/standards#understanding-the-
    jaccard-score)

    Args:
        case_identifier_uuid (UUID):
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        min_jaccard_score (float | Unset):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ListCrosswalkedStandardsResponse200]
     """


    kwargs = _get_kwargs(
        case_identifier_uuid=case_identifier_uuid,
jurisdiction=jurisdiction,
min_jaccard_score=min_jaccard_score,
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
    jurisdiction: JurisdictionENUM | Unset = UNSET,
    min_jaccard_score: float | Unset = UNSET,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | ListCrosswalkedStandardsResponse200 | None:
    """ Crosswalks for a standard

     Fetches a list of standards that align to a specific standard through shared learning components.

    This endpoint retrieves crosswalk relationships bidirectionally:
    - **State standard → CCSS**: Pass in a state standard to get matching Common Core State Standards
    (CCSS)
    - **CCSS → State standards**: Pass in a Common Core State Standards (CCSS) standard to get matching
    state standards across jurisdictions

    Each crosswalk includes similarity metrics based on measurable overlap of learning components to
    help understand the strength and nature of the alignment.

    Crosswalks provide a scalable way to extend mappings between CCSS and state-specific frameworks
    without independent matching logic. By leveraging the LC superset, crosswalks show where standards
    converge in content coverage.

    Use this endpoint when you need to:
    - Find Common Core State Standards (CCSS) standards that align to a state standard for content
    adaptation
    - Find state standards that align to a Common Core State Standards (CCSS) standard across multiple
    jurisdictions
    - Understand the similarity between standards
    - Map content between Common Core and state frameworks
    - Analyze the degree of overlap between standards

    **Note:** Crosswalks are currently available for Mathematics and English Language Arts (ELA)
    standards in states where LC alignment exists. Math crosswalks cover grades K-12. ELA crosswalks
    cover grades K-2. Crosswalks are evidence-based (require at least one shared learning component).

    The endpoint returns paginated results. Use the `limit` and `cursor` parameters to control the
    number of results returned.

    **Related topics:**
    - [Standards crosswalks methodology](/knowledge-graph/schema-reference/standards#understanding-the-
    jaccard-score)

    Args:
        case_identifier_uuid (UUID):
        jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
        min_jaccard_score (float | Unset):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ListCrosswalkedStandardsResponse200
     """


    return (await asyncio_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,
jurisdiction=jurisdiction,
min_jaccard_score=min_jaccard_score,
limit=limit,
cursor=cursor,

    )).parsed
