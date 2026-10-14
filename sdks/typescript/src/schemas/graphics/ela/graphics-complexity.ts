// GENERATED — do not edit directly.
// Source: ../../evals/graphics/ela/graphics-complexity/output_schema.json
//         ../../evals/graphics/ela/graphics-complexity/input_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

/** What this evaluator accepts, from its input schema. */
export type GraphicsComplexityInput = {
  /** The passage to evaluate. */
  "text": string;
  /** Target student grade level. */
  "grade_level": "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12";
  /** One local image path per graphic in scope, in the order they should be considered. Each file is checked against the `x-image` bounds before any model call; an image outside them is rejected, not resized. */
  "image_paths": string[];
  /** Optional comma-separated labels matching the order of `image_paths` (e.g. 'Figure 1, Figure 2'). If omitted, graphics are auto-labeled 'Image 1', 'Image 2', etc. */
  "figure_labels"?: string;
};

/** What the model is asked for: the output plus the working fields its contract marks `x-model-only`. */
// prettier-ignore
export const GraphicsComplexityResponseSchema = z.object({ "complexity_score": z.enum(["slightly_complex","moderately_complex","very_complex","exceedingly_complex","more_context_needed"]).describe("The Graphics Complexity level for the target grade, or `more_context_needed` when the excerpt gives no graphic to rate."), "reasoning": z.string().describe("A high-level summary of why the text is at this graphics complexity level for the target grade."), "details": z.object({ "detailed_summary": z.array(z.object({ "factor": z.string().describe("The specific text complexity factor identified."), "description": z.string().describe("How this factor manifests in the text."), "effect_on_complexity_dimension": z.string().describe("How this factor affects the reader's ability to understand the text's specific complexity dimension.") }).strict()).describe("Individual graphics complexity factors with descriptions and their effects."), "adjustment_and_scaffolding": z.array(z.object({ "scaffolding_need": z.string().describe("The complexity factor that requires scaffolding."), "suggestion": z.string().describe("A specific instructional strategy to support students with this factor.") }).strict()).describe("Scaffolding strategies to make the text's graphics accessible at the target grade."), "recommended_use_cases": z.array(z.object({ "opportunity": z.string().describe("An instructional opportunity related to the text."), "suggestion": z.string().describe("A specific way to leverage this text for that instructional purpose.") }).strict()).describe("Additional instructional opportunities for using this text's graphics.") }).strict().describe("Practical instructional details including scaffolding strategies and recommended use cases."), "graphics": z.array(z.object({ "label": z.string().describe("The supplied figure label identifying this graphic."), "role": z.enum(["decorative","supporting","extending","complicating"]).describe("This graphic's relationship to the surrounding text."), "demand_notes": z.string().describe("What drives this graphic's demand: density, layering, interpretive elements, abstraction."), "complexity": z.enum(["slightly_complex","moderately_complex","very_complex","exceedingly_complex","more_context_needed"]).describe("This graphic's own rating.") }).strict()).describe("Exactly one entry per attached image, in the supplied order."), "joint_reading": z.object({ "applies": z.boolean().describe("True only if the reader must hold two or more graphics together to use either. Several graphics on a page is not by itself a joint reading."), "which": z.array(z.string()).describe("The labels read together (at least two) when applies is true; otherwise empty."), "complexity": z.union([z.literal("slightly_complex"), z.literal("moderately_complex"), z.literal("very_complex"), z.literal("exceedingly_complex"), z.literal(null)]).describe("The grouping rated as one thing. Null when applies is false."), "reasoning": z.string().describe("What the reader has to carry from one graphic to the other.") }).strict(), "aggregation_rule": z.enum(["highest_individual","joint_reading"]).describe("Which rule produced complexity_score.") }).strict();

/** What the caller receives: the response without its `x-model-only` fields. */
export const GraphicsComplexityOutputSchema = GraphicsComplexityResponseSchema.omit({ "graphics": true, "joint_reading": true, "aggregation_rule": true });

export type GraphicsComplexityResult = z.infer<typeof GraphicsComplexityOutputSchema>;
