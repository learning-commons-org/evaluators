"""Validate evaluator config.json files.

Each config is validated in two complementary layers:

  1. Schema  — structural rules a JSON Schema can express (required fields,
     enums, types). Every config points at the shared contract via its own
     `$schema` field; we load that and report every schema error.

  2. Cross-file — rules a schema cannot express because they span files:
       - referenced files actually exist ($ref schemas, prompt files, fixtures)
       - each declared sha256 matches the prompt file on disk (drift tripwire)
       - placeholders declared in config line up with the {vars} in the prompts
       - every attachment names a required, bounded array input with `x-image` items,
         and no input carries `x-image` unless a step attaches it
       - `outcome` names output fields a caller receives, never an `x-model-only` one
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
        self._check_placeholder_sources(config, base, fail)
        self._check_attachments(config, base, fail)
        self._check_supported_grades(config, base, fail)
        self._check_outcome(config, base, fail)
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

    def _check_placeholder_sources(self, config: dict, base: str, fail) -> None:
        """Every placeholder `source` must resolve to something that exists.

        The four forms are `input`, `input.<field>`, `preprocessing.<output>` and
        `steps.<id>.output`. A source naming a preprocessing entry that does not exist
        is undetectable any other way -- the placeholder name still matches the prompt
        text, so every other rule passes.

        Note `preprocessing.<X>` resolves against an entry's declared `output` key, not
        its `id`; those differ, and only one of them is the value a step can read.
        """
        try:
            input_props = set(
                load_json(os.path.join(base, config["input_schema"]["$ref"]))
                .get("properties", {})
                .keys()
            )
        except (KeyError, TypeError, OSError, json.JSONDecodeError):
            return  # _check_referenced_files already reported this

        outputs = {
            entry["output"]
            for entry in config.get("preprocessing", [])
            if entry.get("output")
        }
        step_ids: set[str] = set()

        for step in config.get("steps", []):
            placeholders = (step.get("prompt") or {}).get("placeholders") or {}
            step_id = step.get("id", "?")
            for name, spec in placeholders.items():
                source = spec.get("source")
                if not isinstance(source, str):
                    continue
                where = f"{step_id}.{name}: source {source!r}"

                if source == "input":
                    if name not in input_props:
                        fail(f"{where} names no input; input_schema has no {name!r}")
                elif source.startswith("input."):
                    field = source.split(".", 1)[1]
                    if field not in input_props:
                        fail(f"{where} names no input; input_schema has no {field!r}")
                elif source.startswith("preprocessing."):
                    key = source.split(".", 1)[1]
                    if key not in outputs:
                        fail(
                            f"{where} resolves to no preprocessing output; "
                            f"declared outputs are {sorted(outputs) or 'none'}"
                        )
                elif source.startswith("steps."):
                    producer = source.split(".")[1]
                    if producer not in step_ids:
                        fail(f"{where} names no earlier step; {producer!r} does not run before {step_id!r}")
            step_ids.add(step_id)

    @staticmethod
    def _check_attachments(config: dict, base: str, fail) -> None:
        """Every `attachments[].input` must be a required, bounded array of local file paths.

        An attachment is not a placeholder, so nothing else ties it to an input: a typo here
        (`image` for `image_paths`) passes the schema and leaves a runner with no file to
        send, so it would send the prompt text alone. The input is always an array -- one
        image and many images are the same shape with different bounds -- so it must declare
        string items, `minItems` >= 1 and `maxItems` >= `minItems`, and, for `kind: "image"`,
        an `x-image` block on its items giving the SDK the per-file bounds to enforce. It
        must also be `required`: `minItems` only applies when the property is present, so an
        optional input would let a request through with no image at all. `items` must be
        written inline, not as a `$ref`.

        Conversely, `x-image` anywhere other than the items of an attached input is flagged:
        no runner would read those bounds, so they would go silently unenforced.
        """
        try:
            input_schema = load_json(os.path.join(base, config["input_schema"]["$ref"]))
        except (KeyError, TypeError, OSError, json.JSONDecodeError):
            return  # _check_referenced_files already reported this
        input_props = input_schema.get("properties", {})
        required = set(input_schema.get("required", []))
        attached: set[str] = set()

        for step in config.get("steps", []):
            step_id = step.get("id", "?")
            for entry in step.get("attachments") or []:
                name = entry.get("input") if isinstance(entry, dict) else None
                if not isinstance(name, str):
                    continue  # the schema layer already reports a malformed entry
                attached.add(name)
                where = f"{step_id}.attachments: input {name!r}"
                spec = input_props.get(name)
                if not isinstance(spec, dict):
                    fail(f"{where} is not declared in input_schema")
                    continue
                if name not in required:
                    fail(f"{where} must be listed in input_schema `required`")
                if spec.get("type") != "array":
                    fail(f"{where} must be an array of local file paths, not {spec.get('type')!r}")
                    continue
                items = spec.get("items") if isinstance(spec.get("items"), dict) else {}
                if items.get("type") != "string":
                    fail(f"{where} items must be inline string schemas (local file paths)")
                lo, hi = spec.get("minItems"), spec.get("maxItems")
                if type(lo) is not int or lo < 1:
                    fail(f"{where} must declare minItems >= 1")
                if type(hi) is not int:
                    fail(f"{where} must declare maxItems")
                elif type(lo) is int and hi < lo:
                    fail(f"{where} maxItems ({hi}) is below minItems ({lo})")
                if entry.get("kind") == "image" and "x-image" not in items:
                    fail(f"{where} items must declare x-image bounds")

        for name, spec in input_props.items():
            if not isinstance(spec, dict):
                continue
            if "x-image" in spec:
                fail(f"input {name!r}: x-image belongs on the items of an attached array input")
            items = spec.get("items")
            if isinstance(items, dict) and "x-image" in items and name not in attached:
                fail(f"input {name!r}: carries x-image but no step attaches it")

    @staticmethod
    def _check_supported_grades(config: dict, base: str, fail) -> None:
        """`supported_grades` must agree with the grades the evaluator actually accepts.

        `supported_grades` states what the evaluator is built for and is declared even
        when no grade is an input. Where a grade *is* an input, its enum is what
        consumers validate against, so the two disagreeing means one of them is wrong.
        """
        try:
            props = load_json(os.path.join(base, config["input_schema"]["$ref"])).get(
                "properties", {}
            )
        except (KeyError, TypeError, OSError, json.JSONDecodeError):
            return

        accepted = props.get("grade_level", {}).get("enum")
        if accepted is None:
            return

        declared = config.get("evaluator", {}).get("supported_grades")
        if declared != accepted:
            fail(
                "evaluator.supported_grades does not match the grades accepted by "
                f"input_schema.properties.grade_level.enum: {declared} vs {accepted}"
            )

    @staticmethod
    def _check_outcome(config: dict, base: str, fail) -> None:
        """`outcome` must name properties the output schema declares *and* requires.

        Declared is not enough: a verdict the schema permits to be absent is not a
        verdict a report can rely on. Nor may it name an `x-model-only` property, which
        SDKs strip before returning, so the caller would never see the verdict.
        """
        outcome = config.get("outcome")
        if not outcome:
            return

        try:
            declared = load_json(os.path.join(base, config["output_schema"]["$ref"]))
        except (KeyError, TypeError, OSError, json.JSONDecodeError):
            return

        properties = declared.get("properties", {})
        required = declared.get("required", [])
        for role in ("score", "reasoning"):
            field = outcome.get(role)
            if field not in properties:
                fail(f"outcome.{role} names {field!r}, which output_schema does not declare")
            elif field not in required:
                fail(
                    f"outcome.{role} names {field!r}, which output_schema declares but "
                    "does not require -- a verdict that may be absent is not a verdict"
                )
            elif isinstance(properties[field], dict) and properties[field].get("x-model-only"):
                fail(
                    f"outcome.{role} names {field!r}, which is x-model-only -- SDKs strip "
                    "it before returning"
                )

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

