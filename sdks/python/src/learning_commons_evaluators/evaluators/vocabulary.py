"""Vocabulary evaluator: evaluates text for vocabulary complexity relative to grade level."""

from __future__ import annotations

from typing import ClassVar

import textstat
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
    VocabularyEvaluationSettings,
    VocabularyOutputGrades34,
    VocabularyOutputOtherGrades,
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

        inp = VocabularyEvaluationInput(text="The quick brown fox...", grade_level=5)
    """

    _input_settings: ClassVar[dict] = _INPUT_SETTINGS

    text: TextInputField = Field(description="The text to evaluate.")
    grade_level: GradeInputField = Field(description="The grade level of the text (3–12).")

    def __init__(self, *, text: str, grade_level: int, **kwargs):
        super().__init__(text=text, grade_level=grade_level, **kwargs)


class VocabularyEvaluator(
    BaseEvaluator[VocabularyEvaluationInput, TextComplexityResult, VocabularyEvaluationSettings]
):
    """Evaluates text for vocabulary complexity relative to the target grade level.

    The evaluation runs in two steps:
    1. **Background knowledge** – the model generates a short assumption about what
       students at the target grade already know about the text's topic.  This
       provides context that keeps the complexity rating from penalising familiar
       domain words.
    2. **Vocabulary complexity** – a grade-specific prompt + model produces the
       final score and reasoning.  Grades 3–4 use a Gemini model and return a
       rubric label plus a word-level breakdown; grades 5–12 use a GPT model and
       return an integer score (1–4).

    Supported grades: 3–12.
    """

    metadata: EvaluatorMetadata = _VOCABULARY_CONFIG.evaluator_metadata
    default_evaluation_settings: VocabularyEvaluationSettings = (
        _VOCABULARY_CONFIG.evaluation_settings
    )

    def evaluate_impl(
        self,
        input: VocabularyEvaluationInput,
        evaluation_settings: VocabularyEvaluationSettings,
        evaluation_metadata: EvaluationMetadata,
    ) -> TextComplexityResult:
        """Run the two-step vocabulary evaluation and return a TextComplexityResult.

        Grade validation is handled by the framework before this method is called:
        ``VocabularyEvaluationInput`` automatically constrains ``grade_level`` to
        :data:`~learning_commons_evaluators.schemas.vocabulary.VOCABULARY_SUPPORTED_GRADES`
        (3–12), so ``BaseEvaluator.evaluate`` raises before reaching here for
        unsupported grades.
        """
        ps_bk = evaluation_settings.prompt_settings_step_background_knowledge
        ps_34 = evaluation_settings.prompt_settings_step_vocab_grades_3_4
        ps_og = evaluation_settings.prompt_settings_step_vocab_other_grades
        assert ps_bk is not None and ps_34 is not None and ps_og is not None

        grade = input.grade_level.value
        fk_score = round(textstat.flesch_kincaid_grade(input.text.value), 2)
        prompts = _VOCABULARY_CONFIG.prompts

        # ── Step 1: background knowledge ──────────────────────────────────────
        # parser_output_type=None → execute_prompt_chain_step returns plain str.
        bk_template = ChatPromptTemplate.from_messages(
            [("human", prompts["background_knowledge_prompt"])]
        )
        background_knowledge: str = self.execute_prompt_chain_step(
            step_name="background_knowledge",
            prompt_settings=ps_bk,
            evaluation_metadata=evaluation_metadata,
            template=bk_template,
            chain_inputs={"text": input.text.value, "grade": grade},
            parser_output_type=None,
        )

        # ── Step 2: vocabulary complexity (grade-specific) ────────────────────
        if grade in _GRADES_3_4:
            answer, explanation = self._evaluate_grades_3_4(
                input=input,
                grade=grade,
                fk_score=fk_score,
                background_knowledge=background_knowledge,
                evaluation_metadata=evaluation_metadata,
                prompts=prompts,
                prompt_settings_vocab=ps_34,
            )
        else:
            answer, explanation = self._evaluate_other_grades(
                input=input,
                grade=grade,
                background_knowledge=background_knowledge,
                evaluation_metadata=evaluation_metadata,
                prompts=prompts,
                prompt_settings_vocab=ps_og,
            )

        return TextComplexityResult(
            answer=answer,
            explanation=explanation,
            metadata=evaluation_metadata,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _evaluate_grades_3_4(
        self,
        *,
        input: VocabularyEvaluationInput,
        grade: int,
        fk_score: float,
        background_knowledge: str,
        evaluation_metadata: EvaluationMetadata,
        prompts: dict,
        prompt_settings_vocab: PromptSettings,
    ) -> tuple[TextComplexityAnswer, EvaluationExplanation]:
        """Run the grades 3–4 vocabulary complexity step.

        Returns a rubric-label score and a word-breakdown explanation.
        """
        parser = JsonOutputParser(pydantic_object=VocabularyOutputGrades34)
        template = ChatPromptTemplate.from_messages(
            [
                ("system", prompts["vocab_grades_3_4_system_prompt"]),
                ("human", prompts["vocab_grades_3_4_user_prompt"]),
            ]
        ).partial(format_instructions=parser.get_format_instructions())

        output = self.execute_prompt_chain_step(
            step_name="vocab_complexity",
            prompt_settings=prompt_settings_vocab,
            evaluation_metadata=evaluation_metadata,
            template=template,
            chain_inputs={
                "text": input.text.value,
                "student_grade_level": grade,
                "student_background_knowledge": background_knowledge,
                "fk_level": fk_score,
            },
            parser_output_type=VocabularyOutputGrades34,
        )
        assert isinstance(output, VocabularyOutputGrades34)

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

    def _evaluate_other_grades(
        self,
        *,
        input: VocabularyEvaluationInput,
        grade: int,
        background_knowledge: str,
        evaluation_metadata: EvaluationMetadata,
        prompts: dict,
        prompt_settings_vocab: PromptSettings,
    ) -> tuple[TextComplexityAnswer, EvaluationExplanation]:
        """Run the grades 5–12 vocabulary complexity step.

        Returns a string-label score and a reasoning explanation.
        The OTHER_GRADES prompt uses the same ``Output``-style schema as grades 3–4,
        so the LLM returns a word-level breakdown and a string ``complexity_score``.
        """
        parser = JsonOutputParser(pydantic_object=VocabularyOutputOtherGrades)
        template = ChatPromptTemplate.from_messages(
            [
                ("system", prompts["vocab_other_grades_system_prompt"]),
                ("human", prompts["vocab_other_grades_user_prompt"]),
            ]
        ).partial(format_instructions=parser.get_format_instructions())

        output = self.execute_prompt_chain_step(
            step_name="vocab_complexity",
            prompt_settings=prompt_settings_vocab,
            evaluation_metadata=evaluation_metadata,
            template=template,
            chain_inputs={
                "text": input.text.value,
                "student_grade_level": grade,
                "student_background_knowledge": background_knowledge,
            },
            parser_output_type=VocabularyOutputOtherGrades,
        )
        assert isinstance(output, VocabularyOutputOtherGrades)

        # Normalise the score string: the prompt may return spaces ("slightly complex")
        # but TextComplexityAnswer expects underscores ("slightly_complex").
        score = output.complexity_score.lower().replace(" ", "_")
        answer = TextComplexityAnswer.from_score(score)
        explanation = EvaluationExplanation(summary=output.reasoning, details={})
        return answer, explanation
