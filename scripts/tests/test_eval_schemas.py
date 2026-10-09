"""The eval-schemas input-shape rule: the shapes contracts use pass, everything else fails."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from checks.eval_schemas import input_shape_problems  # noqa: E402

X_IMAGE = {
    "formats": ["image/png"],
    "detect": "signature",
    "min_bytes": 1,
    "max_bytes": 10,
    "min_edge": 1,
    "max_edge": 10,
}

#: Every supported shape at once.
SUPPORTED = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "input_schema.json",
    "title": "EvaluatorInput",
    "description": "Inputs.",
    "type": "object",
    "required": ["text", "grade_level", "count", "image_paths"],
    "additionalProperties": False,
    "properties": {
        "text": {
            "type": "string",
            "minLength": 1,
            "maxLength": 10,
            "description": "Text.",
        },
        "grade_level": {"type": "string", "enum": ["3", "4"]},
        "count": {"type": "integer", "minimum": 1, "maximum": 4},
        "image_paths": {
            "type": "array",
            "minItems": 1,
            "maxItems": 2,
            "items": {"type": "string", "minLength": 1, "x-image": X_IMAGE},
        },
    },
    "$defs": {
        "SourcePassage": {
            "type": "object",
            "title": "SourcePassage",
            "additionalProperties": False,
            "required": ["text"],
            "properties": {
                "title": {"type": "string", "minLength": 1},
                "text": {"type": "string", "minLength": 1, "maxLength": 100},
            },
        }
    },
}


def with_property(name: str, spec: object) -> dict:
    doc = copy.deepcopy(SUPPORTED)
    doc["properties"][name] = spec
    return doc


def with_passage_field(name: str, spec: object) -> dict:
    doc = copy.deepcopy(SUPPORTED)
    doc["$defs"]["SourcePassage"]["properties"][name] = spec
    return doc


class SupportedShapes(unittest.TestCase):
    def test_every_supported_shape_passes(self) -> None:
        self.assertEqual(input_shape_problems(SUPPORTED), [])

    def test_the_x_image_block_is_left_to_its_own_rule(self) -> None:
        doc = copy.deepcopy(SUPPORTED)
        doc["properties"]["image_paths"]["items"]["x-image"] = {"anything": True}
        self.assertEqual(input_shape_problems(doc), [])

    def test_an_optional_top_level_property(self) -> None:
        # Graphics Complexity ships `figure_labels` outside `required`. Both SDKs skip
        # a missing field that the schema does not require.
        doc = copy.deepcopy(SUPPORTED)
        doc["required"].remove("count")
        self.assertEqual(input_shape_problems(doc), [])


class RejectedShapes(unittest.TestCase):
    def assert_rejected(self, doc: dict, message: str) -> None:
        self.assertIn(message, input_shape_problems(doc))

    def test_a_root_that_is_not_an_object(self) -> None:
        self.assertEqual(
            input_shape_problems(True),
            ["(root): an input schema must be an object schema"],
        )
        doc = copy.deepcopy(SUPPORTED)
        doc["type"] = "array"
        self.assert_rejected(doc, "(root): an input schema must have type object")

    def test_an_unsupported_root_keyword(self) -> None:
        doc = copy.deepcopy(SUPPORTED)
        doc["patternProperties"] = {}
        self.assert_rejected(
            doc, "(root): patternProperties is not supported in an input schema"
        )

    def test_unsupported_top_level_types(self) -> None:
        for kind in ("number", "boolean", "null", "object"):
            with self.subTest(kind=kind):
                self.assert_rejected(
                    with_property("x", {"type": kind}),
                    f"properties/x: type {kind!r} is not supported",
                )

    def test_a_union_or_missing_type(self) -> None:
        self.assert_rejected(
            with_property("x", {"type": ["string", "null"]}),
            "properties/x: type ['string', 'null'] is not supported",
        )
        self.assert_rejected(
            with_property("x", {"anyOf": [{"type": "string"}]}),
            "properties/x: type None is not supported",
        )

    def test_unsupported_keywords_on_a_top_level_field(self) -> None:
        cases = [
            ({"type": "string", "pattern": "a"}, "pattern"),
            ({"type": "string", "format": "uri"}, "format"),
            ({"type": "string", "const": "a"}, "const"),
            ({"type": "string", "default": "a"}, "default"),
            ({"type": "integer", "enum": [1, 2]}, "enum"),
            (
                {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
                "uniqueItems",
            ),
        ]
        for spec, keyword in cases:
            with self.subTest(keyword=keyword):
                self.assert_rejected(
                    with_property("x", spec),
                    f"properties/x: {keyword} is not supported in an input schema",
                )

    def test_a_string_enum_with_non_string_values(self) -> None:
        self.assert_rejected(
            with_property("x", {"type": "string", "enum": ["3", 4]}),
            "properties/x: enum values must be strings",
        )

    def test_an_array_without_items(self) -> None:
        self.assert_rejected(
            with_property("x", {"type": "array"}),
            "properties/x/items: an array input must declare its items",
        )

    def test_unsupported_item_types(self) -> None:
        for kind in ("integer", "number", "boolean", "object", "array"):
            with self.subTest(kind=kind):
                self.assert_rejected(
                    with_property("x", {"type": "array", "items": {"type": kind}}),
                    f"properties/x/items: {kind} items are not supported",
                )

    def test_an_enum_on_string_items(self) -> None:
        self.assert_rejected(
            with_property(
                "x", {"type": "array", "items": {"type": "string", "enum": ["a"]}}
            ),
            "properties/x/items: enum is not supported in an input schema",
        )

    def test_a_ref_array_is_not_supported_on_this_branch(self) -> None:
        self.assert_rejected(
            with_property(
                "x", {"type": "array", "items": {"$ref": "#/$defs/SourcePassage"}}
            ),
            "properties/x/items: $ref items are not supported",
        )

    def test_a_required_entry_that_is_not_a_property(self) -> None:
        doc = copy.deepcopy(SUPPORTED)
        doc["required"].append("missing")
        self.assert_rejected(doc, "(root): required entry 'missing' is not a property")

    def test_a_def_required_entry_that_is_not_a_property(self) -> None:
        doc = copy.deepcopy(SUPPORTED)
        doc["$defs"]["SourcePassage"]["required"].append("missing")
        self.assert_rejected(
            doc, "$defs/SourcePassage: required entry 'missing' is not a property"
        )

    def test_additional_properties_must_be_false(self) -> None:
        for where, edit in (
            ("(root)", lambda doc: doc.pop("additionalProperties")),
            (
                "$defs/SourcePassage",
                lambda doc: doc["$defs"]["SourcePassage"].pop("additionalProperties"),
            ),
        ):
            with self.subTest(where=where):
                doc = copy.deepcopy(SUPPORTED)
                edit(doc)
                self.assert_rejected(
                    doc, f"{where}: additionalProperties must be false"
                )

    def test_a_def_name_that_is_not_pascal_case(self) -> None:
        doc = copy.deepcopy(SUPPORTED)
        doc["$defs"]["source-passage"] = doc["$defs"].pop("SourcePassage")
        self.assert_rejected(
            doc, "$defs/source-passage: definition names must be PascalCase identifiers"
        )

    def test_a_def_that_is_not_an_object(self) -> None:
        doc = copy.deepcopy(SUPPORTED)
        doc["$defs"]["Code"] = {"type": "string"}
        self.assert_rejected(doc, "$defs/Code: only object definitions are supported")

    def test_an_unsupported_keyword_on_a_def(self) -> None:
        doc = copy.deepcopy(SUPPORTED)
        doc["$defs"]["SourcePassage"]["minProperties"] = 1
        self.assert_rejected(
            doc,
            "$defs/SourcePassage: minProperties is not supported in an input schema",
        )

    def test_unsupported_object_field_types(self) -> None:
        for kind in ("integer", "number", "boolean", "array", "object"):
            with self.subTest(kind=kind):
                self.assert_rejected(
                    with_passage_field("x", {"type": kind}),
                    f"$defs/SourcePassage/properties/x: {kind} fields are not supported",
                )

    def test_an_enum_on_an_object_field(self) -> None:
        self.assert_rejected(
            with_passage_field("x", {"type": "string", "enum": ["a"]}),
            "$defs/SourcePassage/properties/x: enum is not supported in an input schema",
        )


if __name__ == "__main__":
    unittest.main()
