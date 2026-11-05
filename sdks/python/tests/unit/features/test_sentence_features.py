"""The ratios derived from the sentence-structure analysis, and their JSON form."""

from __future__ import annotations

import json
from typing import Any

import pytest

from learning_commons_evaluators.features.sentence_features import (
    FEATURE_COLS,
    add_engineered_features,
    features_to_json,
)

#: An analysis of four sentences, chosen so every derived family has a non-trivial value.
ANALYSIS: dict[str, Any] = {
    "reasoning": "...",
    "num_sentences": 4,
    "num_words": 80,
    "flesch_kincaid_grade": 6.42,
    "num_simple_sentences": 1,
    "num_compound_sentences": 1,
    "num_complex_sentences": 1,
    "num_compound_complex_sentences": 1,
    "num_other_sentences": 0,
    "num_independent_clauses": 6,
    "num_subordinate_clauses": 3,
    "num_total_clauses": 9,
    "num_sentences_with_subordinate": 2,
    "num_sentences_with_multiple_subordinates": 1,
    "num_sentences_with_embedded_clauses": 1,
    "num_prepositional_phrases": 8,
    "num_participle_phrases": 2,
    "num_appositive_phrases": 1,
    "num_simple_transitions": 3,
    "num_sophisticated_transitions": 1,
    "words_in_simple_sentences": 8,
    "words_in_compound_sentences": 16,
    "words_in_complex_sentences": 24,
    "words_in_compound_complex_sentences": 32,
    "words_in_other_sentences": 0,
    "sentence_word_counts": [8, 16, 24, 32],
    "num_one_concept_sentences": 1,
    "num_multi_concept_sentences": 3,
    "num_cleft_sentences": 0,
    "max_clauses_in_any_sentence": 4,
    "num_compound": 1,
    "num_basic_complex": 1,
    "num_advanced_complex": 1,
    "percentage_simple": 25.0,
    "percentage_compound": 25.0,
    "percentage_basic_complex": 25.0,
    "percentage_advanced_complex": 25.0,
}


def test_the_counts_come_through_unchanged() -> None:
    features = add_engineered_features(ANALYSIS)
    assert {k: features[k] for k in ANALYSIS} == ANALYSIS


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("avg_words_per_sentence", 20.0),
        ("avg_subordinates_per_sentence", 0.8),
        ("avg_clauses_per_sentence", 2.2),
        ("percent_simple_sentences", 25.0),
        ("percent_words_in_compound_complex_sentences", 40.0),
        ("prep_phrase_density", 10.0),
        ("participle_phrase_density", 2.5),
        # Of the transitions used, not of the sentences: 1 of 4 was sophisticated.
        ("avg_transitions_per_sentence", 1.0),
        ("percent_sophisticated_transitions", 25.0),
        ("percent_sentences_w_multi_concept", 75.0),
        # 8 and 16 words are short and medium; 24 is long; 32 is very long.
        ("percent_short_sentences", 25.0),
        ("percent_medium_sentences", 25.0),
        ("percent_long_sentences", 25.0),
        ("percent_very_long_sentences", 25.0),
        ("sentence_length_variation", 8.9),
    ],
)
def test_each_derived_family_is_computed_and_rounded_to_one_place(
    name: str, expected: float
) -> None:
    assert add_engineered_features(ANALYSIS)[name] == expected


def test_the_length_buckets_partition_the_sentences() -> None:
    features = add_engineered_features(
        {**ANALYSIS, "sentence_word_counts": [0, 10, 11, 20, 21, 30, 31]}
    )
    shares = [
        features[name]
        for name in (
            "percent_short_sentences",
            "percent_medium_sentences",
            "percent_long_sentences",
            "percent_very_long_sentences",
        )
    ]
    assert sum(shares) == pytest.approx(100, abs=0.4)


def test_an_empty_passage_divides_by_no_sentences_instead_of_failing() -> None:
    empty = {"num_sentences": 0, "num_words": 0, "sentence_word_counts": []}
    features = add_engineered_features(empty)
    assert features["avg_words_per_sentence"] == 0
    assert features["percent_simple_sentences"] == 0
    assert features["percent_sophisticated_transitions"] == 0
    assert features["sentence_length_variation"] == 0


def test_the_json_carries_every_feature_column_in_order() -> None:
    payload = json.loads(features_to_json(add_engineered_features(ANALYSIS)))
    assert list(payload) == list(FEATURE_COLS)


def test_every_value_is_a_whole_number_truncated_not_rounded() -> None:
    features = add_engineered_features(ANALYSIS)
    payload = json.loads(features_to_json(features))
    assert all(isinstance(v, int) for v in payload.values())
    # 8.9 -> 8 and 6.42 -> 6: this is the notebook's arithmetic, and the rubric thresholds
    # this evaluator was validated against were produced by it.
    assert payload["sentence_length_variation"] == 8
    assert payload["flesch_kincaid_grade"] == 6


def test_a_feature_the_analysis_did_not_produce_is_null_rather_than_zero() -> None:
    payload = json.loads(features_to_json({}))
    assert set(payload) == set(FEATURE_COLS)
    assert all(value is None for value in payload.values())


@pytest.mark.parametrize("boundary", [12, 13, 16, 17, 19, 22, 25, 30, 40, 45, 50, 55, 60])
@pytest.mark.parametrize("offset", [-0.04, 0, 0.04])
def test_flooring_preserves_integer_boundary_comparisons(boundary: int, offset: float) -> None:
    raw = boundary + offset
    payload = json.loads(features_to_json({"avg_words_per_sentence": raw}, floor_values=True))
    floored = payload["avg_words_per_sentence"]
    assert (floored < boundary) == (raw < boundary)
    assert (floored >= boundary) == (raw >= boundary)


def test_floor_uses_the_unrounded_ratio_and_handles_negative_values() -> None:
    analysis = {**ANALYSIS, "num_sentences": 25, "num_words": 299, "flesch_kincaid_grade": -0.4}
    raw = add_engineered_features(analysis, round_values=False)
    assert raw["avg_words_per_sentence"] == 11.96
    payload = json.loads(features_to_json(raw, floor_values=True))
    assert payload["avg_words_per_sentence"] == 11
    assert payload["flesch_kincaid_grade"] == -1
    assert payload["avg_subordinates_per_sentence"] == 0
    # The legacy helper still rounds, and its serializer still truncates.
    assert add_engineered_features(analysis)["avg_words_per_sentence"] == 12.0
    assert json.loads(features_to_json(raw))["flesch_kincaid_grade"] == 0
