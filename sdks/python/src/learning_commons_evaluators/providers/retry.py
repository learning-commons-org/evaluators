"""The evaluator-side half of the retry split (SDK spec §6.3).

Dependency failures back off, and that loop belongs to the vendor SDKs: ``max_retries`` is
passed to them (see :class:`~.base.ProviderConfig`) and they retry their own 408/409/429/5xx
and connection failures with exponential backoff, honouring ``Retry-After``. Evaluation
failures resample: a response that fails its output schema is sampling variance, so the
call is simply made again, immediately, up to the same ``max_retries``. This module is that
second loop.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from learning_commons_evaluators.errors import (
    DependencyId,
    EvaluatorError,
    LLMOutputProcessingError,
    wrap_provider_error,
)

T = TypeVar("T")


async def call_with_resampling(
    call: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    dependency: DependencyId,
    model: str | None = None,
    logger: logging.Logger | None = None,
) -> T:
    """Await ``call``, resampling immediately on ``LLMOutputProcessingError``.

    Every other failure is classified with :func:`wrap_provider_error` and raised at once:
    a retryable dependency error has already exhausted the vendor SDK's own backoff by the
    time it surfaces here, and a non-retryable one must not be retried at all. Total
    attempts are ``1 + max_retries``; ``0`` disables resampling.
    """
    attempt = 0
    while True:
        try:
            return await call()
        except Exception as raw:  # noqa: BLE001 — everything is classified below
            error = (
                raw
                if isinstance(raw, EvaluatorError)
                else wrap_provider_error(raw, dependency=dependency, model=model)
            )
            if isinstance(error, LLMOutputProcessingError) and attempt < max_retries:
                attempt += 1
                if logger is not None:
                    logger.debug(
                        "Resampling after output processing failure",
                        extra={"attempt": attempt, "max_retries": max_retries, "model": model},
                    )
                continue
            if error is raw:
                raise
            raise error from raw


__all__ = ["call_with_resampling"]
