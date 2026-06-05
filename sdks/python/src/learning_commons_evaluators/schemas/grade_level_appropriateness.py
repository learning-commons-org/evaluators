"""Grade Level Appropriateness schemas."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from learning_commons_evaluators.schemas.config import (
    EvaluationSettings,
    PromptSettings,
)
from learning_commons_evaluators.schemas.evaluator import (
    EvaluationAnswer,
    EvaluationResult,
)

GradeBandLiteral = Literal["K-1", "2-3", "4-5", "6-8", "9-10", "11-CCR"]


class GradeLevelAppropriatenessEvaluationSettings(EvaluationSettings):
    """Settings for a grade level appropriateness evaluation."""

    prompt_settings_step_gla_evaluation: PromptSettings


class GradeLevelAppropriatenessOutput(BaseModel):
    """Raw LLM output for grade level appropriateness evaluation."""

    reasoning: str = Field(
        description="Your reasoning for your answer in numbered bullet points for 4 steps with a 4th bullet point for synthesis."
    )
    grade: GradeBandLiteral = Field(description="The appropriate grade level for the text")
    alternative_grade: GradeBandLiteral = Field(
        description="An alternative grade level for the text"
    )
    scaffolding_needed: str = Field(
        description="Scaffolding needed for the text to be appropriate for the alternative grade"
    )


class GradeLevelAnswer(Enum):
    """Allowed grade level answers. Each member's value is an EvaluationAnswer."""

    K1 = EvaluationAnswer(score="K-1", label="Grades K-1")
    TWO_THREE = EvaluationAnswer(score="2-3", label="Grades 2-3")
    FOUR_FIVE = EvaluationAnswer(score="4-5", label="Grades 4-5")
    SIX_EIGHT = EvaluationAnswer(score="6-8", label="Grades 6-8")
    NINE_TEN = EvaluationAnswer(score="9-10", label="Grades 9-10")
    ELEVEN_CCR = EvaluationAnswer(score="11-CCR", label="Grades 11-CCR")

    @property
    def score(self) -> str:
        return self.value.score

    @property
    def label(self) -> str:
        return self.value.label

    @classmethod
    def from_score(cls, score: str) -> "GradeLevelAnswer":
        for member in cls:
            if member.value.score == score:
                return member
        raise ValueError(f"Unknown grade band: {score!r}")


class GradeLevelAppropriatenessResult(EvaluationResult):
    """Result of a grade level appropriateness evaluation: answer (enum), explanation, metadata."""

    answer: GradeLevelAnswer  # type: ignore[assignment]  # Enum members hold EvaluationAnswer values
