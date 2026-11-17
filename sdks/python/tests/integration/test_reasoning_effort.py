"""Every reasoning effort config.schema.json admits, sent to a real model of each provider.

Skipped unless ``RUN_INTEGRATION_TESTS=1`` and the provider's key is set. The unit wire tests
show each value reaches the request; these show the vendor takes that request, effort and
structured output together, on a current model. Which of its provider's values a model
accepts is the model's own property, so each case states what this model does: answers, or
refuses with an error the caller sees. A value the model refuses must never be dropped or
swapped for a neighbour, so a refusal that turns into an answer fails here too. The
TypeScript SDK's ``reasoning-effort.integration.test.ts`` holds the same table.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from pydantic import BaseModel

from learning_commons_evaluators.providers import Message, Provider, ProviderConfig, create_provider

pytestmark = pytest.mark.integration


class _Sum(BaseModel):
    total: int


MESSAGES: list[Message] = [
    {"role": "system", "content": "Answer in the JSON shape requested."},
    {"role": "user", "content": "What is 2 + 3?"},
]

#: One model per provider and, for each value its provider admits, whether it answers.
CASES: dict[Provider, tuple[str, dict[str, bool]]] = {
    Provider.OPENAI: (
        "gpt-5.5",
        {
            "none": True,
            "minimal": False,
            "low": True,
            "medium": True,
            "high": True,
            "xhigh": True,
            "max": True,
        },
    ),
    Provider.ANTHROPIC: (
        "claude-haiku-5-5",
        {"low": True, "medium": True, "high": True, "xhigh": True, "max": True},
    ),
    Provider.GOOGLE: (
        "gemini-3.6-flash",
        {"minimal": True, "low": True, "medium": True, "high": True},
    ),
}
KEY_ENV = {
    Provider.OPENAI: "OPENAI_API_KEY",
    Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
    Provider.GOOGLE: "GOOGLE_API_KEY",
}


@pytest.mark.parametrize(
    ("provider", "effort", "answers"),
    [
        pytest.param(provider, effort, answers, id=f"{provider.value}-{model}-{effort}")
        for provider, (model, efforts) in CASES.items()
        for effort, answers in efforts.items()
    ],
)
async def test_the_model_takes_or_refuses_each_effort(
    provider: Provider, effort: str, answers: bool
) -> None:
    key = os.environ.get(KEY_ENV[provider])
    if not key:
        pytest.skip(f"{KEY_ENV[provider]} is not set")
    # A built-in adapter, which takes the keyword the LLMProvider protocol leaves optional.
    adapter: Any = create_provider(
        ProviderConfig(type=provider, model=CASES[provider][0], api_key=key, max_retries=0)
    )
    if not answers:
        with pytest.raises(Exception, match="(?i)effort|reasoning|thinking"):
            await adapter.generate_structured(MESSAGES, _Sum, reasoning_effort=effort)
        return
    response = await adapter.generate_structured(MESSAGES, _Sum, reasoning_effort=effort)
    assert response.data.total == 5
