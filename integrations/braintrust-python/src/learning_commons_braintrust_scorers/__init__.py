"""learning-commons-braintrust-scorers

Braintrust adapters for Learning Commons evaluators.

Adapters implement LLMGeneratorProtocol and can be passed directly to any
evaluator that accepts an ``llm_provider`` argument::

    from learning_commons_braintrust_scorers import BraintrustAnthropicAdapter
    from learning_commons_evaluators.evaluators.gla import (
        GradeLevelAppropriatenessEvaluator,
        GradeLevelAppropriatenessEvaluationInput,
    )

    evaluator = GradeLevelAppropriatenessEvaluator(
        config=...,
        llm_provider=BraintrustAnthropicAdapter(project="my-project"),
    )
    result = await evaluator.evaluate(GradeLevelAppropriatenessEvaluationInput(text="..."))
    print(result.answer.score)         # e.g. "6-8"
    print(result.explanation.summary)  # reasoning text
"""

from learning_commons_braintrust_scorers.adapter import (
    BraintrustAnthropicAdapter,
    BraintrustProxyAdapter,
)

__all__ = ["BraintrustAnthropicAdapter", "BraintrustProxyAdapter"]
