"""The six feedback evaluators ported in Phase 4, which differ only in their key features.

Tone Appropriateness, the pilot, has its own file covering the family's flow in depth. These
six declare the same contract shape — two texts in, a binary ``quality_score`` out, one call
on OpenAI — so a per-evaluator file would be the same test written six times. What actually
distinguishes them is the set of criteria their ``key_features`` object carries, and which
schema module each class is wired to; both are checked here against the contract.
"""

from __future__ import annotations

import pytest

from learning_commons_evaluators import (
    InputValidationError,
    Provider,
    RevisionAccuracyEvaluator,
    RevisionActionabilityEvaluator,
    RevisionManageabilityEvaluator,
    StrengthAcknowledgmentEvaluator,
    StudentResponseSpecificityEvaluator,
    WithholdingAnswersEvaluator,
    get_evaluator,
    read_outcome,
)
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from tests.unit.conftest import ProviderFactory

STUDENT = "Some people think AI-powered pets are a good alternative to real pets."
FEEDBACK = "That's true. Now be more specific: what makes them more affordable?"

#: Each evaluator with the legacy id it must still answer to. The key features are read off
#: the contract rather than repeated here — restating them would just copy the registry.
FAMILY: list[tuple[type[BaseEvaluator], str]] = [
    (RevisionAccuracyEvaluator, "is_appropriate_feedback"),
    (RevisionActionabilityEvaluator, "is_actionable_revision"),
    (RevisionManageabilityEvaluator, "is_manageable"),
    (StrengthAcknowledgmentEvaluator, "is_acknowledges_strength"),
    (StudentResponseSpecificityEvaluator, "is_anchored_in_student_response"),
    (WithholdingAnswersEvaluator, "is_withholding_answers"),
]

CASES = pytest.mark.parametrize(
    ("evaluator", "legacy"), FAMILY, ids=lambda v: v if isinstance(v, str) else v.metadata.slug
)


@CASES
def test_identity_and_the_legacy_id_it_answers_to(
    evaluator: type[BaseEvaluator], legacy: str
) -> None:
    metadata = evaluator.metadata
    assert metadata.id == f"feedback.ela_writing.{metadata.slug}"
    assert metadata.id_history == (f"feedback.productive_coaching_writing_feedback.{legacy}",)
    assert get_evaluator(metadata.id_history[0]) is metadata
    assert metadata.default_providers == (Provider.OPENAI,)
    assert metadata.outcome is not None and metadata.outcome.score == "quality_score"


@CASES
def test_key_features_are_this_evaluators_own(evaluator: type[BaseEvaluator], legacy: str) -> None:
    """The one thing that differs across the six, so the one place a mis-wiring would hide.

    Six classes built from one template can easily name a sibling's schema module; the
    generic conformance checks would not notice, because every model in the family has the
    same four top-level fields. The nested criteria are what tell them apart.
    """
    assert issubclass(evaluator, SingleStepEvaluator)
    declared = evaluator.contract.output_schema["$defs"]["KeyFeatures"]["properties"]
    features = evaluator.output_model.model_fields["key_features"].annotation
    assert features is not None
    assert list(features.model_fields) == list(declared)  # type: ignore[attr-defined]


@CASES
async def test_binds_both_texts_and_nothing_else(
    providers: ProviderFactory, evaluator: type[BaseEvaluator], legacy: str
) -> None:
    instance = evaluator(openai_api_key="k")
    await instance.evaluate(student_text=STUDENT, feedback_text=FEEDBACK)
    [system, user] = providers.last.calls[0]["messages"]
    assert system["content"] == instance.contract.document("system.txt")
    assert user["content"] == instance.contract.document("user.txt").replace(
        "{student_text}", STUDENT
    ).replace("{feedback_text}", FEEDBACK)
    assert providers.last.calls[0]["temperature"] == 1


@CASES
async def test_both_texts_are_required_and_a_grade_is_not_accepted(
    providers: ProviderFactory, evaluator: type[BaseEvaluator], legacy: str
) -> None:
    instance = evaluator(openai_api_key="k")
    with pytest.raises(InputValidationError, match="student_text is required."):
        await instance.evaluate(feedback_text=FEEDBACK)
    with pytest.raises(InputValidationError, match="feedback_text is required."):
        await instance.evaluate(student_text=STUDENT)
    # The family judges feedback, not a text against a grade; §4.2 grade validation only
    # exists where the contract declares a grade, and these do not.
    with pytest.raises(InputValidationError, match='Unknown input "grade_level"'):
        await instance.evaluate(student_text=STUDENT, feedback_text=FEEDBACK, grade_level=8)


@CASES
async def test_returns_a_binary_verdict_on_the_contracts_model(
    providers: ProviderFactory, evaluator: type[BaseEvaluator], legacy: str
) -> None:
    instance = evaluator(openai_api_key="k")
    evaluation = await instance.evaluate(student_text=STUDENT, feedback_text=FEEDBACK)
    assert evaluation.evaluator == evaluator.metadata.id
    assert evaluation.metadata.model == "openai:gpt-5.4-2026-03-05"
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {"0", "1"}


def test_strength_acknowledgment_keeps_the_american_spelling() -> None:
    # D7: the registry id, the module path and the class name all use "acknowledgment".
    assert StrengthAcknowledgmentEvaluator.metadata.id.endswith("strength_acknowledgment")
    assert StrengthAcknowledgmentEvaluator.__name__ == "StrengthAcknowledgmentEvaluator"
    assert "acknowledgement" not in StrengthAcknowledgmentEvaluator.__module__
