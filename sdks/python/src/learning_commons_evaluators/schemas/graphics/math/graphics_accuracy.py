# GENERATED — do not edit directly.
# Source: evals/graphics/math/graphics-accuracy/output_schema.json
#         evals/graphics/math/graphics-accuracy/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Graphics Accuracy Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "graphics.math.graphics_accuracy"


class GraphicsAccuracyInput(BaseModel):
    """Inputs to the Graphics Accuracy Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    image_paths: list[str] = Field(description="Local path to the image under review (absolute, or relative to the working directory), as a one-item array. Read in the caller's environment; format identified by file signature, not extension. The `x-image` bounds are enforced before any model call; an image outside them is rejected, not resized.")
    claim: str = Field(description="The specification the image is checked against: a statement about what it shows (\"The chart shows 12 apples.\"), or a question with its expected answer as `Question: \"<question>\" The answer is <answer>.`")


class GraphicsAccuracyOutput(BaseModel):
    """Output of the Graphics Accuracy Evaluator, per its output_schema.json."""

    model_config = ConfigDict(extra="forbid")

    observed: str = Field(description="Describe only what is literally in the image. For every countable feature relevant to the specification (dots, bars, sides, vertices, tiles, segments, arrows, cubes, petals), enumerate them with explicit labels and commit to a single integer count.")
    defects: list[str] = Field(description="Every defect in the image itself, anywhere in the frame and whether or not the specification depends on it: missing, cut-off, covered, illegible or garbled labels, numbers or axes; tick or gridline spacing that does not match its labels; parts shown as equal that are unequal; drawn sizes that contradict printed values; parts that do not add up to their stated total; a figure that does not match the question. A label that can be read more than one way is a defect. A schematic drawing is not a defect unless it contradicts its own labels. Empty when the image is sound.")
    reasoning: str = Field(description="Derive, from scratch, the value or result the image yields for the specification's question, using the counts and structure in observed together with any facts the question states in words. Do not fault the image for omitting facts the question supplies in text. Show the computation. No appeals to memorized knowledge. No hedging language (\"plausible\", \"appears to match\", \"consistent as a possibility\").")
    errors: list[str] = Field(description="Every way the image fails to show what the specification requires: what the image shows, and what was required instead. If the derivation could not be completed, what in the image could not be read or resolved. Empty when the image is correct.")
    correction: str = Field(description="What the image actually shows — the value or result your derivation produced — independently of the specification. If derivation is incomplete, say \"derivation incomplete\".")
    basis: Literal["supported", "contradicted", "unverified", "defective"] = Field(description="defective: defects is not empty; takes precedence. supported: derivation completed and X equals Y. contradicted: derivation completed and X differs from Y. unverified: the derivation could not be completed from the image together with the question's stated facts, or hedging was needed; the image was not shown wrong, but not shown right either. Consistency alone is never \"supported\".")
    is_correct: bool = Field(description="Set LAST, after writing the explicit \"The image yields X; the specification states Y; therefore is_correct = ___\" sentence in your reasoning. True only when basis is \"supported\" (which requires defects to be empty); false for \"defective\", \"contradicted\" and \"unverified\".")


__all__ = [
    "GraphicsAccuracyInput",
    "GraphicsAccuracyOutput",
]
