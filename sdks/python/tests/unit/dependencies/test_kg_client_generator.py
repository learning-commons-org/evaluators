"""The Knowledge Graph codegen scripts: spec validation, drift detection, tree comparison.

Everything here is the pure part of ``scripts/fetch_kg_openapi.py`` and
``scripts/generate_kg_client.py`` — nothing downloads, and nothing shells out to the
generator. That the committed client actually matches the vendored spec is
``make check-kg-client``'s job in CI, not a unit test's.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SDK_ROOT = Path(__file__).resolve().parents[3]


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SDK_ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fetch = _load_script("fetch_kg_openapi")
generate = _load_script("generate_kg_client")


# --- Fetching -----------------------------------------------------------------------


def test_an_openapi_3_document_is_accepted() -> None:
    fetch.validate_openapi_3('openapi: "3.0.3"\npaths: {}\n')
    fetch.validate_openapi_3("openapi: 3.1.0\npaths: {}\n")


@pytest.mark.parametrize(
    "document",
    [
        # A redirect to a login or error page still arrives as a 200; overwriting the
        # vendored spec with it would only surface as an inscrutable generator crash.
        "<!DOCTYPE html><title>Sign in</title>",
        "swagger: '2.0'\npaths: {}\n",
        "",
    ],
)
def test_anything_that_is_not_openapi_3_is_refused(document: str) -> None:
    with pytest.raises(SystemExit, match="not OpenAPI 3"):
        fetch.validate_openapi_3(document)


# --- Taxonomy drift -----------------------------------------------------------------


def test_drift_separates_sdk_only_from_spec_only() -> None:
    sdk_only, spec_only = generate.taxonomy_drift({"Texas", "Atlantis"}, {"Texas", "Ohio"})
    assert sdk_only == ["Atlantis"]
    assert spec_only == ["Ohio"]


def test_enum_values_are_read_from_the_spec_schemas() -> None:
    schemas = {"JurisdictionENUM": {"type": "string", "enum": ["Texas", "Ohio"]}}
    assert generate.openapi_enum_values(schemas, "JurisdictionENUM") == {"Texas", "Ohio"}


@pytest.mark.parametrize(
    "schemas",
    [
        {},
        {"JurisdictionENUM": {"type": "string"}},
        {"JurisdictionENUM": {"type": "string", "enum": []}},
    ],
)
def test_a_missing_or_empty_enum_fails_rather_than_passing_vacuously(
    schemas: dict[str, object],
) -> None:
    # An empty set would make every SDK value look like drift-free agreement.
    with pytest.raises(SystemExit):
        generate.openapi_enum_values(schemas, "JurisdictionENUM")


def test_the_committed_taxonomy_matches_the_vendored_spec() -> None:
    """The check `make check-kg-client` runs, as a test, so drift fails the suite too.

    Values the spec has and we do not are a warning there and are tolerated here: the
    mapping layer drops an unknown value rather than failing the standard.
    """
    assert generate.check_taxonomy() == 0


# --- Tree comparison ----------------------------------------------------------------


def _tree(root: Path, files: dict[str, str]) -> Path:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def test_identical_trees_have_no_differences(tmp_path: Path) -> None:
    files = {"client.py": "a\n", "models/error.py": "b\n"}
    left = _tree(tmp_path / "left", files)
    right = _tree(tmp_path / "right", files)
    assert generate.tree_differences(left, right) == []


def test_a_changed_file_reads_as_stale(tmp_path: Path) -> None:
    left = _tree(tmp_path / "left", {"client.py": "old\n"})
    right = _tree(tmp_path / "right", {"client.py": "new\n"})
    assert generate.tree_differences(left, right) == ["STALE    client.py"]


def test_an_endpoint_the_spec_dropped_reads_as_an_orphan(tmp_path: Path) -> None:
    left = _tree(tmp_path / "left", {"client.py": "a\n", "api/gone.py": "x\n"})
    right = _tree(tmp_path / "right", {"client.py": "a\n"})
    assert generate.tree_differences(left, right) == [f"ORPHAN   {Path('api/gone.py')}"]


def test_an_endpoint_the_spec_added_reads_as_missing(tmp_path: Path) -> None:
    left = _tree(tmp_path / "left", {"client.py": "a\n"})
    right = _tree(tmp_path / "right", {"client.py": "a\n", "api/new.py": "x\n"})
    assert generate.tree_differences(left, right) == [f"MISSING  {Path('api/new.py')}"]


def test_build_noise_is_not_a_difference(tmp_path: Path) -> None:
    # __pycache__ and .DS_Store are never committed, so a local one must not fail CI.
    left = _tree(
        tmp_path / "left",
        {"client.py": "a\n", "__pycache__/client.pyc": "junk", ".DS_Store": "junk"},
    )
    right = _tree(tmp_path / "right", {"client.py": "a\n"})
    assert generate.tree_differences(left, right) == []


# --- Filtering the spec to the operations we call -----------------------------------


def _document() -> dict:
    """A miniature spec: two operations, one of which we keep, and a ref chain."""
    return {
        "openapi": "3.1.0",
        "paths": {
            "/kept": {
                "parameters": [{"$ref": "#/components/parameters/Shared"}],
                "get": {
                    "operationId": "keepMe",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Outer"}
                                }
                            }
                        }
                    },
                },
                "post": {"operationId": "dropMe", "responses": {}},
            },
            "/dropped": {"get": {"operationId": "alsoDropMe", "responses": {}}},
        },
        "components": {
            "schemas": {
                "Outer": {"properties": {"inner": {"$ref": "#/components/schemas/Inner"}}},
                "Inner": {"type": "string"},
                "Unrelated": {"type": "string"},
            },
            "parameters": {"Shared": {"name": "q", "in": "query"}, "Unused": {"name": "z"}},
            "securitySchemes": {"apiKey": {"type": "apiKey", "name": "X-Key", "in": "header"}},
        },
    }


def test_only_the_declared_operations_survive() -> None:
    trimmed = generate.filtered_spec(_document(), {"keepMe"})
    assert list(trimmed["paths"]) == ["/kept"]
    assert set(trimmed["paths"]["/kept"]) == {"parameters", "get"}


def test_a_schema_reachable_only_through_another_is_kept() -> None:
    # Inner is referenced by Outer, never by a path: a single pass would drop it and the
    # generated client would not compile.
    trimmed = generate.filtered_spec(_document(), {"keepMe"})
    assert set(trimmed["components"]["schemas"]) == {"Outer", "Inner"}


def test_components_nothing_reaches_are_pruned() -> None:
    trimmed = generate.filtered_spec(_document(), {"keepMe"})
    assert "Unrelated" not in trimmed["components"]["schemas"]
    assert set(trimmed["components"]["parameters"]) == {"Shared"}


def test_security_schemes_are_kept_whole() -> None:
    # Answered by the root `security` block rather than by a $ref, so the closure cannot
    # find them and dropping them would generate a client that cannot authenticate.
    trimmed = generate.filtered_spec(_document(), {"keepMe"})
    assert set(trimmed["components"]["securitySchemes"]) == {"apiKey"}


def test_the_vendored_document_is_not_mutated() -> None:
    document = _document()
    generate.filtered_spec(document, {"keepMe"})
    assert set(document["paths"]) == {"/kept", "/dropped"}
    assert "Unrelated" in document["components"]["schemas"]


def test_an_operation_id_the_spec_does_not_declare_fails_loudly() -> None:
    # Otherwise the client would generate happily without an endpoint the wrapper imports,
    # and the failure would land at someone's runtime instead.
    with pytest.raises(SystemExit, match="ghostOperation"):
        generate.filtered_spec(_document(), {"keepMe", "ghostOperation"})


def test_the_allowlist_matches_the_vendored_spec() -> None:
    from ruamel.yaml import YAML

    document = YAML(typ="safe").load(generate._SPEC_PATH)
    trimmed = generate.filtered_spec(document, generate._OPERATIONS)
    kept = {
        operation["operationId"]
        for item in trimmed["paths"].values()
        for method, operation in item.items()
        if method in generate._HTTP_METHODS
    }
    assert kept == set(generate._OPERATIONS)
