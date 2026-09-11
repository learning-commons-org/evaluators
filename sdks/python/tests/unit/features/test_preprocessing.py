"""Contract-declared computations dispatch to the library the contract names."""

from __future__ import annotations

import pytest
import textstat

from learning_commons_evaluators.contracts.loader import Implementation
from learning_commons_evaluators.features import format_number, run_preprocessing_step

TEXT = "Trees are important plants that grow in many parts of the world."


def test_runs_textstat_by_function_name_and_rounds() -> None:
    impl = Implementation.model_validate(
        {
            "library": "textstat",
            "function": "flesch_kincaid_grade",
            "post_transform": {"type": "round", "precision": 2},
        }
    )
    assert run_preprocessing_step(TEXT, impl) == round(textstat.flesch_kincaid_grade(TEXT), 2)


def test_without_a_transform_the_raw_value_is_returned() -> None:
    impl = Implementation(library="textstat", function="flesch_kincaid_grade")
    assert run_preprocessing_step(TEXT, impl) == textstat.flesch_kincaid_grade(TEXT)


def test_unknown_library_function_and_transform_fail_loudly() -> None:
    with pytest.raises(
        ValueError, match='Unsupported preprocessing library "nltk". Supported: textstat'
    ):
        run_preprocessing_step(TEXT, Implementation(library="nltk", function="f"))
    with pytest.raises(ValueError, match='Function "nope" not found in textstat'):
        run_preprocessing_step(TEXT, Implementation(library="textstat", function="nope"))
    impl = Implementation.model_validate(
        {
            "library": "textstat",
            "function": "flesch_kincaid_grade",
            "post_transform": {"type": "floor"},
        }
    )
    with pytest.raises(ValueError, match='Unsupported post_transform type "floor"'):
        run_preprocessing_step(TEXT, impl)


@pytest.mark.parametrize(
    ("value", "rendered"), [(7.0, "7"), (7.1, "7.1"), (7.15, "7.15"), (0.0, "0"), (-2.62, "-2.62")]
)
def test_format_number_matches_javascript_string(value: float, rendered: str) -> None:
    assert format_number(value) == rendered
