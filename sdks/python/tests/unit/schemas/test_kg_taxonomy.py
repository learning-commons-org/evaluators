"""The Knowledge Graph taxonomy enums: wire strings a caller may pass.

Their agreement with the vendored OpenAPI spec is ``make check-kg-client``'s job, and
``test_kg_client_generator`` runs that comparison as a test. What is checked here is the
module's own shape — that ``.value`` is the wire string, that a plain string works
anywhere a member does, and that the awkward spellings are the service's rather than
tidied-up Python ones.
"""

from __future__ import annotations

from enum import Enum

import pytest

from learning_commons_evaluators.schemas.kg_taxonomy import (
    DEFAULT_JURISDICTION,
    AcademicSubject,
    GradeLevel,
    Jurisdiction,
)

TAXONOMIES: list[type[Enum]] = [AcademicSubject, GradeLevel, Jurisdiction]


@pytest.mark.parametrize("enum", TAXONOMIES, ids=lambda e: e.__name__)
def test_members_are_usable_as_plain_strings(enum: type[Enum]) -> None:
    """``str`` subclasses, so a caller may pass either the member or the raw string.

    Both the client's request building and its parsing rely on this, and it is the
    difference between a friendly enum and one callers have to remember to ``.value``.
    """
    for member in enum:
        assert isinstance(member, str)
        assert member == member.value
        assert enum(member.value) is member


@pytest.mark.parametrize("enum", TAXONOMIES, ids=lambda e: e.__name__)
def test_no_two_members_share_a_wire_string(enum: type[Enum]) -> None:
    # A duplicate would silently alias one member to another and make a lookup ambiguous.
    values = [member.value for member in enum]
    assert len(values) == len(set(values))


def test_the_awkward_spellings_are_the_services_own() -> None:
    """The values the service actually sends, punctuation and all.

    Spelled out because these are the ones a well-meaning cleanup would "fix" — dropping
    the periods, the hyphen, or the comma would produce a token the service rejects.
    """
    assert Jurisdiction.WASHINGTON_D_C.value == "Washington, D.C."
    assert Jurisdiction.MULTI_STATE.value == "Multi-State"
    assert AcademicSubject.ENGLISH_LANGUAGE_ARTS.value == "English Language Arts"
    assert GradeLevel.PK.value == "PK"
    assert GradeLevel.K.value == "K"
    # Numeric grades are strings on the wire, not ints.
    assert GradeLevel.GRADE_3.value == "3"


def test_jurisdictions_cover_the_states_plus_dc_and_multi_state() -> None:
    assert len(Jurisdiction) == 52


def test_grade_levels_run_from_pre_k_to_twelve() -> None:
    assert [level.value for level in GradeLevel] == [
        "PK",
        "K",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "11",
        "12",
    ]


def test_the_default_jurisdiction_is_multi_state() -> None:
    """Common Core, and what a lookup falls back to — matching the TypeScript SDK."""
    assert DEFAULT_JURISDICTION is Jurisdiction.MULTI_STATE
