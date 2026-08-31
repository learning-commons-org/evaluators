// GENERATED — do not edit directly.
// Source: ../../evals/student-facing-text/ela-reading/meaning-directness/output_schema.json
//         ../../evals/student-facing-text/ela-reading/meaning-directness/input_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

/** What this evaluator accepts, from its input schema. */
export type MeaningDirectnessInput = {
  /** The passage to evaluate. Bounds mirror the SDK text input spec (sdks/settings/conventionality/settings.toml: min_text_length / max_text_length). */
  "text": string;
  /** Target student grade level. */
  "grade_level": "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12";
};

// prettier-ignore
export const MeaningDirectnessOutputSchema = z.object({ "reasoning": z.string().describe("A detailed explanation of the rating, citing specific features in the text and referencing the expert guardrails (e.g., noting if the text relies on abstract qualities/rhetorical idealization, if vocabulary/background knowledge demands make a literal text vague for the grade level, or if it is strictly concrete/procedural)."), "complexity_score": z.enum(["slightly_complex","moderately_complex","very_complex","exceedingly_complex"]).describe("The conventionality complexity level of the text."), "conventionality_features": z.array(z.string()).describe("The specific language features driving the complexity (e.g., literal narrative, concrete actions, less familiar expressions, sustained irony, abstract qualities, rhetorical idealization, archaic phrasing) with direct quotes from the text."), "grade_context": z.string().describe("How the conventionality demands compare to general expectations for the provided target grade."), "instructional_insights": z.string().describe("Actionable pedagogical suggestions for scaffolding the conventionality features in the classroom.") }).strict();

export type MeaningDirectnessResult = z.infer<typeof MeaningDirectnessOutputSchema>;
