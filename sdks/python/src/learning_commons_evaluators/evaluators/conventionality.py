"""Conventionality evaluator: evaluates text for conventionality of language."""

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
from learning_commons_evaluators.schemas.conventionality import (
    ConventionalityEvaluationSettings,
    ConventionalityOutput,
)
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
from learning_commons_evaluators.settings._generated_conventionality_settings import (
    CONFIG as _CONVENTIONALITY_CONFIG,
)

_INPUT_SETTINGS = _CONVENTIONALITY_CONFIG.evaluator_metadata.inputs


class ConventionalityEvaluationInput(EvaluationInput):
    """Input for a conventionality evaluation.

    Constraints (min/max text length, allowed grades) are sourced from
    ``[[evaluator_metadata.inputs]]`` in evaluator settings and applied
    automatically — callers supply raw values, not field objects.

    Example::

        inp = ConventionalityEvaluationInput(text="The quick brown fox...", grade=5)
    """

    _input_settings: ClassVar[dict] = _INPUT_SETTINGS

    text: TextInputField = Field(description="The text to evaluate.")
    grade: GradeInputField = Field(description="The grade level of the text.")

    def __init__(self, *, text: str, grade: int, **kwargs):
        super().__init__(text=text, grade=grade, **kwargs)


class ConventionalityEvaluator(
    BaseEvaluator[
        ConventionalityEvaluationInput,
        TextComplexityResult,
        ConventionalityEvaluationSettings,
    ]
):
    """Evaluates text for conventionality (idioms, metaphors, implied meaning) relative to grade."""

    metadata: EvaluatorMetadata = _CONVENTIONALITY_CONFIG.evaluator_metadata
    default_evaluation_settings: ConventionalityEvaluationSettings = (
        _CONVENTIONALITY_CONFIG.evaluation_settings
    )

    def evaluate_impl(
        self,
        input: ConventionalityEvaluationInput,
        evaluation_settings: ConventionalityEvaluationSettings,
        evaluation_metadata: EvaluationMetadata,
    ) -> TextComplexityResult:
        """Run conventionality evaluation. Returns TextComplexityResult with answer, explanation, metadata."""
        ps_main = evaluation_settings.prompt_settings_step_main
        assert ps_main is not None

        fk_score = round(textstat.flesch_kincaid_grade(input.text.value), 2)
        prompt_inputs = input.input_values()
        prompt_inputs["fk_score"] = fk_score

        parser = JsonOutputParser(pydantic_object=ConventionalityOutput)
        prompts = _CONVENTIONALITY_CONFIG.prompts
        template = ChatPromptTemplate.from_messages(
            [
                ("system", prompts["system_prompt"]),
                ("human", prompts["human_prompt"]),
            ]
        ).partial(format_instructions=parser.get_format_instructions())
        conventionality_output = self.execute_prompt_chain_step(
            step_name="main",
            prompt_settings=ps_main,
            evaluation_metadata=evaluation_metadata,
            template=template,
            chain_inputs=prompt_inputs,
            parser_output_type=ConventionalityOutput,
        )
        assert isinstance(conventionality_output, ConventionalityOutput)

        answer = TextComplexityAnswer.from_score(conventionality_output.complexity_score)
        return TextComplexityResult(
            answer=answer,
            explanation=EvaluationExplanation(
                summary=conventionality_output.reasoning,
                details={
                    "conventionality_features": conventionality_output.conventionality_features,
                    "grade_context": conventionality_output.grade_context,
                    "instructional_insights": conventionality_output.instructional_insights,
                },
            ),
            metadata=evaluation_metadata,
        )
