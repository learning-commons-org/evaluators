"""A short live call for Critical Thinking.

The expert multi-source fixture stays in ``fixtures.json`` and is left out of the pilot
suite: three long passages on Claude Opus are the expensive call. This one uses four short
passages, once, and checks that a level on the scale comes back and matches their median.
"""

from __future__ import annotations

import pytest

from learning_commons_evaluators import CriticalThinkingEvaluator, read_outcome
from learning_commons_evaluators.providers import provider_label
from tests.integration.conftest import keys_for
from tests.unit.evaluators.durable_skills.ela_writing.test_critical_thinking_score import (
    LEVELS,
    median_rating,
    present_ratings,
)


@pytest.mark.integration
async def test_short_essay_returns_a_level() -> None:
    contract = CriticalThinkingEvaluator.contract
    evaluator = CriticalThinkingEvaluator(**keys_for(contract), telemetry=False)
    evaluation = await evaluator.evaluate(
        assignment_text="Argue whether towns should plant more street trees. Use the sources.",
        source_passages=[
            {
                "title": "Shade",
                "author": "City trees office",
                "text": "Street trees cool sidewalks and give birds a place to nest.",
            },
            {
                "title": "Roots",
                "author": None,
                "text": "Tree roots can lift pavement when they are planted in a narrow strip.",
            },
            {
                "author": "A gardener",
                "text": "Young trees need water through their first summer.",
            },
            {"text": "Bare soil dries faster when nothing shades it."},
        ],
        essay_text=(
            "Towns should plant more street trees. Shade says they cool sidewalks. "
            "Roots warns that pavement can lift, so each tree needs room. "
            "A gardener says young trees need water. Bare soil dries faster without shade."
        ),
    )

    assert evaluation.evaluator == contract.evaluator.id
    model = contract.steps[0].model
    assert model is not None
    assert evaluation.metadata.model == provider_label(model.provider, model.name)
    outcome = read_outcome(evaluation, CriticalThinkingEvaluator.metadata.outcome)
    assert outcome.score in LEVELS
    assert outcome.score == median_rating(present_ratings(evaluation.result.indicators))
