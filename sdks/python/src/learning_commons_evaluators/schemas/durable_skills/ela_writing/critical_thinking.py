# GENERATED — do not edit directly.
# Source: evals/durable-skills/ela-writing/critical-thinking/output_schema.json
#         evals/durable-skills/ela-writing/critical-thinking/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Critical Thinking Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "durable_skills.ela_writing.critical_thinking"


class SourcePassage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1)
    author: str | None = Field(default=None, min_length=1)
    text: str = Field(min_length=1)


class CriticalThinkingInput(BaseModel):
    """Inputs to the Critical Thinking Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    assignment_text: str = Field(description="The writing assignment / prompt given to the student.")
    source_passages: list[SourcePassage] = Field(description="Source passages in the order the student received them. Position is the source number: the first item is Source 1, the second is Source 2, and so on. The SDK does not sort or renumber this list. When a passage has no title or author, that number is a valid way for the student to name it.")
    essay_text: str = Field(description="The student's essay, verbatim (may contain spelling/grammar errors).")


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quote: str = Field(description="A verbatim substring of the essay text, including any original spelling/grammar errors.")
    comment: str = Field(description="Why this excerpt matters for this indicator.")


# Ordered rating level, lowest to highest.
Level = Literal["not_evident", "exploring", "analyzing", "integrating", "extending"]


class Indicator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: list[Evidence] = Field(description="Verbatim quote/comment pairs supporting the rating. At least one for any indicator rated above not_evident; may be empty for not_evident.")
    reasoning: str = Field(description="2–5 sentences explaining the rating against the rubric cells and decision rules. Produced before the rating.")
    rating: Level


class Indicators(BaseModel):
    """One property per rated indicator, keyed by indicator id: synthesizing_sources = 2.1, evidence_strength = 2.2, counterarguments = 3.1, facts_over_opinions = 3.2, drawing_conclusions = 4.1. The last four are always rated. synthesizing_sources is rated only when source_count > 1; when source_count is 1 it is omitted entirely."""

    model_config = ConfigDict(extra="forbid")

    synthesizing_sources: Indicator | None = None
    evidence_strength: Indicator
    counterarguments: Indicator
    facts_over_opinions: Indicator
    drawing_conclusions: Indicator


class CriticalThinkingOutput(BaseModel):
    """Output of the Critical Thinking Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    indicators: Indicators = Field(description="One property per rated indicator, keyed by indicator id: synthesizing_sources = 2.1, evidence_strength = 2.2, counterarguments = 3.1, facts_over_opinions = 3.2, drawing_conclusions = 4.1. The last four are always rated. synthesizing_sources is rated only when source_count > 1; when source_count is 1 it is omitted entirely.")
    reasoning: str = Field(description="How the median was formed over the indicator ratings, and any tie handling.")
    critical_thinking_score: Level = Field(description="The headline Critical Thinking rating, formed last as the median of the indicator ratings.")


__all__ = [
    "CriticalThinkingInput",
    "CriticalThinkingOutput",
]
