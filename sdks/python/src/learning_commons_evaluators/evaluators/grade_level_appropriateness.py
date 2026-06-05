"""Grade Level Appropriateness evaluator: determines appropriate grade band for a text."""

from __future__ import annotations

from typing import ClassVar

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import Field

from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.schemas.common_inputs import TextInputField
from learning_commons_evaluators.schemas.evaluator import (
    EvaluationExplanation,
    EvaluationInput,
)
from learning_commons_evaluators.schemas.grade_level_appropriateness import (
    GradeLevelAnswer,
    GradeLevelAppropriatenessEvaluationSettings,
    GradeLevelAppropriatenessOutput,
    GradeLevelAppropriatenessResult,
)
from learning_commons_evaluators.schemas.metadata import (
    EvaluationMetadata,
    EvaluatorMetadata,
)
from learning_commons_evaluators.settings._generated_grade_level_appropriateness_settings import (
    CONFIG as _GLA_CONFIG,
)

_INPUT_SETTINGS = _GLA_CONFIG.evaluator_metadata.inputs


class GradeLevelAppropriatenessEvaluationInput(EvaluationInput):
    """Input for a grade level appropriateness evaluation.

    Constraints (min/max text length) are sourced from
    ``[[evaluator_metadata.inputs]]`` in evaluator settings and applied
    automatically — callers supply raw values, not field objects.

    Example::

        inp = GradeLevelAppropriatenessEvaluationInput(text="The quick brown fox...")
    """

    _input_settings: ClassVar[dict] = _INPUT_SETTINGS

    text: TextInputField = Field(description="The text to evaluate.")

    def __init__(self, *, text: str, **kwargs):
        super().__init__(text=text, **kwargs)


class GradeLevelAppropriatenessEvaluator(
    BaseEvaluator[
        GradeLevelAppropriatenessEvaluationInput,
        GradeLevelAppropriatenessResult,
        GradeLevelAppropriatenessEvaluationSettings,
    ]
):
    """Evaluates text to determine appropriate K-12 grade band for independent reading."""

    metadata: EvaluatorMetadata = _GLA_CONFIG.evaluator_metadata
    default_evaluation_settings: GradeLevelAppropriatenessEvaluationSettings = (
        _GLA_CONFIG.evaluation_settings
    )

    async def evaluate_impl(
        self,
        input: GradeLevelAppropriatenessEvaluationInput,
        evaluation_settings: GradeLevelAppropriatenessEvaluationSettings,
        evaluation_metadata: EvaluationMetadata,
    ) -> GradeLevelAppropriatenessResult:
        """Run grade level appropriateness evaluation. Returns GradeLevelAppropriatenessResult."""
        step_prompt_settings = evaluation_settings.prompt_settings_step_gla_evaluation

        prompt_inputs = input.input_values()

        parser = JsonOutputParser(pydantic_object=GradeLevelAppropriatenessOutput)
        prompts = _GLA_CONFIG.prompts
        template = ChatPromptTemplate.from_messages(
            [
                ("system", prompts["system_prompt"]),
                ("human", prompts["human_prompt"]),
            ]
        ).partial(format_instructions=parser.get_format_instructions())

        gla_output = await self.execute_prompt_chain_step(
            step_name="gla_evaluation",
            prompt_settings=step_prompt_settings,
            evaluation_metadata=evaluation_metadata,
            template=template,
            chain_inputs=prompt_inputs,
            parser_output_type=GradeLevelAppropriatenessOutput,
        )

        answer = GradeLevelAnswer.from_score(gla_output.grade)
        return GradeLevelAppropriatenessResult(
            answer=answer,
            explanation=EvaluationExplanation(
                summary=gla_output.reasoning,
                details={
                    "alternative_grade": gla_output.alternative_grade,
                    "scaffolding_needed": gla_output.scaffolding_needed,
                },
            ),
            metadata=evaluation_metadata,
        )
