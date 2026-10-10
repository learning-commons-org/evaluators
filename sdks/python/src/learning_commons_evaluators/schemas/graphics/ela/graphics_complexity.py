# GENERATED — do not edit directly.
# Source: evals/graphics/ela/graphics-complexity/output_schema.json
#         evals/graphics/ela/graphics-complexity/input_schema.json
# Regenerate: make generate-contracts
"""Input and output models for the Graphics Complexity Evaluator."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVALUATOR_ID = "graphics.ela.graphics_complexity"


#: Accepted values of ``grade_level``, as the input schema declares them.
GRADE_LEVEL_VALUES: tuple[str, ...] = (
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
    "12",
)


class GraphicsComplexityInput(BaseModel):
    """Inputs to the Graphics Complexity Evaluator, named as its input_schema.json declares them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="The passage to evaluate.")
    grade_level: int = Field(description="Target student grade level.")
    image_paths: list[str] = Field(description="One local image path per graphic in scope, in the order they should be considered. Each file is checked against the `x-image` bounds before any model call; an image outside them is rejected, not resized.")
    figure_labels: str | None = Field(default=None, description="Optional comma-separated labels matching the order of `image_paths` (e.g. 'Figure 1, Figure 2'). If omitted, graphics are auto-labeled 'Image 1', 'Image 2', etc.")


class DetailedSummaryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    factor: str = Field(description="The specific text complexity factor identified.")
    description: str = Field(description="How this factor manifests in the text.")
    effect_on_complexity_dimension: str = Field(description="How this factor affects the reader's ability to understand the text's specific complexity dimension.")


class ScaffoldingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scaffolding_need: str = Field(description="The complexity factor that requires scaffolding.")
    suggestion: str = Field(description="A specific instructional strategy to support students with this factor.")


class UseCaseItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunity: str = Field(description="An instructional opportunity related to the text.")
    suggestion: str = Field(description="A specific way to leverage this text for that instructional purpose.")


class GraphicsComplexityDetails(BaseModel):
    """Practical instructional details including scaffolding strategies and recommended use cases."""

    model_config = ConfigDict(extra="forbid")

    detailed_summary: list[DetailedSummaryItem] = Field(description="Individual graphics complexity factors with descriptions and their effects.")
    adjustment_and_scaffolding: list[ScaffoldingItem] = Field(description="Scaffolding strategies to make the text's graphics accessible at the target grade.")
    recommended_use_cases: list[UseCaseItem] = Field(description="Additional instructional opportunities for using this text's graphics.")


class GraphicAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(description="The supplied figure label identifying this graphic.")
    role: Literal["decorative", "supporting", "extending", "complicating"] = Field(description="This graphic's relationship to the surrounding text.")
    demand_notes: str = Field(description="What drives this graphic's demand: density, layering, interpretive elements, abstraction.")
    complexity: Literal["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex", "more_context_needed"] = Field(description="This graphic's own rating.")


class JointReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applies: bool = Field(description="True only if the reader must hold two or more graphics together to use either. Several graphics on a page is not by itself a joint reading.")
    which: list[str] = Field(description="The labels read together (at least two) when applies is true; otherwise empty.")
    complexity: Literal["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex"] | None = Field(description="The grouping rated as one thing. Null when applies is false.")
    reasoning: str = Field(description="What the reader has to carry from one graphic to the other.")


class GraphicsComplexityResponse(BaseModel):
    """What the Graphics Complexity Evaluator asks the model for: its output plus the working fields output_schema.json marks ``x-model-only``."""

    model_config = ConfigDict(extra="forbid")

    complexity_score: Literal["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex", "more_context_needed"] = Field(description="The Graphics Complexity level for the target grade, or `more_context_needed` when the excerpt gives no graphic to rate.")
    reasoning: str = Field(description="A high-level summary of why the text is at this graphics complexity level for the target grade.")
    details: GraphicsComplexityDetails
    graphics: list[GraphicAssessment] = Field(description="Exactly one entry per attached image, in the supplied order.")
    joint_reading: JointReading
    aggregation_rule: Literal["highest_individual", "joint_reading"] = Field(description="Which rule produced complexity_score.")


class GraphicsComplexityOutput(BaseModel):
    """Output of the Graphics Complexity Evaluator, per its output_schema.json, without the fields it marks ``x-model-only``."""

    model_config = ConfigDict(extra="forbid")

    complexity_score: Literal["slightly_complex", "moderately_complex", "very_complex", "exceedingly_complex", "more_context_needed"] = Field(description="The Graphics Complexity level for the target grade, or `more_context_needed` when the excerpt gives no graphic to rate.")
    reasoning: str = Field(description="A high-level summary of why the text is at this graphics complexity level for the target grade.")
    details: GraphicsComplexityDetails


__all__ = [
    "GraphicsComplexityInput",
    "GraphicsComplexityOutput",
    "GraphicsComplexityResponse",
]
