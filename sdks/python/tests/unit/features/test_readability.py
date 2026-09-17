"""The textstat counts the sentence-structure contract binds to ``{ground_truth_counts}``."""

from __future__ import annotations

import textstat

from learning_commons_evaluators.features.preprocessing import round_half_up
from learning_commons_evaluators.features.readability import (
    compute_ground_truth_counts,
    readability_counts,
)

TEXT = "The cat sat on the mat. It was sleeping quietly in the warm afternoon sun."


def test_counts_are_textstats_own() -> None:
    counts = readability_counts(TEXT)
    assert counts.sentence_count == textstat.sentence_count(TEXT)
    # Words exclude punctuation and characters exclude spaces, as the notebook counted them.
    assert counts.word_count == textstat.lexicon_count(TEXT, removepunct=True)
    assert counts.character_count == textstat.char_count(TEXT, ignore_spaces=True)
    assert counts.syllable_count == textstat.syllable_count(TEXT)
    # The SDK's one rounding rule, the same one the contracts' post_transform applies to
    # fk_score, so no evaluator rounds this quantity differently from another.
    assert counts.flesch_kincaid_grade == round_half_up(textstat.flesch_kincaid_grade(TEXT), 2)


def test_the_block_is_the_five_lines_the_prompt_reads_in_order() -> None:
    counts = readability_counts(TEXT)
    assert compute_ground_truth_counts(TEXT).splitlines() == [
        f"num_sentences: {counts.sentence_count}",
        f"num_words: {counts.word_count}",
        f"num_char: {counts.character_count}",
        f"num_syllable: {counts.syllable_count}",
        f"flesch_kincaid_grade: {counts.flesch_kincaid_grade}",
    ]


def test_an_integral_score_renders_without_a_trailing_zero() -> None:
    # As JavaScript's String(number) renders it, so both SDKs bind the same characters.
    text = "Cats nap."
    expected = round(textstat.flesch_kincaid_grade(text), 2)
    rendered = compute_ground_truth_counts(text).splitlines()[-1]
    assert (
        rendered
        == f"flesch_kincaid_grade: {int(expected) if float(expected).is_integer() else expected}"
    )


def test_an_empty_passage_counts_zero_rather_than_failing() -> None:
    assert compute_ground_truth_counts("").startswith("num_sentences: 0")
