"""The base every evaluator builds on: configuration checks, provider construction, telemetry."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any, ClassVar

from pydantic import BaseModel

from learning_commons_evaluators.config import EvaluatorConfig, ModelOverride
from learning_commons_evaluators.contracts.loader import Contract
from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.features.preprocessing import format_number
from learning_commons_evaluators.logger import get_logger
from learning_commons_evaluators.providers import (
    LLMProvider,
    Provider,
    ProviderConfig,
    create_provider,
)
from learning_commons_evaluators.schemas.evaluator import EvaluationResult
from learning_commons_evaluators.schemas.metadata import EvaluatorMetadata
from learning_commons_evaluators.telemetry import (
    COLLECTOR_ENDPOINT,
    EvaluationStatus,
    TelemetryClient,
    TelemetryClientConfig,
    TelemetryEvent,
    TelemetryRun,
    client_id,
    sdk_version,
    utc_timestamp,
)


class BaseEvaluator(ABC):
    """Configuration validation, provider construction, telemetry, and the ``evaluate`` contract.

    Construct with an :class:`EvaluatorConfig` or with its fields as keyword arguments::

        evaluator = PurposeClarityEvaluator(google_api_key="...")
        evaluator = PurposeClarityEvaluator(EvaluatorConfig(google_api_key="..."))

    :raises ConfigurationError: for a malformed ``model_override`` or a missing credential
        the evaluator's contract requires (§3.1), before any I/O.
    """

    #: The registry contract the evaluator is built from; set by the concrete class.
    contract: ClassVar[Contract]
    #: Static facts from the contract; derived at class creation.
    metadata: ClassVar[EvaluatorMetadata]

    def __init__(self, config: EvaluatorConfig | None = None, /, **fields: Any) -> None:
        if config is not None and fields:
            raise TypeError("Pass an EvaluatorConfig or its fields as keyword arguments, not both.")
        if config is None:
            try:
                config = EvaluatorConfig(**fields)
            except TypeError as error:
                accepted = ", ".join(EvaluatorConfig.__dataclass_fields__)
                raise ConfigurationError(
                    f"Unknown configuration field. Accepted fields: {accepted}."
                ) from error
        self.config = config
        self.logger = get_logger(self.metadata.id)

        self._override_provider = self._validate_model_override(config.model_override)
        self._validate_credentials()

        telemetry = config.telemetry_options
        # Disabled means disabled: no client, so nothing is built, queued, or sent, and the
        # process never starts a sender thread on this evaluator's account.
        self._telemetry: TelemetryClient | None = (
            TelemetryClient(
                TelemetryClientConfig(
                    endpoint=COLLECTOR_ENDPOINT,
                    client_id=client_id(),
                    enabled=True,
                    learning_commons_api_key=telemetry.learning_commons_api_key,
                    logger=self.logger,
                )
            )
            if telemetry.enabled
            else None
        )

        if config.model_override is not None:
            # Once, at construction (§3.2): evaluators are validated against their default
            # models only. Per-evaluation log lines carry the effective model.
            self.logger.warning(
                "model_override is active: using %s:%s instead of the default model. "
                "Evaluation quality may differ from recommended defaults.%s",
                self._override_provider.value if self._override_provider else "?",
                config.model_override.model,
                self._dropped_temperature_note(),
                extra={"evaluator": self.metadata.id, "operation": "construct"},
            )

    # --- configuration -------------------------------------------------------------

    @staticmethod
    def _validate_model_override(override: ModelOverride | None) -> Provider | None:
        if override is None:
            return None
        try:
            provider = Provider(override.provider)
        except ValueError:
            valid = ", ".join(p.value for p in Provider)
            raise ConfigurationError(
                f'Invalid provider "{override.provider}" in model_override. '
                f"Valid providers are: {valid}."
            ) from None
        if not isinstance(override.model, str) or not override.model.strip():
            raise ConfigurationError(
                f'model_override.model is required. Specify the model ID for provider "{provider.value}".'
            )
        return provider

    @property
    def providers_in_use(self) -> tuple[Provider, ...]:
        """The LLM providers this instance will call: the override's, or the contract's."""
        if self._override_provider is not None:
            return (self._override_provider,)
        return self.metadata.default_providers

    def _validate_credentials(self) -> None:
        """Every credential the evaluator needs was supplied (§3.1).

        Requirements are derived, not listed: the LLM keys come from the providers the
        steps use, and the non-LLM ones from the contract's ``required_credentials``. A
        model override replaces the former and leaves the latter alone, so an override
        cannot skip a credential for a service the evaluator still calls.
        """
        required = [
            *(f"{provider.value}_api_key" for provider in self.providers_in_use),
            *self.metadata.required_credentials,
        ]
        for key in required:
            value = self.config.credential(key)
            if value is None or not value.strip():
                raise ConfigurationError(
                    f"Missing required credential: {key}. Required by {self.metadata.name}."
                )

    # --- providers -----------------------------------------------------------------

    def effective_model(self, default: Provider, default_model: str) -> tuple[Provider, str]:
        """The provider and model a step actually runs on, honouring ``model_override``.

        Read by anything that needs to know what will be called rather than what the
        contract declares — provider construction here, and the multi-step base's one
        client per distinct model, which would otherwise key on a model an override replaced.
        """
        override = self.config.model_override
        if override is not None and self._override_provider is not None:
            return self._override_provider, override.model
        return default, default_model

    def _dropped_temperature_note(self) -> str:
        """What the override warning adds when a declared temperature will not be sent.

        Said once, at construction, alongside the override warning §3.2 requires — not per
        call. Empty when the contract pins none, so the warning never claims to have
        dropped something that was never there.
        """
        pinned = sorted({s.temperature for s in self.contract.steps if s.temperature is not None})
        if not pinned:
            return ""
        # Rendered as the contract writes it — ``0``, not Python's ``0.0``.
        values = ", ".join(format_number(value) for value in pinned)
        return (
            f" The temperature its contract pins ({values}) is not sent: whether a model"
            " accepts one at all is that model's own property, so the override runs at the"
            " provider's default sampling and its results are not reproducible the way the"
            " default model's are."
        )

    def effective_temperature(self, declared: float | None) -> float | None:
        """The temperature to send for a step, honouring ``model_override``.

        A contract pins temperature for the model it declares, and which value is even
        *accepted* is a property of that model: the registry pins ``0`` for Haiku 4.5 and
        ``null`` for Opus 5, which rejects sampling parameters outright. An override
        replaces the model, so the declared value is no longer known-valid for what will
        actually run and is not carried across — §3 puts override quality in the caller's
        hands, and sending a parameter the override model refuses fails the call rather
        than degrading it.
        """
        return declared if self.config.model_override is None else None

    def _create_configured_provider(self, default: Provider, default_model: str) -> LLMProvider:
        """A provider for one step, honouring ``model_override`` when set."""
        provider, model = self.effective_model(default, default_model)
        return create_provider(
            ProviderConfig(
                type=provider,
                model=model,
                api_key=self.config.api_key_for(provider),
                max_retries=self.config.max_retries,
            )
        )

    # --- telemetry -----------------------------------------------------------------

    @contextmanager
    def _telemetry_run(self, provider: str) -> Iterator[TelemetryRun]:
        """Report the evaluation running inside this block, however it ends.

        One event per evaluation, assembled from what the block recorded on the
        :class:`TelemetryRun` it yields. Emission lives here rather than in each evaluator,
        so an evaluator reports by running its evaluation inside this block and an
        evaluator added later cannot stay silent.

        A failure emits an ``error`` event naming the error's class, then propagates
        untouched: nothing about the result, or the exception, depends on what telemetry
        did. ``BaseException`` — a cancellation, an interrupt — is left alone, because a
        process being torn down is not an evaluation outcome to report.

        :param provider: ``provider:model`` for the model that will be called, so a failure
            before any step runs still names one.
        """
        run = TelemetryRun(provider=provider)
        try:
            yield run
        except Exception as error:
            self._emit(run, status="error", error_code=type(error).__name__)
            raise
        self._emit(run, status="success")

    def _emit(
        self, run: TelemetryRun, *, status: EvaluationStatus, error_code: str | None = None
    ) -> None:
        """Send one event for *run*. Does nothing when telemetry is off."""
        if self._telemetry is None:
            return
        self._telemetry.send(
            TelemetryEvent(
                timestamp=utc_timestamp(),
                sdk_version=sdk_version(),
                evaluator_type=self.metadata.id,
                grade=run.grade,
                status=status,
                # Every raise from an evaluation is an exception with a class, so the class
                # name is always the code; there is no unknown-error case to stand in for.
                error_code=error_code,
                latency_ms=run.elapsed_ms,
                text_length_chars=run.text_length,
                provider=run.provider,
                token_usage=run.token_usage,
                stage_details=tuple(run.stages),
                model_override=True if self.config.model_override is not None else None,
            )
        )

    # --- evaluation ----------------------------------------------------------------

    @staticmethod
    def _raw_fields(input: Any, fields: Mapping[str, Any]) -> Any:
        """The caller's inputs, however they passed them, as one mapping to validate.

        Accepting either form and rejecting both at once is a programmer error rather than
        an evaluation failure, so it is raised as ``TypeError`` outside the error boundary.
        """
        if input is None:
            return dict(fields)
        if fields:
            raise TypeError("Pass the input model or keyword fields, not both.")
        if isinstance(input, BaseModel):
            return input.model_dump(by_alias=True)
        return input

    @abstractmethod
    async def evaluate(self, input: Any = None, /, **fields: Any) -> EvaluationResult[Any]:
        """Run one evaluation. Takes the contract's inputs by their canonical names."""

    def evaluate_sync(self, input: Any = None, /, **fields: Any) -> EvaluationResult[Any]:
        """Run :meth:`evaluate` to completion from synchronous code.

        :raises RuntimeError: if an asyncio event loop is already running in this thread;
            ``await evaluator.evaluate(...)`` there instead.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                "evaluate_sync() cannot be used while an asyncio event loop is running in "
                "this thread; use await evaluator.evaluate(...) from async code instead."
            ) from None
        return asyncio.run(self.evaluate(input, **fields))


__all__ = ["BaseEvaluator"]
