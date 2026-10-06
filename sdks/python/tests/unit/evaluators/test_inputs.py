"""Input validation in the order and wording §4.1 fixes, driven by the declared schema."""

from __future__ import annotations

from typing import Any

import pytest

from learning_commons_evaluators.errors import InputValidationError
from learning_commons_evaluators.evaluators.inputs import (
    primary_text_field,
    text_inputs,
    validate_inputs,
)

SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["text", "grade_level"],
    "properties": {
        "text": {"type": "string", "minLength": 10, "maxLength": 20},
        "grade_level": {"type": "string", "enum": ["3", "4", "5"]},
        "note": {"type": "string"},
        "count": {"type": "integer", "minimum": 1},
    },
}

GOOD = {"text": "twelve chars", "grade_level": "4"}


def test_returns_canonical_string_values() -> None:
    assert validate_inputs(GOOD, SCHEMA) == GOOD


def test_renders_an_int_grade_as_its_token() -> None:
    # The idiomatic convenience (§2.3): Python callers pass an int, the prompt binds "4".
    assert validate_inputs({**GOOD, "grade_level": 4}, SCHEMA)["grade_level"] == "4"


def test_an_int_is_not_accepted_for_a_free_text_field() -> None:
    with pytest.raises(InputValidationError, match="text must be a string."):
        validate_inputs({**GOOD, "text": 12345678901}, SCHEMA)


def test_rejects_a_non_mapping() -> None:
    with pytest.raises(InputValidationError, match="Expected a mapping of inputs, received str"):
        validate_inputs("hello", SCHEMA)


def test_rejects_an_unknown_key_naming_the_accepted_ones() -> None:
    with pytest.raises(
        InputValidationError,
        match='Unknown input "grade". This evaluator accepts: text, grade_level, note, count.',
    ):
        validate_inputs({**GOOD, "grade": "4"}, SCHEMA)


def test_required_fields_are_checked_first_in_declared_order() -> None:
    # Two faults: a missing required field and a bad optional one. The required one wins.
    with pytest.raises(InputValidationError, match="text is required."):
        validate_inputs({"grade_level": "4", "count": 0}, SCHEMA)


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("   ", "text cannot be empty or contain only whitespace"),
        ("short", "text is too short. Minimum length is 10 characters."),
        ("x" * 21, "text is too long. Maximum length is 20 characters."),
    ],
)
def test_text_checks_in_order(value: str, message: str) -> None:
    with pytest.raises(InputValidationError, match=message):
        validate_inputs({**GOOD, "text": value}, SCHEMA)


def test_length_is_measured_as_supplied_not_trimmed() -> None:
    # Trimming only decides blankness; the caller's text is what reaches the model.
    assert validate_inputs({**GOOD, "text": "  ten chars  "}, SCHEMA)["text"] == "  ten chars  "


def test_enum_violation_lists_the_accepted_values() -> None:
    with pytest.raises(
        InputValidationError, match='Invalid grade_level "9". Accepted values: 3, 4, 5.'
    ):
        validate_inputs({**GOOD, "grade_level": "9"}, SCHEMA)


def test_optional_fields_may_be_omitted_or_none() -> None:
    assert "note" not in validate_inputs({**GOOD, "note": None}, SCHEMA)


def test_integer_fields() -> None:
    assert validate_inputs({**GOOD, "count": 3}, SCHEMA)["count"] == "3"
    with pytest.raises(InputValidationError, match="count must be an integer."):
        validate_inputs({**GOOD, "count": "3"}, SCHEMA)
    with pytest.raises(InputValidationError, match="count must be an integer."):
        validate_inputs({**GOOD, "count": True}, SCHEMA)
    with pytest.raises(InputValidationError, match="count must be at least 1."):
        validate_inputs({**GOOD, "count": 0}, SCHEMA)


def test_primary_text_field_is_the_first_non_enum_string() -> None:
    assert primary_text_field(SCHEMA) == "text"
    assert (
        primary_text_field({"properties": {"grade_level": {"type": "string", "enum": ["3"]}}})
        is None
    )


#: The shape an attached input takes: a bounded array of non-blank paths.
ARRAY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["figures", "claim"],
    "properties": {
        "figures": {
            "type": "array",
            "minItems": 1,
            "maxItems": 2,
            "items": {"type": "string", "minLength": 1},
        },
        "claim": {"type": "string", "minLength": 1},
    },
}


class TestArrayInputs:
    def test_returns_the_items_in_order_as_a_tuple(self) -> None:
        values = validate_inputs({"figures": ["a.png", "b.png"], "claim": "c"}, ARRAY_SCHEMA)
        assert values == {"figures": ("a.png", "b.png"), "claim": "c"}

    def test_accepts_a_tuple_as_readily_as_a_list(self) -> None:
        values = validate_inputs({"figures": ("a.png",), "claim": "c"}, ARRAY_SCHEMA)
        assert values["figures"] == ("a.png",)

    @pytest.mark.parametrize("value", ["a.png", {"a.png"}, {"path": "a.png"}, 3])
    def test_rejects_anything_but_a_list_or_tuple(self, value: object) -> None:
        # A bare string most of all: it is the mistake of passing one path for an array.
        with pytest.raises(InputValidationError, match=r"^figures must be an array\.$"):
            validate_inputs({"figures": value, "claim": "c"}, ARRAY_SCHEMA)

    def test_counts_against_min_and_max_items_with_the_typescript_wording(self) -> None:
        with pytest.raises(
            InputValidationError, match=r"^figures needs at least 1 item; received 0\.$"
        ):
            validate_inputs({"figures": [], "claim": "c"}, ARRAY_SCHEMA)
        with pytest.raises(
            InputValidationError, match=r"^figures accepts at most 2 items; received 3\.$"
        ):
            validate_inputs({"figures": ["a", "b", "c"], "claim": "c"}, ARRAY_SCHEMA)

    def test_checks_each_item_as_a_string_named_by_its_position(self) -> None:
        with pytest.raises(InputValidationError, match=r"^figures\[1\] must be a string\.$"):
            validate_inputs({"figures": ["a.png", 7], "claim": "c"}, ARRAY_SCHEMA)
        with pytest.raises(
            InputValidationError,
            match=r"^figures\[0\] cannot be empty or contain only whitespace$",
        ):
            validate_inputs({"figures": ["   "], "claim": "c"}, ARRAY_SCHEMA)

    def test_visits_the_array_in_declared_order(self) -> None:
        # Required first, as declared: a bad array is reported before a bad claim after it.
        with pytest.raises(InputValidationError, match="^figures"):
            validate_inputs({"figures": [], "claim": " "}, ARRAY_SCHEMA)

    def test_an_array_of_anything_but_strings_is_a_contract_fault(self) -> None:
        schema = {
            "required": ["counts"],
            "properties": {"counts": {"type": "array", "items": {"type": "integer"}}},
        }
        with pytest.raises(ValueError, match="array of integer; only arrays of strings") as caught:
            validate_inputs({"counts": [1]}, schema)
        assert not isinstance(caught.value, InputValidationError)

    def test_text_inputs_keeps_only_what_a_prompt_can_bind(self) -> None:
        values = validate_inputs({"figures": ["a.png"], "claim": "c"}, ARRAY_SCHEMA)
        assert text_inputs(values) == {"claim": "c"}

    def test_the_primary_text_is_never_an_array(self) -> None:
        assert primary_text_field(ARRAY_SCHEMA) == "claim"
