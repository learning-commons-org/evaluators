"""Tests for ConventionalityEvaluator and conventionality helpers."""

from unittest.mock import patch

import pytest

from learning_commons_evaluators import ConventionalityEvaluationInput, ConventionalityEvaluator
from learning_commons_evaluators.schemas.conventionality import ConventionalityOutput
from learning_commons_evaluators.schemas.errors import ConfigurationError
from learning_commons_evaluators.schemas.metadata import Status

# Long sample text (well above ``min_text_length`` from conventionality settings TOML).
_SAMPLE_TEXT = (
    "Marco Polo was a Venetian merchant and explorer who traveled through Asia "
    "in the late 13th century. He spent nearly two decades at the court of "
    "Kublai Khan, the Mongol ruler of China, and described his experiences in "
    "a book that introduced Europeans to the Far East."
)


def _make_mock_output():
    return ConventionalityOutput(
        conventionality_features=["idioms"],
        grade_context="Grade-appropriate.",
        instructional_insights="Consider scaffolding.",
        complexity_score="moderately_complex",
        reasoning="The text uses some conventional language.",
    )


class TestConventionalityEvaluator:
    def test_evaluate_returns_evaluation_result(self, config_with_google):
        evaluator = ConventionalityEvaluator(config_with_google)
        inp = ConventionalityEvaluationInput(text=_SAMPLE_TEXT, grade=5)
        with patch.object(evaluator, "execute_prompt_chain_step", return_value=_make_mock_output()):
            result = evaluator.evaluate_sync(inp)
        assert result.answer.score == "moderately_complex"
        assert result.answer.label == "Moderately complex"
        assert result.explanation.summary is not None
        assert result.metadata.status == Status.succeeded
        assert result.metadata.evaluator_metadata.id == "conventionality"

    def test_evaluate_with_explicit_settings(self, config_with_google):
        from learning_commons_evaluators.schemas.config import (
            LLMProvider,
            PromptSettings,
        )
        from learning_commons_evaluators.schemas.conventionality import (
            ConventionalityEvaluationSettings,
        )

        evaluator = ConventionalityEvaluator(config_with_google)
        settings = ConventionalityEvaluationSettings(
            prompt_settings_step_conventionality_evaluation=PromptSettings(
                provider_type=LLMProvider.GOOGLE,
                model="gemini-2.0-flash",
                temperature=0.0,
            )
        )
        inp = ConventionalityEvaluationInput(text=_SAMPLE_TEXT, grade=3)
        with patch.object(evaluator, "execute_prompt_chain_step", return_value=_make_mock_output()):
            result = evaluator.evaluate_sync(inp, evaluation_settings=settings)
        assert result.metadata.status == Status.succeeded

    def test_metadata_and_default_settings(self, config_with_google):
        evaluator = ConventionalityEvaluator(config_with_google)
        assert evaluator.metadata.id == "conventionality"
        assert evaluator.metadata.version == "0.1"
        assert evaluator.default_evaluation_settings is not None


class TestConventionalityEvaluationInputConfiguration:
    """Tests that ConventionalityEvaluationInput fails loudly on bad configuration.

    These tests patch ``ConventionalityEvaluationInput._input_settings`` directly
    because the ClassVar is bound at class-definition time.  Patching the
    module-level ``_INPUT_SETTINGS`` name would rebind the module variable but
    leave the class variable pointing at the original dict.
    """

    def test_missing_text_spec_raises_configuration_error(self, monkeypatch):
        """If 'text' is absent from _input_settings, ConfigurationError is raised immediately."""
        monkeypatch.setattr(ConventionalityEvaluationInput, "_input_settings", {})
        with pytest.raises(ConfigurationError, match="'text'"):
            ConventionalityEvaluationInput(text=_SAMPLE_TEXT, grade=5)

    def test_missing_grade_spec_raises_configuration_error(self, monkeypatch):
        """If 'grade' is absent from _input_settings, ConfigurationError is raised immediately."""
        from learning_commons_evaluators.schemas.input_specs import TextInputSpec

        monkeypatch.setattr(
            ConventionalityEvaluationInput,
            "_input_settings",
            {"text": TextInputSpec(name="text")},
        )
        with pytest.raises(ConfigurationError, match="'grade'"):
            ConventionalityEvaluationInput(text=_SAMPLE_TEXT, grade=5)

    def test_wrong_text_spec_type_raises_configuration_error(self, monkeypatch):
        """If the 'text' spec has the wrong type, ConfigurationError names the type mismatch."""
        from learning_commons_evaluators.schemas.input_specs import GradeInputSpec

        monkeypatch.setattr(
            ConventionalityEvaluationInput,
            "_input_settings",
            {"text": GradeInputSpec(name="text")},
        )
        with pytest.raises(ConfigurationError, match="TextInputSpec"):
            ConventionalityEvaluationInput(text=_SAMPLE_TEXT, grade=5)

    def test_wrong_grade_spec_type_raises_configuration_error(self, monkeypatch):
        """If the 'grade' spec has the wrong type, ConfigurationError names the type mismatch."""
        from learning_commons_evaluators.schemas.input_specs import TextInputSpec

        monkeypatch.setattr(
            ConventionalityEvaluationInput,
            "_input_settings",
            {
                "text": TextInputSpec(name="text"),
                "grade": TextInputSpec(name="grade"),  # wrong type
            },
        )
        with pytest.raises(ConfigurationError, match="GradeInputSpec"):
            ConventionalityEvaluationInput(text=_SAMPLE_TEXT, grade=5)


class TestConventionalityOutput:
    def test_conventionality_output_literal_score(self):
        out = ConventionalityOutput(
            conventionality_features=[],
            grade_context="",
            instructional_insights="",
            complexity_score="slightly_complex",
            reasoning="Test.",
        )
        assert out.complexity_score == "slightly_complex"
        assert out.reasoning == "Test."
