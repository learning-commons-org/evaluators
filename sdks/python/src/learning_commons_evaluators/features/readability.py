"""Deterministic text counts a contract binds to a prompt.

``textstat`` is the library every contract names under ``implementation.python``, so the
counts here are textstat's. They are deliberately not the TypeScript SDK's, which the same
contracts bind to ``compromise`` + ``syllable`` under ``implementation.typescript``: the
registry declares one implementation per language and the two disagree on syllables, so a
cross-SDK prompt comparison masks every value computed here (SDK spec §10.4).
"""

from __future__ import annotations

from dataclasses import dataclass

import textstat

from learning_commons_evaluators.features.preprocessing import format_number, round_half_up


@dataclass(frozen=True)
class ReadabilityCounts:
    """What ``textstat`` counts in one passage."""

    sentence_count: int
    word_count: int
    character_count: int
    syllable_count: int
    #: Rounded to two places by the same rule the contracts' ``post_transform`` applies
    #: to ``fk_score``, so one SDK never rounds one quantity two ways.
    flesch_kincaid_grade: float


def readability_counts(text: str) -> ReadabilityCounts:
    """Count ``text`` the way the sentence-structure notebook counted it.

    Each call is the textstat function the notebook used, with its arguments: words exclude
    punctuation and characters exclude spaces, which is what makes the numbers comparable
    to the ones the prompt's examples were written against.
    """
    return ReadabilityCounts(
        sentence_count=textstat.sentence_count(text),
        word_count=textstat.lexicon_count(text, removepunct=True),
        character_count=textstat.char_count(text, ignore_spaces=True),
        syllable_count=textstat.syllable_count(text),
        flesch_kincaid_grade=round_half_up(textstat.flesch_kincaid_grade(text), 2),
    )


def compute_ground_truth_counts(text: str) -> str:
    """The block the sentence-structure contract binds to ``{ground_truth_counts}``.

    The prompt tells the model to treat these as a reference rather than a constraint, and
    reads them as ``name: value`` lines, so the field names and their order are part of the
    prompt's contract rather than a display choice.
    """
    counts = readability_counts(text)
    return "\n".join(
        [
            f"num_sentences: {counts.sentence_count}",
            f"num_words: {counts.word_count}",
            f"num_char: {counts.character_count}",
            f"num_syllable: {counts.syllable_count}",
            f"flesch_kincaid_grade: {format_number(counts.flesch_kincaid_grade)}",
        ]
    )


__all__ = ["ReadabilityCounts", "compute_ground_truth_counts", "readability_counts"]
