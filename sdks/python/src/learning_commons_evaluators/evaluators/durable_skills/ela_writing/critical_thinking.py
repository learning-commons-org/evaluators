"""Critical Thinking: how a student essay reasons with its sources.

Rates a grade 8-10 argumentative essay across five indicators plus an overall
rating, on a five-level scale from ``not_evident`` to ``extending``.

One model call on Anthropic. The caller passes the assignment, the source
passages as one string, how many passages that string contains, and the essay.
"""

from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from learning_commons_evaluators.schemas.durable_skills.ela_writing.critical_thinking import (
    EVALUATOR_ID,
    CriticalThinkingInput,
    CriticalThinkingOutput,
)


class CriticalThinkingEvaluator(SingleStepEvaluator[CriticalThinkingInput, CriticalThinkingOutput]):
    contract = load_contract(EVALUATOR_ID)
    input_model = CriticalThinkingInput
    output_model = CriticalThinkingOutput


__all__ = [
    "CriticalThinkingEvaluator",
    "CriticalThinkingInput",
    "CriticalThinkingOutput",
]
