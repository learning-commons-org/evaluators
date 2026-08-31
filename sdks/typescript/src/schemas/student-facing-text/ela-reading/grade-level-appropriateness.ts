// GENERATED — do not edit directly.
// Source: ../../evals/student-facing-text/ela-reading/grade-level-appropriateness/output_schema.json
//         ../../evals/student-facing-text/ela-reading/grade-level-appropriateness/input_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

/** What this evaluator accepts, from its input schema. */
export type GradeLevelAppropriatenessInput = {
  /** The passage to evaluate. Note this evaluator takes no grade input — it determines which grade band the text suits. Bounds mirror the SDK text input spec (sdks/settings/grade-level-appropriateness/settings.toml: min_text_length / max_text_length). */
  "text": string;
};

// prettier-ignore
export const GradeLevelAppropriatenessOutputSchema = z.object({ "reasoning": z.string().describe("Numbered bullet points for each of the 3 analysis steps (quantitative, qualitative, background knowledge), followed by a 4th bullet point called 'synthesis'."), "grade_band": z.enum(["K-1","2-3","4-5","6-8","9-10","11-12"]).describe("Target grade band for the text at independent reading."), "alternative_grade_band": z.enum(["K-1","2-3","4-5","6-8","9-10","11-12"]).describe("A second grade band that could read and comprehend the text with the scaffolding named in scaffolding_needed, or as a read-aloud."), "scaffolding_needed": z.string().describe("The types of scaffolding (picture, graph, additional context, vocabulary pre-teaching, ...) that make the text accessible at alternative_grade_band.") }).strict();

export type GradeLevelAppropriatenessResult = z.infer<typeof GradeLevelAppropriatenessOutputSchema>;
