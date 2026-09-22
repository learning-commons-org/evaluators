from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.get_assessment_standards_response_200 import GetAssessmentStandardsResponse200
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    assessment_id: str,
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
        "url": "/assessments/{assessment_id}/standards".format(assessment_id=quote(str(assessment_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | GetAssessmentStandardsResponse200 | None:
    if response.status_code == 200:
        response_200 = GetAssessmentStandardsResponse200.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | GetAssessmentStandardsResponse200]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    assessment_id: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | GetAssessmentStandardsResponse200]:
    """ Standards for an assessment

     Fetches all academic standards aligned to a specific assessment.

    Returns the standards that this assessment evaluates. These alignments indicate which learning
    expectations the assessment is designed to measure.

    Use this endpoint when you need to:
    - See which standards an assessment evaluates
    - Build standards-aligned assessments
    - Track standards coverage in assessments
    - Generate assessment standards reports

    Args:
        assessment_id (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetAssessmentStandardsResponse200]
     """


    kwargs = _get_kwargs(
        assessment_id=assessment_id,
limit=limit,
cursor=cursor,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    assessment_id: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | GetAssessmentStandardsResponse200 | None:
    """ Standards for an assessment

     Fetches all academic standards aligned to a specific assessment.

    Returns the standards that this assessment evaluates. These alignments indicate which learning
    expectations the assessment is designed to measure.

    Use this endpoint when you need to:
    - See which standards an assessment evaluates
    - Build standards-aligned assessments
    - Track standards coverage in assessments
    - Generate assessment standards reports

    Args:
        assessment_id (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetAssessmentStandardsResponse200
     """


    return sync_detailed(
        assessment_id=assessment_id,
client=client,
limit=limit,
cursor=cursor,

    ).parsed

async def asyncio_detailed(
    assessment_id: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Response[Error | GetAssessmentStandardsResponse200]:
    """ Standards for an assessment

     Fetches all academic standards aligned to a specific assessment.

    Returns the standards that this assessment evaluates. These alignments indicate which learning
    expectations the assessment is designed to measure.

    Use this endpoint when you need to:
    - See which standards an assessment evaluates
    - Build standards-aligned assessments
    - Track standards coverage in assessments
    - Generate assessment standards reports

    Args:
        assessment_id (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | GetAssessmentStandardsResponse200]
     """


    kwargs = _get_kwargs(
        assessment_id=assessment_id,
limit=limit,
cursor=cursor,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    assessment_id: str,
    *,
    client: AuthenticatedClient | Client,
    limit: int | Unset = 100,
    cursor: str | Unset = UNSET,

) -> Error | GetAssessmentStandardsResponse200 | None:
    """ Standards for an assessment

     Fetches all academic standards aligned to a specific assessment.

    Returns the standards that this assessment evaluates. These alignments indicate which learning
    expectations the assessment is designed to measure.

    Use this endpoint when you need to:
    - See which standards an assessment evaluates
    - Build standards-aligned assessments
    - Track standards coverage in assessments
    - Generate assessment standards reports

    Args:
        assessment_id (str):
        limit (int | Unset):  Default: 100.
        cursor (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | GetAssessmentStandardsResponse200
     """


    return (await asyncio_detailed(
        assessment_id=assessment_id,
client=client,
limit=limit,
cursor=cursor,

    )).parsed
