from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.standards_framework_item import StandardsFrameworkItem
from typing import cast
from uuid import UUID



def _get_kwargs(
    case_identifier_uuid: UUID,

) -> dict[str, Any]:
    

    

    

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/academic-standards/{case_identifier_uuid}".format(case_identifier_uuid=quote(str(case_identifier_uuid), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | StandardsFrameworkItem | None:
    if response.status_code == 200:
        response_200 = StandardsFrameworkItem.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | StandardsFrameworkItem]:
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

) -> Response[Error | StandardsFrameworkItem]:
    """ Standard by ID

     Fetches a single `StandardsFrameworkItem` by its CASE Network UUID.

    A `StandardsFrameworkItem` represents an individual statement or structural element within a
    standards framework. These items can be normative statements that specify what students should know
    or be able to do (e.g., "Describe the impact of a transformation matrix on a graphical object"), or
    organizational groupings that structure the framework (e.g., domains, strands, clusters).

    Use this endpoint when you need to:
    - Display the full details of a specific academic standard in your application
    - Retrieve the exact statement text, grade levels, and classification for a known academic standard
    - Trace an academic standard back to its source in the CASE Network via the CASE identifiers

    The response includes the statement text, grade level(s), subject area, jurisdiction, and all source
    attribution required by the CC BY 4.0 license.

    **Related topics:**
    - [Understanding StandardsFrameworkItem vs StandardsFramework](/knowledge-graph/schema-
    reference/standards)
    - [Standard classification types](/knowledge-graph/schema-reference/enums-and-
    formats#normalizedstatementtypeenum)

    Args:
        case_identifier_uuid (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | StandardsFrameworkItem]
     """


    kwargs = _get_kwargs(
        case_identifier_uuid=case_identifier_uuid,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    case_identifier_uuid: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Error | StandardsFrameworkItem | None:
    """ Standard by ID

     Fetches a single `StandardsFrameworkItem` by its CASE Network UUID.

    A `StandardsFrameworkItem` represents an individual statement or structural element within a
    standards framework. These items can be normative statements that specify what students should know
    or be able to do (e.g., "Describe the impact of a transformation matrix on a graphical object"), or
    organizational groupings that structure the framework (e.g., domains, strands, clusters).

    Use this endpoint when you need to:
    - Display the full details of a specific academic standard in your application
    - Retrieve the exact statement text, grade levels, and classification for a known academic standard
    - Trace an academic standard back to its source in the CASE Network via the CASE identifiers

    The response includes the statement text, grade level(s), subject area, jurisdiction, and all source
    attribution required by the CC BY 4.0 license.

    **Related topics:**
    - [Understanding StandardsFrameworkItem vs StandardsFramework](/knowledge-graph/schema-
    reference/standards)
    - [Standard classification types](/knowledge-graph/schema-reference/enums-and-
    formats#normalizedstatementtypeenum)

    Args:
        case_identifier_uuid (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | StandardsFrameworkItem
     """


    return sync_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,

    ).parsed

async def asyncio_detailed(
    case_identifier_uuid: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[Error | StandardsFrameworkItem]:
    """ Standard by ID

     Fetches a single `StandardsFrameworkItem` by its CASE Network UUID.

    A `StandardsFrameworkItem` represents an individual statement or structural element within a
    standards framework. These items can be normative statements that specify what students should know
    or be able to do (e.g., "Describe the impact of a transformation matrix on a graphical object"), or
    organizational groupings that structure the framework (e.g., domains, strands, clusters).

    Use this endpoint when you need to:
    - Display the full details of a specific academic standard in your application
    - Retrieve the exact statement text, grade levels, and classification for a known academic standard
    - Trace an academic standard back to its source in the CASE Network via the CASE identifiers

    The response includes the statement text, grade level(s), subject area, jurisdiction, and all source
    attribution required by the CC BY 4.0 license.

    **Related topics:**
    - [Understanding StandardsFrameworkItem vs StandardsFramework](/knowledge-graph/schema-
    reference/standards)
    - [Standard classification types](/knowledge-graph/schema-reference/enums-and-
    formats#normalizedstatementtypeenum)

    Args:
        case_identifier_uuid (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | StandardsFrameworkItem]
     """


    kwargs = _get_kwargs(
        case_identifier_uuid=case_identifier_uuid,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    case_identifier_uuid: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Error | StandardsFrameworkItem | None:
    """ Standard by ID

     Fetches a single `StandardsFrameworkItem` by its CASE Network UUID.

    A `StandardsFrameworkItem` represents an individual statement or structural element within a
    standards framework. These items can be normative statements that specify what students should know
    or be able to do (e.g., "Describe the impact of a transformation matrix on a graphical object"), or
    organizational groupings that structure the framework (e.g., domains, strands, clusters).

    Use this endpoint when you need to:
    - Display the full details of a specific academic standard in your application
    - Retrieve the exact statement text, grade levels, and classification for a known academic standard
    - Trace an academic standard back to its source in the CASE Network via the CASE identifiers

    The response includes the statement text, grade level(s), subject area, jurisdiction, and all source
    attribution required by the CC BY 4.0 license.

    **Related topics:**
    - [Understanding StandardsFrameworkItem vs StandardsFramework](/knowledge-graph/schema-
    reference/standards)
    - [Standard classification types](/knowledge-graph/schema-reference/enums-and-
    formats#normalizedstatementtypeenum)

    Args:
        case_identifier_uuid (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | StandardsFrameworkItem
     """


    return (await asyncio_detailed(
        case_identifier_uuid=case_identifier_uuid,
client=client,

    )).parsed
