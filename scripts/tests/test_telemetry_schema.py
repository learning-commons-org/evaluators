"""The telemetry event schema, its generator, and the schema_version ↔ wire-shape rule."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jsonschema import Draft202012Validator  # noqa: E402

import generate_telemetry_schema as gen  # noqa: E402
from checks.base import Result  # noqa: E402
from checks.telemetry_schema import (  # noqa: E402
    TelemetrySchema,
    base_ref,
    gitattributes_problems,
    registry_at,
)

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


class HistoryProblems(unittest.TestCase):
    BASE: ClassVar[Mapping[int, str]] = MappingProxyType({1: "sha256:one", 2: "sha256:two"})

    def test_an_unchanged_registry_passes(self) -> None:
        self.assertEqual(gen.history_problems(self.BASE, dict(self.BASE), 2), [])

    def test_recording_the_schemas_new_version_passes(self) -> None:
        self.assertEqual(gen.history_problems(self.BASE, {**self.BASE, 3: "sha256:three"}, 3), [])

    def test_a_rehashed_version_fails(self) -> None:
        # The gap `version_problems` cannot see: change the shape, overwrite version 2's
        # hash to match it, and the current file alone is self-consistent.
        problems = gen.history_problems(self.BASE, {**self.BASE, 2: "sha256:other"}, 2)
        self.assertEqual(len(problems), 1)
        self.assertIn("version 2's recorded hash was changed", problems[0])
        self.assertIn("takes version 3", problems[0])

    def test_a_removed_version_fails(self) -> None:
        problems = gen.history_problems(self.BASE, {1: "sha256:one"}, 1)
        self.assertEqual(len(problems), 1)
        self.assertIn("version 2 was removed", problems[0])

    def test_a_version_other_than_the_schemas_may_not_be_added(self) -> None:
        added = {**self.BASE, 3: "sha256:three", 4: "sha256:four"}
        problems = gen.history_problems(self.BASE, added, 4)
        self.assertEqual(len(problems), 1)
        self.assertIn("version 3 was added, but the schema is at 4", problems[0])

    def test_reports_every_problem(self) -> None:
        rewritten = {1: "sha256:other", 5: "sha256:five"}
        self.assertEqual(len(gen.history_problems(self.BASE, rewritten, 1)), 3)


class BaseRef(unittest.TestCase):
    def test_an_explicit_ref_wins_and_is_required(self) -> None:
        env = {"TELEMETRY_REGISTRY_BASE": "abc123", "GITHUB_BASE_REF": "main"}
        self.assertEqual(base_ref(env), ("abc123", True))

    def test_a_pull_request_compares_with_its_base_branch_and_requires_it(self) -> None:
        env = {"GITHUB_BASE_REF": "dscr-2598/telemetry-p0"}
        self.assertEqual(base_ref(env), ("origin/dscr-2598/telemetry-p0", True))

    def test_elsewhere_it_is_origin_main_on_a_best_effort_basis(self) -> None:
        # GitHub Actions sets GITHUB_BASE_REF to "" outside pull_request events.
        self.assertEqual(base_ref({"GITHUB_BASE_REF": ""}), ("origin/main", False))
        self.assertEqual(base_ref({}), ("origin/main", False))


class RegistryAt(unittest.TestCase):
    """Reads the registry out of a throwaway repository's history."""

    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        self.git("init", "-q")
        self.git("commit", "-q", "--allow-empty", "-m", "before the registry")
        self.git("tag", "before")
        registry = self.repo / gen.VERSIONS_PATH.relative_to(gen.REPO_ROOT)
        registry.parent.mkdir(parents=True)
        registry.write_text(gen.render_versions({1: "sha256:one"}), encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "record version 1")
        self.git("tag", "after")

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=self.repo,
            check=True,
            capture_output=True,
        )

    def test_reads_the_registry_at_a_ref(self) -> None:
        self.assertEqual(registry_at("after", self.repo), {1: "sha256:one"})

    def test_a_ref_before_the_registry_existed_has_none(self) -> None:
        self.assertIsNone(registry_at("before", self.repo))

    def test_an_unknown_ref_raises(self) -> None:
        with self.assertRaises(LookupError):
            registry_at("origin/no-such-branch", self.repo)


class CheckHistory(unittest.TestCase):
    def violations(self, env: dict[str, str]) -> list[str]:
        result = Result("telemetry-schema")
        TelemetrySchema._check_history(schema(), result, env)
        return [v.message for v in result.violations]

    def test_an_unreadable_required_base_is_a_violation(self) -> None:
        # In CI, failing to fetch the base must not quietly turn the comparison off.
        (message,) = self.violations({"GITHUB_BASE_REF": "no-such-branch-for-this-test"})
        self.assertIn("cannot compare with origin/no-such-branch-for-this-test", message)

    def test_an_unreadable_best_effort_base_is_skipped(self) -> None:
        with mock.patch("checks.telemetry_schema.registry_at", side_effect=LookupError("x")):
            self.assertEqual(self.violations({}), [])

    def test_a_rewritten_registry_is_reported_against_the_base(self) -> None:
        recorded = gen.load_versions()
        base = {version: "sha256:different" for version in recorded}
        with mock.patch("checks.telemetry_schema.registry_at", return_value=base):
            messages = self.violations({"TELEMETRY_REGISTRY_BASE": "the-base"})
        self.assertEqual(len(messages), len(recorded))
        self.assertTrue(all(m.endswith("(compared with the-base)") for m in messages))


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


if __name__ == "__main__":
    unittest.main()
