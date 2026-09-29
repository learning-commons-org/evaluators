"""Meta-validate each evaluator's input_schema.json / output_schema.json.

These files *are* JSON Schemas (they describe an evaluator's input and output),
so the check is: is each one a well-formed JSON Schema document? We run the
Draft 2020-12 meta-schema against them. Existence of the $ref is already covered
by eval-config; here we only judge validity of the schema documents themselves.

We also enforce snake_case property names. These keys are the one part of a contract
every SDK reproduces verbatim, in every language, so a camelCase key is not a style
preference - it forces one evaluator's public surface to differ from its fifteen
siblings' in every SDK at once. Math Standards Alignment carried four such keys,
inherited from the Knowledge Graph API's own field names, until they were renamed.

Input properties may carry an `x-image` block bounding the image file their value names;
each block is validated against `_schemas/x-image.schema.json`, since meta-validation
accepts any value for an extension keyword.
"""

from __future__ import annotations

import json
import os
import re

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .base import Check, Result, Violation, evaluator_configs, load_json

# Digits are allowed mid-name: `tier_2_words` is a real key.
SNAKE_CASE = re.compile(r"[a-z][a-z0-9]*(_[a-z0-9]+)*")


def _to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


# JSON Schema keywords whose values are instance data, not subschemas.
_INSTANCE_KEYWORDS = frozenset({"const", "default", "enum", "examples"})


def _evals_root(schema_path: str) -> str:
    """The `evals/` directory an evaluator schema file lives under."""
    here = os.path.dirname(os.path.abspath(schema_path))
    while os.path.basename(here) != "evals" and os.path.dirname(here) != here:
        here = os.path.dirname(here)
    return here


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
            return
        self._check_key_casing(doc, path, result)
        self._check_x_image(doc, path, result)

    def _check_x_image(self, doc: dict, path: str, result: Result) -> None:
        """Every `x-image` block must match `_schemas/x-image.schema.json`, with max >= min.

        `x-image` bounds the file an input string points at; it normally sits on the `items`
        of an array input. It is an extension keyword, so Draft 2020-12 meta-validation
        accepts any value for it -- including `"garbage"` -- and the SDKs would then have
        nothing consistent to enforce. Blocks are found at any depth, so a nested one is
        checked as strictly as a top-level one.
        """
        blocks = list(self._x_image_blocks(doc, ""))
        if not blocks:
            return
        meta_path = os.path.join(_evals_root(path), "_schemas", "x-image.schema.json")
        validator = Draft202012Validator(load_json(meta_path))
        for name, block in blocks:
            for err in sorted(validator.iter_errors(block), key=lambda e: list(e.path)):
                loc = "/".join(str(p) for p in err.path) or "(root)"
                result.violations.append(Violation(path, f"{name}.x-image: {loc}: {err.message}"))
            if isinstance(block, dict):
                for lo, hi in (("min_bytes", "max_bytes"), ("min_edge", "max_edge")):
                    a, b = block.get(lo), block.get(hi)
                    if isinstance(a, int) and isinstance(b, int) and a > b:
                        result.violations.append(
                            Violation(path, f"{name}.x-image: {lo} ({a}) exceeds {hi} ({b})")
                        )

    def _x_image_blocks(self, node: object, where: str):
        """Yield (location, block) for every `x-image` keyword under `node`.

        Keywords whose values are instance data rather than schemas are not entered, so an
        example or default that happens to contain an `x-image` key is not mistaken for one.
        """
        if isinstance(node, dict):
            for key, value in node.items():
                here = f"{where}/{key}" if where else key
                if key == "x-image":
                    yield where or "(root)", value
                elif key not in _INSTANCE_KEYWORDS:
                    yield from self._x_image_blocks(value, here)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                yield from self._x_image_blocks(item, f"{where}/{i}")

    def _check_key_casing(self, doc: dict, path: str, result: Result) -> None:
        for name in sorted(self._property_names(doc)):
            if not SNAKE_CASE.fullmatch(name):
                result.violations.append(
                    Violation(path, f"property {name!r} is not snake_case: use {_to_snake(name)!r}")
                )

    def _property_names(self, node: object) -> set[str]:
        """Every declared property name, at any nesting depth."""
        names: set[str] = set()
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, dict):
                names |= set(props.keys())
            for value in node.values():
                names |= self._property_names(value)
        elif isinstance(node, list):
            for item in node:
                names |= self._property_names(item)
        return names
