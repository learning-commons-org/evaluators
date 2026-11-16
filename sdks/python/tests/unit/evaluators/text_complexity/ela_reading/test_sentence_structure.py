"""Sentence Structure: grammatical counting, then classification against the grade's rubric."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel

from learning_commons_evaluators import (
    ModelOverride,
    Provider,
    SentenceStructureEvaluator,
    SentenceStructureInput,
    SentenceStructureOutput,
    read_outcome,
)
from learning_commons_evaluators.evaluators.text_complexity.ela_reading.sentence_structure import (
    SentenceAnalysis,
)
from learning_commons_evaluators.features import (
    add_engineered_features,
    compute_ground_truth_counts,
    features_to_json,
)
from tests.unit.conftest import ProviderFactory, sample_for

TEXT = "The cat sat on the mat. It was sleeping quietly in the warm afternoon sun."
#: What a grade 5 run reports: the grades 5-12 pair's model.
MODEL = "openai:gpt-5.5"

#: What the fake analysis step returns, so the derived features are predictable.
ANALYSIS = SentenceAnalysis.model_validate(
    {
        **{
            name: 2
            for name, field in SentenceAnalysis.model_fields.items()
            if field.annotation is int
        },
        **{
            name: 2.0
            for name, field in SentenceAnalysis.model_fields.items()
            if field.annotation is float
        },
        "reasoning": "synthetic sentence-length boundary case",
        "num_sentences": 25,
        "num_words": 299,
        "sentence_word_counts": [12] * 24 + [11],
        "num_subordinate_clauses": 1,
        "num_simple_transitions": 1,
        "num_sophisticated_transitions": 0,
    }
)


def scripted(schema: type[BaseModel]) -> BaseModel:
    """The analysis for step one, and a generated sample for the classification."""
    return ANALYSIS if schema is SentenceAnalysis else sample_for(schema)


@pytest.fixture
def providers() -> Any:
    from unittest.mock import patch

    factory = ProviderFactory(payload=scripted)
    with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
        yield factory


def test_metadata_is_the_contracts() -> None:
    metadata = SentenceStructureEvaluator.metadata
    assert metadata.id == "text_complexity.ela_reading.sentence_structure"
    assert metadata.id_history == ("sentence-structure",)
    # Both grade bands run on OpenAI models, so one vendor and one key.
    assert metadata.default_providers == (Provider.OPENAI,)
    assert metadata.supported_grades == tuple(str(g) for g in range(3, 13))


async def test_one_client_per_grade_bands_model(providers: ProviderFactory) -> None:
    await SentenceStructureEvaluator(openai_api_key="o").evaluate(text=TEXT, grade_level=5)
    # Two steps per band on one model each, so a client for each band and no more.
    assert sorted(p.config.model for p in providers.created) == ["gpt-5.5", "gpt-6-luna"]
    assert [c["schema"] for c in providers.calls] == [SentenceAnalysis, SentenceStructureOutput]


@pytest.mark.parametrize(
    ("grade", "band", "model"),
    [
        (3, "grades_3_4", "gpt-6-luna"),
        (4, "grades_3_4", "gpt-6-luna"),
        (5, "grades_5_12", "gpt-5.5"),
        (12, "grades_5_12", "gpt-5.5"),
    ],
)
async def test_a_grade_runs_its_own_bands_pair_of_steps_on_that_bands_model(
    providers: ProviderFactory, grade: int, band: str, model: str
) -> None:
    # Grades 3-4 and grades 5-12 are two evaluators in one contract: validated on different
    # texts, and so on different models. Exactly one band's analysis and classification run.
    evaluation = await SentenceStructureEvaluator(openai_api_key="o").evaluate(
        text=TEXT, grade_level=grade
    )
    assert [c["model"] for c in providers.calls] == [model, model]
    assert [c["schema"] for c in providers.calls] == [SentenceAnalysis, SentenceStructureOutput]
    assert evaluation.metadata.model == f"openai:{model}"
    plan = SentenceStructureEvaluator(openai_api_key="o")._plan({"grade_level": str(grade)})
    assert [step.id for step in plan] == [
        f"sentence_analysis_{band}",
        f"classify_complexity_{band}",
    ]


@pytest.mark.parametrize("grade", [3, 5])
async def test_every_step_sends_the_reasoning_effort_it_was_validated_at(
    providers: ProviderFactory, grade: int
) -> None:
    # Both models rate texts harder at their default effort; "none" is the validated value,
    # and no temperature is pinned alongside it.
    await SentenceStructureEvaluator(openai_api_key="o").evaluate(text=TEXT, grade_level=grade)
    assert [c["reasoning_effort"] for c in providers.calls] == ["none", "none"]
    assert [c["temperature"] for c in providers.calls] == [None, None]


async def test_an_override_does_not_carry_the_reasoning_effort_across(
    providers: ProviderFactory,
) -> None:
    # The value was validated for the declared model; whether another model takes the
    # parameter at all is that model's own property, as with temperature.
    override = ModelOverride(provider=Provider.OPENAI, model="gpt-4.1")
    evaluator = SentenceStructureEvaluator(openai_api_key="o", model_override=override)
    await evaluator.evaluate(text=TEXT, grade_level=5)
    assert [c["model"] for c in providers.calls] == ["gpt-4.1", "gpt-4.1"]
    assert [c["reasoning_effort"] for c in providers.calls] == [None, None]


async def test_an_injected_provider_is_not_handed_the_reasoning_effort() -> None:
    # The keyword is OpenAI's; a caller's own provider may not take it, and what that
    # provider does with a prompt is already the caller's to answer for.
    from learning_commons_evaluators.providers import ProviderConfig
    from tests.unit.conftest import FakeProvider

    injected = FakeProvider(ProviderConfig(type=Provider.OPENAI, model="m"), scripted)
    evaluator = SentenceStructureEvaluator(llm_provider=injected, telemetry=False)
    await evaluator.evaluate(text=TEXT, grade_level=3)
    assert [c["reasoning_effort"] for c in injected.calls] == [None, None]


async def test_the_analysis_step_reads_the_textstat_counts(providers: ProviderFactory) -> None:
    await SentenceStructureEvaluator(openai_api_key="o").evaluate(text=TEXT, grade_level=5)
    analysis = providers.calls[0]
    user = analysis["messages"][1]["content"]
    assert compute_ground_truth_counts(TEXT) in user
    assert TEXT in user


async def test_the_classification_step_reads_the_features_derived_from_the_analysis(
    providers: ProviderFactory,
) -> None:
    await SentenceStructureEvaluator(openai_api_key="o").evaluate(text=TEXT, grade_level=5)
    user = providers.calls[1]["messages"][1]["content"]
    expected = features_to_json(
        add_engineered_features(ANALYSIS.model_dump(), round_values=False), floor_values=True
    )
    assert expected in user
    # Floor the raw ratio 299/25 = 11.96, without rounding it up to 12 first.
    assert json.loads(expected)["avg_words_per_sentence"] == 11
    assert json.loads(expected)["avg_subordinates_per_sentence"] == 0
    assert json.loads(expected)["avg_transitions_per_sentence"] == 0
    assert TEXT in user


@pytest.mark.parametrize(
    ("grade", "count_name", "numerator", "denominator", "expected", "boundary", "at_or_above"),
    [
        (3, "num_sentences_with_subordinate", 624, 2500, 24, 25, False),
        (3, "num_sentences_with_subordinate", 449, 1000, 44, 45, False),
        (3, "num_sentences_with_subordinate", 1124, 2500, 44, 45, False),
        (3, "num_sentences_with_subordinate", 45, 100, 45, 45, True),
        (3, "num_simple_sentences", 1499, 2500, 59, 60, False),
        (3, "num_simple_sentences", 3, 5, 60, 60, True),
        (3, "num_simple_sentences", 121, 200, 60, 60, True),
        (4, "num_sentences_with_subordinate", 749, 2500, 29, 30, False),
        (4, "num_sentences_with_subordinate", 1249, 2500, 49, 50, False),
        (4, "num_sentences_with_subordinate", 1, 2, 50, 50, True),
        (4, "num_sentences_with_multiple_subordinates", 199, 2500, 7, 8, False),
        (4, "num_sentences_with_multiple_subordinates", 2, 25, 8, 8, True),
    ],
)
async def test_percentage_boundaries_in_classification_request(
    providers: ProviderFactory,
    monkeypatch: pytest.MonkeyPatch,
    grade: int,
    count_name: str,
    numerator: int,
    denominator: int,
    expected: int,
    boundary: int,
    at_or_above: bool,
) -> None:
    # Mock the grammatical counts, then inspect the real classification request.
    # In particular, 44.9 catches TS whole-number rounding; 44.96 and 59.96
    # catch rounding to one decimal before truncation in either SDK.
    monkeypatch.setitem(
        globals(),
        "ANALYSIS",
        ANALYSIS.model_copy(
            update={
                "num_sentences": denominator,
                "num_words": denominator * 10,
                "sentence_word_counts": [10] * denominator,
                count_name: numerator,
            }
        ),
    )
    await SentenceStructureEvaluator(openai_api_key="o").evaluate(text=TEXT, grade_level=grade)
    user = providers.calls[1]["messages"][1]["content"]
    features = json.loads(user.split("# TEXT STATISTICS\n", 1)[1])
    feature_name = count_name.replace("num_", "percent_", 1)
    assert features[feature_name] == expected
    assert (features[feature_name] >= boundary) is at_or_above
    assert (features[feature_name] < boundary) is (not at_or_above)
    assert any(
        f"`{feature_name}`" in line and f">= {boundary}%" in line for line in user.splitlines()
    )
    # The mocked final label is not evidence of LLM accuracy. This test guards
    # the numbers and inclusive cutoff instructions that the classifier receives.


@pytest.mark.parametrize(
    ("grade", "marker"),
    [(3, "rubric-grade-3.txt"), (4, "rubric-grade-4.txt"), (9, "rubric-grades-5-12.txt")],
)
async def test_the_rubric_for_the_grade_is_the_one_the_contract_names(
    providers: ProviderFactory, grade: int, marker: str
) -> None:
    await SentenceStructureEvaluator(openai_api_key="o").evaluate(text=TEXT, grade_level=grade)
    rubric = SentenceStructureEvaluator.contract.document(marker)
    user = providers.calls[1]["messages"][1]["content"]
    assert f"# GRADE {grade} RUBRIC\n{rubric}" in user
    assert "avg_sentence_length" not in user
    if grade in (3, 4):
        assert rubric.count("avg_words_per_sentence") == 4
        assert "typically between " not in rubric
        assert " > " not in rubric
        assert ">= " in rubric


async def test_returns_the_classification_as_the_result(providers: ProviderFactory) -> None:
    evaluator = SentenceStructureEvaluator(openai_api_key="o")
    evaluation = await evaluator.evaluate(SentenceStructureInput(text=TEXT, grade_level=5))
    assert isinstance(evaluation.result, SentenceStructureOutput)
    assert evaluation.metadata.model == MODEL
    assert read_outcome(evaluation, evaluator.metadata.outcome).score in {
        "slightly_complex",
        "moderately_complex",
        "very_complex",
        "exceedingly_complex",
    }
    # Both steps' tokens, added: the intermediate call costs the caller too.
    assert evaluation.metadata.token_usage.input_tokens == 14


def test_the_analysis_model_covers_every_feature_the_classifier_is_given() -> None:
    from learning_commons_evaluators.features import FEATURE_COLS

    derived = add_engineered_features(ANALYSIS.model_dump())
    assert set(FEATURE_COLS) <= set(derived), set(FEATURE_COLS) - set(derived)
