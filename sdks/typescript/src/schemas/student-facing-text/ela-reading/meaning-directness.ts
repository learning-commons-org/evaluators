// GENERATED — do not edit directly.
// Source: ../../evals/student-facing-text/ela-reading/meaning-directness/output_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

// prettier-ignore
export const MeaningDirectnessOutputSchema = z.object({ "reasoning": z.string().describe("A detailed explanation of the rating, citing specific features in the text and referencing the expert guardrails (e.g., noting if the text relies on abstract qualities/rhetorical idealization, if vocabulary/background knowledge demands make a literal text vague for the grade level, or if it is strictly concrete/procedural)."), "complexity_score": z.enum(["slightly_complex","moderately_complex","very_complex","exceedingly_complex"]).describe("The conventionality complexity level of the text."), "conventionality_features": z.array(z.string()).describe("The specific language features driving the complexity (e.g., literal narrative, concrete actions, less familiar expressions, sustained irony, abstract qualities, rhetorical idealization, archaic phrasing) with direct quotes from the text."), "grade_context": z.string().describe("How the conventionality demands compare to general expectations for the provided target grade."), "instructional_insights": z.string().describe("Actionable pedagogical suggestions for scaffolding the conventionality features in the classroom.") }).strict();

export type MeaningDirectnessResult = z.infer<typeof MeaningDirectnessOutputSchema>;
