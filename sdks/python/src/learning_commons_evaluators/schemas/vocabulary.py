"""Vocabulary evaluator schemas."""

from pydantic import BaseModel, Field

from learning_commons_evaluators.schemas.config import (
    EvaluationSettings,
    PromptSettings,
)


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


class VocabularyComplexityOutput(BaseModel):
    tier_2_words: str = Field(description="List of Tier 2 words")
    tier_3_words: str = Field(description="List of Tier 3 words")
    archaic_words: str = Field(description="List of Archaic words")
    other_complex_words: str = Field(description="List of Other Complex words")
    complexity_score: str = Field(
        description="the complexity of the text, one of: slightly complex, moderately complex, very complex, or exceedingly complex"
    )
    reasoning: str = Field(description="your reasoning for your answer")


def normalize_complexity_output(output: dict) -> dict:
    """Mirror ``evals/vocabulary_evaluator.ipynb`` ``normalize_complexity_output``.

    Maps integer ``answer`` (1–4, including string digits) from the grades 5–12
    path to ``complexity_score`` using the same labels as the notebook. When
    ``answer`` is absent, ``complexity_score`` is left unchanged.

    Missing ``tier_*`` / ``archaic_words`` / ``other_complex_words`` keys are
    filled with ``\"\"`` so minimal JSON still validates as ``VocabularyComplexityOutput``.
    """
    result = dict(output)
    for key in ("tier_2_words", "tier_3_words", "archaic_words", "other_complex_words"):
        if key not in result or result[key] is None:
            result[key] = ""
    mapping = {
        1: "Slightly Complex",
        2: "Moderately Complex",
        3: "Very Complex",
        4: "Exceedingly Complex",
    }
    if "answer" in result:
        value = result["answer"]
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        result["complexity_score"] = mapping.get(value, str(value))
    return result
