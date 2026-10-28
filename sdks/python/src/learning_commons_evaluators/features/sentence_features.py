"""The ratios the sentence-structure contract derives from its first step's counts.

The first step returns raw grammatical counts; the second is asked to classify against a
rubric written in terms of percentages and averages. Turning the former into the latter is
arithmetic, so the contract declares it as preprocessing (``sentence_features``) rather
than asking a model for it, and this module is that computation.

Every derived value is rounded to one place here. The classifier preserves that fractional
place so per-sentence averages and phrase densities below one remain meaningful.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

#: The features the classifier prompt receives, in the order it receives them. Both SDKs
#: and the notebook this evaluator comes from use this list; the prompt's rubric names
#: these keys, so the set and its order are part of the contract with the model.
FEATURE_COLS: tuple[str, ...] = (
    # Foundational & distributional
    "avg_words_per_sentence",
    "sentence_length_variation",
    "percent_short_sentences",
    "percent_medium_sentences",
    "percent_long_sentences",
    "percent_very_long_sentences",
    "flesch_kincaid_grade",
    # Sentence structure (grammatical type)
    "percent_simple_sentences",
    "percent_compound_sentences",
    "percent_complex_sentences",
    "percent_compound_complex_sentences",
    "percent_other_sentences",
    # Word distribution
    "percent_words_in_simple_sentences",
    "percent_words_in_complex_sentences",
    "percent_words_in_compound_sentences",
    "percent_words_in_compound_complex_sentences",
    "percent_words_in_other_sentences",
    # Clausal & subordination
    "avg_subordinates_per_sentence",
    "avg_clauses_per_sentence",
    "percent_sentences_with_subordinate",
    "percent_sentences_with_multiple_subordinates",
    "percent_sentences_with_embedded_clauses",
    # Phrase density
    "prep_phrase_density",
    "participle_phrase_density",
    "appositive_phrase_density",
    # Cohesion & transitions
    "avg_transitions_per_sentence",
    "percent_sophisticated_transitions",
    # Conceptual & other
    "percent_sentences_w_one_concept",
    "percent_sentences_w_multi_concept",
    "percent_cleft_sentences",
    "max_clauses_in_any_sentence",
    # Grades 5-12
    "num_sentences",
    "num_simple_sentences",
    "num_compound",
    "num_basic_complex",
    "num_advanced_complex",
    "percentage_simple",
    "percentage_compound",
    "percentage_basic_complex",
    "percentage_advanced_complex",
)

#: Upper bound, in words, of each sentence-length bucket. The last bucket is open-ended.
_LENGTH_BUCKETS: tuple[tuple[str, int | None], ...] = (
    ("percent_short_sentences", 10),
    ("percent_medium_sentences", 20),
    ("percent_long_sentences", 30),
    ("percent_very_long_sentences", None),
)

#: Derived name -> counted name, as a percentage of the sentence count.
_PERCENT_OF_SENTENCES: Mapping[str, str] = {
    "percent_simple_sentences": "num_simple_sentences",
    "percent_compound_sentences": "num_compound_sentences",
    "percent_complex_sentences": "num_complex_sentences",
    "percent_compound_complex_sentences": "num_compound_complex_sentences",
    "percent_other_sentences": "num_other_sentences",
    "percent_sentences_with_subordinate": "num_sentences_with_subordinate",
    "percent_sentences_with_multiple_subordinates": "num_sentences_with_multiple_subordinates",
    "percent_sentences_with_embedded_clauses": "num_sentences_with_embedded_clauses",
    "percent_sentences_w_one_concept": "num_one_concept_sentences",
    "percent_sentences_w_multi_concept": "num_multi_concept_sentences",
    "percent_cleft_sentences": "num_cleft_sentences",
}

#: Derived name -> counted name, as a percentage of the word count.
_PERCENT_OF_WORDS: Mapping[str, str] = {
    "percent_words_in_simple_sentences": "words_in_simple_sentences",
    "percent_words_in_complex_sentences": "words_in_complex_sentences",
    "percent_words_in_compound_sentences": "words_in_compound_sentences",
    "percent_words_in_compound_complex_sentences": "words_in_compound_complex_sentences",
    "percent_words_in_other_sentences": "words_in_other_sentences",
    "prep_phrase_density": "num_prepositional_phrases",
    "participle_phrase_density": "num_participle_phrases",
    "appositive_phrase_density": "num_appositive_phrases",
}

#: Derived name -> counted name, as a per-sentence average.
_PER_SENTENCE: Mapping[str, str] = {
    "avg_words_per_sentence": "num_words",
    "avg_subordinates_per_sentence": "num_subordinate_clauses",
    "avg_clauses_per_sentence": "num_total_clauses",
}

#: Places every derived value is rounded to before it reaches the prompt.
PRECISION = 1


def _count(analysis: Mapping[str, Any], name: str) -> float:
    """One count from the analysis, as a number. A missing or null count reads as zero."""
    value = analysis.get(name)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _ratio(numerator: float, denominator: float) -> float:
    """``numerator / denominator``, or zero — an empty passage divides by no sentences."""
    return 0.0 if denominator == 0 else numerator / denominator


def _population_stdev(values: Sequence[float]) -> float:
    """Population standard deviation; zero for fewer than two values, as variation of one."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _sentence_word_counts(analysis: Mapping[str, Any]) -> list[float]:
    raw = analysis.get("sentence_word_counts")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [float(value) for value in raw if isinstance(value, (int, float))]


def _length_distribution(word_counts: Sequence[float]) -> dict[str, float]:
    """The share of sentences in each length bucket; all zero when there are no sentences.

    The buckets partition the sentences, so the four shares always sum to 100: each takes
    everything at or below its bound that an earlier bucket did not claim.
    """
    if not word_counts:
        return {name: 0.0 for name, _ in _LENGTH_BUCKETS}

    distribution: dict[str, float] = {}
    remaining = list(word_counts)
    for name, upper in _LENGTH_BUCKETS:
        in_bucket = remaining if upper is None else [c for c in remaining if c <= upper]
        remaining = [] if upper is None else [c for c in remaining if c > upper]
        distribution[name] = len(in_bucket) / len(word_counts) * 100
    return distribution


def add_engineered_features(analysis: Mapping[str, Any]) -> dict[str, Any]:
    """The analysis plus every feature derived from it, each rounded to one place.

    Takes the first step's output as a mapping and returns a new one; the counts are copied
    through unchanged, because the classifier prompt asks for several of them alongside the
    ratios (see :data:`FEATURE_COLS`).
    """
    features = dict(analysis)
    sentences = _count(analysis, "num_sentences")
    words = _count(analysis, "num_words")
    word_counts = _sentence_word_counts(analysis)

    derived: dict[str, float] = {
        **{name: _ratio(_count(analysis, of), sentences) for name, of in _PER_SENTENCE.items()},
        **{
            name: _ratio(_count(analysis, of), sentences) * 100
            for name, of in _PERCENT_OF_SENTENCES.items()
        },
        **{
            name: _ratio(_count(analysis, of), words) * 100
            for name, of in _PERCENT_OF_WORDS.items()
        },
        **_length_distribution(word_counts),
        "sentence_length_variation": _population_stdev(word_counts),
    }

    # Transitions are the one pair measured against each other rather than against the
    # sentence or word count: how many of the transitions used were the sophisticated ones.
    transitions = _count(analysis, "num_simple_transitions") + _count(
        analysis, "num_sophisticated_transitions"
    )
    derived["avg_transitions_per_sentence"] = _ratio(transitions, sentences)
    derived["percent_sophisticated_transitions"] = (
        _ratio(_count(analysis, "num_sophisticated_transitions"), transitions) * 100
    )

    # Preserve the notebook's ties-to-even rounding; cross-SDK rounding alignment
    # is tracked separately in DSCR-2223.
    features.update({name: round(value, PRECISION) for name, value in derived.items()})
    return features


def features_to_json(features: Mapping[str, Any], *, cast_to_int: bool = True) -> str:
    """:data:`FEATURE_COLS` as the JSON object bound to ``{sentence_features}``.

    Set ``cast_to_int=False`` to retain one decimal place for the classifier, including
    averages and densities below one. The default preserves the legacy serializer API.
    A feature the analysis did not produce is sent as ``null`` rather than zero.
    """
    payload: dict[str, int | float | None] = {}
    for name in FEATURE_COLS:
        value = features.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            payload[name] = None
        elif isinstance(value, int):
            payload[name] = value
        else:
            payload[name] = int(value) if cast_to_int else round(value, PRECISION)
    return json.dumps(payload, indent=2)


__all__ = [
    "FEATURE_COLS",
    "PRECISION",
    "add_engineered_features",
    "features_to_json",
]
