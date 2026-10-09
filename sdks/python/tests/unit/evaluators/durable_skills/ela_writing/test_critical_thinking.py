"""One source passage: the prompt count is 1, and indicator 2.1 may be absent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from learning_commons_evaluators import CriticalThinkingEvaluator
from learning_commons_evaluators.schemas.durable_skills.ela_writing.critical_thinking import (
    CriticalThinkingOutput,
)
from tests.unit.conftest import ProviderFactory

ASSIGNMENT = "Using the sources, argue whether the town should limit cars downtown."
ESSAY = "Dear city council, the article says the face is a mesa."


def _without_synthesizing(schema: type[BaseModel]) -> Any:
    indicator = {
        "evidence": [{"quote": "the face is a mesa", "comment": "restates the article"}],
        "reasoning": "The essay names the article and stops there.",
        "rating": "exploring",
    }
    return schema.model_validate(
        {
            "indicators": {
                "evidence_strength": indicator,
                "counterarguments": indicator,
                "facts_over_opinions": indicator,
                "drawing_conclusions": indicator,
            },
            "reasoning": "Median of the four ratings is exploring.",
            "critical_thinking_score": "exploring",
        }
    )


async def test_one_passage_omits_synthesizing_sources(providers: ProviderFactory) -> None:
    providers.payload = _without_synthesizing
    evaluator = CriticalThinkingEvaluator(anthropic_api_key="k")
    evaluation = await evaluator.evaluate(
        assignment_text=ASSIGNMENT,
        source_passages=[{"title": "Unmasking the Face on Mars", "text": "The face is a mesa."}],
        essay_text=ESSAY,
    )

    assert isinstance(evaluation.result, CriticalThinkingOutput)
    assert evaluation.result.indicators.synthesizing_sources is None
    assert evaluation.result.critical_thinking_score == "exploring"
    prompt = providers.last.calls[0]["messages"][1]["content"]
    assert "Number of source passages provided: 1" in prompt
    assert "### Source 1: Unmasking the Face on Mars" in prompt
