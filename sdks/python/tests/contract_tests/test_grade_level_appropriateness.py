"""Contract test: GradeLevelAppropriatenessEvaluator matches the notebook.

This test verifies two things for each contract case:
  1. The SDK sends the same LLM request as the notebook (same fully-formatted
     system prompt, user prompt, model, and temperature).
  2. Given the same LLM response, the SDK produces the same result as the
     notebook.

HOW TO ADD A NEW CASE
---------------------
1. Add a ``[cases.<name>]`` entry to
   ``sdks/settings/grade-level-appropriateness/contracts.toml``.
2. Add a loader function to ``contract_tests/grade_level_appropriateness.py``.
3. Add a test function here following the pattern below.

HOW TO REFRESH CONTRACT DATA
-----------------------------
Run the notebook for the GLA evaluator from the **repository root** with a
valid ``GOOGLE_API_KEY``. The notebook loads prompts from the evaluator settings
TOML (same as the SDK) and prints a TOML block. Paste it into
``sdks/settings/grade-level-appropriateness/contracts.toml`` (the canonical
copy), then run ``make sync-settings`` from ``sdks/python/`` to update the
bundled copy.
"""

from learning_commons_evaluators import (
    GradeLevelAppropriatenessEvaluationInput,
    GradeLevelAppropriatenessEvaluator,
    create_config_no_telemetry,
)
from learning_commons_evaluators.schemas.metadata import Status

from .grade_level_appropriateness import (
    gla_notebook_to_sdk_result,
    load_gla_trees_case,
)
from .harness import ContractTestHarness


class TestGradeLevelAppropriatenessContract:
    def test_trees_passage(self) -> None:
        """Simple trees informational passage.

        Verifies:
        - The fully-formatted system and user prompts match the notebook.
        - The model and temperature match the notebook.
        - Given the notebook's LLM response, the SDK returns the same
          answer and explanation as the notebook.
        """
        case = load_gla_trees_case()

        config = create_config_no_telemetry()
        evaluator = GradeLevelAppropriatenessEvaluator(config)
        inp = GradeLevelAppropriatenessEvaluationInput(
            text=case.input["text"],
        )

        with ContractTestHarness(case) as harness:
            result = evaluator.evaluate_sync(inp)

        # --- Prompt fidelity ---
        harness.assert_prompt_step("main")

        # --- Result fidelity ---
        expected = gla_notebook_to_sdk_result(case)
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
