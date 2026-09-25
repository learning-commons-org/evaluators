#!/usr/bin/env python3
"""Generate the Knowledge Graph HTTP client from the vendored OpenAPI spec (D9).

The hand-written wrapper in ``dependencies/knowledge_graph.py`` is what the SDK and its
callers use; this script produces the transport layer underneath it, in
``dependencies/_generated/knowledge_graph/``. That tree is committed, so an installed
package carries it and a stale checkout fails ``--check`` in CI rather than at a user's
import — the same rule ``generate_contracts.py`` follows.

Usage (from ``sdks/python/``)::

    python scripts/generate_kg_client.py            # regenerate the client
    python scripts/generate_kg_client.py --check    # exit 1 if the committed client is stale
    make generate-kg-client
    make check-kg-client

Needs the ``dev`` extra (``openapi-python-client``). Generation is offline from
``openapi/knowledge-graph.yaml``; run ``make fetch-kg-openapi`` first to pick up a newer
published spec.

The client covers the operations in ``_OPERATIONS`` rather than all 31 the service
publishes. The generator has no include/exclude option, so the subset is produced by
filtering its *input*: the vendored spec is reduced to those operations and the
components they reference, and the generator runs on that. The output is still entirely
generator-produced, so ``--check`` compares byte for byte exactly as it would otherwise,
and the vendored document itself stays whole.

Both commands also compare the hand-written taxonomy enums in ``schemas/kg_taxonomy.py``
against the spec's enum lists. A value only the SDK has is an error — it is a token we
would send that the service will reject. A value only the spec has is a warning: the
service gained a jurisdiction or subject and we have not caught up yet, which narrows what
callers can ask for but never produces a bad request.
"""

from __future__ import annotations

import argparse
import filecmp
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Collection
from pathlib import Path
from types import ModuleType
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_SDK_ROOT = _SCRIPT_DIR.parent
_PACKAGE_ROOT = _SDK_ROOT / "src" / "learning_commons_evaluators"
_SPEC_PATH = _SDK_ROOT / "openapi" / "knowledge-graph.yaml"
_CONFIG_PATH = _SDK_ROOT / "openapi" / "knowledge-graph-client.yaml"
_GENERATED_DIR = _PACKAGE_ROOT / "dependencies" / "_generated" / "knowledge_graph"
_TAXONOMY_PATH = _PACKAGE_ROOT / "schemas" / "kg_taxonomy.py"

#: The operations the SDK calls, by ``operationId``. The client is generated from a spec
#: filtered to these and whatever they reference, so the committed tree is the transport
#: for the endpoints we use rather than for all 31 the service publishes. Adding an
#: endpoint means adding it here — a deliberate line in a reviewed diff.
#:
#: Keyed on ``operationId`` rather than on the path, because that is the name the
#: generated module takes and the wrapper imports. An id the spec no longer declares
#: fails generation rather than silently producing a client missing an endpoint we call.
_OPERATIONS: frozenset[str] = frozenset(
    {
        "getAcademicStandardByCaseIdentifierUUID",
        "searchAcademicStandards",
        "listLearningComponentsByAcademicStandard",
    }
)

#: The OpenAPI operation keys a path item may carry.
_HTTP_METHODS: frozenset[str] = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)

#: Never part of the committed tree, so never part of the comparison.
_IGNORE_NAMES = frozenset({".DS_Store", "__pycache__"})

#: Hand-written enum in ``kg_taxonomy`` -> the OpenAPI schema whose values it mirrors.
_TAXONOMY_SCHEMAS: tuple[tuple[str, str], ...] = (
    ("AcademicSubject", "AcademicSubjectENUM"),
    ("GradeLevel", "GradeLevelENUM"),
    ("Jurisdiction", "JurisdictionENUM"),
)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def _require_spec() -> None:
    if not _SPEC_PATH.is_file():
        raise SystemExit(f"Missing vendored spec {_SPEC_PATH}. Run `make fetch-kg-openapi` first.")


def _generator_installed() -> bool:
    return importlib.util.find_spec("openapi_python_client") is not None


def _require_generator() -> None:
    if not _generator_installed():
        raise SystemExit(
            "openapi-python-client is not installed. From sdks/python/: pip install -e '.[dev]'"
        )


# ---------------------------------------------------------------------------
# Filtering the spec to the operations we call
# ---------------------------------------------------------------------------


def _collect_refs(node: Any, found: set[str]) -> None:
    """Every ``$ref`` string anywhere under ``node``."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                found.add(value)
            else:
                _collect_refs(value, found)
    elif isinstance(node, list):
        for value in node:
            _collect_refs(value, found)


def _component_target(ref: str) -> tuple[str, str] | None:
    """``("schemas", "AcademicStandard")`` for a local component ref, else ``None``."""
    prefix = "#/components/"
    if not ref.startswith(prefix):
        return None
    section, _, name = ref[len(prefix) :].partition("/")
    return (section, name) if section and name else None


def _referenced_components(roots: Any, components: dict[str, Any]) -> dict[str, set[str]]:
    """The components ``roots`` needs, transitively, as ``{section: {name, ...}}``.

    A fixed point rather than one pass: a schema the paths reach pulls in the schemas it
    references, and so on, so pruning cannot strip something reachable only indirectly.
    """
    pending: set[str] = set()
    _collect_refs(roots, pending)
    seen: set[str] = set()
    keep: dict[str, set[str]] = {}
    while pending:
        ref = pending.pop()
        if ref in seen:
            continue
        seen.add(ref)
        target = _component_target(ref)
        if target is None:
            continue
        section, name = target
        definition = components.get(section, {}).get(name)
        if definition is None:
            continue
        keep.setdefault(section, set()).add(name)
        _collect_refs(definition, pending)
    return keep


def filtered_spec(document: dict[str, Any], operation_ids: Collection[str]) -> dict[str, Any]:
    """``document`` reduced to ``operation_ids`` and everything they reference.

    The generator has no include/exclude option (0.29.1), so the subset is expressed by
    narrowing its input. That keeps the output generator-produced rather than hand-pruned,
    which is what lets ``--check`` keep comparing byte for byte.

    :raises SystemExit: an id no operation in the document declares — a wrapper importing
        it would fail at runtime, so it fails here instead.
    """
    wanted = set(operation_ids)
    paths: dict[str, Any] = {}
    for path, item in (document.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        kept = {
            method: operation
            for method, operation in item.items()
            if method in _HTTP_METHODS
            and isinstance(operation, dict)
            and operation.get("operationId") in wanted
        }
        if not kept:
            continue
        # Shared path-level keys (``parameters``, ``servers``) travel with the operations
        # they apply to; dropping them would change how the kept ones generate.
        shared = {key: value for key, value in item.items() if key not in _HTTP_METHODS}
        paths[path] = {**shared, **kept}
        wanted -= {operation["operationId"] for operation in kept.values()}

    if wanted:
        raise SystemExit(
            f"{_SPEC_PATH} declares no operation with id(s) {sorted(wanted)}. "
            "Either the published spec renamed them or _OPERATIONS is out of date."
        )

    trimmed = {key: value for key, value in document.items() if key != "components"}
    trimmed["paths"] = paths

    components = document.get("components") or {}
    keep = _referenced_components(paths, components)
    pruned: dict[str, Any] = {}
    for section, definitions in components.items():
        # Security schemes answer to the root ``security`` block rather than to a ``$ref``,
        # so they have no incoming reference to find and are kept whole.
        names = set(definitions) if section == "securitySchemes" else keep.get(section, set())
        surviving = {name: body for name, body in definitions.items() if name in names}
        if surviving:
            pruned[section] = surviving
    if pruned:
        trimmed["components"] = pruned
    return trimmed


def write_filtered_spec(destination: Path) -> None:
    """Write the filtered spec to ``destination`` for the generator to read.

    Key order is preserved on the way out. The generator emits a model's fields in the
    order the spec declares its properties, and an attrs class takes them positionally in
    that order, so sorting the mapping — which this dumper does unless told not to —
    would reorder generated constructors for no reason but the round trip.
    """
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    yaml.representer.sort_base_mapping_type_on_output = False
    document = yaml.load(_SPEC_PATH)
    with destination.open("w", encoding="utf-8") as handle:
        yaml.dump(filtered_spec(document, _OPERATIONS), handle)


def _run_generator(output_dir: Path) -> None:
    """Write a fresh client into ``output_dir``. Callers check the generator exists first.

    Reads a filtered copy of the vendored spec rather than the spec itself, so the tree is
    the transport for the operations in :data:`_OPERATIONS` alone. The filtered copy is a
    temporary: the vendored document stays whole, so ``make fetch-kg-openapi`` remains a
    plain download and an upstream change is still reviewable in its diff.
    """
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kg-spec-") as tmp:
        spec_path = Path(tmp) / "knowledge-graph.filtered.yaml"
        write_filtered_spec(spec_path)
        command = [
            sys.executable,
            "-m",
            "openapi_python_client",
            "generate",
            "--path",
            str(spec_path),
            "--config",
            str(_CONFIG_PATH),
            # No project scaffolding: the output is a package inside ours, not a distribution.
            "--meta",
            "none",
            "--output-path",
            str(output_dir),
            "--overwrite",
        ]
        try:
            subprocess.run(command, check=True, cwd=_SDK_ROOT)
        except subprocess.CalledProcessError as e:
            raise SystemExit(e.returncode) from e


def _tree_files(root: Path) -> set[Path]:
    """Every committed-file path under ``root``, relative to it."""
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not _IGNORE_NAMES.intersection(path.parts)
    }


def tree_differences(committed: Path, fresh: Path) -> list[str]:
    """Human-readable differences between the committed client and a fresh one."""
    committed_files, fresh_files = _tree_files(committed), _tree_files(fresh)
    differences = [f"ORPHAN   {path}" for path in sorted(committed_files - fresh_files)]
    differences += [f"MISSING  {path}" for path in sorted(fresh_files - committed_files)]
    differences += [
        f"STALE    {path}"
        for path in sorted(committed_files & fresh_files)
        if not filecmp.cmp(committed / path, fresh / path, shallow=False)
    ]
    return differences


# ---------------------------------------------------------------------------
# Taxonomy drift
# ---------------------------------------------------------------------------


def _load_taxonomy() -> ModuleType:
    """Load ``kg_taxonomy.py`` as a standalone module.

    Imported by path rather than through the package, so the check runs before the
    generated client it is checking exists — on a fresh checkout ``import
    learning_commons_evaluators`` would fail on the very tree this script writes.
    """
    spec = importlib.util.spec_from_file_location("kg_taxonomy", _TAXONOMY_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover — unreachable for a real file
        raise SystemExit(f"Cannot load the public taxonomy from {_TAXONOMY_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_spec_schemas() -> dict[str, Any]:
    # ruamel.yaml rather than the standard library: OpenAPI is YAML, and the generator
    # this script drives already pins it.
    from ruamel.yaml import YAML

    document = YAML(typ="safe").load(_SPEC_PATH)
    schemas = (document or {}).get("components", {}).get("schemas")
    if not isinstance(schemas, dict):
        raise SystemExit(f"{_SPEC_PATH} has no components.schemas section")
    return schemas


def openapi_enum_values(schemas: dict[str, Any], schema_name: str) -> set[str]:
    """The declared string members of one OpenAPI enum schema."""
    schema = schemas.get(schema_name)
    if not isinstance(schema, dict):
        raise SystemExit(f"OpenAPI schema {schema_name!r} not found in {_SPEC_PATH}")
    values = schema.get("enum")
    if not isinstance(values, list) or not values:
        raise SystemExit(f"OpenAPI schema {schema_name!r} has no enum list in {_SPEC_PATH}")
    return {str(value) for value in values}


def taxonomy_drift(sdk_values: set[str], spec_values: set[str]) -> tuple[list[str], list[str]]:
    """``(sdk_only, spec_only)``, both sorted."""
    return sorted(sdk_values - spec_values), sorted(spec_values - sdk_values)


def check_taxonomy() -> int:
    """Compare the hand-written enums to the spec. Returns an exit code."""
    schemas = _load_spec_schemas()
    taxonomy = _load_taxonomy()
    exit_code = 0
    for enum_name, schema_name in _TAXONOMY_SCHEMAS:
        sdk_values = {member.value for member in getattr(taxonomy, enum_name)}
        sdk_only, spec_only = taxonomy_drift(sdk_values, openapi_enum_values(schemas, schema_name))
        if spec_only:
            print(
                f"warning: OpenAPI {schema_name} has values {enum_name} does not: {spec_only}",
                file=sys.stderr,
            )
        if sdk_only:
            print(
                f"{enum_name} has values OpenAPI {schema_name} does not: {sdk_only}",
                file=sys.stderr,
            )
            exit_code = 1
    return exit_code


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_generate() -> int:
    _require_spec()
    # Before anything is touched: generating into the committed tree and only then
    # finding the generator missing would leave the package with no client at all and
    # `import learning_commons_evaluators` broken.
    _require_generator()

    # Staged beside the target rather than in /tmp, so publishing is two renames on one
    # filesystem rather than a cross-device copy. Each rename is atomic, so the committed
    # path is never a partially written tree; the only window is between them, and it
    # leaves the old tree under ``previous`` for the rollback below rather than losing it.
    staging = _GENERATED_DIR.with_name(f".{_GENERATED_DIR.name}.new")
    previous = _GENERATED_DIR.with_name(f".{_GENERATED_DIR.name}.old")
    for leftover in (staging, previous):
        shutil.rmtree(leftover, ignore_errors=True)

    _GENERATED_DIR.parent.mkdir(parents=True, exist_ok=True)
    try:
        _run_generator(staging)
        # Moved aside rather than deleted, so a failure below can put it back. Replaced
        # wholesale rather than merged, so an endpoint the spec dropped does not linger.
        had_previous = _GENERATED_DIR.exists()
        if had_previous:
            _GENERATED_DIR.rename(previous)
        try:
            staging.rename(_GENERATED_DIR)
        except OSError:
            if had_previous:
                previous.rename(_GENERATED_DIR)
            raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(previous, ignore_errors=True)

    print(f"Generated {_GENERATED_DIR.relative_to(_SDK_ROOT)}")
    return check_taxonomy()


def cmd_check() -> int:
    _require_spec()
    if not _GENERATED_DIR.is_dir():
        print(
            f"Generated client missing at {_GENERATED_DIR.relative_to(_SDK_ROOT)}. "
            "Run: make generate-kg-client",
            file=sys.stderr,
        )
        return 1
    # Never a silent pass: a missing generator is a broken dev install, not a check that
    # quietly does less than it claims.
    _require_generator()
    with tempfile.TemporaryDirectory(prefix="kg-client-") as tmp:
        fresh = Path(tmp) / "knowledge_graph"
        _run_generator(fresh)
        differences = tree_differences(_GENERATED_DIR, fresh)
        if differences:
            print("\n".join(differences))
            print("\nRun: make generate-kg-client", file=sys.stderr)
            return 1
    print("Knowledge Graph client is up to date.")
    return check_taxonomy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Regenerate into a temp directory and exit 1 if the committed client differs.",
    )
    args = parser.parse_args(argv)
    return cmd_check() if args.check else cmd_generate()


if __name__ == "__main__":
    sys.exit(main())
