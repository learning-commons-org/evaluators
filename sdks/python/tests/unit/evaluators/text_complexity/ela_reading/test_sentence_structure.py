"""Sentence Structure: grammatical counting, then classification against the grade's rubric."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel

from learning_commons_evaluators import (
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
MODEL = "openai:gpt-4o-2024-08-06"

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
        "reasoning": "two sentences",
        "num_sentences": 2,
        "num_words": 20,
        "sentence_word_counts": [6, 14],
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
    # Both steps run on the same OpenAI model, so one vendor and one key.
    assert metadata.default_providers == (Provider.OPENAI,)
    assert metadata.supported_grades == tuple(str(g) for g in range(3, 13))


async def test_both_steps_share_one_client(providers: ProviderFactory) -> None:
    await SentenceStructureEvaluator(openai_api_key="o").evaluate(text=TEXT, grade_level=5)
    assert len(providers.created) == 1
    assert [c["schema"] for c in providers.calls] == [SentenceAnalysis, SentenceStructureOutput]


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
    expected = features_to_json(add_engineered_features(ANALYSIS.model_dump()))
    assert expected in user
    # Derived, not passed through: 20 words over 2 sentences, truncated for the prompt.
    assert json.loads(expected)["avg_words_per_sentence"] == 10
    assert TEXT in user


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
