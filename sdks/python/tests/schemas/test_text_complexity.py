"""Unit tests for schemas/text_complexity.py.

Covers: TextComplexityAnswer (all members, from_score, score/label properties),
TextComplexityEvaluationInput, TextComplexityResult.
"""

import pytest

from learning_commons_evaluators.schemas.common_inputs import (
    GradeInputField,
    TextInputField,
)
from learning_commons_evaluators.schemas.evaluator import EvaluationExplanation
from learning_commons_evaluators.schemas.input_specs import (
    GradeInputSpec,
    TextInputSpec,
)
from learning_commons_evaluators.schemas.metadata import Status
from learning_commons_evaluators.schemas.text_complexity import (
    TextComplexityAnswer,
    TextComplexityEvaluationInput,
    TextComplexityResult,
)

_ANSWER_CASES = [
    ("slightly_complex", "Slightly complex", TextComplexityAnswer.SLIGHTLY_COMPLEX),
    (
        "moderately_complex",
        "Moderately complex",
        TextComplexityAnswer.MODERATELY_COMPLEX,
    ),
    ("very_complex", "Very complex", TextComplexityAnswer.VERY_COMPLEX),
    (
        "exceedingly_complex",
        "Exceedingly complex",
        TextComplexityAnswer.EXCEEDINGLY_COMPLEX,
    ),
]


class TestTextComplexityAnswer:
    @pytest.mark.parametrize("score,label,member", _ANSWER_CASES)
    def test_score_and_label(self, score, label, member):
        assert member.score == score
        assert member.label == label

    @pytest.mark.parametrize("score,_label,member", _ANSWER_CASES)
    def test_from_score_round_trip(self, score, _label, member):
        assert TextComplexityAnswer.from_score(score) is member

    def test_from_score_raises_on_unknown_score(self):
        with pytest.raises(ValueError, match="Unknown text complexity score"):
            TextComplexityAnswer.from_score("not_a_real_score")

    def test_from_score_is_case_sensitive(self):
        """Scores are lowercase; the wrong case must not silently succeed."""
        with pytest.raises(ValueError):
            TextComplexityAnswer.from_score("Slightly_Complex")


class TestTextComplexityEvaluationInput:
    def test_input_values_returns_primitives(self):
        inp = TextComplexityEvaluationInput(
            text=TextInputField(spec=TextInputSpec(name="text"), value="Some text."),
            grade_level=GradeInputField(spec=GradeInputSpec(name="grade_level"), value=7),
        )
        values = inp.input_values()
        assert values["text"] == "Some text."
        assert values["grade_level"] == 7


class TestTextComplexityResult:
    def test_answer_and_metadata_status(self, evaluation_metadata):
        result = TextComplexityResult(
            answer=TextComplexityAnswer.VERY_COMPLEX,
            explanation=EvaluationExplanation(
                summary="Abstract language throughout.",
                details={"conventionality_features": ["metaphor"]},
            ),
            metadata=evaluation_metadata,
        )
        assert result.answer is TextComplexityAnswer.VERY_COMPLEX
        assert result.answer.score == "very_complex"
        assert result.metadata.status == Status.processing
