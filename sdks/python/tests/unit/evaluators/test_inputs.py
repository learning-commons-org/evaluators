"""Input validation in the order and wording §4.1 fixes, driven by the declared schema."""

from __future__ import annotations

from typing import Any

import pytest

from learning_commons_evaluators.errors import InputValidationError
from learning_commons_evaluators.evaluators.inputs import primary_text_field, validate_inputs

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


PASSAGE_SCHEMA = {
    "properties": {
        "source_passages": {
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#/$defs/SourcePassage"},
        }
    },
    "required": ["source_passages"],
    "$defs": {
        "SourcePassage": {
            "type": "object",
            "additionalProperties": False,
            "required": ["text"],
            "properties": {
                "title": {"type": "string", "minLength": 1},
                "author": {"type": "string", "minLength": 1},
                "text": {"type": "string", "minLength": 1},
            },
        }
    },
}


def test_array_of_objects_binds_as_json() -> None:
    passages = [{"text": "A passage."}, {"title": "A title", "text": "Another."}]
    bound = validate_inputs({"source_passages": passages}, PASSAGE_SCHEMA)["source_passages"]
    assert bound == '[{"text":"A passage."},{"title":"A title","text":"Another."}]'
    assert bound != str(passages)


def test_array_rejects_shape_mistakes() -> None:
    with pytest.raises(InputValidationError, match="source_passages must be an array."):
        validate_inputs({"source_passages": "A passage."}, PASSAGE_SCHEMA)
    with pytest.raises(InputValidationError, match="source_passages must contain at least 1 item."):
        validate_inputs({"source_passages": []}, PASSAGE_SCHEMA)
    with pytest.raises(InputValidationError, match=r"source_passages\[0\].text is required."):
        validate_inputs({"source_passages": [{"title": "Only a title"}]}, PASSAGE_SCHEMA)
    with pytest.raises(InputValidationError, match="title cannot be empty"):
        validate_inputs(
            {"source_passages": [{"title": "  ", "text": "A passage."}]}, PASSAGE_SCHEMA
        )
    with pytest.raises(InputValidationError, match=r'Unknown input "source_passages\[0\].note"'):
        validate_inputs(
            {"source_passages": [{"text": "A passage.", "note": "nope"}]}, PASSAGE_SCHEMA
        )


def test_primary_text_field_is_the_first_non_enum_string() -> None:
    assert primary_text_field(SCHEMA) == "text"
    assert (
        primary_text_field({"properties": {"grade_level": {"type": "string", "enum": ["3"]}}})
        is None
    )
