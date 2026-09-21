"""Static facts about an evaluator, read from its contract once at class creation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from learning_commons_evaluators.contracts.loader import DeclaredOutcome
from learning_commons_evaluators.providers.base import Provider

if TYPE_CHECKING:
    from learning_commons_evaluators.contracts.loader import Contract


@dataclass(frozen=True)
class EvaluatorMetadata:
    """Every evaluator class carries one of these as ``metadata``."""

    #: Current dotted registry id, e.g. ``text_complexity.ela_reading.purpose_clarity``.
    #: Appears in results and telemetry. May be renamed — the name is not the identity.
    id: str
    #: Immutable UUID assigned at the evaluator's creation; survives renames.
    stable_id: str
    #: Prior ``id`` values, oldest first, so old names remain resolvable.
    id_history: tuple[str, ...]
    name: str
    description: str
    #: The grades the evaluator is built for, as its contract declares them. Not a
    #: validation set: where a ``grade_level`` input exists, its schema enum is what
    #: rejects a bad value, and a grade-free evaluator still reports what it targets.
    supported_grades: tuple[str, ...]
    #: Which output properties carry the verdict and its rationale; ``None`` for an
    #: evaluator whose output is not a single judgement.
    outcome: DeclaredOutcome | None
    #: Canonical config keys for non-LLM services the evaluator calls (never LLM keys,
    #: which follow ``default_providers`` and are replaced by a model override).
    required_credentials: tuple[str, ...]
    #: Providers the evaluator's default configuration calls, in step order.
    default_providers: tuple[Provider, ...]

    @classmethod
    def from_contract(
        cls, contract: Contract, default_providers: Sequence[Provider]
    ) -> EvaluatorMetadata:
        """Everything static an evaluator publishes, read straight off its contract.

        ``default_providers`` is the one fact the contract does not state directly: which
        steps an evaluator actually runs is the evaluator's own decision, so each base
        derives the providers from the steps it will call and passes them in.
        """
        return cls(
            id=contract.evaluator.id,
            stable_id=contract.evaluator.stable_id,
            id_history=tuple(contract.evaluator.id_history),
            name=contract.evaluator.name,
            description=contract.evaluator.description,
            supported_grades=tuple(contract.evaluator.supported_grades),
            outcome=contract.outcome,
            required_credentials=tuple(contract.required_credentials),
            default_providers=tuple(default_providers),
        )

    @property
    def slug(self) -> str:
        return self.id.rsplit(".", 1)[-1]

    @property
    def label(self) -> str:
        """The name as logs say it: the contract names every evaluator "<Thing> Evaluator"."""
        return self.name.removesuffix(" Evaluator")


__all__ = ["EvaluatorMetadata"]
