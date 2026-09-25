"""The result envelope (SDK spec §5.1), identical for every evaluator and every SDK."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

ResultT = TypeVar("ResultT")


class EvaluationTokenUsage(BaseModel):
    """Tokens consumed by an evaluation, summed across every step without deduplication."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int
    output_tokens: int


class EvaluationMetadata(BaseModel):
    """Operational facts about how an evaluation ran."""

    model_config = ConfigDict(frozen=True)

    #: ``provider:model`` for the model that actually ran, including any override (§3.4).
    model: str
    #: Wall-clock time for the whole evaluation, not just the LLM calls.
    processing_time_ms: int
    token_usage: EvaluationTokenUsage


class EvaluationResult(BaseModel, Generic[ResultT]):
    """What every ``evaluate()`` returns. The three fields are the whole envelope.

    ``result`` is the model's structured output as the evaluator's ``output_schema.json``
    declares it, keys and values unaltered, so the payload is identical across SDKs. There
    is no scalar score hoisted up here; reports that need one use :func:`read_outcome`.
    """

    model_config = ConfigDict(frozen=True)

    #: The evaluator's current registry id; renames stay resolvable via ``id_history``.
    evaluator: str
    result: ResultT
    metadata: EvaluationMetadata


__all__ = ["EvaluationMetadata", "EvaluationResult", "EvaluationTokenUsage"]
