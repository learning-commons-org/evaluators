"""Vocabulary evaluator schemas."""

from pydantic import BaseModel, Field

from learning_commons_evaluators.schemas.config import (
    EvaluationSettings,
    PromptSettings,
)

# Grades supported by the vocabulary evaluator.
# Kept here for backwards-compatibility; the actual constraint is now enforced
# via allowed_grades in [[evaluator_metadata.inputs]] in the vocabulary evaluator settings.
VOCABULARY_SUPPORTED_GRADES: frozenset[int] = frozenset(range(3, 13))


class VocabularyEvaluationSettings(EvaluationSettings):
    """Settings for a vocabulary complexity evaluation.

    Requires three prompt step configurations:
    - ``prompt_settings_step_background_knowledge``: generates a student background knowledge
      assumption (used as context for the vocabulary complexity step).
    - ``prompt_settings_step_vocab_grades_3_4``: vocabulary complexity for grades 3–4.
    - ``prompt_settings_step_vocab_other_grades``: vocabulary complexity for grades 5–12.
    """

    prompt_settings_step_background_knowledge: PromptSettings
    prompt_settings_step_vocab_grades_3_4: PromptSettings
    prompt_settings_step_vocab_other_grades: PromptSettings


# Note: avoid class docstrings here — Pydantic adds them as a root ``description``
# key in ``model_json_schema()``, which changes ``JsonOutputParser`` format
# instructions and breaks vocabulary contract tests that snapshot prompts without
# that key (see ``contracts.toml``). Document behavior on fields / comments.


class VocabularyOutputGrades34(BaseModel):
    # LLM output for grades 3–4: rubric label + word breakdown; mirrors evals notebook Output.
    tier_2_words: str = Field(description="List of Tier 2 words")
    tier_3_words: str = Field(description="List of Tier 3 words")
    archaic_words: str = Field(description="List of Archaic words")
    other_complex_words: str = Field(description="List of Other Complex words")
    complexity_score: str = Field(
        description="the complexity of the text, one of: slightly complex, moderately complex, very complex, or exceedingly complex"
    )
    reasoning: str = Field(description="your reasoning for your answer")


class VocabularyOutputOtherGrades(BaseModel):
    # Same shape as grades 3–4; complexity_score is normalised to underscores before TextComplexityAnswer.
    tier_2_words: str = Field(description="List of Tier 2 words")
    tier_3_words: str = Field(description="List of Tier 3 words")
    archaic_words: str = Field(description="List of Archaic words")
    other_complex_words: str = Field(description="List of Other Complex words")
    complexity_score: str = Field(
        description="the complexity of the text, one of: slightly complex, moderately complex, very complex, or exceedingly complex"
    )
    reasoning: str = Field(description="your reasoning for your answer")
