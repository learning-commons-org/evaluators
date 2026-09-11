"""Live integration tests: real provider calls, driven by ``evals/**/fixtures.json``.

Skipped unless ``RUN_INTEGRATION_TESTS`` is set and the provider key an evaluator needs is
in the environment. These are the same cases the TypeScript SDK runs live, so both SDKs are
held to the same expectations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from learning_commons_evaluators.contracts import Contract

REPO_ROOT = Path(__file__).resolve().parents[4]
EVALS_ROOT = REPO_ROOT / "evals"

KEY_ENV = {"google": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("RUN_INTEGRATION_TESTS", "").lower() in ("", "0", "false"):
        skip = pytest.mark.skip(reason="set RUN_INTEGRATION_TESTS=1 to run live provider tests")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)


def fixtures_for(contract: Contract) -> list[dict[str, Any]]:
    directory = EVALS_ROOT.joinpath(
        *(s.replace("_", "-") for s in contract.evaluator.id.split("."))
    )
    path = (
        contract.fixtures.path if contract.fixtures and contract.fixtures.path else "fixtures.json"
    )
    return json.loads((directory / path).read_text(encoding="utf-8"))


def keys_for(contract: Contract) -> dict[str, str]:
    """The config keys the contract's providers need, from the environment, or skip."""
    keys: dict[str, str] = {}
    for provider in contract.providers:
        value = os.environ.get(KEY_ENV[provider.value])
        if not value:
            pytest.skip(f"{KEY_ENV[provider.value]} is not set")
        keys[f"{provider.value}_api_key"] = value
    return keys
