"""Validate each evaluator's fixtures.json.

Three layers, the first two mirroring eval-config:
  - shared structure: every case is {id, input, expected} per the shared
    evals/_schemas/fixtures.schema.json.
  - per-evaluator binding: each case's `input` must satisfy that evaluator's own
    input_schema.json, and each field in `expected` must satisfy the matching
    property in its output_schema.json. (`expected` is a subset of the full
    output — just the label(s) — so we validate present fields, not requireds.)
  - outcome coverage: if the config declares `outcome.score`, every case must pin
    that field. It is the only part of the output stable enough to assert, so a
    fixture that omits it asserts nothing a caller depends on.
"""

from __future__ import annotations

import json
import os

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .base import Check, Result, Violation, evaluator_configs, load_json, shared_schema_path

_FIXTURES_SCHEMA = "fixtures.schema.json"


class EvalFixtures(Check):
    name = "eval-fixtures"
    description = "Validate fixtures.json structure + bind each case's input/expected to the evaluator's schemas"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)
        shared = Draft202012Validator(load_json(shared_schema_path(_FIXTURES_SCHEMA)))
        for cfg_path in evaluator_configs():
            self._check_fixtures(cfg_path, shared, result)
        return result

    def _check_fixtures(self, cfg_path: str, shared: Draft202012Validator, result: Result) -> None:
        base = os.path.dirname(cfg_path)
        try:
            config = load_json(cfg_path)
        except (OSError, json.JSONDecodeError):
            return  # eval-config reports unreadable configs

        def fail(msg: str) -> None:
            result.violations.append(Violation(cfg_path, msg))

        rel = config.get("fixtures", {}).get("path")
        if not rel:
            return
        path = os.path.join(base, rel)
        if not os.path.exists(path):
            return  # eval-config reports the missing file
        try:
            fixtures = load_json(path)
        except json.JSONDecodeError as e:
            fail(f"{rel}: invalid JSON: {e}")
            return

        # Layer 1: shared structure.
        structurally_ok = True
        for err in sorted(shared.iter_errors(fixtures), key=lambda e: list(e.path)):
            structurally_ok = False
            fail(f"{rel}: {self._loc(err)}: {err.message}")
        if not structurally_ok:
            return  # per-case binding below assumes well-formed cases

        # Layer 2: bind input/expected to this evaluator's own schemas.
        # Layer 3: every case pins the declared outcome score.
        input_validator = self._validator_for(config, base, "input_schema")
        expected_validator = self._expected_validator(config, base)
        # Absent for evaluators whose payload has no single verdict field, such as
        # Math Standards Alignment; `outcome` is optional in the config schema.
        score_field = (config.get("outcome") or {}).get("score")
        for case in fixtures:
            cid = case.get("id", "?")
            if input_validator:
                for err in input_validator.iter_errors(case.get("input", {})):
                    fail(f"{rel}[{cid}].input: {self._loc(err)}: {err.message}")
            if expected_validator:
                for err in expected_validator.iter_errors(case.get("expected", {})):
                    fail(f"{rel}[{cid}].expected: {self._loc(err)}: {err.message}")
            if score_field and score_field not in case.get("expected", {}):
                fail(
                    f"{rel}[{cid}].expected: missing {score_field!r}, "
                    f"the outcome score declared in config.json"
                )

    def _validator_for(self, config: dict, base: str, key: str):
        ref = config.get(key, {})
        if not (isinstance(ref, dict) and "$ref" in ref):
            return None
        path = os.path.join(base, ref["$ref"])
        doc = self._load_or_none(path)
        return self._safe_validator(doc) if doc is not None else None

    def _expected_validator(self, config: dict, base: str):
        """A partial validator: each expected field must match its output property.

        Built from output_schema.properties (+ $defs for $ref resolution) with no
        `required`, so a fixture carrying only the label validates, and an unknown
        expected field is rejected.
        """
        ref = config.get("output_schema", {})
        if not (isinstance(ref, dict) and "$ref" in ref):
            return None
        path = os.path.join(base, ref["$ref"])
        out = self._load_or_none(path)
        if out is None:
            return None
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": out.get("properties", {}),
        }
        if "$defs" in out:
            schema["$defs"] = out["$defs"]
        return self._safe_validator(schema)

    @staticmethod
    def _load_or_none(path: str):
        """Load a JSON file, or None if missing/unreadable/invalid.

        A malformed input/output schema is reported by eval-schemas; here we just
        skip binding rather than crash on it.
        """
        if not os.path.exists(path):
            return None
        try:
            return load_json(path)
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _safe_validator(schema: dict):
        """Build a validator only if `schema` is itself a valid JSON Schema."""
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError:
            return None
        return Draft202012Validator(schema)

    @staticmethod
    def _loc(err) -> str:
        return "/".join(str(p) for p in err.path) or "(root)"
