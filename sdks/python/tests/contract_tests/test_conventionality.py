"""Contract test: ConventionalityEvaluator matches the notebook.

This test verifies two things for each contract case:
  1. The SDK sends the same LLM request as the notebook (same fully-formatted
     system prompt, user prompt, model, and temperature).
  2. Given the same LLM response, the SDK produces the same result as the
     notebook.

HOW TO ADD A NEW CASE
---------------------
1. Add a ``[cases.<name>]`` entry to
   ``sdks/settings/conventionality/contracts.toml``.
2. Add a loader function to ``contract_tests/conventionality.py``.
3. Add a test function here following the pattern below.

HOW TO REFRESH CONTRACT DATA
-----------------------------
Run the notebook ``evals/Final ship - Conventionality Experimental Evaluator.ipynb``
from the **repository root** with a valid ``GOOGLE_API_KEY``. The notebook loads
prompts from the evaluator settings TOML (same as the SDK) and prints a TOML block.
Paste it into ``sdks/settings/conventionality/contracts.toml`` (the canonical
copy), then run ``make sync-settings`` from ``sdks/python/`` to update the bundled
copy.
"""

from learning_commons_evaluators import (
    ConventionalityEvaluationInput,
    ConventionalityEvaluator,
    create_config_no_telemetry,
)
from learning_commons_evaluators.schemas.metadata import Status

from .conventionality import (
    conventionality_notebook_to_sdk_result,
    load_conventionality_turnip_case,
)
from .harness import ContractTestHarness


class TestConventionalityContract:
    def test_turnip_grade4(self) -> None:
        """Turnip classroom narrative, grade 4.

        Verifies:
        - The fully-formatted system and user prompts match the notebook.
        - The model and temperature match the notebook.
        - Given the notebook's LLM response, the SDK returns the same
          answer and explanation as the notebook.
        """
        case = load_conventionality_turnip_case()

        config = create_config_no_telemetry()
        evaluator = ConventionalityEvaluator(config)
        inp = ConventionalityEvaluationInput(
            text=case.input["text"],
            grade=case.input["grade"],
        )

        with ContractTestHarness(case) as harness:
            result = evaluator.evaluate(inp)

        # --- Prompt fidelity ---
        # Asserts that the SDK sent the same fully-formatted request as the
        # notebook (model, temperature, and both message contents).
        harness.assert_prompt_step("main")

        # --- Result fidelity ---
        # Asserts the SDK maps the LLM response to the same answer and
        # explanation as the notebook.  Metadata (timing, evaluation_id, etc.)
        # is intentionally excluded from this comparison.
        expected = conventionality_notebook_to_sdk_result(case)
        assert result.metadata.status == Status.succeeded
        assert result.answer.score == expected.answer.score, (
            f"answer.score: SDK={result.answer.score!r}, notebook={expected.answer.score!r}"
        )
        assert result.answer.label == expected.answer.label, (
            f"answer.label: SDK={result.answer.label!r}, notebook={expected.answer.label!r}"
        )
        assert result.explanation.summary == expected.explanation.summary, (
            "explanation.summary (reasoning) differs between SDK and notebook"
        )
        assert result.explanation.details == expected.explanation.details, (
            "explanation.details differs between SDK and notebook"
        )
