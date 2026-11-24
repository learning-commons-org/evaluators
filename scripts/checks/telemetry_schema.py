"""The telemetry event schema, and every SDK module generated from it.

`evals/telemetry/event.schema.json` is the single source of truth for the event both SDKs
send to the collector; `scripts/generate_telemetry_schema.py` renders it into each SDK. This
check is the CI gate that keeps the three in step:

- the schema is a well-formed Draft 2020-12 document, inside the subset the generator
  renders, and obeys the envelope rule (per-evaluator variation only in named, typed
  `metadata` blocks) — see `schema_problems`;
- `schema_version` names the wire shape: the hash recorded for the current version in
  `evals/telemetry/schema-versions.json` matches the schema. A wire change without a bump
  fails and is not auto-fixed (bumping is a decision); `--fix` records a genuine bump;
- every generated module matches what the schema renders (`--fix` rewrites it);
- every generated module is marked `linguist-generated` in `.gitattributes`.
"""

from __future__ import annotations

import os
import sys

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .base import Check, Result, Violation

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_telemetry_schema as gen  # noqa: E402

SCHEMA = gen.SCHEMA_PATH.relative_to(gen.REPO_ROOT).as_posix()
VERSIONS = gen.VERSIONS_PATH.relative_to(gen.REPO_ROOT).as_posix()


def gitattributes_problems(text: str, generated: list[str]) -> list[str]:
    """Generated paths missing their ``linguist-generated=true`` line."""
    marked = {
        line.split()[0]
        for line in text.splitlines()
        if line.strip() and not line.startswith("#") and "linguist-generated=true" in line
    }
    return [path for path in generated if path not in marked]


class TelemetrySchema(Check):
    name = "telemetry-schema"
    description = "Telemetry event schema is valid and versioned; generated SDK types match it"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)
        try:
            schema = gen.load_schema()
        except (OSError, ValueError) as error:
            result.violations.append(Violation(SCHEMA, f"cannot read: {error}"))
            return result

        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            result.violations.append(Violation(SCHEMA, f"invalid JSON Schema: {error.message}"))
            return result

        problems = gen.schema_problems(schema)
        for problem in problems:
            result.violations.append(Violation(SCHEMA, problem))
        if problems:
            return result

        self._check_version(schema, fix, result)
        self._check_generated(schema, fix, result)
        self._check_gitattributes(result)
        return result

    @staticmethod
    def _check_version(schema: dict, fix: bool, result: Result) -> None:
        try:
            versions = gen.load_versions()
        except (OSError, ValueError, KeyError) as error:
            result.violations.append(Violation(VERSIONS, f"cannot read: {error}"))
            return
        problems, fixable = gen.version_problems(schema, versions)
        if fixable and fix:
            version = schema["properties"]["schema_version"]["const"]
            versions[version] = gen.wire_shape_hash(schema)
            gen.VERSIONS_PATH.write_text(gen.render_versions(versions), encoding="utf-8")
            result.fixed.append(VERSIONS)
            return
        for problem in problems:
            result.violations.append(Violation(VERSIONS, problem))

    @staticmethod
    def _check_generated(schema: dict, fix: bool, result: Result) -> None:
        for target, content in gen.stale_targets(schema):
            if fix:
                target.path.write_text(content, encoding="utf-8")
                result.fixed.append(target.relative)
            else:
                result.violations.append(
                    Violation(
                        target.relative,
                        f"stale: regenerate with `{gen.REGENERATE}` (or run --fix)",
                    )
                )

    @staticmethod
    def _check_gitattributes(result: Result) -> None:
        path = gen.REPO_ROOT / ".gitattributes"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for missing in gitattributes_problems(text, [t.relative for t in gen.TARGETS]):
            result.violations.append(
                Violation(
                    ".gitattributes",
                    f"{missing} is generated but not marked `linguist-generated=true`",
                )
            )
