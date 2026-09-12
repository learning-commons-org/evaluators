"""Evaluator configuration (SDK spec §3): one flat config for every evaluator.

Credentials are passed explicitly; the SDK never reads them from the environment (§3.1).
Which keys an evaluator needs is derived from its contract, so a missing one is a
``ConfigurationError`` at construction, before any I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

from learning_commons_evaluators.providers.base import Provider


@dataclass(frozen=True)
class ModelOverride:
    """Run every LLM step of an evaluator on this provider and model instead (§3.2).

    Both fields are required. The override replaces the evaluator's provider-derived key
    requirement with the override provider's; a rejected model id surfaces as
    ``ConfigurationError`` when the provider answers. Evaluators are validated against
    their default models only, so a warning is logged once at construction.
    """

    provider: Provider
    model: str


@dataclass(frozen=True)
class TelemetryOptions:
    """Granular telemetry settings (§3). Emission lands with the telemetry phase."""

    enabled: bool = True
    #: Include verbatim caller inputs in telemetry events. Off by default.
    record_raw_inputs: bool = False
    #: Opt in to identified telemetry, attributed to this Learning Commons user.
    learning_commons_api_key: str | None = None


@dataclass(frozen=True)
class EvaluatorConfig:
    """What an evaluator takes at construction.

    Fields are the spec's canonical names (§2.1 casing is the identity in Python). Pass
    it whole, or pass the same fields as keyword arguments to the evaluator constructor.
    """

    google_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    #: Authorizes Learning Commons API calls such as the Knowledge Graph. Identified
    #: telemetry is opted into separately via ``telemetry.learning_commons_api_key``.
    learning_commons_api_key: str | None = None
    model_override: ModelOverride | None = None
    #: Retries on retryable errors; total attempts are ``1 + max_retries``. ``0`` disables.
    max_retries: int = 2
    #: ``True`` / ``False`` shorthand, or a :class:`TelemetryOptions`.
    telemetry: bool | TelemetryOptions = True

    def credential(self, canonical_key: str) -> str | None:
        """The value of a canonical credential key (e.g. ``"openai_api_key"``), or ``None``.

        Rendering a canonical key as a config field is the mechanical casing map of §2.1,
        which in Python is the identity — so no per-key table.
        """
        value = getattr(self, canonical_key, None)
        return value if isinstance(value, str) else None

    def api_key_for(self, provider: Provider) -> str | None:
        return self.credential(f"{provider.value}_api_key")

    @property
    def telemetry_options(self) -> TelemetryOptions:
        """``telemetry`` with the boolean shorthands resolved."""
        if self.telemetry is True:
            return TelemetryOptions()
        if self.telemetry is False:
            return TelemetryOptions(enabled=False)
        return self.telemetry


__all__ = ["EvaluatorConfig", "ModelOverride", "TelemetryOptions"]
