#!/usr/bin/env python3
"""Generate each SDK's telemetry event types from ``evals/telemetry/event.schema.json``.

The schema is the single source of truth for the event both SDKs send to the collector.
Each target below renders it into one generated module, so the SDKs cannot drift from the
schema or from each other: a field, its type, its position on the wire, and whether it may
be omitted all come from the schema.

  python3 scripts/generate_telemetry_schema.py          # rewrite the generated modules
  python3 scripts/generate_telemetry_schema.py --check  # exit 1 if any is stale

``scripts/check.py`` runs the same comparison as its ``telemetry-schema`` check (and
``--fix`` rewrites), alongside the schema-hash ↔ ``schema_version`` rule.

The generator understands a deliberately small subset of JSON Schema — the shapes the event
uses — and refuses anything else rather than guessing at it (:func:`schema_problems`):

- the root and every ``$defs`` object: ``type: object`` with ``properties``, ``required``,
  and ``additionalProperties: false``;
- a ``$defs`` string enum, referenced by ``$ref``;
- a property that is a ``string``, an ``integer`` (optionally ``const`` or ``minimum``), a
  ``boolean``, a ``$ref`` to a ``$defs`` entry, or an ``array`` whose ``items`` is a
  ``$ref`` to a ``$defs`` object.

Wire rules, identical in every target: keys are written in schema property order; a
required property is always written; an optional property is omitted when unset, never
written as ``null``; and a key the schema does not declare is never written.

Only the standard library is used, so the repo-checks CI job runs this with no extra
dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "evals" / "telemetry" / "event.schema.json"
#: ``schema_version`` → hash of the wire shape it names. Append-only.
VERSIONS_PATH = REPO_ROOT / "evals" / "telemetry" / "schema-versions.json"

REGENERATE = "python3 scripts/generate_telemetry_schema.py"
GENERATED_MARKER = "GENERATED — do not edit directly."

_SNAKE_CASE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
_PASCAL_CASE = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_ANNOTATIONS = frozenset({"title", "description", "$comment"})
_REF_PREFIX = "#/$defs/"


# --- the model the targets render ---------------------------------------------------------


@dataclass(frozen=True)
class FieldType:
    """One property's type. ``kind`` is string | integer | boolean | ref | array."""

    kind: str
    #: The ``$defs`` name, for ``ref`` and ``array``.
    ref: str | None = None
    #: A ``const`` value, for a property pinned to one value.
    const: Any = None


@dataclass(frozen=True)
class Field:
    name: str
    type: FieldType
    required: bool
    description: str | None


@dataclass(frozen=True)
class EnumDef:
    name: str
    values: tuple[str, ...]
    description: str | None


@dataclass(frozen=True)
class ObjectDef:
    name: str
    fields: tuple[Field, ...]
    description: str | None


@dataclass(frozen=True)
class Model:
    """The schema, as the targets see it. ``objects`` ends with the event itself."""

    enums: tuple[EnumDef, ...]
    objects: tuple[ObjectDef, ...]
    schema_version: int

    @property
    def event(self) -> ObjectDef:
        return self.objects[-1]

    def kind_of(self, name: str) -> str:
        if any(e.name == name for e in self.enums):
            return "enum"
        return "object"


# --- reading and checking the schema ------------------------------------------------------


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_problems(schema: Any) -> list[str]:
    """Every place the schema leaves the subset the targets render, or the envelope rule.

    The envelope rule: per-evaluator variation lives only under ``metadata``, as named,
    typed, optional blocks; every other part of the event is the same for every evaluator.
    That is enforced structurally — every object is closed (``additionalProperties: false``),
    so nothing can be added outside a declared property, and ``metadata`` may hold only
    optional ``$ref``/array-of-``$ref`` blocks pointing at closed ``$defs`` objects.
    """
    if not isinstance(schema, dict):
        return ["(root): the schema must be a JSON object"]
    problems: list[str] = []
    defs = schema.get("$defs", {})
    if not isinstance(defs, dict):
        return ["$defs: must be an object"]

    title = schema.get("title")
    if not isinstance(title, str) or not _PASCAL_CASE.match(title):
        problems.append("(root): title must be a PascalCase name; it names the event type")
    if title in defs:
        problems.append(f"(root): title {title!r} collides with a $defs name")

    for name, node in defs.items():
        where = f"$defs/{name}"
        if not _PASCAL_CASE.match(name):
            problems.append(f"{where}: a $defs name must be PascalCase")
        if not isinstance(node, dict):
            problems.append(f"{where}: must be an object")
            continue
        if node.get("type") == "string":
            problems.extend(_enum_problems(where, node))
        else:
            problems.extend(_object_problems(where, node, defs))

    problems.extend(_object_problems("(root)", schema, defs, root=True))

    version = schema.get("properties", {}).get("schema_version")
    if not (
        isinstance(version, dict)
        and version.get("type") == "integer"
        and isinstance(version.get("const"), int)
        and version["const"] >= 1
    ):
        problems.append("properties/schema_version: must be an integer with a const >= 1")
    if "schema_version" not in schema.get("required", []):
        problems.append("properties/schema_version: must be required")

    problems.extend(_envelope_problems(schema, defs))
    return problems


def _enum_problems(where: str, node: dict[str, Any]) -> list[str]:
    problems = [
        f"{where}: {keyword} is not supported in a string $defs entry"
        for keyword in node
        if keyword not in _ANNOTATIONS | {"type", "enum"}
    ]
    values = node.get("enum")
    if not (
        isinstance(values, list)
        and values
        and all(isinstance(v, str) for v in values)
        and len(set(values)) == len(values)
    ):
        problems.append(f"{where}: a string $defs entry must be an enum of distinct strings")
    return problems


def _object_problems(
    where: str, node: dict[str, Any], defs: dict[str, Any], *, root: bool = False
) -> list[str]:
    allowed = _ANNOTATIONS | {"type", "properties", "required", "additionalProperties"}
    if root:
        allowed |= {"$schema", "$id", "$defs"}
    problems = [
        f"{where}: {keyword} is not supported on an object"
        for keyword in node
        if keyword not in allowed
    ]
    if node.get("type") != "object":
        problems.append(f"{where}: must have type object (or be a string enum)")
    if node.get("additionalProperties") is not False:
        problems.append(f"{where}: additionalProperties must be false")
    properties = node.get("properties")
    if not isinstance(properties, dict) or not properties:
        problems.append(f"{where}: must declare at least one property")
        return problems
    required = node.get("required", [])
    if not isinstance(required, list):
        problems.append(f"{where}: required must be a list")
        required = []
    for name in required:
        if name not in properties:
            problems.append(f"{where}: required names {name!r}, which is not a property")
    for name, prop in properties.items():
        problems.extend(_property_problems(f"{where}/properties/{name}", name, prop, defs))
    return problems


def _property_problems(where: str, name: str, prop: Any, defs: dict[str, Any]) -> list[str]:
    if not _SNAKE_CASE.match(name):
        return [f"{where}: a property name must be snake_case"]
    if not isinstance(prop, dict):
        return [f"{where}: must be an object"]
    if "$ref" in prop:
        return _ref_problems(where, prop, defs, allowed=_ANNOTATIONS | {"$ref"})
    kind = prop.get("type")
    allowed_by_kind = {
        "string": {"type"},
        "integer": {"type", "const", "minimum"},
        "boolean": {"type"},
        "array": {"type", "items"},
    }
    if kind not in allowed_by_kind:
        return [f"{where}: type must be one of {sorted(allowed_by_kind)}, or a $ref"]
    problems = [
        f"{where}: {keyword} is not supported on a {kind} property"
        for keyword in prop
        if keyword not in _ANNOTATIONS | allowed_by_kind[kind]
    ]
    if kind == "integer":
        if "const" in prop and not isinstance(prop["const"], int):
            problems.append(f"{where}: const must be an integer")
        if "minimum" in prop and not isinstance(prop["minimum"], int):
            problems.append(f"{where}: minimum must be an integer")
    if kind == "array":
        items = prop.get("items")
        if not isinstance(items, dict) or "$ref" not in items:
            problems.append(f"{where}: items must be a $ref to a $defs object")
        else:
            problems.extend(_ref_problems(f"{where}/items", items, defs, allowed={"$ref"}))
            target = _ref_name(items["$ref"])
            if target in defs and defs[target].get("type") != "object":
                problems.append(f"{where}/items: must reference a $defs object")
    return problems


def _ref_problems(
    where: str, node: dict[str, Any], defs: dict[str, Any], *, allowed: set[str] | frozenset[str]
) -> list[str]:
    problems = [
        f"{where}: {keyword} cannot sit beside $ref" for keyword in node if keyword not in allowed
    ]
    ref = node["$ref"]
    if not isinstance(ref, str) or not ref.startswith(_REF_PREFIX):
        problems.append(f"{where}: $ref must point into #/$defs/")
    elif _ref_name(ref) not in defs:
        problems.append(f"{where}: $ref {ref!r} names no $defs entry")
    return problems


def _envelope_problems(schema: dict[str, Any], defs: dict[str, Any]) -> list[str]:
    metadata = schema.get("properties", {}).get("metadata")
    if metadata is None:
        return []
    where = "properties/metadata"
    if not isinstance(metadata, dict) or "$ref" not in metadata:
        return [f"{where}: must be a $ref to the $defs object holding the metadata blocks"]
    if "metadata" in schema.get("required", []):
        return [f"{where}: must be optional; an event with no block to report omits it"]
    target = defs.get(_ref_name(metadata["$ref"]))
    if not isinstance(target, dict) or target.get("type") != "object":
        return [f"{where}: must reference a $defs object"]
    problems = []
    if target.get("required"):
        problems.append(f"{where}: every metadata block must be optional")
    for name, block in target.get("properties", {}).items():
        ref = block.get("$ref") or (block.get("items") or {}).get("$ref")
        block_def = defs.get(_ref_name(ref)) if isinstance(ref, str) else None
        if not isinstance(block_def, dict) or block_def.get("type") != "object":
            problems.append(
                f"{where}/{name}: a metadata block must be a $ref, or an array of $ref, "
                "to a typed $defs object"
            )
    return problems


def _ref_name(ref: str) -> str:
    return ref[len(_REF_PREFIX) :] if ref.startswith(_REF_PREFIX) else ref


def build_model(schema: dict[str, Any]) -> Model:
    """The schema as targets render it. Raises ``ValueError`` on any :func:`schema_problems`."""
    problems = schema_problems(schema)
    if problems:
        raise ValueError("telemetry schema is not renderable:\n  " + "\n  ".join(problems))
    enums: list[EnumDef] = []
    objects: list[ObjectDef] = []
    for name, node in schema["$defs"].items():
        if node["type"] == "string":
            enums.append(EnumDef(name, tuple(node["enum"]), node.get("description")))
        else:
            objects.append(_object(name, node))
    objects.append(_object(schema["title"], schema))
    version = schema["properties"]["schema_version"]["const"]
    return Model(tuple(enums), tuple(objects), version)


def _object(name: str, node: dict[str, Any]) -> ObjectDef:
    required = set(node.get("required", []))
    fields = []
    for prop_name, prop in node["properties"].items():
        if "$ref" in prop:
            field_type = FieldType("ref", ref=_ref_name(prop["$ref"]))
        elif prop["type"] == "array":
            field_type = FieldType("array", ref=_ref_name(prop["items"]["$ref"]))
        else:
            field_type = FieldType(prop["type"], const=prop.get("const"))
        fields.append(Field(prop_name, field_type, prop_name in required, prop.get("description")))
    return ObjectDef(name, tuple(fields), node.get("description"))


# --- schema_version ↔ wire-shape hash -----------------------------------------------------


def wire_shape_hash(schema: dict[str, Any]) -> str:
    """A hash of what the schema puts on the wire, and nothing else.

    Annotations (``description``, ``title``, ``$comment``) are dropped, so rewording a doc
    comment needs no version bump. ``schema_version``'s own ``const`` is dropped too, so the
    hash names the shape, not the number given to it. Key order is normalized everywhere
    except inside ``properties``, whose order *is* wire order: reordering two properties
    changes what is sent, so it changes the hash. The ``required`` and ``enum`` arrays are
    sorted, since they are sets in JSON Schema and their order reaches no wire.
    """
    stripped = _without_annotations(schema)
    version = stripped.get("properties", {}).get("schema_version")
    if isinstance(version, dict):
        version.pop("const", None)
    canonical = json.dumps(_canonical(stripped), separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _without_annotations(node: Any, *, in_properties: bool = False) -> Any:
    if isinstance(node, dict):
        return {
            key: _without_annotations(value, in_properties=key == "properties" and not in_properties)
            for key, value in node.items()
            # A property *named* like an annotation is a property, not an annotation.
            if in_properties or key not in _ANNOTATIONS | {"$id", "$schema"}
        }
    if isinstance(node, list):
        return [_without_annotations(item) for item in node]
    return node


#: Keywords whose array value is a set: its order is not part of the wire shape.
_UNORDERED_ARRAYS = frozenset({"required", "enum"})


def _canonical(node: Any, *, ordered: bool = False) -> Any:
    """Plain data with dict key order normalized, except where order is meaningful."""
    if isinstance(node, dict):
        keys = list(node) if ordered else sorted(node)
        # A list of pairs, not a dict, so json.dumps cannot reorder what we just ordered.
        return [[key, _canonical_value(key, node[key], in_properties=ordered)] for key in keys]
    if isinstance(node, list):
        return [_canonical(item) for item in node]
    return node


def _canonical_value(key: str, value: Any, *, in_properties: bool) -> Any:
    # Inside ``properties`` a key is a property name, so one named ``required`` or ``enum``
    # holds a subschema, not a keyword's set.
    if not in_properties and key in _UNORDERED_ARRAYS and isinstance(value, list):
        return sorted((_canonical(item) for item in value), key=json.dumps)
    return _canonical(value, ordered=key == "properties" and not in_properties)


def load_versions(path: Path = VERSIONS_PATH) -> dict[int, str]:
    return parse_versions(path.read_text(encoding="utf-8"))


def parse_versions(text: str) -> dict[int, str]:
    data = json.loads(text)
    return {int(version): digest for version, digest in data["versions"].items()}


def render_versions(versions: dict[int, str]) -> str:
    data = {
        "$comment": (
            "schema_version -> hash of the wire shape it names, written by "
            "`python3 scripts/check.py --fix telemetry-schema`. Append-only: a recorded "
            "version is never re-hashed. See scripts/generate_telemetry_schema.py "
            "(wire_shape_hash)."
        ),
        "versions": {str(v): versions[v] for v in sorted(versions)},
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def version_problems(schema: dict[str, Any], versions: dict[int, str]) -> tuple[list[str], bool]:
    """Problems with the current ``schema_version``, and whether recording it would fix them.

    - The current version is recorded with this shape's hash: fine.
    - It is recorded with a different hash: the wire shape changed without a bump. Not
      auto-fixable — bumping is a decision, like a prompt's pinned sha256.
    - It is not recorded, it is one past the newest recorded version, and the shape really
      differs from that version's: a bump. Fixable by recording it.
    - It is older than the newest recorded version: a rollback, even when the older shape's
      hash matches. Versions only move forward, so an event never claims a version the
      collector has seen superseded; restoring an old shape takes a new number. Not fixable.
    - Anything else (a skipped number, a bump with no wire change): not fixable.
    """
    version = schema["properties"]["schema_version"]["const"]
    digest = wire_shape_hash(schema)
    newest = max(versions, default=0)
    if version < newest:
        return [
            f"schema_version {version} is older than the newest recorded version, {newest}; "
            f"versions only move forward, so restoring an older wire shape takes {newest + 1}"
        ], False
    if version in versions:
        if versions[version] == digest:
            return [], False
        return [
            f"the wire shape changed but schema_version is still {version}: bump it to "
            f"{max(versions) + 1} in event.schema.json, then run "
            "`python3 scripts/check.py --fix telemetry-schema` to record it"
        ], False
    if version != newest + 1:
        return [f"schema_version {version} must be the next version after {newest}"], False
    if versions.get(newest) == digest:
        return [
            f"schema_version was bumped to {version} but the wire shape is unchanged from "
            f"{newest}; only a wire-shape change takes a new version"
        ], False
    return [f"schema_version {version} is new and not yet recorded in schema-versions.json"], True


def history_problems(base: dict[int, str], current: dict[int, str], version: int) -> list[str]:
    """How the registry was rewritten relative to ``base``, the copy on the branch it merges into.

    :func:`version_problems` sees only the current file, so it cannot tell a recorded hash
    that was overwritten from one that was always there: change the wire shape, re-hash
    version 1 by hand, and every rule there still holds. Against the base it can: a version
    recorded there must survive with the same hash, and the only entry a change may add is
    the version the schema now names — the one ``--fix`` records. Never auto-fixable.
    """
    problems: list[str] = []
    next_version = max([*base, *current], default=0) + 1
    for recorded in sorted(base):
        if recorded not in current:
            problems.append(
                f"version {recorded} was removed; a recorded version is permanent, because "
                "events already sent under it still carry the number"
            )
        elif current[recorded] != base[recorded]:
            problems.append(
                f"version {recorded}'s recorded hash was changed; a recorded version is "
                f"permanent, so a new wire shape takes version {next_version} instead"
            )
    for added in sorted(set(current) - set(base)):
        if added != version:
            problems.append(
                f"version {added} was added, but the schema is at {version}; record only the "
                "version the schema names (`python3 scripts/check.py --fix telemetry-schema`)"
            )
    return problems


# --- targets ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Target:
    """One generated module: where it goes and how it is rendered."""

    path: Path
    render: Any  # Callable[[Model], str]

    @property
    def relative(self) -> str:
        return self.path.relative_to(REPO_ROOT).as_posix()


def _doc_lines(text: str | None, indent: str, width: int = 92) -> list[str]:
    """``text`` wrapped for a doc comment body, each line prefixed with ``indent``."""
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(indent) + len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return [f"{indent}{line}" for line in lines]


# TypeScript ------------------------------------------------------------------------------


def _ts_type(model: Model, field_type: FieldType) -> str:
    if field_type.const is not None:
        return json.dumps(field_type.const)
    if field_type.kind == "string":
        return "string"
    if field_type.kind == "integer":
        return "number"
    if field_type.kind == "boolean":
        return "boolean"
    if field_type.kind == "array":
        return f"{field_type.ref}[]"
    return field_type.ref or "never"


def _ts_doc(text: str | None, indent: str) -> list[str]:
    body = _doc_lines(text, f"{indent} * ")
    if not body:
        return []
    if len(body) == 1 and len(body[0]) + 3 <= 92:
        return [f"{indent}/** {body[0][len(indent) + 3 :]} */"]
    return [f"{indent}/**", *body, f"{indent} */"]


def _lower_first(name: str) -> str:
    return name[0].lower() + name[1:]


def render_typescript(model: Model) -> str:
    out = [
        f"// {GENERATED_MARKER}",
        "// Source: ../../evals/telemetry/event.schema.json",
        f"// Regenerate: {REGENERATE} (from the repo root)",
        "//",
        "// The telemetry event's types and wire serialization. Keys are written in schema",
        "// order, an unset optional field is omitted, and a key the schema does not declare",
        "// is never written, whatever else the object passed in carries.",
        "",
        "/** The `schema_version` this SDK's events are built against. */",
        f"export const TELEMETRY_SCHEMA_VERSION = {model.schema_version} as const;",
        "",
    ]
    for enum in model.enums:
        out += _ts_doc(enum.description, "")
        out.append(f"export type {enum.name} = {' | '.join(repr(v) for v in enum.values)};")
        out.append("")
    for obj in model.objects:
        out += _ts_doc(obj.description, "")
        out.append(f"export interface {obj.name} {{")
        for i, field in enumerate(obj.fields):
            if i and field.description:
                out.append("")
            out += _ts_doc(field.description, "  ")
            optional = "" if field.required else "?"
            out.append(f"  {field.name}{optional}: {_ts_type(model, field.type)};")
        out.append("}")
        out.append("")
    for obj in model.objects:
        fn = f"{_lower_first(obj.name)}ToWire"
        out.append(f"/** A `{obj.name}` as it goes on the wire. */")
        out.append(f"export function {fn}(value: {obj.name}): Record<string, unknown> {{")
        out.append("  const wire: Record<string, unknown> = {};")
        for field in obj.fields:
            source = f"value.{field.name}"
            if field.type.kind == "ref" and model.kind_of(field.type.ref or "") == "object":
                expr = f"{_lower_first(field.type.ref or '')}ToWire({source})"
            elif field.type.kind == "array":
                expr = f"{source}.map({_lower_first(field.type.ref or '')}ToWire)"
            else:
                expr = source
            if field.required:
                out.append(f"  wire[{field.name!r}] = {expr};")
            else:
                out.append(f"  if ({source} !== undefined) wire[{field.name!r}] = {expr};")
        out.append("  return wire;")
        out.append("}")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


TARGETS: list[Target] = [
    Target(
        REPO_ROOT / "sdks" / "typescript" / "src" / "telemetry" / "types.generated.ts",
        render_typescript,
    ),
]


def rendered(schema: dict[str, Any] | None = None) -> dict[Target, str]:
    """Every target's content for ``schema`` (by default, the committed one)."""
    model = build_model(schema if schema is not None else load_schema())
    return {target: target.render(model) for target in TARGETS}


def stale_targets(schema: dict[str, Any] | None = None) -> list[tuple[Target, str]]:
    """The targets whose committed file differs from what the schema renders."""
    stale = []
    for target, content in rendered(schema).items():
        current = target.path.read_text(encoding="utf-8") if target.path.exists() else None
        if current != content:
            stale.append((target, content))
    return stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a target is stale")
    args = parser.parse_args()
    try:
        stale = stale_targets()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if args.check:
        for target, _ in stale:
            print(f"stale: {target.relative} — run `{REGENERATE}`", file=sys.stderr)
        return 1 if stale else 0
    for target, content in stale:
        target.path.write_text(content, encoding="utf-8")
        print(f"wrote {target.relative}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
