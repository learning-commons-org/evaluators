"""The median the Critical Thinking prompt asks the model to form.

Odd count takes the middle rating. Even count takes the higher of the two middle
ratings. A missing indicator is not a rating.
"""

from __future__ import annotations

from pydantic import BaseModel

LEVELS = ("not_evident", "exploring", "analyzing", "integrating", "extending")


def median_rating(ratings: list[str]) -> str:
    """The upper median of ratings, on the prompt's order."""
    ordered = sorted(ratings, key=LEVELS.index)
    return ordered[len(ordered) // 2]


def present_ratings(indicators: BaseModel) -> list[str]:
    """Ratings the model actually returned. An unset indicator is absent, not a level."""
    ratings: list[str] = []
    for name in type(indicators).model_fields:
        value = getattr(indicators, name)
        if value is not None:
            ratings.append(value.rating)
    return ratings


def test_five_ratings_take_the_middle() -> None:
    assert (
        median_rating(["not_evident", "exploring", "analyzing", "integrating", "extending"])
        == "analyzing"
    )


def test_four_ratings_round_up() -> None:
    assert median_rating(["exploring", "exploring", "analyzing", "analyzing"]) == "analyzing"


def test_equal_ratings_stay_put() -> None:
    assert (
        median_rating(["integrating", "integrating", "integrating", "integrating"]) == "integrating"
    )
