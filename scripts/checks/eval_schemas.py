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

An input schema may declare only the shapes the SDKs on this branch validate, type, and
bind the same way. Anything else would be accepted by one SDK and mishandled by the other,
or by both, without any test noticing; see `input_shape_problems` for the list.
"""

from __future__ import annotations

import json
import os
import re

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .base import (
    Check,
    Result,
    Violation,
    evaluator_configs,
    load_json,
    shared_schema_path,
)

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


_ANNOTATIONS = frozenset({"title", "description"})
_ROOT = _ANNOTATIONS | {
    "$schema",
    "$id",
    "$defs",
    "type",
    "properties",
    "required",
    "additionalProperties",
}
_TOP_LEVEL = {
    "string": _ANNOTATIONS | {"type", "enum", "minLength", "maxLength"},
    "integer": _ANNOTATIONS | {"type", "minimum", "maximum"},
    "array": _ANNOTATIONS | {"type", "items", "minItems", "maxItems"},
}
_STRING_ITEM = _ANNOTATIONS | {"type", "minLength", "maxLength", "x-image"}
_DEF_OBJECT = _ANNOTATIONS | {"type", "properties", "required", "additionalProperties"}
_DEF_FIELD = _ANNOTATIONS | {"type", "minLength", "maxLength"}
_DEF_NAME = re.compile(r"^[A-Z][A-Za-z0-9]*$")


def input_shape_problems(doc: object) -> list[str]:
    """Every place an input schema steps outside the shapes this branch's SDKs support.

    The supported shapes are the ones contracts on this branch use:

    - a top-level `string`, with `enum`, `minLength`, or `maxLength`;
    - a top-level `integer`, with `minimum` or `maximum`;
    - a top-level `array` of strings, or of a `$ref` to a `$defs` object, with
      `minItems` and `maxItems`. String items may set `minLength`, `maxLength`, or
      `x-image`.

    A property may be omitted from `required`; both SDKs treat that as optional.
    The root and each `$defs` object set `additionalProperties` to false, and every
    `required` entry names a property.
    A `$defs` name is a PascalCase identifier. Its fields are strings with `minLength`
    or `maxLength`.

    `title` and `description` are allowed anywhere. `x-image` is not walked into; the
    x-image rule validates it.
    """
    if not isinstance(doc, dict):
        return ["(root): an input schema must be an object schema"]
    problems: list[str] = []

    def unsupported(where: str, node: dict, allowed: frozenset[str] | set[str]) -> None:
        for keyword in node:
            if keyword not in allowed:
                problems.append(
                    f"{where}: {keyword} is not supported in an input schema"
                )

    unsupported("(root)", doc, _ROOT)
    if doc.get("type") != "object":
        problems.append("(root): an input schema must have type object")
    if doc.get("additionalProperties") is not False:
        problems.append("(root): additionalProperties must be false")
    properties = doc.get("properties", {})
    if isinstance(properties, dict):
        problems.extend(
            _required_problems("(root)", properties, doc.get("required", []))
        )

    defs = doc.get("$defs", {})
    for name, spec in properties.items() if isinstance(properties, dict) else []:
        where = f"properties/{name}"
        kind = spec.get("type") if isinstance(spec, dict) else None
        if not isinstance(kind, str) or kind not in _TOP_LEVEL:
            problems.append(f"{where}: type {kind!r} is not supported")
            continue
        unsupported(where, spec, _TOP_LEVEL[kind])
        if kind == "string" and not all(
            isinstance(v, str) for v in spec.get("enum", [])
        ):
            problems.append(f"{where}: enum values must be strings")
        if kind == "array":
            problems.extend(_item_problems(f"{where}/items", spec.get("items"), defs))

    if isinstance(defs, dict):
        for name, spec in defs.items():
            where = f"$defs/{name}"
            if not isinstance(name, str) or not _DEF_NAME.fullmatch(name):
                problems.append(
                    f"{where}: definition names must be PascalCase identifiers"
                )
            if not isinstance(spec, dict) or spec.get("type") != "object":
                problems.append(f"{where}: only object definitions are supported")
                continue
            unsupported(where, spec, _DEF_OBJECT)
            if spec.get("additionalProperties") is not False:
                problems.append(f"{where}: additionalProperties must be false")
            def_properties = spec.get("properties", {})
            if isinstance(def_properties, dict):
                problems.extend(
                    _required_problems(where, def_properties, spec.get("required", []))
                )
            for field, field_spec in spec.get("properties", {}).items():
                here = f"{where}/properties/{field}"
                if (
                    not isinstance(field_spec, dict)
                    or field_spec.get("type") != "string"
                ):
                    kind = (
                        field_spec.get("type") if isinstance(field_spec, dict) else None
                    )
                    problems.append(f"{here}: {kind} fields are not supported")
                    continue
                unsupported(here, field_spec, _DEF_FIELD)
    return problems


def _required_problems(where: str, properties: dict, required: object) -> list[str]:
    """`required` names that are not properties."""
    if not isinstance(required, list):
        return [f"{where}: required must list property names"]
    return [
        f"{where}: required entry {entry!r} is not a property"
        for entry in required
        if entry not in properties
    ]


def _item_problems(where: str, items: object, defs: dict) -> list[str]:
    if not isinstance(items, dict):
        return [f"{where}: an array input must declare its items"]
    if "$ref" in items:
        ref = items["$ref"]
        key = ref.removeprefix("#/$defs/") if isinstance(ref, str) else None
        extra = [
            f"{where}: {k} is not supported beside $ref" for k in items if k != "$ref"
        ]
        if not (
            isinstance(ref, str)
            and ref.startswith("#/$defs/")
            and isinstance(defs, dict)
            and key in defs
        ):
            return [*extra, f"{where}: $ref {ref!r} must name an entry in $defs"]
        return extra
    kind = items.get("type")
    if kind != "string":
        return [f"{where}: {kind} items are not supported"]
    return [
        f"{where}: {keyword} is not supported in an input schema"
        for keyword in items
        if keyword not in _STRING_ITEM
    ]


class EvalSchemas(Check):
    name = "eval-schemas"
    description = (
        "Meta-validate each evaluator's input_schema.json / output_schema.json"
    )

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

    def _check_schema_file(
        self, ref: dict, key: str, base: str, result: Result
    ) -> None:
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
            result.violations.append(
                Violation(path, f"not a valid JSON Schema: {e.message}")
            )
            return
        self._check_key_casing(doc, path, result)
        self._check_x_image(doc, path, result)
        self._check_model_only(doc, key, path, result)
        if key == "input_schema":
            result.violations.extend(
                Violation(path, m) for m in input_shape_problems(doc)
            )

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
                message = (
                    "x-model-only belongs only on a top-level output_schema property"
                )
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
            for err in sorted(
                self._x_image_validator.iter_errors(block), key=lambda e: list(e.path)
            ):
                loc = "/".join(str(p) for p in err.path) or "(root)"
                result.violations.append(
                    Violation(path, f"{name}.x-image: {loc}: {err.message}")
                )
            if isinstance(block, dict):
                for lo, hi in (("min_bytes", "max_bytes"), ("min_edge", "max_edge")):
                    a, b = block.get(lo), block.get(hi)
                    if type(a) is int and type(b) is int and a > b:
                        result.violations.append(
                            Violation(
                                path, f"{name}.x-image: {lo} ({a}) exceeds {hi} ({b})"
                            )
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
                    Violation(
                        path,
                        f"property {name!r} is not snake_case: use {_to_snake(name)!r}",
                    )
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
