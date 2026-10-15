"""A short live call for Critical Thinking.

The expert multi-source fixture stays in ``fixtures.json`` and is left out of the pilot
suite: three long passages on Claude Opus are the expensive call. This one uses two short
passages and a short essay, once, and checks that a level on the scale comes back.
"""

from __future__ import annotations

import pytest

from learning_commons_evaluators import CriticalThinkingEvaluator, read_outcome
from learning_commons_evaluators.providers import provider_label
from tests.integration.conftest import keys_for

LEVELS = ("not_evident", "exploring", "analyzing", "integrating", "extending")


@pytest.mark.integration
async def test_short_essay_returns_a_level() -> None:
    contract = CriticalThinkingEvaluator.contract
    evaluator = CriticalThinkingEvaluator(**keys_for(contract), telemetry=False)
    evaluation = await evaluator.evaluate(
        assignment_text="Argue whether towns should plant more street trees. Use both sources.",
        source_passages=[
            {
                "title": "Shade",
                "author": "City trees office",
                "text": "Street trees cool sidewalks and give birds a place to nest.",
            },
            {
                "title": "Roots",
                "text": "Tree roots can lift pavement when they are planted in a narrow strip.",
            },
        ],
        essay_text=(
            "Towns should plant more street trees. The first source says they cool sidewalks. "
            "The second source warns that roots can lift pavement, so towns should give each "
            "tree enough room."
        ),
    )

    assert evaluation.evaluator == contract.evaluator.id
    model = contract.steps[0].model
    assert model is not None
    assert evaluation.metadata.model == provider_label(model.provider, model.name)
    outcome = read_outcome(evaluation, CriticalThinkingEvaluator.metadata.outcome)
    assert outcome.score in LEVELS
