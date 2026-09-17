"""What one evaluation reports to telemetry, recorded as the evaluation happens.

The base class creates one of these per evaluation and the evaluator fills it in: the size
of what was evaluated, the grade, which model is answering, and one entry per step that
completed. Whatever it holds when the evaluation ends is the event — including when it ends
by raising, which is why the length and the steps are recorded as they are learned rather
than assembled at the end.

It holds no input text, and there is no field it could be put in.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from learning_commons_evaluators.providers.base import TokenUsage
from learning_commons_evaluators.telemetry.types import EventTokenUsage, StageDetail


@dataclass
class TelemetryRun:
    """One evaluation's telemetry, in progress."""

    #: ``provider:model`` for the model answering now: the last step to start, so a failure
    #: reports the step that was running rather than one that already finished. Before any
    #: step runs — a validation failure, say — it is the model that would have been called.
    provider: str
    #: Length of the evaluator's primary text input; ``0`` until the inputs are validated.
    #: Counted in characters, where JavaScript counts UTF-16 code units, so text outside the
    #: BMP reads one lower per astral character than the same text does from the TypeScript
    #: SDK. The field is a magnitude in an aggregate, not an identity, so it is counted the
    #: way each language counts.
    text_length: int = 0
    #: The grade evaluated, empty for an evaluator that takes none.
    grade: str = ""
    #: One entry per completed step, in run order.
    stages: list[StageDetail] = field(default_factory=list)
    _started: float = field(default_factory=time.perf_counter, repr=False)

    @property
    def elapsed_ms(self) -> int:
        """Wall-clock milliseconds since the evaluation began."""
        return int((time.perf_counter() - self._started) * 1000)

    @property
    def token_usage(self) -> EventTokenUsage | None:
        """What the completed steps cost in total, or ``None`` if none completed.

        A failure before the first step therefore reports no usage at all, rather than a
        pair of zeroes that would read as a free evaluation.
        """
        if not self.stages:
            return None
        return EventTokenUsage(
            input_tokens=sum(s.token_usage.input_tokens for s in self.stages if s.token_usage),
            output_tokens=sum(s.token_usage.output_tokens for s in self.stages if s.token_usage),
        )

    def step(self, stage: str, provider: str, latency_ms: int, usage: TokenUsage) -> None:
        """Record a step that completed, with what the call itself cost."""
        self.stages.append(
            StageDetail(
                stage=stage,
                provider=provider,
                latency_ms=latency_ms,
                token_usage=EventTokenUsage(
                    input_tokens=usage.input_tokens, output_tokens=usage.output_tokens
                ),
            )
        )


__all__ = ["TelemetryRun"]
