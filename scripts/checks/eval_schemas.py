"""Meta-validate each evaluator's input_schema.json / output_schema.json.

These files *are* JSON Schemas (they describe an evaluator's input and output),
so the check is: is each one a well-formed JSON Schema document? We run the
Draft 2020-12 meta-schema against them. Existence of the $ref is already covered
by eval-config; here we only judge validity of the schema documents themselves.
"""

from __future__ import annotations

import json
import os

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .base import Check, Result, Violation, evaluator_configs, load_json


class EvalSchemas(Check):
    name = "eval-schemas"
    description = "Meta-validate each evaluator's input_schema.json / output_schema.json"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)
        for cfg_path in evaluator_configs():
            base = os.path.dirname(cfg_path)
            try:
                config = load_json(cfg_path)
            except (OSError, json.JSONDecodeError):
                continue  # eval-config reports unreadable configs
            for key in ("input_schema", "output_schema"):
                self._check_schema_file(config.get(key, {}), base, result)
        return result

    def _check_schema_file(self, ref: dict, base: str, result: Result) -> None:
        if not (isinstance(ref, dict) and "$ref" in ref):
            return
        rel = ref["$ref"]
        path = os.path.join(base, rel)
        if not os.path.exists(path):
            return  # eval-config already flags missing $ref targets
        try:
            doc = load_json(path)
        except json.JSONDecodeError as e:
            result.violations.append(Violation(path, f"invalid JSON: {e}"))
            return
        try:
            Draft202012Validator.check_schema(doc)
        except SchemaError as e:
            result.violations.append(Violation(path, f"not a valid JSON Schema: {e.message}"))
