"""The telemetry event schema, its generator, and the schema_version ↔ wire-shape rule."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jsonschema import Draft202012Validator  # noqa: E402

import generate_telemetry_schema as gen  # noqa: E402
from checks.telemetry_schema import TelemetrySchema, gitattributes_problems  # noqa: E402

ORACLE = gen.REPO_ROOT / "sdks" / "typescript" / "tests" / "fixtures" / "telemetry-events.json"


def schema() -> dict:
    return gen.load_schema()


class TheCommittedSchema(unittest.TestCase):
    def test_passes_the_check(self) -> None:
        result = TelemetrySchema().run(fix=False)
        self.assertEqual([v.render() for v in result.violations], [])

    def test_renders_with_no_problems(self) -> None:
        self.assertEqual(gen.schema_problems(schema()), [])

    def test_every_oracle_event_conforms(self) -> None:
        # The oracle is what the TypeScript SDK actually emits; the schema must accept it.
        # Masked values are strings, so they are swapped for in-range stand-ins first.
        validator = Draft202012Validator(schema())
        stand_ins = {"timestamp": "x", "sdk_version": "x", "sdk_language": "typescript"}
        for case in json.loads(ORACLE.read_text(encoding="utf-8")):
            event = {**case["event"], **stand_ins, "latency_ms": 0}
            errors = [e.message for e in validator.iter_errors(event)]
            self.assertEqual(errors, [], case["id"])


class SchemaProblems(unittest.TestCase):
    def assertProblem(self, broken: dict, fragment: str) -> None:
        problems = gen.schema_problems(broken)
        self.assertTrue(
            any(fragment in p for p in problems), f"no problem mentions {fragment!r}: {problems}"
        )

    def test_an_open_object_is_rejected(self) -> None:
        broken = schema()
        broken["$defs"]["StageDetail"]["additionalProperties"] = True
        self.assertProblem(broken, "additionalProperties must be false")

    def test_an_open_root_is_rejected(self) -> None:
        broken = schema()
        del broken["additionalProperties"]
        self.assertProblem(broken, "(root): additionalProperties must be false")

    def test_a_camel_case_property_is_rejected(self) -> None:
        broken = schema()
        broken["properties"]["latencyMs"] = {"type": "integer"}
        self.assertProblem(broken, "snake_case")

    def test_an_unsupported_keyword_is_rejected(self) -> None:
        broken = schema()
        broken["properties"]["grade"]["maxLength"] = 3
        self.assertProblem(broken, "maxLength is not supported")

    def test_a_dangling_ref_is_rejected(self) -> None:
        broken = schema()
        broken["properties"]["status"] = {"$ref": "#/$defs/Nope"}
        self.assertProblem(broken, "names no $defs entry")

    def test_a_required_name_that_is_not_a_property_is_rejected(self) -> None:
        broken = schema()
        broken["required"].append("nope")
        self.assertProblem(broken, "'nope', which is not a property")

    def test_schema_version_must_be_a_pinned_integer(self) -> None:
        broken = schema()
        del broken["properties"]["schema_version"]["const"]
        self.assertProblem(broken, "schema_version")

    def test_a_metadata_block_must_be_typed(self) -> None:
        broken = schema()
        broken["$defs"]["TelemetryMetadata"]["properties"]["graphics"] = {"type": "string"}
        self.assertProblem(broken, "metadata/graphics: a metadata block must be")

    def test_a_metadata_block_must_be_optional(self) -> None:
        broken = schema()
        broken["$defs"]["TelemetryMetadata"]["required"] = ["stage_details"]
        self.assertProblem(broken, "every metadata block must be optional")

    def test_metadata_itself_must_be_optional(self) -> None:
        broken = schema()
        broken["required"].append("metadata")
        self.assertProblem(broken, "metadata: must be optional")

    def test_build_model_refuses_a_broken_schema(self) -> None:
        broken = schema()
        broken["additionalProperties"] = True
        with self.assertRaises(ValueError):
            gen.build_model(broken)


class WireShapeHash(unittest.TestCase):
    def test_ignores_annotations(self) -> None:
        reworded = schema()
        reworded["description"] = "something else"
        reworded["properties"]["grade"]["description"] = "reworded"
        self.assertEqual(gen.wire_shape_hash(reworded), gen.wire_shape_hash(schema()))

    def test_ignores_the_version_number_itself(self) -> None:
        bumped = schema()
        bumped["properties"]["schema_version"]["const"] = 99
        self.assertEqual(gen.wire_shape_hash(bumped), gen.wire_shape_hash(schema()))

    def test_ignores_key_order_outside_properties(self) -> None:
        shuffled = schema()
        shuffled["$defs"]["TokenUsage"] = dict(reversed(shuffled["$defs"]["TokenUsage"].items()))
        self.assertEqual(gen.wire_shape_hash(shuffled), gen.wire_shape_hash(schema()))

    def test_sees_property_order(self) -> None:
        reordered = schema()
        reordered["properties"] = dict(reversed(reordered["properties"].items()))
        self.assertNotEqual(gen.wire_shape_hash(reordered), gen.wire_shape_hash(schema()))

    def test_sees_a_new_field(self) -> None:
        grown = schema()
        grown["properties"]["run_id"] = {"type": "string"}
        self.assertNotEqual(gen.wire_shape_hash(grown), gen.wire_shape_hash(schema()))

    def test_sees_a_property_named_like_an_annotation(self) -> None:
        grown = schema()
        grown["$defs"]["StageDetail"]["properties"]["description"] = {"type": "string"}
        self.assertNotEqual(gen.wire_shape_hash(grown), gen.wire_shape_hash(schema()))

    def test_ignores_the_order_of_required(self) -> None:
        # A set in JSON Schema: reversing it renders identical SDK code.
        reordered = schema()
        reordered["required"] = list(reversed(reordered["required"]))
        reordered["$defs"]["StageDetail"]["required"].reverse()
        self.assertEqual(gen.wire_shape_hash(reordered), gen.wire_shape_hash(schema()))
        self.assertEqual(
            gen.render_typescript(gen.build_model(reordered)),
            gen.render_typescript(gen.build_model(schema())),
        )

    def test_ignores_the_order_of_an_enum(self) -> None:
        reordered = schema()
        reordered["$defs"]["EvaluationStatus"]["enum"].reverse()
        self.assertEqual(gen.wire_shape_hash(reordered), gen.wire_shape_hash(schema()))

    def test_still_sees_a_change_to_required(self) -> None:
        loosened = schema()
        loosened["required"].remove("grade")
        self.assertNotEqual(gen.wire_shape_hash(loosened), gen.wire_shape_hash(schema()))

    def test_still_sees_a_change_to_an_enum(self) -> None:
        grown = schema()
        grown["$defs"]["EvaluationStatus"]["enum"].append("partial")
        self.assertNotEqual(gen.wire_shape_hash(grown), gen.wire_shape_hash(schema()))

    def test_a_property_named_like_an_unordered_keyword_keeps_its_subschema(self) -> None:
        # Inside ``properties``, ``required`` is a property name; its subschema is hashed
        # like any other, not sorted as if it were the keyword's set.
        first = schema()
        first["$defs"]["StageDetail"]["properties"]["required"] = {"type": "string"}
        second = schema()
        second["$defs"]["StageDetail"]["properties"]["required"] = {"type": "boolean"}
        self.assertNotEqual(gen.wire_shape_hash(first), gen.wire_shape_hash(second))


class VersionProblems(unittest.TestCase):
    def setUp(self) -> None:
        self.versions = {1: gen.wire_shape_hash(schema())}

    def grown(self, version: int) -> dict:
        changed = copy.deepcopy(schema())
        changed["properties"]["run_id"] = {"type": "string"}
        changed["properties"]["schema_version"]["const"] = version
        return changed

    def test_the_recorded_version_and_shape_pass(self) -> None:
        self.assertEqual(gen.version_problems(schema(), self.versions), ([], False))

    def test_a_shape_change_without_a_bump_fails_and_is_not_fixable(self) -> None:
        problems, fixable = gen.version_problems(self.grown(1), self.versions)
        self.assertIn("bump it to 2", problems[0])
        self.assertIn("Do not re-record version 1's hash", problems[0])
        self.assertFalse(fixable)

    def test_a_genuine_bump_is_fixable(self) -> None:
        problems, fixable = gen.version_problems(self.grown(2), self.versions)
        self.assertEqual(len(problems), 1)
        self.assertTrue(fixable)

    def test_a_bump_with_no_shape_change_fails(self) -> None:
        bumped = schema()
        bumped["properties"]["schema_version"]["const"] = 2
        problems, fixable = gen.version_problems(bumped, self.versions)
        self.assertIn("wire shape is unchanged", problems[0])
        self.assertFalse(fixable)

    def test_a_skipped_version_fails(self) -> None:
        problems, fixable = gen.version_problems(self.grown(3), self.versions)
        self.assertIn("must be the next version after 1", problems[0])
        self.assertFalse(fixable)

    def test_restoring_an_older_recorded_version_fails(self) -> None:
        # Version 1's shape still matches version 1's hash, but version 2 superseded it.
        versions = {**self.versions, 2: gen.wire_shape_hash(self.grown(2))}
        problems, fixable = gen.version_problems(schema(), versions)
        self.assertIn("older than the newest recorded version, 2", problems[0])
        self.assertFalse(fixable)

    def test_restoring_an_older_shape_under_a_new_number_is_a_genuine_bump(self) -> None:
        versions = {**self.versions, 2: gen.wire_shape_hash(self.grown(2))}
        restored = schema()
        restored["properties"]["schema_version"]["const"] = 3
        problems, fixable = gen.version_problems(restored, versions)
        self.assertEqual(len(problems), 1)
        self.assertTrue(fixable)


class Gitattributes(unittest.TestCase):
    def test_reports_an_unmarked_generated_file(self) -> None:
        text = "# a.ts linguist-generated=true\nb.ts linguist-generated=true\n"
        self.assertEqual(gitattributes_problems(text, ["a.ts", "b.ts"]), ["a.ts"])


class TypeScriptTarget(unittest.TestCase):
    def render(self, changed: dict) -> str:
        return gen.render_typescript(gen.build_model(changed))

    def test_writes_keys_in_schema_order(self) -> None:
        content = self.render(schema())
        body = content[content.index("export function telemetryEventToWire") :]
        positions = [body.index(f"wire['{name}']") for name in schema()["properties"]]
        self.assertEqual(positions, sorted(positions))

    def test_a_required_field_is_always_written_and_an_optional_one_only_when_set(self) -> None:
        content = self.render(schema())
        self.assertIn("  wire['grade'] = value.grade;", content)
        self.assertIn(
            "  if (value.error_code !== undefined) wire['error_code'] = value.error_code;", content
        )

    def test_a_new_field_reaches_the_type_and_the_serializer(self) -> None:
        grown = schema()
        grown["properties"]["run_id"] = {"type": "string"}
        content = self.render(grown)
        self.assertIn("  run_id?: string;", content)
        self.assertIn("wire['run_id'] = value.run_id;", content)

    def test_the_version_constant_follows_the_schema(self) -> None:
        bumped = schema()
        bumped["properties"]["schema_version"]["const"] = 7
        content = self.render(bumped)
        self.assertIn("export const TELEMETRY_SCHEMA_VERSION = 7 as const;", content)
        self.assertIn("  schema_version: 7;", content)

    def test_starts_with_the_generated_marker(self) -> None:
        self.assertTrue(self.render(schema()).startswith(f"// {gen.GENERATED_MARKER}"))


class PythonTarget(unittest.TestCase):
    def render(self, changed: dict) -> str:
        return gen.render_python(gen.build_model(changed))

    def test_writes_keys_in_schema_order(self) -> None:
        content = self.render(schema())
        body = content[content.index("class TelemetryEvent:") :]
        body = body[body.index("def payload") :]
        positions = [body.index(f'wire["{name}"]') for name in schema()["properties"]]
        self.assertEqual(positions, sorted(positions))

    def test_a_required_field_is_always_written_and_an_optional_one_only_when_set(self) -> None:
        content = self.render(schema())
        self.assertIn('        wire["grade"] = self.grade\n', content)
        self.assertIn(
            '        if self.error_code is not None:\n'
            '            wire["error_code"] = self.error_code\n',
            content,
        )

    def test_the_class_is_keyword_only_so_field_order_can_follow_the_wire(self) -> None:
        # Required and optional fields interleave in wire order; a positional dataclass
        # could not declare a required field after a defaulted one.
        self.assertIn("@dataclass(frozen=True, kw_only=True)\nclass TelemetryEvent:", self.render(schema()))

    def test_a_new_field_reaches_the_class_and_the_payload(self) -> None:
        grown = schema()
        grown["properties"]["run_id"] = {"type": "string"}
        content = self.render(grown)
        self.assertIn("    run_id: str | None = None\n", content)
        self.assertIn('wire["run_id"] = self.run_id', content)

    def test_the_version_constant_follows_the_schema(self) -> None:
        bumped = schema()
        bumped["properties"]["schema_version"]["const"] = 7
        content = self.render(bumped)
        self.assertIn("SCHEMA_VERSION: Literal[7] = 7", content)
        self.assertIn("    schema_version: Literal[7] = 7", content)

    def test_the_module_runs_and_serializes_like_the_schema_says(self) -> None:
        namespace: dict = {}
        exec(compile(self.render(schema()), "_event_generated.py", "exec"), namespace)
        event = namespace["TelemetryEvent"](
            timestamp="t",
            sdk_version="v",
            sdk_language="python",
            evaluator_type="e",
            grade="",
            status="success",
            latency_ms=1,
            text_length_chars=0,
            provider="p",
        )
        wire = event.payload()
        required = [p for p in schema()["properties"] if p in schema()["required"]]
        self.assertEqual(list(wire), required)
        self.assertEqual(wire["schema_version"], 1)
        Draft202012Validator(schema()).validate(wire)

    def test_an_optional_constant_is_omitted_when_unset_as_in_typescript(self) -> None:
        # A constant that is optional means "this value or absent". Defaulting it to its
        # value would write it on every event, where TypeScript's `field?: 0` omits it.
        grown = schema()
        grown["properties"]["retry_count"] = {"type": "integer", "const": 0}
        content = self.render(grown)
        self.assertIn("    retry_count: Literal[0] | None = None\n", content)
        self.assertIn("  retry_count?: 0;", gen.render_typescript(gen.build_model(grown)))

        namespace: dict = {}
        exec(compile(content, "_event_generated.py", "exec"), namespace)
        fields = dict(
            timestamp="t",
            sdk_version="v",
            sdk_language="python",
            evaluator_type="e",
            grade="",
            status="success",
            latency_ms=1,
            text_length_chars=0,
            provider="p",
        )
        self.assertNotIn("retry_count", namespace["TelemetryEvent"](**fields).payload())
        self.assertEqual(
            namespace["TelemetryEvent"](**fields, retry_count=0).payload()["retry_count"], 0
        )

    def test_a_required_constant_defaults_to_its_value(self) -> None:
        self.assertIn("    schema_version: Literal[1] = 1\n", self.render(schema()))

    def test_starts_with_the_generated_marker(self) -> None:
        self.assertTrue(self.render(schema()).startswith(f'"""{gen.GENERATED_MARKER}'))


class EveryTarget(unittest.TestCase):
    def test_is_registered_and_marked_generated(self) -> None:
        relative = {t.relative for t in gen.TARGETS}
        self.assertEqual(
            relative,
            {
                "sdks/typescript/src/telemetry/types.generated.ts",
                "sdks/python/src/learning_commons_evaluators/telemetry/_event_generated.py",
            },
        )
        text = (gen.REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertEqual(gitattributes_problems(text, sorted(relative)), [])


if __name__ == "__main__":
    unittest.main()
