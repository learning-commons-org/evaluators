"""Every reasoning effort config.schema.json admits, sent to real models of each provider.

Skipped unless ``RUN_INTEGRATION_TESTS=1`` and the provider's key is set. The unit wire tests
show each value reaches the request; these show the vendor takes that request, effort and
structured output together, on a current model. The values are read from the schema, so a
value added there is sent here too. Which of them a model accepts is the model's own
property, so each model case names the values it refuses with an error the caller sees;
it answers the rest. A value the model refuses must never be dropped or
swapped for a neighbour, so a refusal that turns into an answer fails here too. The
TypeScript SDK's ``reasoning-effort.integration.test.ts`` holds the same table.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
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

_DEFS = json.loads(
    (Path(__file__).resolve().parents[4] / "evals/_schemas/config.schema.json").read_text(
        encoding="utf-8"
    )
)["$defs"]

_OPENAI = _DEFS["ReasoningEffortOpenAI"]["enum"]

#: Each model, its provider's values from the schema, and those it refuses. gpt-6-luna and
#: gpt-5.5 are the models Sentence Structure runs on.
CASES: list[tuple[Provider, str, list[str], set[str]]] = [
    (Provider.OPENAI, "gpt-6-luna", _OPENAI, {"minimal"}),
    (Provider.OPENAI, "gpt-5.5", _OPENAI, {"minimal", "max"}),
    (Provider.ANTHROPIC, "claude-haiku-5-5", _DEFS["ReasoningEffortAnthropic"]["enum"], set()),
    (Provider.GOOGLE, "gemini-3.6-flash", _DEFS["ReasoningEffortGoogle"]["enum"], set()),
]
# A refused value the schema no longer lists would never be sent, so it must be one of them.
assert all(refused <= set(efforts) for _, _, efforts, refused in CASES)

KEY_ENV = {
    Provider.OPENAI: "OPENAI_API_KEY",
    Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
    Provider.GOOGLE: "GOOGLE_API_KEY",
}


@pytest.mark.parametrize(
    ("provider", "model", "effort", "answers"),
    [
        pytest.param(
            provider,
            model,
            effort,
            effort not in refused,
            id=f"{provider.value}-{model}-{effort}",
        )
        for provider, model, efforts, refused in CASES
        for effort in efforts
    ],
)
async def test_the_model_takes_or_refuses_each_effort(
    provider: Provider, model: str, effort: str, answers: bool
) -> None:
    key = os.environ.get(KEY_ENV[provider])
    if not key:
        pytest.skip(f"{KEY_ENV[provider]} is not set")
    # A built-in adapter, which takes the keyword the LLMProvider protocol leaves optional.
    adapter: Any = create_provider(
        ProviderConfig(type=provider, model=model, api_key=key, max_retries=0)
    )
    if not answers:
        # The refusal names the value, so it is this value being refused and not, say, the key.
        with pytest.raises(Exception, match=f"'{effort}'"):
            await adapter.generate_structured(MESSAGES, _Sum, reasoning_effort=effort)
        return
    response = await adapter.generate_structured(MESSAGES, _Sum, reasoning_effort=effort)
    assert response.data.total == 5
