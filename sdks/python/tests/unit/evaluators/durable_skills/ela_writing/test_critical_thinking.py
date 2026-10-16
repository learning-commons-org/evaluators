"""One source passage: the prompt count is 1, and indicator 2.1 may be absent."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from learning_commons_evaluators import CriticalThinkingEvaluator, InputValidationError
from learning_commons_evaluators.schemas.durable_skills.ela_writing.critical_thinking import (
    CriticalThinkingOutput,
)
from tests.unit.conftest import ProviderFactory

ASSIGNMENT = "Using the sources, argue whether the town should limit cars downtown."
ESSAY = (
    "Dear city council, the article says the face is a mesa. The student names that "
    "source and restates its claim, then stops. No other evidence is weighed, and the "
    "essay does not answer whether the town should limit cars downtown."
)
PASSAGE = "The face is a mesa, according to the article the student was given."


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
        source_passages=[{"title": "Unmasking the Face on Mars", "text": PASSAGE}],
        essay_text=ESSAY,
    )

    assert isinstance(evaluation.result, CriticalThinkingOutput)
    indicators = evaluation.result.indicators
    assert indicators.synthesizing_sources is None
    assert "synthesizing_sources" not in indicators.model_dump()
    assert "synthesizing_sources" not in indicators.model_dump_json()
    assert evaluation.result.critical_thinking_score == "exploring"
    prompt = providers.last.calls[0]["messages"][1]["content"]
    assert "Number of source passages provided: 1" in prompt
    assert "### Source 1: Unmasking the Face on Mars" in prompt


def _call(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "assignment_text": ASSIGNMENT,
        "source_passages": [{"text": PASSAGE}],
        "essay_text": ESSAY,
    }
    fields.update(overrides)
    return fields


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"essay_text": "a" * 199}, "essay_text is too short. Minimum length is 200 characters."),
        (
            {"essay_text": "a" * 12001},
            "essay_text is too long. Maximum length is 12000 characters.",
        ),
        (
            {"assignment_text": "a" * 19},
            "assignment_text is too short. Minimum length is 20 characters.",
        ),
        (
            {"assignment_text": "a" * 3001},
            "assignment_text is too long. Maximum length is 3000 characters.",
        ),
        (
            {"source_passages": [{"text": "a" * 49}]},
            r"source_passages\[0\].text is too short. Minimum length is 50 characters.",
        ),
        (
            {"source_passages": [{"text": "a" * 9001}]},
            r"source_passages\[0\].text is too long. Maximum length is 9000 characters.",
        ),
        (
            {"source_passages": [{"title": "t" * 301, "text": PASSAGE}]},
            r"source_passages\[0\].title is too long. Maximum length is 300 characters.",
        ),
        (
            {"source_passages": [{"author": "a" * 201, "text": PASSAGE}]},
            r"source_passages\[0\].author is too long. Maximum length is 200 characters.",
        ),
        (
            {"source_passages": [{"text": PASSAGE}] * 6},
            "source_passages accepts at most 5 items; received 6.",
        ),
    ],
)
async def test_rejects_inputs_outside_the_bounds(overrides: dict[str, Any], message: str) -> None:
    evaluator = CriticalThinkingEvaluator(anthropic_api_key="k")
    with pytest.raises(InputValidationError, match=message):
        await evaluator.evaluate(**_call(**overrides))
