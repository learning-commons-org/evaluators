"""Contract tests: VocabularyEvaluator matches the notebook.

Each test verifies two things for a known input:
  1. The SDK sends the same LLM requests as the notebook (fully-formatted
     system prompt, user prompt, model, and temperature — for both steps).
  2. Given the same LLM responses, the SDK produces the same result as the
     notebook.

The vocabulary evaluator makes two LLM calls per evaluation:
  - Step "background_knowledge": plain-text response (no system prompt).
  - Step "vocab_complexity":      JSON response (system + human prompt).

HOW TO ADD A NEW CASE
---------------------
1. Add a ``[cases.<name>]`` entry to
   ``settings/vocabulary/contracts.toml`` with both prompt steps.
2. Add a loader function to ``contract_tests/vocabulary.py``.
3. Add a test function here following the pattern below.

HOW TO REFRESH CONTRACT DATA
-----------------------------
Run the notebook ``evals/vocabulary_evaluator.ipynb`` with valid API keys.
The final cells output a TOML block; paste it into ``contracts.toml``
replacing the placeholder values.

IMPORTANT: ``system_prompt = ""`` for the background_knowledge step is the
correct value (the prompt has no system message), not a placeholder. Only
the ``user_prompt`` and ``llm_response`` fields need to be populated.
"""

from learning_commons_evaluators import (
    VocabularyEvaluationInput,
    VocabularyEvaluator,
    create_config_no_telemetry,
)
from learning_commons_evaluators.schemas.metadata import Status

from .harness import ContractTestHarness
from .vocabulary import (
    load_vocabulary_grade34_case,
    load_vocabulary_other_grades_case,
    vocabulary_grade34_notebook_to_sdk_result,
    vocabulary_other_grades_notebook_to_sdk_result,
)


class TestVocabularyContractGrades34:
    def test_marco_polo_grade3(self) -> None:
        """Marco Polo passage, grade 3 — grades 3–4 Gemini path.

        Verifies:
        - Both LLM requests (background_knowledge and vocab_complexity) match
          the fully-formatted prompts captured from the notebook.
        - Given the notebook's LLM responses, the SDK returns the same answer,
          reasoning, and word-breakdown details as the notebook.
        """
        case = load_vocabulary_grade34_case()

        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(
            text=case.input["text"],
            grade_level=case.input["grade_level"],
        )

        with ContractTestHarness(case) as harness:
            result = evaluator.evaluate(inp)

        # --- Prompt fidelity ---
        # Both steps are asserted: model, temperature, and formatted messages
        # must match what the notebook sent to the LLM.
        harness.assert_prompt_step("background_knowledge")
        harness.assert_prompt_step("vocab_complexity")

        # --- Result fidelity ---
        expected = vocabulary_grade34_notebook_to_sdk_result(case)
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
            "explanation.details (word breakdown) differs between SDK and notebook"
        )


class TestVocabularyContractOtherGrades:
    def test_hurricanes_grade7(self) -> None:
        """Hurricane formation passage, grade 7 — grades 5–12 GPT path.

        Verifies:
        - Both LLM requests match the notebook.
        - Given the notebook's LLM responses, the SDK maps the integer score
          to the correct TextComplexityAnswer and returns the same reasoning.
        """
        case = load_vocabulary_other_grades_case()

        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(
            text=case.input["text"],
            grade_level=case.input["grade_level"],
        )

        with ContractTestHarness(case) as harness:
            result = evaluator.evaluate(inp)

        # --- Prompt fidelity ---
        harness.assert_prompt_step("background_knowledge")
        harness.assert_prompt_step("vocab_complexity")

        # --- Result fidelity ---
        expected = vocabulary_other_grades_notebook_to_sdk_result(case)
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
