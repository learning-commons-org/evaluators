"""Conventionality schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from learning_commons_evaluators.schemas.config import (
    EvaluationSettings,
    PromptSettings,
)


class ConventionalityEvaluationSettings(EvaluationSettings):
    """Settings for a conventionality evaluation."""

    prompt_settings_step_main: PromptSettings | None = None


class ConventionalityOutput(BaseModel):
    conventionality_features: list[str] = Field(
        description="List of the specific language features driving the complexity (e.g., idioms, metaphors, implied meaning) with direct quotes from the text."
    )
    grade_context: str = Field(
        description="How the conventionality demands compare to general expectations for the provided target grade."
    )
    instructional_insights: str = Field(
        description="Actionable pedagogical suggestions for scaffolding the unconventional language features in the classroom."
    )
    complexity_score: Literal[
        "slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"
    ] = Field(description="The conventionality complexity level of the text")
    reasoning: str = Field(description="A synthesis of why the text fits the chosen rubric level.")
