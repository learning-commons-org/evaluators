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
- the registry only grows: against the copy on the branch this one merges into, every
  recorded version keeps its hash, and the only new entry is the version the schema names
  (see `base_ref` for which branch that is, and when the comparison is skipped);
- every generated module matches what the schema renders (`--fix` rewrites it);
- every generated module is marked `linguist-generated` in `.gitattributes`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .base import Check, Result, Violation

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_telemetry_schema as gen  # noqa: E402

SCHEMA = gen.SCHEMA_PATH.relative_to(gen.REPO_ROOT).as_posix()
VERSIONS = gen.VERSIONS_PATH.relative_to(gen.REPO_ROOT).as_posix()


#: Names the git ref to compare the registry against, overriding the default.
BASE_REF_ENV = "TELEMETRY_REGISTRY_BASE"


def base_ref(env: Mapping[str, str]) -> tuple[str, bool]:
    """The ref holding the registry this change must extend, and whether it must be readable.

    An explicit ``TELEMETRY_REGISTRY_BASE`` wins. On a pull request in GitHub Actions it is
    the PR's base branch, which `checks.yml` fetches; either way the comparison is required,
    because a CI run that silently skipped it would reopen the gap it closes. Anywhere else
    (a local run, the pre-commit hook, a push build) it is ``origin/main`` on a best-effort
    basis: skipped when that ref is not there, since the pull request is the gate.
    """
    if env.get(BASE_REF_ENV):
        return env[BASE_REF_ENV], True
    if env.get("GITHUB_BASE_REF"):
        return f"origin/{env['GITHUB_BASE_REF']}", True
    return "origin/main", False


def registry_at(ref: str, repo: Path = gen.REPO_ROOT) -> dict[int, str] | None:
    """The version registry as committed at ``ref``; ``None`` if it did not exist there yet.

    Raises ``LookupError`` when ``ref`` itself cannot be resolved (not fetched, or no git).
    """

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        # Return codes are the answers here (ref missing, file absent), not errors.
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)

    try:
        if git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode:
            raise LookupError(f"git ref {ref!r} is not available")
        blob = f"{ref}:{VERSIONS}"
        if git("cat-file", "-e", blob).returncode:
            return None
        shown = git("show", blob)
    except OSError as error:
        raise LookupError(f"cannot run git: {error}") from error
    if shown.returncode:
        raise LookupError(f"cannot read {blob}: {shown.stderr.strip()}")
    return gen.parse_versions(shown.stdout)


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
        self._check_history(schema, result)
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
    def _check_history(schema: dict, result: Result, env: Mapping[str, str] = os.environ) -> None:
        # Runs after `_check_version`, so a bump `--fix` just recorded is judged as written.
        try:
            current = gen.load_versions()
        except (OSError, ValueError, KeyError):
            return  # already reported by `_check_version`
        ref, required = base_ref(env)
        try:
            base = registry_at(ref)
        except LookupError as error:
            if required:
                result.violations.append(
                    Violation(
                        VERSIONS,
                        f"cannot compare with {ref}: {error}; fetch it, or set "
                        f"{BASE_REF_ENV} to the branch this one merges into",
                    )
                )
            return
        except (ValueError, KeyError) as error:
            result.violations.append(Violation(VERSIONS, f"cannot read the copy at {ref}: {error}"))
            return
        if base is None:
            return  # the registry is new in this change; nothing to extend
        version = schema["properties"]["schema_version"]["const"]
        for problem in gen.history_problems(base, current, version):
            result.violations.append(Violation(VERSIONS, f"{problem} (compared with {ref})"))

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
