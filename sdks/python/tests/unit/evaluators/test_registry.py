"""Registry lookup by current and historical id, and the collision guard."""

from __future__ import annotations

import pytest

from learning_commons_evaluators import (
    BackgroundKnowledgeDemandsEvaluator,
    GradeLevelAppropriatenessEvaluator,
    MeaningDirectnessEvaluator,
    OrganizationalStructureEvaluator,
    PurposeClarityEvaluator,
    ReferenceKnowledgeDemandsEvaluator,
    RevisionAccuracyEvaluator,
    RevisionActionabilityEvaluator,
    RevisionManageabilityEvaluator,
    SentenceStructureEvaluator,
    StrengthAcknowledgmentEvaluator,
    StudentResponseSpecificityEvaluator,
    ToneAppropriatenessEvaluator,
    VocabularyComplexityEvaluator,
    WithholdingAnswersEvaluator,
    get_evaluator,
    get_evaluators,
)
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.registry import (
    EVALUATORS,
    get_evaluator_class,
    index_by_id,
)


def test_lists_every_evaluator_in_taxonomy_order() -> None:
    assert [m.id for m in get_evaluators()] == [
        "feedback.ela_writing.revision_accuracy",
        "feedback.ela_writing.revision_actionability",
        "feedback.ela_writing.revision_manageability",
        "feedback.ela_writing.strength_acknowledgment",
        "feedback.ela_writing.student_response_specificity",
        "feedback.ela_writing.tone_appropriateness",
        "feedback.ela_writing.withholding_answers",
        "text_complexity.ela_reading.background_knowledge_demands",
        "text_complexity.ela_reading.grade_level_appropriateness",
        "text_complexity.ela_reading.meaning_directness",
        "text_complexity.ela_reading.organizational_structure",
        "text_complexity.ela_reading.purpose_clarity",
        "text_complexity.ela_reading.reference_knowledge_demands",
        "text_complexity.ela_reading.sentence_structure",
        "text_complexity.ela_reading.vocabulary_complexity",
    ]
    assert [e.metadata for e in EVALUATORS] == list(get_evaluators())


def test_resolves_current_ids() -> None:
    assert (
        get_evaluator("text_complexity.ela_reading.purpose_clarity")
        is PurposeClarityEvaluator.metadata
    )
    assert (
        get_evaluator_class("feedback.ela_writing.tone_appropriateness")
        is ToneAppropriatenessEvaluator
    )


@pytest.mark.parametrize(
    ("old_id", "evaluator"),
    [
        ("grade-level-appropriateness", GradeLevelAppropriatenessEvaluator),
        ("subject-matter-knowledge", BackgroundKnowledgeDemandsEvaluator),
        ("conventionality", MeaningDirectnessEvaluator),
        ("literacy.gla.organizational_structure", OrganizationalStructureEvaluator),
        ("literacy.gla.intertextuality", ReferenceKnowledgeDemandsEvaluator),
        ("literacy.gla.purpose", PurposeClarityEvaluator),
        ("sentence-structure", SentenceStructureEvaluator),
        ("vocabulary", VocabularyComplexityEvaluator),
        (
            "feedback.productive_coaching_writing_feedback.is_tone_appropriate",
            ToneAppropriatenessEvaluator,
        ),
        (
            "feedback.productive_coaching_writing_feedback.is_appropriate_feedback",
            RevisionAccuracyEvaluator,
        ),
        (
            "feedback.productive_coaching_writing_feedback.is_actionable_revision",
            RevisionActionabilityEvaluator,
        ),
        (
            "feedback.productive_coaching_writing_feedback.is_manageable",
            RevisionManageabilityEvaluator,
        ),
        (
            "feedback.productive_coaching_writing_feedback.is_acknowledges_strength",
            StrengthAcknowledgmentEvaluator,
        ),
        (
            "feedback.productive_coaching_writing_feedback.is_anchored_in_student_response",
            StudentResponseSpecificityEvaluator,
        ),
        (
            "feedback.productive_coaching_writing_feedback.is_withholding_answers",
            WithholdingAnswersEvaluator,
        ),
    ],
)
def test_resolves_historical_ids_to_the_current_evaluator(
    old_id: str, evaluator: type[BaseEvaluator]
) -> None:
    resolved = get_evaluator(old_id)
    assert resolved is evaluator.metadata
    # Results carry only the current id; the old one is for lookup.
    assert resolved.id != old_id


def test_not_found_is_none_not_an_error() -> None:
    assert get_evaluator("nope") is None
    assert get_evaluator_class("nope") is None


def test_a_collision_between_a_history_entry_and_a_current_id_fails_loudly() -> None:
    class Impostor:
        metadata = type(
            "M",
            (),
            {"id": "grade-level-appropriateness", "id_history": (), "name": "Impostor Evaluator"},
        )()

    with pytest.raises(
        ValueError, match='Registry id "grade-level-appropriateness" is claimed by both'
    ):
        index_by_id([GradeLevelAppropriatenessEvaluator, Impostor])  # type: ignore[list-item]
