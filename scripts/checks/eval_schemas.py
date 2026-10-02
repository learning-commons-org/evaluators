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

The `items` of an attached array input carry an `x-image` block bounding each image file;
every block is validated against `_schemas/x-image.schema.json`, since meta-validation
accepts any value for an extension keyword. For the same reason, `x-model-only` is checked
to be `true` and to sit only on a top-level property of an output schema.
"""

from __future__ import annotations

import json
import os
import re

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .base import Check, Result, Violation, evaluator_configs, load_json, shared_schema_path

# Digits are allowed mid-name: `tier_2_words` is a real key.
SNAKE_CASE = re.compile(r"[a-z][a-z0-9]*(_[a-z0-9]+)*")


def _to_snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


# JSON Schema keywords whose values are instance data, not subschemas.
_INSTANCE_KEYWORDS = frozenset({"const", "default", "enum", "examples"})

# Keywords whose value maps names to subschemas; the names are not keywords.
_NAMED_SUBSCHEMAS = frozenset(
    {"properties", "patternProperties", "dependentSchemas", "$defs", "definitions"}
)


class EvalSchemas(Check):
    name = "eval-schemas"
    description = "Meta-validate each evaluator's input_schema.json / output_schema.json"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)
        self._x_image_validator = Draft202012Validator(
            load_json(shared_schema_path("x-image.schema.json"))
        )
        for cfg_path in evaluator_configs():
            base = os.path.dirname(cfg_path)
            try:
                config = load_json(cfg_path)
            except (OSError, json.JSONDecodeError):
                continue  # eval-config reports unreadable configs
            for key in ("input_schema", "output_schema"):
                self._check_schema_file(config.get(key, {}), key, base, result)
        return result

    def _check_schema_file(self, ref: dict, key: str, base: str, result: Result) -> None:
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
        self._check_model_only(doc, key, path, result)

    def _check_model_only(self, doc: dict, key: str, path: str, result: Result) -> None:
        """`x-model-only` is `true` on a required top-level output_schema property, and nowhere else.

        It marks a field the model must produce but an SDK strips before returning, so the
        caller gets the output schema minus the marked fields. Only a top-level output
        property can be dropped that way; anywhere else the mark has no defined meaning.
        It must be required: the marked fields are the working-out that conditions the
        returned answer, which the model would otherwise be free to skip.
        """
        if not isinstance(doc, dict):
            return  # a boolean schema declares no properties to mark
        top = doc.get("properties", {}) if key == "output_schema" else {}
        required = doc.get("required", []) if key == "output_schema" else []
        top_paths = {f"properties/{name}": name for name in top}
        for where, value in self._keyword_blocks(doc, "", "x-model-only"):
            if where not in top_paths:
                message = "x-model-only belongs only on a top-level output_schema property"
            elif value is not True:
                message = f"x-model-only must be true, got {value!r}"
            elif top_paths[where] not in required:
                message = "x-model-only property must be listed in required"
            else:
                continue
            result.violations.append(Violation(path, f"{where}: {message}"))

    def _check_x_image(self, doc: dict, path: str, result: Result) -> None:
        """Every `x-image` block must match `_schemas/x-image.schema.json`, with max >= min.

        `x-image` bounds the file an input string points at; it normally sits on the `items`
        of an array input. It is an extension keyword, so Draft 2020-12 meta-validation
        accepts any value for it -- including `"garbage"` -- and the SDKs would then have
        nothing consistent to enforce. Blocks are found at any depth, so a nested one is
        checked as strictly as a top-level one.
        """
        for name, block in self._keyword_blocks(doc, "", "x-image"):
            for err in sorted(self._x_image_validator.iter_errors(block), key=lambda e: list(e.path)):
                loc = "/".join(str(p) for p in err.path) or "(root)"
                result.violations.append(Violation(path, f"{name}.x-image: {loc}: {err.message}"))
            if isinstance(block, dict):
                for lo, hi in (("min_bytes", "max_bytes"), ("min_edge", "max_edge")):
                    a, b = block.get(lo), block.get(hi)
                    if type(a) is int and type(b) is int and a > b:
                        result.violations.append(
                            Violation(path, f"{name}.x-image: {lo} ({a}) exceeds {hi} ({b})")
                        )

    def _keyword_blocks(self, node: object, where: str, keyword: str):
        """Yield (location, value) for every `keyword` in the schema `node`.

        Walks schema positions only. Instance-valued keywords (`examples`, `default`, ...)
        are not entered, and under `properties`/`$defs` the keys are names, not keywords,
        so a property called `default` or `x-image` is walked as the schema it names.
        """
        if isinstance(node, dict):
            for key, value in node.items():
                here = f"{where}/{key}" if where else key
                if key == keyword:
                    yield where or "(root)", value
                elif key in _NAMED_SUBSCHEMAS and isinstance(value, dict):
                    for name, sub in value.items():
                        yield from self._keyword_blocks(sub, f"{here}/{name}", keyword)
                elif key not in _INSTANCE_KEYWORDS:
                    yield from self._keyword_blocks(value, here, keyword)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                yield from self._keyword_blocks(item, f"{where}/{i}", keyword)

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
