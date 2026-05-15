"""Vocabulary evaluator: evaluates text for vocabulary complexity relative to grade level."""

from __future__ import annotations

from typing import Any, ClassVar

import textstat  # type: ignore[import-untyped]
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field

from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.schemas.common_inputs import (
    GradeInputField,
    TextInputField,
)
from learning_commons_evaluators.schemas.config import PromptSettings
from learning_commons_evaluators.schemas.evaluator import (
    EvaluationExplanation,
    EvaluationInput,
)
from learning_commons_evaluators.schemas.metadata import (
    EvaluationMetadata,
    EvaluatorMetadata,
)
from learning_commons_evaluators.schemas.text_complexity import (
    TextComplexityAnswer,
    TextComplexityResult,
)
from learning_commons_evaluators.schemas.vocabulary import (
    VocabularyComplexityOutput,
    VocabularyEvaluationSettings,
    normalize_complexity_output,
)
from learning_commons_evaluators.settings._generated_vocabulary_settings import (
    CONFIG as _VOCABULARY_CONFIG,
)

_INPUT_SETTINGS = _VOCABULARY_CONFIG.evaluator_metadata.inputs

# Grades 3–4 use the Gemini-based rubric prompt; grades 5–12 use the GPT-based annotation guide prompt.
_GRADES_3_4 = frozenset({3, 4})


class VocabularyEvaluationInput(EvaluationInput):
    """Input for a vocabulary evaluation.

    Constraints (allowed grade levels) are sourced from
    ``[[evaluator_metadata.inputs]]`` in evaluator settings and applied
    automatically — callers supply raw values, not field objects.

    Example::

        inp = VocabularyEvaluationInput(text="The quick brown fox...", grade=5)
    """

    _input_settings: ClassVar[dict] = _INPUT_SETTINGS

    text: TextInputField = Field(description="The text to evaluate.")
    grade: GradeInputField = Field(description="The grade level of the text (3–12).")

    def __init__(self, *, text: str, grade: int, **kwargs):
        super().__init__(text=text, grade=grade, **kwargs)


class VocabularyEvaluator(
    BaseEvaluator[VocabularyEvaluationInput, TextComplexityResult, VocabularyEvaluationSettings]
):
    """Evaluates text for vocabulary complexity relative to the target grade level.

    The evaluation runs in two steps:
    1. **Background knowledge** – the model generates a short assumption about what
       students at the target grade already know about the text's topic.  This
       provides context that keeps the complexity rating from penalising familiar
       domain words.
    2. **Vocabulary complexity** – a grade-specific prompt + model produces JSON
       matching the notebook ``Output`` shape. Raw JSON is passed through
       :func:`~learning_commons_evaluators.schemas.vocabulary.normalize_complexity_output`
       (same behaviour as the notebook), then validated. Grades 3–4 use Gemini;
       grades 5–12 use GPT. Scores are normalised to :class:`TextComplexityAnswer`.

    Supported grades: 3–12.
    """

    metadata: EvaluatorMetadata = _VOCABULARY_CONFIG.evaluator_metadata
    default_evaluation_settings: VocabularyEvaluationSettings = (
        _VOCABULARY_CONFIG.evaluation_settings
    )

    async def evaluate_impl(
        self,
        input: VocabularyEvaluationInput,
        evaluation_settings: VocabularyEvaluationSettings,
        evaluation_metadata: EvaluationMetadata,
    ) -> TextComplexityResult:
        """Run the two-step vocabulary evaluation and return a TextComplexityResult.

        Grade validation is handled by the framework before this method is called:
        ``VocabularyEvaluationInput`` automatically constrains ``grade`` to the
        evaluator's ``allowed_grades`` from settings (3–12), so
        ``BaseEvaluator.evaluate`` / ``evaluate_sync`` raises before reaching here for unsupported grades.
        """
        ps_bk = evaluation_settings.prompt_settings_step_background_knowledge
        ps_34 = evaluation_settings.prompt_settings_step_vocab_grades_3_4
        ps_og = evaluation_settings.prompt_settings_step_vocab_other_grades

        grade = input.grade.value
        text = input.text.value
        fk_score = round(textstat.flesch_kincaid_grade(text), 2)
        prompts = _VOCABULARY_CONFIG.prompts

        # ── Step 1: background knowledge ──────────────────────────────────────
        bk_template = ChatPromptTemplate.from_messages(
            [("human", prompts["background_knowledge_prompt"])]
        )
        background_knowledge: str = await self.execute_prompt_chain_step(
            step_name="background_knowledge",
            prompt_settings=ps_bk,
            evaluation_metadata=evaluation_metadata,
            template=bk_template,
            chain_inputs={"text": text, "grade": grade},
            parser_output_type=None,
        )

        # ── Step 2: vocabulary complexity (grade-specific prompts, shared Output shape)
        chain_inputs: dict[str, Any] = {
            "text": input.text.value,
            "student_grade_level": grade,
            "student_background_knowledge": background_knowledge,
        }
        if grade in _GRADES_3_4:
            chain_inputs["fk_level"] = fk_score
            answer, explanation = await self._run_vocab_complexity_chain(
                chain_inputs=chain_inputs,
                evaluation_metadata=evaluation_metadata,
                prompt_settings_vocab=ps_34,
                system_prompt=prompts["vocab_grades_3_4_system_prompt"],
                user_prompt_template=prompts["vocab_grades_3_4_user_prompt"],
            )
        else:
            answer, explanation = await self._run_vocab_complexity_chain(
                chain_inputs=chain_inputs,
                evaluation_metadata=evaluation_metadata,
                prompt_settings_vocab=ps_og,
                system_prompt=prompts["vocab_other_grades_system_prompt"],
                user_prompt_template=prompts["vocab_other_grades_user_prompt"],
            )

        return TextComplexityResult(
            answer=answer,
            explanation=explanation,
            metadata=evaluation_metadata,
        )

    async def _run_vocab_complexity_chain(
        self,
        *,
        chain_inputs: dict[str, Any],
        evaluation_metadata: EvaluationMetadata,
        prompt_settings_vocab: PromptSettings,
        system_prompt: str,
        user_prompt_template: str,
    ) -> tuple[TextComplexityAnswer, EvaluationExplanation]:
        parser = JsonOutputParser(pydantic_object=VocabularyComplexityOutput)
        template = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", user_prompt_template),
            ]
        ).partial(format_instructions=parser.get_format_instructions())

        output = await self.execute_prompt_chain_step(
            step_name="vocab_complexity",
            prompt_settings=prompt_settings_vocab,
            evaluation_metadata=evaluation_metadata,
            template=template,
            chain_inputs=chain_inputs,
            parser_output_type=VocabularyComplexityOutput,
            json_dict_normalizer=normalize_complexity_output,
        )

        # Normalise the score string: the prompt may return spaces ("very complex")
        # but TextComplexityAnswer expects underscores ("very_complex").
        score = output.complexity_score.lower().replace(" ", "_")
        answer = TextComplexityAnswer.from_score(score)
        explanation = EvaluationExplanation(
            summary=output.reasoning,
            details={
                "tier_2_words": output.tier_2_words,
                "tier_3_words": output.tier_3_words,
                "archaic_words": output.archaic_words,
                "other_complex_words": output.other_complex_words,
            },
        )
        return answer, explanation
