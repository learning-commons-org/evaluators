"""Validate evaluator config.json files.

Each config is validated in two complementary layers:

  1. Schema  — structural rules a JSON Schema can express (required fields,
     enums, types). Every config points at the shared contract via its own
     `$schema` field; we load that and report every schema error.

  2. Cross-file — rules a schema cannot express because they span files:
       - referenced files actually exist ($ref schemas, prompt files, fixtures)
       - each declared sha256 matches the prompt file on disk (drift tripwire)
       - placeholders declared in config line up with the {vars} in the prompts
       - system prompts carry no user-input placeholders
       - no obsolete format-instruction placeholders survive anywhere

Every rule reports *all* offenders (never stops at the first) so one run lists
everything to fix. Check-only: config intent isn't safely auto-fixable — notably
sha256, which is a deliberate drift tripwire, not something to silently rewrite.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

from jsonschema import Draft202012Validator

from .base import Check, Result, Violation, evaluator_configs, load_json

# {placeholder} tokens in a prompt template.
_PLACEHOLDER = re.compile(r"\{([a-zA-Z0-9_]+)\}")

# Placeholder names that should never appear: structured_output makes
# LangChain-era format-instruction injection obsolete. Substring match so
# variants ("format_instructions", "json_format_instructions", …) are caught.
_OBSOLETE_PLACEHOLDERS = ("format_instructions",)


class EvalConfig(Check):
    name = "eval-config"
    description = "Validate config.json against the shared schema + cross-file refs/sha/placeholders"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)
        configs: list[tuple[str, dict]] = []
        for cfg_path in evaluator_configs():
            self._check_config(cfg_path, result)
            try:
                configs.append((cfg_path, load_json(cfg_path)))
            except (OSError, json.JSONDecodeError):
                continue
        self._check_stable_ids(configs, result)
        return result

    def _check_config(self, cfg_path: str, result: Result) -> None:
        """Run every rule against one config, collecting violations."""
        base = os.path.dirname(cfg_path)

        def fail(msg: str) -> None:
            result.violations.append(Violation(cfg_path, msg))

        try:
            config = load_json(cfg_path)
        except (OSError, json.JSONDecodeError) as e:
            fail(f"invalid JSON: {e}")
            return

        self._check_schema(config, base, fail)
        self._check_referenced_files(config, base, fail)
        for step in config.get("steps", []):
            prompt = step.get("prompt")
            if not prompt:
                continue
            step_id = step.get("id", "?")
            template_vars = self._check_prompts(prompt, base, fail, step_id)
            self._check_placeholders(prompt, template_vars, fail, step_id)
        self._check_fixtures_path(config, base, fail)

    # --- Layer 1: schema -----------------------------------------------------

    def _check_schema(self, config: dict, base: str, fail) -> None:
        """Validate the config against the schema named in its own `$schema`."""
        ref = config.get("$schema")
        if not ref:
            fail("missing $schema reference")
            return
        schema_path = os.path.normpath(os.path.join(base, ref))
        if not os.path.exists(schema_path):
            fail(f"$schema not found: {ref}")
            return
        try:
            schema = load_json(schema_path)
        except (OSError, json.JSONDecodeError) as e:
            fail(f"$schema unreadable ({ref}): {e}")
            return
        validator = Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(config), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            fail(f"schema: {loc}: {err.message}")

    # --- Layer 2: cross-file -------------------------------------------------

    def _check_referenced_files(self, config: dict, base: str, fail) -> None:
        """The schema $refs for input/output must resolve to real files."""
        for key in ("input_schema", "output_schema"):
            ref = config.get(key, {})
            if isinstance(ref, dict) and "$ref" in ref:
                if not os.path.exists(os.path.join(base, ref["$ref"])):
                    fail(f"{key} $ref not found: {ref['$ref']}")

    def _check_prompts(self, prompt: dict, base: str, fail, step_id: str) -> set[str]:
        """Validate each prompt file for one step; return the set of {vars} used
        across its own messages.

        Per message: the file exists, its sha256 matches, system prompts hold no
        placeholders, and no obsolete placeholders appear.
        """
        template_vars: set[str] = set()
        for msg in prompt.get("messages", []):
            src = msg.get("source_path")
            if not src:
                continue
            path = os.path.join(base, src)
            if not os.path.exists(path):
                fail(f"{step_id}: prompt file not found: {src}")
                continue

            try:
                with open(path, "rb") as f:
                    raw = f.read()
            except OSError as e:
                fail(f"{step_id}: prompt file unreadable: {src}: {e}")
                continue

            used = set(_PLACEHOLDER.findall(raw.decode("utf-8", "replace")))
            template_vars |= used

            self._check_sha(msg, src, raw, fail, step_id)
            self._check_role_placeholders(msg, src, used, fail, step_id)
        return template_vars

    @staticmethod
    def _check_sha(msg: dict, src: str, raw: bytes, fail, step_id: str) -> None:
        """Declared sha256 must match the file — guards against silent drift.

        Hash the raw bytes (not decoded text) so the result is identical across
        platforms — text-mode reads translate newlines and would skew the hash.
        """
        declared = msg.get("sha256")
        if not declared:
            return
        actual = hashlib.sha256(raw).hexdigest()
        if actual != declared:
            fail(f"{step_id}: sha256 drift for {src}: declared {declared[:12]}…, actual {actual[:12]}…")

    @staticmethod
    def _check_role_placeholders(msg: dict, src: str, used: set[str], fail, step_id: str) -> None:
        """System prompts take no inputs; no prompt may inject format instructions."""
        # All runtime inputs belong in user-role prompts, never the system prompt.
        if msg.get("role") == "system" and used:
            fail(f"{step_id}: system prompt {src} contains placeholders {sorted(used)}; "
                 "user inputs belong only in user-role prompts")
        for var in sorted(used):
            if any(token in var for token in _OBSOLETE_PLACEHOLDERS):
                fail(f'{step_id}: {src} references "{{{var}}}"; structured_output makes '
                     "format-instruction placeholders obsolete")

    def _check_placeholders(self, prompt: dict, template_vars: set[str], fail, step_id: str) -> None:
        """Declared placeholders and template {vars} must be exactly in sync, for one step."""
        declared = set(prompt.get("placeholders", {}).keys())
        for ph in sorted(declared - template_vars):
            fail(f'{step_id}: placeholder "{ph}" declared but not used in any prompt template')
        for var in sorted(template_vars - declared):
            fail(f'{step_id}: template variable "{{{var}}}" used but not declared in placeholders')

    def _check_fixtures_path(self, config: dict, base: str, fail) -> None:
        """Fixtures file must exist (its contents are validated by eval-fixtures)."""
        path = config.get("fixtures", {}).get("path")
        if path and not os.path.exists(os.path.join(base, path)):
            fail(f"fixtures file not found: {path}")

    def _check_stable_ids(self, configs: list[tuple[str, dict]], result: Result) -> None:
        """stable_id is a permanent identity anchor -- it must be globally unique
        across evaluators (skipped for evaluators that don't have one yet, since
        it's optional while being backfilled). id/id_history reuse is checked
        regardless of whether stable_id is present.

        Defensive against structurally invalid configs (already reported by
        _check_schema) -- a non-dict `evaluator` or non-list `id_history` must
        not crash this check and hide every other config's violations."""
        stable_id_owners: dict[str, set[str]] = {}
        id_owners: dict[str, set[str]] = {}

        for cfg_path, config in configs:
            evaluator = config.get("evaluator")
            if not isinstance(evaluator, dict):
                continue

            stable_id = evaluator.get("stable_id")
            if isinstance(stable_id, str) and stable_id:
                stable_id_owners.setdefault(stable_id, set()).add(cfg_path)

            id_history = evaluator.get("id_history")
            if not isinstance(id_history, list):
                id_history = []
            for id_value in [evaluator.get("id"), *id_history]:
                if isinstance(id_value, str) and id_value:
                    id_owners.setdefault(id_value, set()).add(cfg_path)

        for stable_id, owners in sorted(stable_id_owners.items()):
            if len(owners) > 1:
                paths = sorted(owners)
                result.violations.append(Violation(
                    paths[0],
                    f"stable_id {stable_id!r} is used by more than one evaluator: {', '.join(paths)}",
                ))
        for id_value, owners in sorted(id_owners.items()):
            if len(owners) > 1:
                paths = sorted(owners)
                result.violations.append(Violation(
                    paths[0],
                    f"id {id_value!r} appears (as id or id_history) on more than one evaluator: "
                    f"{', '.join(paths)} -- a retired id must never be reused for a different evaluator",
                ))

