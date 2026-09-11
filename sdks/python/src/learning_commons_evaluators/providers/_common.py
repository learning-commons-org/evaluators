"""Helpers shared by the built-in adapters."""

from __future__ import annotations

import time
from collections.abc import Sequence

from learning_commons_evaluators.errors import ConfigurationError, LLMOutputProcessingError
from learning_commons_evaluators.providers.base import Message, Provider, ProviderConfig


def require_config(config: ProviderConfig, expected: Provider) -> tuple[str, str]:
    """The model id and API key an adapter needs, or the ``ConfigurationError`` explaining why not.

    The key is demanded here rather than left to the vendor SDK, which would otherwise fall
    back to reading its environment variable: the spec forbids implicit credential reads
    (§3.1), so a missing key must fail with the canonical message before any client exists.
    """
    if config.type is not expected:
        raise ConfigurationError(
            f"{expected.value} adapter received a config for provider {config.type.value!r}."
        )
    if not config.model or not config.model.strip():
        raise ConfigurationError(
            f"model is required for the {expected.value} provider. No default is assumed."
        )
    if config.api_key is None or not config.api_key.strip():
        raise ConfigurationError(f"Missing required credential: {expected.value}_api_key")
    return config.model, config.api_key


def split_system(messages: Sequence[Message]) -> tuple[str | None, list[Message]]:
    """The system prompt, if any, and every other message in order.

    Every vendor takes the system prompt out of band, so the adapters all split the same
    way: the first ``system`` message is it, and any further ``system`` message is dropped
    rather than sent as a user turn.
    """
    system: str | None = None
    rest: list[Message] = []
    for message in messages:
        if message["role"] == "system":
            if system is None:
                system = message["content"]
            continue
        rest.append(message)
    return system, rest


def elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def no_structured_output(label: str, detail: str | None) -> LLMOutputProcessingError:
    """The error for a call that completed without a parseable structured payload.

    Refusals, truncation and empty completions all land here: the dependency answered, so
    this is the model's output failing our contract, which resamples rather than backs off.
    """
    suffix = f" ({detail})" if detail else ""
    return LLMOutputProcessingError(f"{label} returned no structured output{suffix}.")
