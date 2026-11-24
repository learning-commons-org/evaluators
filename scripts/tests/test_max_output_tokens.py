"""generation.max_output_tokens: an optional integer from 1 to 20,000, with no null spelling."""

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
        for cap in (1, 4096, 20000):
            with self.subTest(cap=cap):
                self.assertEqual(_errors(cap), [])
                self.assertEqual(_errors(cap, MULTI_STEP), [])

    def test_above_the_ceiling_is_refused(self) -> None:
        # One ceiling for every provider. A vendor client refuses a non-streaming call that
        # asks for more than about 21,000 tokens, so a larger cap would fail every call there.
        for cap in (20001, 128000):
            with self.subTest(cap=cap):
                errors = _errors(cap)
                self.assertEqual(len(errors), 1)
                self.assertIn("greater than the maximum of 20000", errors[0])

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

    def test_the_registry_declares_a_cap_on_exactly_these_steps(self) -> None:
        # Each value was sized for its step's model from that step's own runs, so adding or
        # changing one is a deliberate change here too.
        declared = {}
        for path in sorted((ROOT / "evals").glob("**/config.json")):
            config = json.loads(path.read_text())
            for step in config.get("steps", []):
                cap = (step.get("generation") or {}).get("max_output_tokens")
                if cap is not None:
                    declared[f"{path.parent.name}/{step.get('id')}"] = cap
        self.assertEqual(
            declared,
            {
                "sentence-structure/sentence_analysis_grades_3_4": 12000,
                "sentence-structure/sentence_analysis_grades_5_12": 12000,
                "sentence-structure/classify_complexity_grades_3_4": 2000,
                "sentence-structure/classify_complexity_grades_5_12": 2000,
                "vocabulary-complexity/background_knowledge": 2000,
                "vocabulary-complexity/vocab_complexity_grades_3_4": 12000,
                "vocabulary-complexity/vocab_complexity_other_grades": 4000,
            },
        )


if __name__ == "__main__":
    unittest.main()
