"""The contract generator: bundling rules and the JSON Schema → pydantic emitter."""

from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any, get_args

import pytest
from pydantic import BaseModel, ValidationError

SDK_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = SDK_ROOT.parent.parent


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "generate_contracts", SDK_ROOT / "scripts" / "generate_contracts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # ``dataclasses`` resolves a class's module through ``sys.modules`` while decorating.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generator = _load_generator()


def _exec_module(source: str) -> dict[str, Any]:
    # A real module registered in sys.modules: with ``from __future__ import annotations``
    # pydantic resolves the generated forward references through the class's module.
    module = ModuleType(f"generated_under_test_{uuid.uuid4().hex}")
    sys.modules[module.__name__] = module
    exec(compile(source, "<generated>", "exec"), module.__dict__)  # noqa: S102 — our own output
    return module.__dict__


def _write_contract(
    directory: Path,
    *,
    evaluator_id: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "input_schema.json").write_text(json.dumps(input_schema))
    (directory / "output_schema.json").write_text(json.dumps(output_schema))
    config = {
        "$schema": "../../../_schemas/config.schema.json",
        "evaluator": {
            "id": evaluator_id,
            "stable_id": "00000000-0000-0000-0000-000000000000",
            "name": "Widget Evaluator",
            "description": "d",
            "supported_grades": ["3"],
        },
        "input_schema": {"$ref": "input_schema.json"},
        "output_schema": {"$ref": "output_schema.json"},
        "steps": [],
    }
    (directory / "config.json").write_text(json.dumps(config))
    return directory / "config.json"


class TestNaming:
    def test_pascal_case(self) -> None:
        assert (
            generator.to_pascal_case("grade_level_appropriateness") == "GradeLevelAppropriateness"
        )
        assert generator.to_pascal_case("grade-level") == "GradeLevel"

    def test_upper_snake(self) -> None:
        assert generator.to_upper_snake("grade_level") == "GRADE_LEVEL"

    def test_quote_is_double_quoted_and_keeps_unicode(self) -> None:
        assert generator._quote("it's — fine") == '"it\'s — fine"'
        assert generator._quote(3) == "3"


class TestEmitter:
    INPUT = {
        "type": "object",
        "required": ["text", "grade_level", "jurisdiction", "source_count"],
        "additionalProperties": False,
        "properties": {
            "text": {
                "type": "string",
                "minLength": 10,
                "maxLength": 100,
                "description": "The passage.",
            },
            "grade_level": {"type": "string", "enum": ["3", "4"]},
            "jurisdiction": {"type": "string", "enum": ["Multi-State", "Ohio"]},
            "source_count": {"type": "integer", "minimum": 1},
            "in": {"type": "string"},
        },
    }
    OUTPUT = {
        "type": "object",
        "required": ["level", "items", "score", "note", "nested"],
        "additionalProperties": False,
        "description": "Root description is a maintainer note and is dropped.",
        "properties": {
            "level": {"$ref": "#/$defs/Level", "description": "Sibling wins."},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["quote"],
                    "additionalProperties": False,
                    "properties": {"quote": {"type": "string"}},
                },
            },
            "score": {"type": "integer", "enum": [0, 1]},
            "note": {"type": ["string", "null"]},
            "count": {"type": "integer", "minimum": 0},
            "nested": {"$ref": "#/$defs/Nested"},
        },
        "$defs": {
            "Level": {"type": "string", "enum": ["low", "high"], "description": "Ordered."},
            "Nested": {
                "type": "object",
                "required": ["level"],
                "additionalProperties": False,
                "properties": {"level": {"$ref": "#/$defs/Level"}},
            },
        },
    }

    @pytest.fixture
    def module(self, tmp_path: Path) -> dict[str, Any]:
        config_path = _write_contract(
            tmp_path / "widgets" / "gadgets" / "widget",
            evaluator_id="widgets.gadgets.widget",
            input_schema=self.INPUT,
            output_schema=self.OUTPUT,
        )
        config = json.loads(config_path.read_text())
        source = generator.emit_schema_module(config, config_path.parent)
        assert source.startswith(generator.GENERATED_MARKER)
        return _exec_module(source)

    def test_input_model_uses_placeholder_names_with_int_grade_and_no_bounds(
        self, module: dict[str, Any]
    ) -> None:
        widget_input = module["WidgetInput"]
        fields = widget_input.model_fields
        assert set(fields) == {"text", "grade_level", "jurisdiction", "source_count", "in_"}
        assert fields["grade_level"].annotation is int
        assert fields["jurisdiction"].annotation is str
        assert fields["source_count"].annotation is int
        assert fields["in_"].alias == "in"
        # Bounds and enums are the evaluator's to enforce with canonical messages, not
        # pydantic's; a 5-character text constructs fine here.
        instance = widget_input(text="short", grade_level=99, jurisdiction="Mars", source_count=0)
        assert instance.grade_level == 99
        assert module["GRADE_LEVEL_VALUES"] == ("3", "4")
        assert module["JURISDICTION_VALUES"] == ("Multi-State", "Ohio")
        assert module["EVALUATOR_ID"] == "widgets.gadgets.widget"

    def test_input_model_is_frozen_and_forbids_extras(self, module: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            module["WidgetInput"](
                text="t", grade_level=3, jurisdiction="Ohio", source_count=1, extra=1
            )

    def test_output_model_shape(self, module: dict[str, Any]) -> None:
        output = module["WidgetOutput"]
        assert issubclass(output, BaseModel)
        fields = output.model_fields
        assert fields["level"].description == "Sibling wins."
        assert fields["count"].is_required() is False
        assert fields["note"].is_required() is True
        assert get_args(fields["items"].annotation) == (module["ItemsItem"],)
        assert issubclass(module["Nested"], BaseModel)
        assert "Root description" not in (output.__doc__ or "")

    def test_output_model_validates_and_rejects(self, module: dict[str, Any]) -> None:
        output = module["WidgetOutput"]
        payload = {
            "level": "low",
            "items": [{"quote": "q"}],
            "score": 1,
            "note": None,
            "nested": {"level": "high"},
        }
        parsed = output.model_validate(payload)
        assert parsed.count is None
        assert parsed.nested.level == "high"
        for bad in (
            {**payload, "level": "medium"},
            {**payload, "score": 2},
            {**payload, "count": -1},
            {**payload, "extra": "x"},
            {k: v for k, v in payload.items() if k != "note"},
        ):
            with pytest.raises(ValidationError):
                output.model_validate(bad)

    def test_output_json_schema_is_strict(self, module: dict[str, Any]) -> None:
        schema = module["WidgetOutput"].model_json_schema()
        assert schema["additionalProperties"] is False
        assert schema["$defs"]["ItemsItem"]["additionalProperties"] is False

    def test_unsupported_ref_fails_loudly(self, tmp_path: Path) -> None:
        output = {"type": "object", "properties": {"x": {"$ref": "other.json#/Thing"}}}
        config_path = _write_contract(
            tmp_path / "a" / "b" / "c",
            evaluator_id="a.b.c",
            input_schema={"type": "object", "properties": {}},
            output_schema=output,
        )
        with pytest.raises(ValueError, match="Unsupported \\$ref"):
            generator.emit_schema_module(json.loads(config_path.read_text()), config_path.parent)


class TestBundling:
    def test_discovers_every_registry_contract(self) -> None:
        paths = generator.discover_contracts()
        assert len(paths) == len(list((REPO_ROOT / "evals").glob("*/*/*/config.json")))
        assert paths == sorted(paths)

    def test_sha256_drift_fails_the_build(self, tmp_path: Path) -> None:
        directory = tmp_path / "a" / "b" / "c"
        config_path = _write_contract(
            directory,
            evaluator_id="a.b.c",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
        )
        (directory / "system.txt").write_text("edited prompt")
        config = json.loads(config_path.read_text())
        config["steps"] = [
            {
                "id": "s",
                "type": "llm",
                "prompt": {
                    "messages": [
                        {"role": "system", "source_path": "system.txt", "sha256": "0" * 64}
                    ],
                    "placeholders": {},
                },
            }
        ]
        config_path.write_text(json.dumps(config))
        with pytest.raises(SystemExit, match="sha256 drift"):
            generator.plan_contract(config_path)

    def test_committed_files_are_up_to_date(self) -> None:
        # The same assertion CI makes with ``make check-generated``: the bundle and the
        # schema modules match evals/ exactly, and nothing generated is orphaned.
        planned = generator.plan_all(generator.discover_contracts())
        for item in planned:
            assert item.path.exists(), item.path
            assert item.path.read_bytes() == item.content, item.path
        assert generator.existing_generated_files() == {item.path for item in planned}
