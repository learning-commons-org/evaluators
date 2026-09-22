from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error import Error
from ...models.get_course_scope_and_sequence_view import GetCourseScopeAndSequenceView
from ...models.scope_and_sequence_full import ScopeAndSequenceFull
from ...models.scope_and_sequence_summary import ScopeAndSequenceSummary
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    course_id: str,
    *,
    view: GetCourseScopeAndSequenceView | Unset = GetCourseScopeAndSequenceView.SUMMARY,

) -> dict[str, Any]:
    

    

    params: dict[str, Any] = {}

    json_view: str | Unset = UNSET
    if not isinstance(view, Unset):
        json_view = view.value

    params["view"] = json_view


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/courses/{course_id}/scope-and-sequence".format(course_id=quote(str(course_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Error | ScopeAndSequenceFull | ScopeAndSequenceSummary | None:
    if response.status_code == 200:
        def _parse_response_200(data: object) -> ScopeAndSequenceFull | ScopeAndSequenceSummary:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_scope_and_sequence_type_0 = ScopeAndSequenceSummary.from_dict(data)



                return componentsschemas_scope_and_sequence_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            if not isinstance(data, dict):
                raise TypeError()
            componentsschemas_scope_and_sequence_type_1 = ScopeAndSequenceFull.from_dict(data)



            return componentsschemas_scope_and_sequence_type_1

        response_200 = _parse_response_200(response.json())

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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Error | ScopeAndSequenceFull | ScopeAndSequenceSummary]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    course_id: str,
    *,
    client: AuthenticatedClient | Client,
    view: GetCourseScopeAndSequenceView | Unset = GetCourseScopeAndSequenceView.SUMMARY,

) -> Response[Error | ScopeAndSequenceFull | ScopeAndSequenceSummary]:
    """ Scope and sequence for a course

     Returns the complete hierarchical structure of a course including its lesson groupings and lessons
    in a scope and sequence format.

    The structure follows this hierarchy:
    - Course → Lesson Groupings (can be nested) → Lessons

    **Note:** Different curricula use different organizational structures. Lesson groupings might be
    called units, modules, chapters, sections, themes, etc. depending on the curriculum. The `groupName`
    property in each lesson grouping indicates what type it is (e.g., "unit", "section", "module").

    Use this endpoint when you need to:
    - Display the complete course outline or table of contents
    - Navigate the course structure programmatically
    - Build a course curriculum map or scope and sequence view
    - Understand the full instructional progression of a course

    The `view` parameter controls the level of detail:
    - `summary`: Returns only essential navigation fields (identifiers, names, positions)
    - `full`: Returns complete objects with all properties for each element

    Args:
        course_id (str):
        view (GetCourseScopeAndSequenceView | Unset):  Default:
            GetCourseScopeAndSequenceView.SUMMARY.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ScopeAndSequenceFull | ScopeAndSequenceSummary]
     """


    kwargs = _get_kwargs(
        course_id=course_id,
view=view,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    course_id: str,
    *,
    client: AuthenticatedClient | Client,
    view: GetCourseScopeAndSequenceView | Unset = GetCourseScopeAndSequenceView.SUMMARY,

) -> Error | ScopeAndSequenceFull | ScopeAndSequenceSummary | None:
    """ Scope and sequence for a course

     Returns the complete hierarchical structure of a course including its lesson groupings and lessons
    in a scope and sequence format.

    The structure follows this hierarchy:
    - Course → Lesson Groupings (can be nested) → Lessons

    **Note:** Different curricula use different organizational structures. Lesson groupings might be
    called units, modules, chapters, sections, themes, etc. depending on the curriculum. The `groupName`
    property in each lesson grouping indicates what type it is (e.g., "unit", "section", "module").

    Use this endpoint when you need to:
    - Display the complete course outline or table of contents
    - Navigate the course structure programmatically
    - Build a course curriculum map or scope and sequence view
    - Understand the full instructional progression of a course

    The `view` parameter controls the level of detail:
    - `summary`: Returns only essential navigation fields (identifiers, names, positions)
    - `full`: Returns complete objects with all properties for each element

    Args:
        course_id (str):
        view (GetCourseScopeAndSequenceView | Unset):  Default:
            GetCourseScopeAndSequenceView.SUMMARY.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ScopeAndSequenceFull | ScopeAndSequenceSummary
     """


    return sync_detailed(
        course_id=course_id,
client=client,
view=view,

    ).parsed

async def asyncio_detailed(
    course_id: str,
    *,
    client: AuthenticatedClient | Client,
    view: GetCourseScopeAndSequenceView | Unset = GetCourseScopeAndSequenceView.SUMMARY,

) -> Response[Error | ScopeAndSequenceFull | ScopeAndSequenceSummary]:
    """ Scope and sequence for a course

     Returns the complete hierarchical structure of a course including its lesson groupings and lessons
    in a scope and sequence format.

    The structure follows this hierarchy:
    - Course → Lesson Groupings (can be nested) → Lessons

    **Note:** Different curricula use different organizational structures. Lesson groupings might be
    called units, modules, chapters, sections, themes, etc. depending on the curriculum. The `groupName`
    property in each lesson grouping indicates what type it is (e.g., "unit", "section", "module").

    Use this endpoint when you need to:
    - Display the complete course outline or table of contents
    - Navigate the course structure programmatically
    - Build a course curriculum map or scope and sequence view
    - Understand the full instructional progression of a course

    The `view` parameter controls the level of detail:
    - `summary`: Returns only essential navigation fields (identifiers, names, positions)
    - `full`: Returns complete objects with all properties for each element

    Args:
        course_id (str):
        view (GetCourseScopeAndSequenceView | Unset):  Default:
            GetCourseScopeAndSequenceView.SUMMARY.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Error | ScopeAndSequenceFull | ScopeAndSequenceSummary]
     """


    kwargs = _get_kwargs(
        course_id=course_id,
view=view,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    course_id: str,
    *,
    client: AuthenticatedClient | Client,
    view: GetCourseScopeAndSequenceView | Unset = GetCourseScopeAndSequenceView.SUMMARY,

) -> Error | ScopeAndSequenceFull | ScopeAndSequenceSummary | None:
    """ Scope and sequence for a course

     Returns the complete hierarchical structure of a course including its lesson groupings and lessons
    in a scope and sequence format.

    The structure follows this hierarchy:
    - Course → Lesson Groupings (can be nested) → Lessons

    **Note:** Different curricula use different organizational structures. Lesson groupings might be
    called units, modules, chapters, sections, themes, etc. depending on the curriculum. The `groupName`
    property in each lesson grouping indicates what type it is (e.g., "unit", "section", "module").

    Use this endpoint when you need to:
    - Display the complete course outline or table of contents
    - Navigate the course structure programmatically
    - Build a course curriculum map or scope and sequence view
    - Understand the full instructional progression of a course

    The `view` parameter controls the level of detail:
    - `summary`: Returns only essential navigation fields (identifiers, names, positions)
    - `full`: Returns complete objects with all properties for each element

    Args:
        course_id (str):
        view (GetCourseScopeAndSequenceView | Unset):  Default:
            GetCourseScopeAndSequenceView.SUMMARY.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Error | ScopeAndSequenceFull | ScopeAndSequenceSummary
     """


    return (await asyncio_detailed(
        course_id=course_id,
client=client,
view=view,

    )).parsed
