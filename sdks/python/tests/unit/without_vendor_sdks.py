"""Every evaluator, in a process where no vendor SDK can be imported.

Run as its own process by ``test_without_vendor_sdks.py``, after hiding the SDKs, so it
holds for an install that has none: each evaluator refuses to build its own adapters, and
runs on an injected ``llm_provider`` without importing a vendor SDK on the way.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from learning_commons_evaluators import ConfigurationError
from learning_commons_evaluators.evaluators.academic_standards_alignment.mathematics.math_standards_alignment import (
    MathStandardsAlignmentEvaluator,
)
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.registry import EVALUATORS
from learning_commons_evaluators.providers import Provider, ProviderConfig
from tests.unit.conftest import FakeKnowledgeGraph, FakeProvider, sample_for
from tests.unit.telemetry.test_emission import evaluate_with, fixture_input

#: The modules the built-in adapters import.
VENDOR_MODULES = ("openai", "anthropic", "google.genai")


def is_vendor(name: str) -> bool:
    return any(name == module or name.startswith(f"{module}.") for module in VENDOR_MODULES)


def construct(evaluator: type[BaseEvaluator], **overrides: Any) -> BaseEvaluator:
    keys = {f"{p.value}_api_key": "test-key" for p in evaluator.metadata.default_providers}
    if evaluator is MathStandardsAlignmentEvaluator:
        overrides.setdefault("knowledge_graph", FakeKnowledgeGraph())
    else:
        keys.update({key: "test-key" for key in evaluator.metadata.required_credentials})
    return evaluator(**keys, telemetry=False, **overrides)


def main() -> None:
    for evaluator in EVALUATORS:
        try:
            construct(evaluator)
        except ConfigurationError as error:
            assert "not installed" in str(error), (evaluator.metadata.id, error)
        else:
            raise AssertionError(f"{evaluator.metadata.id} built without its vendor SDK")

        injected = FakeProvider(ProviderConfig(type=Provider.OPENAI, model="m"), sample_for)
        asyncio.run(
            evaluate_with(construct(evaluator, llm_provider=injected), fixture_input(evaluator))
        )
        assert injected.calls, evaluator.metadata.id

    imported = sorted(name for name in sys.modules if is_vendor(name))
    assert not imported, f"vendor SDKs imported: {imported}"


if __name__ == "__main__":
    main()
