"""generation.reasoning_effort: each provider admits its own values, and notebooks must read it."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from checks.eval_notebook import reasoning_effort_problem  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "evals/_schemas/config.schema.json").read_text())
#: A real single-step contract, so the cases run against a step the schema already accepts.
CONFIG = json.loads(
    (ROOT / "evals/text-complexity/ela-reading/grade-level-appropriateness/config.json").read_text()
)

ACCEPTED = {
    "openai": ["none", "minimal", "low", "medium", "high", "xhigh", "max"],
    "anthropic": ["low", "medium", "high", "xhigh", "max"],
    "google": ["minimal", "low", "medium", "high"],
}
EVERY_VALUE = sorted({value for values in ACCEPTED.values() for value in values})


def _errors(provider: str, effort: str | None) -> list[str]:
    config = copy.deepcopy(CONFIG)
    step = config["steps"][0]
    step["model"]["provider"] = provider
    if effort is not None:
        step["generation"]["reasoning_effort"] = effort
    return [e.message for e in Draft202012Validator(SCHEMA).iter_errors(config)]


class ReasoningEffortSchema(unittest.TestCase):
    def test_the_base_contract_is_valid(self) -> None:
        self.assertEqual(_errors(CONFIG["steps"][0]["model"]["provider"], None), [])

    def test_each_provider_accepts_exactly_its_own_values(self) -> None:
        for provider, accepted in ACCEPTED.items():
            for value in EVERY_VALUE:
                with self.subTest(provider=provider, value=value):
                    errors = _errors(provider, value)
                    if value in accepted:
                        self.assertEqual(errors, [])
                    else:
                        self.assertEqual(len(errors), 1)
                        self.assertIn(f"'{value}' is not one of", errors[0])

    def test_omitting_it_is_valid_on_every_provider(self) -> None:
        for provider in ACCEPTED:
            with self.subTest(provider=provider):
                self.assertEqual(_errors(provider, None), [])

    def test_a_value_no_provider_defines_is_refused(self) -> None:
        for provider in ACCEPTED:
            with self.subTest(provider=provider):
                self.assertEqual(len(_errors(provider, "default")), 1)

    def test_null_is_not_a_second_spelling_of_omitted(self) -> None:
        config = copy.deepcopy(CONFIG)
        config["steps"][0]["generation"]["reasoning_effort"] = None
        self.assertNotEqual(list(Draft202012Validator(SCHEMA).iter_errors(config)), [])

    def test_the_lists_match_the_schema(self) -> None:
        declared = {
            provider: SCHEMA["$defs"]["ReasoningEffort"][provider]["enum"] for provider in ACCEPTED
        }
        self.assertEqual(declared, ACCEPTED)


class NotebookReadsReasoningEffort(unittest.TestCase):
    def _config(self, *generations: dict) -> dict:
        return {"steps": [{"id": f"step_{i}", "generation": g} for i, g in enumerate(generations)]}

    def test_no_declared_effort_needs_nothing(self) -> None:
        self.assertIsNone(reasoning_effort_problem(self._config({"temperature": 0}), "llm()"))

    def test_a_notebook_that_reads_it_passes(self) -> None:
        config = self._config({"temperature": None, "reasoning_effort": "none"})
        src = 'settings["reasoning_effort"] = generation["reasoning_effort"]'
        self.assertIsNone(reasoning_effort_problem(config, src))

    def test_a_notebook_that_ignores_it_names_the_steps(self) -> None:
        config = self._config(
            {"temperature": 0},
            {"temperature": None, "reasoning_effort": "low"},
            {"temperature": None, "reasoning_effort": "high"},
        )
        problem = reasoning_effort_problem(config, "ChatOpenAI(model=name)")
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertIn("step_1, step_2", problem)
        self.assertNotIn("step_0", problem)


if __name__ == "__main__":
    unittest.main()
