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


def _run_generator(output_dir: Path) -> None:
    """Write a fresh client into ``output_dir``. Callers check the generator exists first."""
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "openapi_python_client",
        "generate",
        "--path",
        str(_SPEC_PATH),
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
