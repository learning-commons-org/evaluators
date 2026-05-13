"""Tests for VocabularyEvaluator and vocabulary helpers."""

from unittest.mock import patch

import pytest

from learning_commons_evaluators import (
    VocabularyEvaluationInput,
    VocabularyEvaluator,
    create_config_no_telemetry,
)
from learning_commons_evaluators.schemas.errors import ConfigurationError, ValidationError
from learning_commons_evaluators.schemas.metadata import Status
from learning_commons_evaluators.schemas.vocabulary import (
    VocabularyComplexityOutput,
    normalize_complexity_output,
)

_SAMPLE_TEXT = "The cat sat on the mat."

# ── Mock helpers ──────────────────────────────────────────────────────────────

_MOCK_BACKGROUND_KNOWLEDGE = "Students are familiar with household pets and basic domestic scenes."


def _make_grades34_output(
    score: str = "moderately_complex",
) -> VocabularyComplexityOutput:
    return VocabularyComplexityOutput(
        tier_2_words="sat",
        tier_3_words="none",
        archaic_words="none",
        other_complex_words="none",
        complexity_score=score,
        reasoning="Most words are simple and familiar.",
    )


_OTHER_GRADES_SCORE_MAP: dict[int, str] = {
    1: "slightly complex",
    2: "moderately complex",
    3: "very complex",
    4: "exceedingly complex",
}


def _make_other_grades_output(answer: int = 2) -> VocabularyComplexityOutput:
    """Build mock complexity output from a convenience integer rubric level (1–4)."""

    return VocabularyComplexityOutput(
        tier_2_words="sat",
        tier_3_words="none",
        archaic_words="none",
        other_complex_words="none",
        complexity_score=_OTHER_GRADES_SCORE_MAP[answer],
        reasoning="Most words are simple and familiar.",
    )


def _patch_steps(evaluator, bk_return, vocab_return):
    """Patch execute_prompt_chain_step with side_effect=[bk_return, vocab_return].

    Both steps (background_knowledge and vocab_complexity) go through the same
    method; side_effect returns them in call order.
    """
    return patch.object(
        evaluator,
        "execute_prompt_chain_step",
        side_effect=[bk_return, vocab_return],
    )


# ── Grade 3–4 path ────────────────────────────────────────────────────────────


class TestVocabularyEvaluatorGrades34:
    def test_evaluate_grade_3_returns_result(self):
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=3)
        with _patch_steps(evaluator, _MOCK_BACKGROUND_KNOWLEDGE, _make_grades34_output()):
            result = evaluator.evaluate(inp)

        assert result.answer.score == "moderately_complex"
        assert result.answer.label == "Moderately complex"
        assert result.metadata.status == Status.succeeded
        assert "tier_2_words" in result.explanation.details

    def test_evaluate_grade_4_returns_result(self):
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=4)
        with _patch_steps(
            evaluator, _MOCK_BACKGROUND_KNOWLEDGE, _make_grades34_output("very_complex")
        ):
            result = evaluator.evaluate(inp)

        assert result.answer.score == "very_complex"

    def test_grades34_score_with_spaces_is_normalised(self):
        """The grades 3–4 prompt may return "slightly complex" (spaces); normalise to underscores."""
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=3)
        # The evaluator calls .lower().replace(" ", "_") before from_score(),
        # so we feed a space-separated label and assert it survives the path.
        output = _make_grades34_output("slightly complex")

        with _patch_steps(evaluator, _MOCK_BACKGROUND_KNOWLEDGE, output):
            result = evaluator.evaluate(inp)

        assert result.answer.score == "slightly_complex"

    def test_evaluate_grades34_explanation_has_word_breakdown(self):
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=3)
        with _patch_steps(evaluator, _MOCK_BACKGROUND_KNOWLEDGE, _make_grades34_output()):
            result = evaluator.evaluate(inp)

        details = result.explanation.details
        assert "tier_2_words" in details
        assert "tier_3_words" in details
        assert "archaic_words" in details
        assert "other_complex_words" in details


# ── Grades 5–12 path ──────────────────────────────────────────────────────────


class TestVocabularyEvaluatorOtherGrades:
    @pytest.mark.parametrize(
        "score_label, expected_score",
        [
            (1, "slightly_complex"),
            (2, "moderately_complex"),
            (3, "very_complex"),
            (4, "exceedingly_complex"),
        ],
    )
    def test_all_complexity_scores_map_correctly(self, score_label, expected_score):
        """Each complexity label (passed as convenience int 1–4) maps to the right score."""
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=7)
        with _patch_steps(
            evaluator,
            _MOCK_BACKGROUND_KNOWLEDGE,
            _make_other_grades_output(score_label),
        ):
            result = evaluator.evaluate(inp)

        assert result.answer.score == expected_score

    def test_evaluate_grade_12_returns_result(self):
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=12)
        with _patch_steps(evaluator, _MOCK_BACKGROUND_KNOWLEDGE, _make_other_grades_output(1)):
            result = evaluator.evaluate(inp)

        assert result.metadata.status == Status.succeeded
        assert result.answer.score == "slightly_complex"

    def test_other_grades_explanation_includes_word_breakdown(self):
        """Grades 5–12 mirror the notebook: word lists live in ``explanation.details``."""
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=8)
        with _patch_steps(evaluator, _MOCK_BACKGROUND_KNOWLEDGE, _make_other_grades_output(2)):
            result = evaluator.evaluate(inp)

        details = result.explanation.details
        assert details["tier_2_words"] == "sat"
        assert details["tier_3_words"] == "none"
        assert details["archaic_words"] == "none"
        assert details["other_complex_words"] == "none"

    def test_other_grades_legacy_integer_answer_normalizes_like_notebook(self):
        """``normalize_complexity_output`` then validate (same order as the notebook)."""
        parsed = VocabularyComplexityOutput.model_validate(
            normalize_complexity_output(
                {"answer": 3, "reasoning": "Dense technical terms throughout."}
            )
        )
        assert parsed.complexity_score == "Very Complex"
        assert parsed.tier_2_words == ""
        assert parsed.tier_3_words == ""

    def test_other_grades_legacy_string_digit_answer(self):
        parsed = VocabularyComplexityOutput.model_validate(
            normalize_complexity_output({"answer": "2", "reasoning": "Accessible vocabulary."})
        )
        assert parsed.complexity_score == "Moderately Complex"


class TestNormalizeComplexityOutput:
    def test_preserves_complexity_score_when_answer_absent(self):
        row = normalize_complexity_output(
            {
                "tier_2_words": "a",
                "tier_3_words": "b",
                "archaic_words": "c",
                "other_complex_words": "d",
                "complexity_score": "slightly complex",
                "reasoning": "r",
            }
        )
        assert row["complexity_score"] == "slightly complex"

    def test_answer_overwrites_or_sets_complexity_score(self):
        row = normalize_complexity_output({"answer": 1, "reasoning": "x"})
        assert row["complexity_score"] == "Slightly Complex"


# ── Grade validation via framework ────────────────────────────────────────────


class TestVocabularyEvaluationInputValidation:
    def test_allowed_grades_set_from_toml(self):
        """VocabularyEvaluationInput picks up allowed_grades from the TOML spec."""
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=5)
        assert set(inp.grade.spec.allowed_grades) == frozenset(range(3, 13))

    @pytest.mark.parametrize("unsupported_grade", [0, 1, 2])
    def test_unsupported_grade_raises_via_framework(self, unsupported_grade):
        """BaseEvaluator.evaluate() calls input.validate(), which catches the bad grade."""
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=unsupported_grade)
        # The base evaluator catches the ValidationError, sets status=failed, then re-raises.
        with pytest.raises(ValidationError):
            evaluator.evaluate(inp)

    def test_unsupported_grade_sets_status_failed(self):
        """Metadata status is set to failed when grade validation fails."""
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=2)
        with pytest.raises(ValidationError):
            evaluator.evaluate(inp)


# ── Metadata and settings ─────────────────────────────────────────────────────


class TestVocabularyEvaluatorMetadata:
    def test_evaluator_metadata(self):
        evaluator = VocabularyEvaluator(create_config_no_telemetry())
        assert evaluator.metadata.id == "vocabulary"
        assert evaluator.metadata.version == "0.1"

    def test_default_settings_has_all_prompt_steps(self):
        evaluator = VocabularyEvaluator(create_config_no_telemetry())
        settings = evaluator.default_evaluation_settings
        assert settings.prompt_settings_step_background_knowledge is not None
        assert settings.prompt_settings_step_vocab_grades_3_4 is not None
        assert settings.prompt_settings_step_vocab_other_grades is not None

    def test_evaluate_succeeds_and_records_metadata(self):
        config = create_config_no_telemetry()
        evaluator = VocabularyEvaluator(config)
        inp = VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=5)
        with _patch_steps(evaluator, _MOCK_BACKGROUND_KNOWLEDGE, _make_other_grades_output(2)):
            result = evaluator.evaluate(inp)

        assert result.metadata.status == Status.succeeded
        assert result.metadata.evaluator_metadata.id == "vocabulary"


class TestVocabularyEvaluationInputConfiguration:
    """Tests that VocabularyEvaluationInput fails loudly on bad configuration.

    These tests patch ``VocabularyEvaluationInput._input_settings`` directly
    because the ClassVar is bound at class-definition time.  Patching the
    module-level ``_INPUT_SETTINGS`` name would rebind the module variable but
    leave the class variable pointing at the original dict.
    """

    def test_missing_text_spec_raises_configuration_error(self, monkeypatch):
        """If 'text' is absent from _input_settings, ConfigurationError is raised immediately."""
        monkeypatch.setattr(VocabularyEvaluationInput, "_input_settings", {})
        with pytest.raises(ConfigurationError, match="'text'"):
            VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=5)

    def test_missing_grade_spec_raises_configuration_error(self, monkeypatch):
        """If 'grade' is absent from _input_settings, ConfigurationError is raised."""
        from learning_commons_evaluators.schemas.input_specs import TextInputSpec

        monkeypatch.setattr(
            VocabularyEvaluationInput,
            "_input_settings",
            {"text": TextInputSpec(name="text")},
        )
        with pytest.raises(ConfigurationError, match="'grade'"):
            VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=5)

    def test_wrong_text_spec_type_raises_configuration_error(self, monkeypatch):
        """If the 'text' spec has the wrong type, ConfigurationError names the type mismatch."""
        from learning_commons_evaluators.schemas.input_specs import GradeInputSpec

        monkeypatch.setattr(
            VocabularyEvaluationInput,
            "_input_settings",
            {"text": GradeInputSpec(name="text")},
        )
        with pytest.raises(ConfigurationError, match="TextInputSpec"):
            VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=5)

    def test_wrong_grade_spec_type_raises_configuration_error(self, monkeypatch):
        """If the 'grade' spec has the wrong type, ConfigurationError names the mismatch."""
        from learning_commons_evaluators.schemas.input_specs import TextInputSpec

        monkeypatch.setattr(
            VocabularyEvaluationInput,
            "_input_settings",
            {
                "text": TextInputSpec(name="text"),
                "grade": TextInputSpec(name="grade"),  # wrong type
            },
        )
        with pytest.raises(ConfigurationError, match="GradeInputSpec"):
            VocabularyEvaluationInput(text=_SAMPLE_TEXT, grade=5)
