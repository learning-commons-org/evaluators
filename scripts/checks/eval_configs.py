"""Validate evaluator config.json files against repo conventions.

Rules (all report every offender, never stop at first):
  1. referenced files exist ($ref schemas, message source_path, fixtures path)
  2. config + referenced schema/fixture files are valid JSON
  3. each message's declared sha256 matches the prompt file (drift tripwire)
  4. parser.kind == "structured_output"
  5. message roles are one of system / user / assistant
  6. placeholder/template consistency: every declared placeholder appears in a
     prompt template, and every {var} in a template is declared

Check-only: config intent can't be safely auto-fixed (notably sha256, which is a
deliberate drift tripwire), so there is no fix mode.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

from .base import Check, Result, Violation, tracked_files

_PLACEHOLDER = re.compile(r"\{([a-zA-Z0-9_]+)\}")
_VALID_ROLES = {"system", "user", "assistant"}


def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class EvalConfigs(Check):
    name = "eval-configs"
    description = "Validate evaluator config.json (refs, sha256, parser, roles, placeholders)"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)
        for cfg_path in tracked_files("evals/**/config.json"):
            self._check_config(cfg_path, result)
        return result

    def _check_config(self, cfg_path: str, result: Result) -> None:
        base = os.path.dirname(cfg_path)

        def fail(msg: str) -> None:
            result.violations.append(Violation(cfg_path, msg))

        try:
            config = _load_json(cfg_path)
        except (OSError, json.JSONDecodeError) as e:
            fail(f"invalid JSON: {e}")
            return

        # Rules 1 & 2: referenced schema files exist and parse.
        for key in ("input_schema", "output_schema"):
            ref = config.get(key, {})
            if isinstance(ref, dict) and "$ref" in ref:
                self._require_json(os.path.join(base, ref["$ref"]), f"{key} $ref", fail)

        steps = config.get("steps") or []
        if not steps:
            fail("no steps defined")
            return
        step = steps[0]

        # Rule 4: parser kind.
        kind = step.get("parser", {}).get("kind")
        if kind != "structured_output":
            fail(f'parser.kind is "{kind}", expected "structured_output"')

        prompt = step.get("prompt", {})
        declared = set(prompt.get("placeholders", {}).keys())
        template_vars: set[str] = set()

        for msg in prompt.get("messages", []):
            # Rule 5: role.
            role = msg.get("role")
            if role not in _VALID_ROLES:
                fail(f'message role "{role}" not in {sorted(_VALID_ROLES)}')

            src = msg.get("source_path")
            if not src:
                fail("message missing source_path")
                continue
            path = os.path.join(base, src)
            if not os.path.exists(path):
                fail(f"prompt file not found: {src}")
                continue

            text = open(path, encoding="utf-8").read()
            template_vars |= set(_PLACEHOLDER.findall(text))

            # Rule 3: sha256.
            declared_sha = msg.get("sha256")
            if declared_sha:
                actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
                if actual != declared_sha:
                    fail(f"sha256 drift for {src}: declared {declared_sha[:12]}…, actual {actual[:12]}…")

        # Rule 6: placeholder/template consistency.
        for ph in sorted(declared - template_vars):
            fail(f'placeholder "{ph}" declared but not used in any prompt template')
        for var in sorted(template_vars - declared):
            fail(f'template variable "{{{var}}}" used but not declared in placeholders')

        # Rules 1 & 2: fixtures file.
        fx = config.get("fixtures", {}).get("sniff_test_path")
        if fx:
            self._require_json(os.path.join(base, fx), "fixtures", fail)

    @staticmethod
    def _require_json(path: str, label: str, fail) -> None:
        if not os.path.exists(path):
            fail(f"{label} file not found: {path}")
            return
        try:
            _load_json(path)
        except json.JSONDecodeError as e:
            fail(f"{label} invalid JSON ({path}): {e}")
