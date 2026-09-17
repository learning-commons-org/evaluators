"""Contract-declared computations dispatch to the library the contract names."""

from __future__ import annotations

import math

import pytest
import textstat

from learning_commons_evaluators.contracts.loader import Implementation
from learning_commons_evaluators.features import (
    format_number,
    round_half_up,
    run_preprocessing_step,
)

TEXT = "Trees are important plants that grow in many parts of the world."


ROUND_2 = Implementation.model_validate(
    {
        "library": "textstat",
        "function": "flesch_kincaid_grade",
        "post_transform": {"type": "round", "precision": 2},
    }
)


def test_runs_textstat_by_function_name_and_rounds() -> None:
    raw = textstat.flesch_kincaid_grade(TEXT)
    assert run_preprocessing_step(TEXT, ROUND_2) == math.floor(raw * 100 + 0.5) / 100


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Ties round half up, as JavaScript's Math.round does; Python's round() would give
        # 0.12 and 2.67 here, binding different text from the TypeScript SDK.
        (0.125, 0.13),
        (2.675, 2.68),
        (-2.675, -2.67),
        (-0.125, -0.12),
        (7.0, 7.0),
        # 1.005 * 100 is 100.49999… in binary, so both languages land on 1.0, not 1.01.
        (1.005, 1.0),
    ],
)
def test_round_matches_javascript_math_round(value: float, expected: float) -> None:
    from learning_commons_evaluators.features.preprocessing import _round

    assert ROUND_2.post_transform is not None
    assert _round(value, ROUND_2.post_transform) == expected


def test_without_a_transform_the_raw_value_is_returned() -> None:
    impl = Implementation(library="textstat", function="flesch_kincaid_grade")
    assert run_preprocessing_step(TEXT, impl) == textstat.flesch_kincaid_grade(TEXT)


def test_unknown_library_function_and_transform_fail_loudly() -> None:
    # NotImplementedError, not a provider error: the gap is this SDK's, and evaluators check
    # it at class creation so it never reaches the evaluation's error boundary.
    with pytest.raises(
        NotImplementedError, match='Unsupported preprocessing library "nltk". Supported: textstat'
    ):
        run_preprocessing_step(TEXT, Implementation(library="nltk", function="f"))
    with pytest.raises(NotImplementedError, match='Function "nope" not found in textstat'):
        run_preprocessing_step(TEXT, Implementation(library="textstat", function="nope"))
    impl = Implementation.model_validate(
        {
            "library": "textstat",
            "function": "flesch_kincaid_grade",
            "post_transform": {"type": "floor"},
        }
    )
    with pytest.raises(NotImplementedError, match='Unsupported post_transform type "floor"'):
        run_preprocessing_step(TEXT, impl)


@pytest.mark.parametrize(
    ("value", "rendered"), [(7.0, "7"), (7.1, "7.1"), (7.15, "7.15"), (0.0, "0"), (-2.62, "-2.62")]
)
def test_format_number_matches_javascript_string(value: float, rendered: str) -> None:
    assert format_number(value) == rendered


class TestRoundHalfUp:
    """The SDK's one rounding operation, shared by the contract transform and features/."""

    @pytest.mark.parametrize(
        ("value", "places", "expected"),
        [
            (0.125, 2, 0.13),  # Python's round() gives 0.12
            (0.135, 2, 0.14),
            (0.95, 1, 1.0),  # 19/20: ties-to-even gives 0.9
            (2.5, 0, 3.0),
            (-0.125, 2, -0.12),  # half up, so toward zero for a negative tie
            (7.0, 2, 7.0),
        ],
    )
    def test_rounds_half_away_from_negative_infinity(
        self, value: float, places: int, expected: float
    ) -> None:
        assert round_half_up(value, places) == expected

    def test_is_what_the_contracts_post_transform_applies(self) -> None:
        implementation = Implementation.model_validate(
            {
                "library": "textstat",
                "function": "flesch_kincaid_grade",
                "post_transform": {"type": "round", "precision": 2},
            }
        )
        text = "The cat sat on the mat. It was sleeping quietly in the warm sun."
        assert run_preprocessing_step(text, implementation) == round_half_up(
            textstat.flesch_kincaid_grade(text), 2
        )
