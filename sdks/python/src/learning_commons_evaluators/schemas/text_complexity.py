"""Common schemas for text complexity evaluators."""

from enum import Enum

from pydantic import Field

from .common_inputs import GradeInputField, TextInputField
from .evaluator import EvaluationAnswer, EvaluationInput, EvaluationResult


class TextComplexityEvaluationInput(EvaluationInput):
    """Input for a text complexity evaluation."""

    text: TextInputField = Field(description="The text to evaluate.")
    grade_level: GradeInputField = Field(description="Target grade level for the text.")


class TextComplexityAnswer(Enum):
    """
    Allowed text complexity answers. Each member's value is an EvaluationAnswer;
    use .label and .score for the human label and score string.
    """

    SLIGHTLY_COMPLEX = EvaluationAnswer(score="slightly_complex", label="Slightly complex")
    MODERATELY_COMPLEX = EvaluationAnswer(score="moderately_complex", label="Moderately complex")
    VERY_COMPLEX = EvaluationAnswer(score="very_complex", label="Very complex")
    EXCEEDINGLY_COMPLEX = EvaluationAnswer(score="exceedingly_complex", label="Exceedingly complex")

    @property
    def score(self) -> str:
        return self.value.score

    @property
    def label(self) -> str:
        return self.value.label

    @classmethod
    def from_score(cls, score: str) -> "TextComplexityAnswer":
        for member in cls:
            if member.value.score == score:
                return member
        raise ValueError(f"Unknown text complexity score: {score!r}")


class TextComplexityResult(EvaluationResult):
    """Result of a text complexity evaluation: answer (enum), explanation, metadata."""

    answer: TextComplexityAnswer  # type: ignore[assignment]  # Enum members hold EvaluationAnswer values
