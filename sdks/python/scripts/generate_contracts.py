#!/usr/bin/env python3
"""Bundle the ``evals/`` registry into the package and generate its schema modules (D1).

Each ``evals/<family>/<subject>/<evaluator>/config.json`` is one evaluator contract. For
every contract this script:

1. Copies the contract into ``src/learning_commons_evaluators/contracts/_generated/`` —
   ``config.json``, the input and output schemas it references, and every prompt or rubric
   file it names — byte for byte, after checking each file against the sha256 the config
   declares for it. A mismatch fails the build: text reaching the model must not drift
   unnoticed.
2. Writes ``src/learning_commons_evaluators/schemas/<family>/<subject>/<evaluator>.py`` with
   a pydantic ``<Class>Input`` model built from ``input_schema.json`` and a ``<Class>Output``
   model built from ``output_schema.json``.

The bundled directory is package data read by ``contracts.loader``; the schema modules are
regular source that the evaluators import. Both are committed, so an installed package
carries them and a stale checkout fails ``--check`` in CI rather than at a user's import.

Usage (from ``sdks/python/``)::

    python scripts/generate_contracts.py            # write everything
    python scripts/generate_contracts.py --check    # exit 1 if anything is stale or orphaned

The Makefile wraps these as ``make generate-contracts`` and ``make check-generated``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import keyword
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_SDK_ROOT = _SCRIPT_DIR.parent
_REPO_ROOT = _SDK_ROOT.parent.parent
_EVALS_ROOT = _REPO_ROOT / "evals"
_PACKAGE_ROOT = _SDK_ROOT / "src" / "learning_commons_evaluators"
_BUNDLE_ROOT = _PACKAGE_ROOT / "contracts" / "_generated"
_SCHEMAS_ROOT = _PACKAGE_ROOT / "schemas"

#: First line of every generated Python module, and the only record of which are generated.
GENERATED_MARKER = "# GENERATED — do not edit directly."

_INDENT = "    "


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_contracts(evals_root: Path = _EVALS_ROOT) -> list[Path]:
    """Every ``config.json`` under ``evals/``, sorted so output order is stable."""
    return sorted(
        path
        for path in evals_root.glob("*/*/*/config.json")
        if not path.parent.name.startswith("_") and ".ipynb_checkpoints" not in path.parts
    )


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------


def to_pascal_case(name: str) -> str:
    """``grade_level_appropriateness`` and ``grade-level`` both become PascalCase."""
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[-_\s]+", name) if part)


def to_upper_snake(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").upper()


def _identifier(name: str) -> tuple[str, str | None]:
    """A usable attribute name for a JSON property, plus the alias pydantic needs if it changed."""
    candidate = re.sub(r"\W", "_", name)
    if not candidate or candidate[0].isdigit():
        candidate = f"field_{candidate}"
    if keyword.iskeyword(candidate):
        candidate = f"{candidate}_"
    return candidate, (name if candidate != name else None)


def _quote(value: Any) -> str:
    """A Python literal for a JSON scalar, double-quoted like the formatter would write it.

    JSON string escapes are a subset of Python's, so ``json.dumps`` yields a valid Python
    string literal; ``ensure_ascii=False`` keeps the registry's typography readable.
    """
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return repr(value)


def _literal(values: list[Any]) -> str:
    return "Literal[" + ", ".join(_quote(v) for v in values) + "]"


# ---------------------------------------------------------------------------
# JSON Schema -> pydantic source
# ---------------------------------------------------------------------------

# JSON Schema keyword -> pydantic ``Field`` keyword, for the constraints the registry uses.
_CONSTRAINTS = {
    "minimum": "ge",
    "maximum": "le",
    "exclusiveMinimum": "gt",
    "exclusiveMaximum": "lt",
    "minLength": "min_length",
    "maxLength": "max_length",
    "minItems": "min_length",
    "maxItems": "max_length",
    "pattern": "pattern",
}


@dataclass
class _Emitter:
    """Turns one JSON Schema document into pydantic classes, dependencies first.

    Classes are appended to ``blocks`` in an order where every referenced class is defined
    before the class that uses it, so the module needs no forward references.
    """

    defs: dict[str, dict[str, Any]]
    blocks: list[str] = field(default_factory=list)
    names: set[str] = field(default_factory=set)
    #: ``$defs`` key -> emitted type expression, filled as each is first referenced.
    def_types: dict[str, str] = field(default_factory=dict)
    uses_literal: bool = False
    uses_field: bool = False
    uses_config: bool = False
    uses_any: bool = False

    def unique(self, name: str) -> str:
        candidate, n = name, 2
        while candidate in self.names:
            candidate = f"{name}{n}"
            n += 1
        self.names.add(candidate)
        return candidate

    def def_type(self, key: str) -> str:
        """The type expression for ``#/$defs/<key>``, emitting it on first use."""
        if key not in self.def_types:
            node = self.defs.get(key)
            if node is None:
                raise ValueError(f'Cannot resolve $ref "#/$defs/{key}": not found in $defs')
            if node.get("type") == "object" and "properties" in node:
                self.def_types[key] = self.emit_class(self.unique(key), node)
            else:
                alias = self.unique(key)
                expr = self.type_expr(node, alias)
                doc = node.get("description")
                lines = [f"# {doc}"] if isinstance(doc, str) else []
                lines.append(f"{alias} = {expr}")
                self.blocks.append("\n".join(lines))
                self.def_types[key] = alias
        return self.def_types[key]

    def type_expr(self, node: dict[str, Any], name_hint: str) -> str:
        """A Python type for one schema node, emitting any class it needs."""
        ref = node.get("$ref")
        if isinstance(ref, str):
            if not ref.startswith("#/$defs/"):
                raise ValueError(f"Unsupported $ref {ref!r}: only #/$defs/<key> is supported")
            return self.def_type(ref[len("#/$defs/") :])

        declared = node.get("type")
        nullable = False
        if isinstance(declared, list):
            kinds = [t for t in declared if t != "null"]
            nullable = len(kinds) != len(declared)
            if len(kinds) != 1:
                raise ValueError(f"Unsupported type union {declared!r} at {name_hint}")
            declared = kinds[0]

        if "enum" in node:
            self.uses_literal = True
            expr = _literal(list(node["enum"]))
        elif declared == "string":
            expr = "str"
        elif declared == "integer":
            expr = "int"
        elif declared == "number":
            expr = "float"
        elif declared == "boolean":
            expr = "bool"
        elif declared == "array":
            items = node.get("items")
            if not isinstance(items, dict):
                raise ValueError(f"Array at {name_hint} declares no items schema")
            expr = f"list[{self.type_expr(items, name_hint + 'Item')}]"
        elif declared == "object":
            if "properties" in node:
                expr = self.emit_class(self.unique(name_hint), node)
            else:
                self.uses_any = True
                expr = "dict[str, Any]"
        else:
            raise ValueError(f"Unsupported schema type {declared!r} at {name_hint}")

        return f"{expr} | None" if nullable else expr

    def field_line(
        self,
        prop: str,
        node: dict[str, Any],
        required: bool,
        class_name: str,
        *,
        constraints: bool,
    ) -> str:
        attr, alias = _identifier(prop)
        # Inline objects are named after their property (``Indicators``, ``LearningComponentsItem``);
        # ``unique`` disambiguates the rare collision with a ``$defs`` key.
        expr = self.type_expr(node, to_pascal_case(prop))
        kwargs: list[str] = []
        if alias is not None:
            kwargs.append(f"alias={_quote(alias)}")
        if constraints:
            for json_key, field_key in _CONSTRAINTS.items():
                if json_key in node:
                    kwargs.append(f"{field_key}={_quote(node[json_key])}")
        description = node.get("description")
        if isinstance(description, str) and description:
            kwargs.append(f"description={_quote(description)}")

        if not required:
            expr = f"{expr} | None"
            kwargs.insert(0, "default=None")
        if not kwargs:
            return f"{_INDENT}{attr}: {expr}"
        self.uses_field = True
        if len(kwargs) == 1 and not required:
            return f"{_INDENT}{attr}: {expr} = None"
        return f"{_INDENT}{attr}: {expr} = Field({', '.join(kwargs)})"

    def emit_class(
        self,
        name: str,
        node: dict[str, Any],
        *,
        docstring: str | None = None,
        config: str | None = None,
        constraints: bool = True,
        type_overrides: dict[str, str] | None = None,
    ) -> str:
        """Emit ``class <name>(BaseModel)`` for an object node and return its name."""
        properties: dict[str, dict[str, Any]] = node.get("properties", {})
        required = set(node.get("required", []))
        lines = [f"class {name}(BaseModel):"]

        doc = docstring or node.get("description")
        if isinstance(doc, str) and doc:
            lines.append(f'{_INDENT}"""{_escape_doc(doc)}"""')
            lines.append("")

        if config is not None:
            self.uses_config = True
            lines.append(f"{_INDENT}model_config = {config}")
            lines.append("")
        elif node.get("additionalProperties") is False:
            self.uses_config = True
            lines.append(f'{_INDENT}model_config = ConfigDict(extra="forbid")')
            lines.append("")

        for prop, spec in properties.items():
            if type_overrides and prop in type_overrides:
                lines.append(
                    self._override_line(prop, spec, type_overrides[prop], prop in required)
                )
            else:
                lines.append(
                    self.field_line(prop, spec, prop in required, name, constraints=constraints)
                )

        if not properties:
            lines.append(f"{_INDENT}pass")
        self.blocks.append("\n".join(lines))
        return name

    def _override_line(self, prop: str, spec: dict[str, Any], expr: str, required: bool) -> str:
        """A field whose type the caller fixed (inputs), keeping alias, description and optionality."""
        attr, alias = _identifier(prop)
        kwargs: list[str] = []
        if alias is not None:
            kwargs.append(f"alias={_quote(alias)}")
        description = spec.get("description")
        if isinstance(description, str) and description:
            kwargs.append(f"description={_quote(description)}")
        if not required:
            expr = f"{expr} | None"
            kwargs.insert(0, "default=None")
        if not kwargs:
            return f"{_INDENT}{attr}: {expr}"
        self.uses_field = True
        if len(kwargs) == 1 and not required:
            return f"{_INDENT}{attr}: {expr} = None"
        return f"{_INDENT}{attr}: {expr} = Field({', '.join(kwargs)})"

    def imports(self) -> list[str]:
        typing: list[str] = []
        if self.uses_any:
            typing.append("Any")
        if self.uses_literal:
            typing.append("Literal")
        pydantic = ["BaseModel"]
        if self.uses_config:
            pydantic.append("ConfigDict")
        if self.uses_field:
            pydantic.append("Field")
        lines = ["from __future__ import annotations", ""]
        if typing:
            lines.append(f"from typing import {', '.join(typing)}")
            lines.append("")
        lines.append(f"from pydantic import {', '.join(pydantic)}")
        return lines


def _escape_doc(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')


def _grade_tokens_are_ints(values: list[Any]) -> bool:
    return all(isinstance(v, str) and v.isdigit() for v in values)


def emit_schema_module(config: dict[str, Any], config_dir: Path) -> str:
    """The source of ``schemas/<family>/<subject>/<evaluator>.py`` for one contract."""
    evaluator = config["evaluator"]
    evaluator_id: str = evaluator["id"]
    slug = evaluator_id.rsplit(".", 1)[-1]
    class_base = to_pascal_case(slug)
    name = str(evaluator.get("name", slug))

    input_ref = config["input_schema"]["$ref"]
    output_ref = config["output_schema"]["$ref"]
    input_schema = json.loads((config_dir / input_ref).read_text(encoding="utf-8"))
    output_schema = json.loads((config_dir / output_ref).read_text(encoding="utf-8"))

    emitter = _Emitter(defs=dict(output_schema.get("$defs", {})))

    # --- Input: placeholder names as kwargs; bounds and enums are enforced by the
    # evaluator from the schema (SDK spec §4), so the model carries only the shape. Grade
    # tokens are digits in every contract today, and Python callers pass an int.
    constants: list[str] = []
    overrides: dict[str, str] = {}
    for prop, spec in input_schema.get("properties", {}).items():
        values = spec.get("enum")
        if isinstance(values, list):
            constant = to_upper_snake(prop) + "_VALUES"
            listed = "".join(f"{_INDENT}{_quote(str(v))},\n" for v in values)
            constants.append(
                f"#: Accepted values of ``{prop}``, as the input schema declares them.\n"
                f"{constant}: tuple[str, ...] = (\n{listed})"
            )
            overrides[prop] = (
                "int" if prop == "grade_level" and _grade_tokens_are_ints(values) else "str"
            )
        elif spec.get("type") == "integer":
            overrides[prop] = "int"
        elif spec.get("type") == "string":
            overrides[prop] = "str"
    input_name = emitter.unique(f"{class_base}Input")
    emitter.emit_class(
        input_name,
        input_schema,
        docstring=f"Inputs to the {name}, named as its input_schema.json declares them.",
        config='ConfigDict(extra="forbid", frozen=True)',
        constraints=False,
        type_overrides=overrides,
    )

    # --- Output: the full structured payload, strict, with descriptions kept for the
    # structured-output request. The root description describes the contract, not a field
    # the model fills in, so it is replaced.
    output_name = emitter.unique(f"{class_base}Output")
    emitter.emit_class(
        output_name,
        output_schema,
        docstring=f"Output of the {name}, per its output_schema.json.",
    )

    def rel(p: str) -> str:
        return _describe((config_dir / p).resolve())

    header = [
        GENERATED_MARKER,
        f"# Source: {rel(output_ref)}",
        f"#         {rel(input_ref)}",
        "# Regenerate: make generate-contracts",
        f'"""Input and output models for the {name}."""',
        "",
        *emitter.imports(),
        "",
        f"EVALUATOR_ID = {_quote(evaluator_id)}",
    ]
    body = [*constants, *emitter.blocks]
    exported = [input_name, output_name]
    footer = ["__all__ = [", *(f"{_INDENT}{_quote(n)}," for n in sorted(exported)), "]"]
    return "\n\n\n".join(["\n".join(header), *body, "\n".join(footer)]) + "\n"


def emit_package_init(dotted: str) -> str:
    return f'{GENERATED_MARKER}\n"""Generated schema modules for ``{dotted}``."""\n'


# ---------------------------------------------------------------------------
# Planning the file set
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlannedFile:
    path: Path
    content: bytes


def _checked_bytes(
    config_dir: Path, source_path: str, declared_sha: str | None, owner: str
) -> bytes:
    path = config_dir / source_path
    if not path.is_file():
        raise SystemExit(f"{owner}: {source_path} does not exist")
    raw = path.read_bytes()
    if declared_sha is not None:
        actual = hashlib.sha256(raw).hexdigest()
        if actual != declared_sha:
            raise SystemExit(
                f"{owner}: sha256 drift for {source_path}: "
                f"declared {declared_sha[:12]}…, actual {actual[:12]}…"
            )
    return raw


def plan_contract(config_path: Path) -> list[PlannedFile]:
    """Every file one contract contributes: its bundle and its schema module."""
    config_dir = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8"))
    evaluator_id: str = config["evaluator"]["id"]
    segments = evaluator_id.split(".")
    owner = _describe(config_path)

    bundle_dir = _BUNDLE_ROOT.joinpath(*segments)
    planned: dict[Path, bytes] = {bundle_dir / "config.json": config_path.read_bytes()}

    for key in ("input_schema", "output_schema"):
        ref = config[key]["$ref"]
        planned[bundle_dir / ref] = _checked_bytes(config_dir, ref, None, owner)

    for step in config.get("steps", []):
        for message in (step.get("prompt") or {}).get("messages", []):
            source = message["source_path"]
            planned[bundle_dir / source] = _checked_bytes(
                config_dir, source, message.get("sha256"), f"{owner} step {step['id']}"
            )
    for entry in config.get("preprocessing", []) or []:
        source = entry.get("source_path")
        if source:
            planned[bundle_dir / source] = _checked_bytes(
                config_dir, source, entry.get("sha256"), f"{owner} preprocessing {entry['id']}"
            )

    module_dir = _SCHEMAS_ROOT.joinpath(*segments[:-1])
    planned[module_dir / f"{segments[-1]}.py"] = emit_schema_module(config, config_dir).encode()
    for depth in range(1, len(segments)):
        package = _SCHEMAS_ROOT.joinpath(*segments[:depth])
        planned[package / "__init__.py"] = emit_package_init(".".join(segments[:depth])).encode()

    return [PlannedFile(path, content) for path, content in planned.items()]


def plan_all(config_paths: list[Path]) -> list[PlannedFile]:
    planned: dict[Path, PlannedFile] = {}
    for config_path in config_paths:
        for item in plan_contract(config_path):
            existing = planned.get(item.path)
            if existing is not None and existing.content != item.content:
                raise SystemExit(f"Two contracts generate {item.path} with different content")
            planned[item.path] = item
    return sorted(planned.values(), key=lambda f: f.path)


def existing_generated_files() -> set[Path]:
    """Everything on disk the generator owns: the bundle, and marker-bearing schema modules."""
    owned: set[Path] = set()
    if _BUNDLE_ROOT.is_dir():
        owned.update(p for p in _BUNDLE_ROOT.rglob("*") if p.is_file())
    for path in _SCHEMAS_ROOT.rglob("*.py"):
        if path.parent == _SCHEMAS_ROOT:
            continue  # hand-written modules live directly under schemas/
        with path.open(encoding="utf-8") as handle:
            if handle.readline().rstrip("\n") == GENERATED_MARKER:
                owned.add(path)
    return owned


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _describe(path: Path) -> str:
    """A path as printed: repo-relative when it is in the repo, absolute otherwise."""
    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def cmd_generate(config_paths: list[Path]) -> int:
    planned = plan_all(config_paths)
    wanted = {f.path for f in planned}
    for orphan in sorted(existing_generated_files() - wanted):
        orphan.unlink()
        print(f"  removed    {_describe(orphan)}")
    written = 0
    for item in planned:
        if item.path.exists() and item.path.read_bytes() == item.content:
            continue
        item.path.parent.mkdir(parents=True, exist_ok=True)
        item.path.write_bytes(item.content)
        written += 1
        print(f"  generated  {_describe(item.path)}")
    _prune_empty_dirs(_BUNDLE_ROOT)
    print(f"Done: {len(config_paths)} contracts, {written} files written.")
    return 0


def cmd_check(config_paths: list[Path]) -> int:
    planned = plan_all(config_paths)
    stale: list[str] = []
    for item in planned:
        if not item.path.exists():
            stale.append(f"MISSING  {_describe(item.path)}")
        elif item.path.read_bytes() != item.content:
            stale.append(f"STALE    {_describe(item.path)}")
    for orphan in sorted(existing_generated_files() - {f.path for f in planned}):
        stale.append(f"ORPHAN   {_describe(orphan)}")
    if stale:
        print("\n".join(stale))
        print("\nRun: make generate-contracts")
        return 1
    print(f"All generated files are up to date ({len(config_paths)} contracts).")
    return 0


def _prune_empty_dirs(root: Path) -> None:
    if not root.is_dir():
        return
    for directory in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed files match what would be generated; exit 1 otherwise.",
    )
    args = parser.parse_args(argv)

    config_paths = discover_contracts()
    if not config_paths:
        print(f"No contracts found under {_EVALS_ROOT}", file=sys.stderr)
        return 1
    return cmd_check(config_paths) if args.check else cmd_generate(config_paths)


if __name__ == "__main__":
    sys.exit(main())
