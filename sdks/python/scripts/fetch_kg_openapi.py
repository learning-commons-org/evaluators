#!/usr/bin/env python3
"""Download the Knowledge Graph OpenAPI spec into ``sdks/python/openapi/``.

Canonical source (OpenAPI 3.x)::

    https://docs.learningcommons.org/api-reference/knowledge-graph-api/openapi.yaml

Usage (from ``sdks/python/``)::

    python scripts/fetch_kg_openapi.py
    make fetch-kg-openapi

This is the one network step in the Knowledge Graph toolchain, and it is deliberately
**not** part of ``make verify``: CI regenerates the client from the vendored YAML, so a
published spec change is a reviewed commit rather than a silent CI-time difference. The
TypeScript SDK pulls its ``kg-api.d.ts`` from the same URL (``npm run generate:kg-types``),
so both SDKs track one document.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_SDK_ROOT = _SCRIPT_DIR.parent
_SPEC_PATH = _SDK_ROOT / "openapi" / "knowledge-graph.yaml"

KG_OPENAPI_URL = "https://docs.learningcommons.org/api-reference/knowledge-graph-api/openapi.yaml"

_OPENAPI_3_RE = re.compile(r"^openapi:\s*['\"]?3\.", re.MULTILINE)


def fetch_spec(url: str = KG_OPENAPI_URL) -> str:
    """Download the spec and return its UTF-8 text."""
    try:
        with urllib.request.urlopen(url) as response:  # noqa: S310 — fixed HTTPS URL
            body = response.read()
    except urllib.error.URLError as e:
        raise SystemExit(f"Failed to fetch Knowledge Graph OpenAPI spec from {url}: {e}") from e
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SystemExit(f"Knowledge Graph OpenAPI spec from {url} is not valid UTF-8: {e}") from e


def validate_openapi_3(text: str) -> None:
    """Fail if the document is not OpenAPI 3.x YAML.

    A redirect to an HTML error page still arrives as a 200, and overwriting the vendored
    spec with it would only surface as an inscrutable generator crash.
    """
    if not _OPENAPI_3_RE.search(text):
        raise SystemExit(
            "Downloaded document is not OpenAPI 3.x (expected a top-level `openapi: 3.` field)."
        )


def main() -> None:
    text = fetch_spec()
    validate_openapi_3(text)
    _SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SPEC_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {_SPEC_PATH.relative_to(_SDK_ROOT)} ({len(text)} bytes)")
    print("Next: make generate-kg-client")


if __name__ == "__main__":
    main()
