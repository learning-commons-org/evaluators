"""Knowledge Graph taxonomy: the wire strings a caller may pass, as ``str`` enums.

Hand-written, and deliberately not the generated ``*ENUM`` classes under
``dependencies/_generated`` — those are transport detail that regeneration may rename,
while these are public API that a caller pins a version against. ``make check-kg-client``
compares the two: a value only this module has fails, a value only the spec has warns.

``.value`` is what the service expects, verbatim: ``"Mathematics"``, ``"3"``,
``"Washington, D.C."``. Because they subclass ``str``, a plain string works anywhere one
of these does — ``Jurisdiction.TEXAS`` and ``"Texas"`` are interchangeable.
"""

from __future__ import annotations

from enum import Enum


class AcademicSubject(str, Enum):
    """Subject area of a standard (Knowledge Graph ``AcademicSubjectENUM``)."""

    ENGLISH_LANGUAGE_ARTS = "English Language Arts"
    MATHEMATICS = "Mathematics"
    SCIENCE = "Science"
    SOCIAL_STUDIES = "Social Studies"
    OTHER = "Other"


class GradeLevel(str, Enum):
    """Grade level of a standard (Knowledge Graph ``GradeLevelENUM``).

    Distinct from the ``grade_level`` evaluators take, which is the token set that
    evaluator's own contract declares.
    """

    PK = "PK"
    K = "K"
    GRADE_1 = "1"
    GRADE_2 = "2"
    GRADE_3 = "3"
    GRADE_4 = "4"
    GRADE_5 = "5"
    GRADE_6 = "6"
    GRADE_7 = "7"
    GRADE_8 = "8"
    GRADE_9 = "9"
    GRADE_10 = "10"
    GRADE_11 = "11"
    GRADE_12 = "12"


class Jurisdiction(str, Enum):
    """US state, territory, or multi-state designation (Knowledge Graph ``JurisdictionENUM``).

    ``MULTI_STATE`` is the Common Core framework and the default every lookup falls back
    to, matching the TypeScript SDK.
    """

    ALABAMA = "Alabama"
    ALASKA = "Alaska"
    ARIZONA = "Arizona"
    ARKANSAS = "Arkansas"
    CALIFORNIA = "California"
    COLORADO = "Colorado"
    CONNECTICUT = "Connecticut"
    DELAWARE = "Delaware"
    FLORIDA = "Florida"
    GEORGIA = "Georgia"
    HAWAII = "Hawaii"
    IDAHO = "Idaho"
    ILLINOIS = "Illinois"
    INDIANA = "Indiana"
    IOWA = "Iowa"
    KANSAS = "Kansas"
    KENTUCKY = "Kentucky"
    LOUISIANA = "Louisiana"
    MAINE = "Maine"
    MARYLAND = "Maryland"
    MASSACHUSETTS = "Massachusetts"
    MICHIGAN = "Michigan"
    MINNESOTA = "Minnesota"
    MISSISSIPPI = "Mississippi"
    MISSOURI = "Missouri"
    MONTANA = "Montana"
    NEBRASKA = "Nebraska"
    NEVADA = "Nevada"
    NEW_HAMPSHIRE = "New Hampshire"
    NEW_JERSEY = "New Jersey"
    NEW_MEXICO = "New Mexico"
    NEW_YORK = "New York"
    NORTH_CAROLINA = "North Carolina"
    NORTH_DAKOTA = "North Dakota"
    OHIO = "Ohio"
    OKLAHOMA = "Oklahoma"
    OREGON = "Oregon"
    PENNSYLVANIA = "Pennsylvania"
    RHODE_ISLAND = "Rhode Island"
    SOUTH_CAROLINA = "South Carolina"
    SOUTH_DAKOTA = "South Dakota"
    TENNESSEE = "Tennessee"
    TEXAS = "Texas"
    UTAH = "Utah"
    VERMONT = "Vermont"
    VIRGINIA = "Virginia"
    WASHINGTON = "Washington"
    WASHINGTON_D_C = "Washington, D.C."
    WEST_VIRGINIA = "West Virginia"
    WISCONSIN = "Wisconsin"
    WYOMING = "Wyoming"
    MULTI_STATE = "Multi-State"


#: Where a lookup goes when the caller names no jurisdiction, matching the TypeScript SDK.
DEFAULT_JURISDICTION = Jurisdiction.MULTI_STATE


__all__ = [
    "DEFAULT_JURISDICTION",
    "AcademicSubject",
    "GradeLevel",
    "Jurisdiction",
]
