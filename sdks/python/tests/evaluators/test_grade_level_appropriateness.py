"""Tests for GradeLevelAppropriatenessEvaluator and related helpers."""

from unittest.mock import patch

import pytest

from learning_commons_evaluators import (
    GradeLevelAppropriatenessEvaluationInput,
    GradeLevelAppropriatenessEvaluator,
)
from learning_commons_evaluators.schemas.errors import ConfigurationError
from learning_commons_evaluators.schemas.grade_level_appropriateness import (
    GradeLevelAppropriatenessOutput,
)
from learning_commons_evaluators.schemas.metadata import Status

# Long sample text (well above ``min_text_length`` from GLA settings TOML).
_SAMPLE_TEXT = (
    "Marco Polo was a Venetian merchant and explorer who traveled through Asia "
    "in the late 13th century. He spent nearly two decades at the court of "
    "Kublai Khan, the Mongol ruler of China, and described his experiences in "
    "a book that introduced Europeans to the Far East."
)


def _make_mock_output():
    return GradeLevelAppropriatenessOutput(
        reasoning=(
            "1. Word count: ~50 words; FK Grade Level: ~8. Grade band signal: 6-8.\n"
            "2. Qualitative: moderately complex structure, some unfamiliar vocabulary.\n"
            "3. Background knowledge: students in grade 6+ would have sufficient context.\n"
            "4. Synthesis: text is appropriate for grades 6-8 for independent reading."
        ),
        grade="6-8",
        alternative_grade="4-5",
        scaffolding_needed="Pre-reading vocabulary support and brief historical context.",
    )


class TestGradeLevelAppropriatenessEvaluator:
    def test_evaluate_returns_evaluation_result(self, config_with_google):
        evaluator = GradeLevelAppropriatenessEvaluator(config_with_google)
        inp = GradeLevelAppropriatenessEvaluationInput(text=_SAMPLE_TEXT)
        with patch.object(evaluator, "execute_prompt_chain_step", return_value=_make_mock_output()):
            result = evaluator.evaluate_sync(inp)
        assert result.answer.score == "6-8"
        assert result.answer.label == "Grades 6-8"
        assert result.explanation.summary is not None
        assert result.explanation.details["alternative_grade"] == "4-5"
        assert result.explanation.details["scaffolding_needed"] is not None
        assert result.metadata.status == Status.succeeded
        assert result.metadata.evaluator_metadata.id == "grade-level-appropriateness"

    def test_evaluate_with_explicit_settings(self, config_with_google):
        from learning_commons_evaluators.schemas.config import (
            LLMProvider,
            PromptSettings,
        )
        from learning_commons_evaluators.schemas.grade_level_appropriateness import (
            GradeLevelAppropriatenessEvaluationSettings,
        )

        evaluator = GradeLevelAppropriatenessEvaluator(config_with_google)
        settings = GradeLevelAppropriatenessEvaluationSettings(
            prompt_settings_step_gla_evaluation=PromptSettings(
                provider_type=LLMProvider.GOOGLE,
                model="gemini-2.0-flash",
                temperature=0.0,
            )
        )
        inp = GradeLevelAppropriatenessEvaluationInput(text=_SAMPLE_TEXT)
        with patch.object(evaluator, "execute_prompt_chain_step", return_value=_make_mock_output()):
            result = evaluator.evaluate_sync(inp, evaluation_settings=settings)
        assert result.metadata.status == Status.succeeded

    def test_metadata_and_default_settings(self, config_with_google):
        evaluator = GradeLevelAppropriatenessEvaluator(config_with_google)
        assert evaluator.metadata.id == "grade-level-appropriateness"
        assert evaluator.metadata.version == "0.1"
        assert evaluator.default_evaluation_settings is not None


class TestGradeLevelAppropriatenessEvaluationInputConfiguration:
    """Tests that GradeLevelAppropriatenessEvaluationInput fails loudly on bad configuration.

    These tests patch ``GradeLevelAppropriatenessEvaluationInput._input_settings`` directly
    because the ClassVar is bound at class-definition time.  Patching the
    module-level ``_INPUT_SETTINGS`` name would rebind the module variable but
    leave the class variable pointing at the original dict.
    """

    def test_missing_text_spec_raises_configuration_error(self, monkeypatch):
        """If 'text' is absent from _input_settings, ConfigurationError is raised immediately."""
        monkeypatch.setattr(GradeLevelAppropriatenessEvaluationInput, "_input_settings", {})
        with pytest.raises(ConfigurationError, match="'text'"):
            GradeLevelAppropriatenessEvaluationInput(text=_SAMPLE_TEXT)

    def test_wrong_text_spec_type_raises_configuration_error(self, monkeypatch):
        """If the 'text' spec has the wrong type, ConfigurationError names the type mismatch."""
        from learning_commons_evaluators.schemas.input_specs import GradeInputSpec

        monkeypatch.setattr(
            GradeLevelAppropriatenessEvaluationInput,
            "_input_settings",
            {"text": GradeInputSpec(name="text")},
        )
        with pytest.raises(ConfigurationError, match="TextInputSpec"):
            GradeLevelAppropriatenessEvaluationInput(text=_SAMPLE_TEXT)


class TestGradeLevelAppropriatenessOutput:
    def test_output_grade_literal(self):
        out = GradeLevelAppropriatenessOutput(
            reasoning="Test reasoning.",
            grade="4-5",
            alternative_grade="2-3",
            scaffolding_needed="Vocabulary preview.",
        )
        assert out.grade == "4-5"
        assert out.alternative_grade == "2-3"
        assert out.reasoning == "Test reasoning."

    def test_all_grade_bands_valid(self):
        from learning_commons_evaluators.schemas.grade_level_appropriateness import GradeLevelAnswer

        bands = ["K-1", "2-3", "4-5", "6-8", "9-10", "11-CCR"]
        for band in bands:
            answer = GradeLevelAnswer.from_score(band)
            assert answer.score == band
