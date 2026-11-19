"""generation.max_output_tokens: an optional positive integer, with no null spelling."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "evals/_schemas/config.schema.json").read_text())
#: A real single-step contract, so the cases run against a step the schema already accepts.
CONFIG = json.loads(
    (ROOT / "evals/text-complexity/ela-reading/grade-level-appropriateness/config.json").read_text()
)
#: A real multi-step contract, whose prose step uses generate_text.
MULTI_STEP = json.loads(
    (ROOT / "evals/text-complexity/ela-reading/vocabulary-complexity/config.json").read_text()
)

_ABSENT = object()


def _errors(cap: Any = _ABSENT, config: dict[str, Any] = CONFIG) -> list[str]:
    """Validation errors for the contract with every step's generation capped at ``cap``."""
    config = copy.deepcopy(config)
    if cap is not _ABSENT:
        for step in config["steps"]:
            if "generation" in step:
                step["generation"]["max_output_tokens"] = cap
    return [e.message for e in Draft202012Validator(SCHEMA).iter_errors(config)]


class MaxOutputTokensSchema(unittest.TestCase):
    def test_omitting_it_is_valid(self) -> None:
        self.assertEqual(_errors(), [])
        self.assertEqual(_errors(config=MULTI_STEP), [])

    def test_a_positive_integer_is_accepted(self) -> None:
        for cap in (1, 4096, 128000):
            with self.subTest(cap=cap):
                self.assertEqual(_errors(cap), [])
                self.assertEqual(_errors(cap, MULTI_STEP), [])

    def test_zero_and_negatives_are_refused(self) -> None:
        for cap in (0, -1, -4096):
            with self.subTest(cap=cap):
                errors = _errors(cap)
                self.assertEqual(len(errors), 1)
                self.assertIn("less than the minimum of 1", errors[0])

    def test_a_non_integer_is_refused(self) -> None:
        for cap in (1.5, "4096", True, [4096]):
            with self.subTest(cap=cap):
                errors = _errors(cap)
                self.assertEqual(len(errors), 1)
                self.assertIn("is not of type 'integer'", errors[0])

    def test_null_is_refused(self) -> None:
        # Absent is the only way to say "no cap"; a null would be a second spelling of it.
        errors = _errors(None)
        self.assertEqual(len(errors), 1)
        self.assertIn("None is not of type 'integer'", errors[0])

    def test_it_sits_alongside_a_reasoning_effort(self) -> None:
        config = copy.deepcopy(CONFIG)
        step = config["steps"][0]
        step["model"]["provider"] = "openai"
        step["generation"] = {"temperature": None, "reasoning_effort": "low", "max_output_tokens": 8000}
        self.assertEqual([e.message for e in Draft202012Validator(SCHEMA).iter_errors(config)], [])

    def test_no_registry_contract_declares_one_yet(self) -> None:
        # Values come with their own change; until then the SDKs pass nothing.
        for path in sorted((ROOT / "evals").glob("**/config.json")):
            config = json.loads(path.read_text())
            for step in config.get("steps", []):
                with self.subTest(path=str(path.relative_to(ROOT)), step=step.get("id")):
                    self.assertNotIn("max_output_tokens", step.get("generation") or {})


if __name__ == "__main__":
    unittest.main()
