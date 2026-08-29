// GENERATED — do not edit directly.
// Source: ../../evals/student-facing-text/ela-reading/sentence-structure/output_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

// prettier-ignore
export const SentenceStructureOutputSchema = z.object({ "complexity_score": z.enum(["slightly_complex","moderately_complex","very_complex","exceedingly_complex"]).describe("The sentence structure complexity level of the text."), "reasoning": z.string().describe("Detailed, pedagogically appropriate reasoning explaining how the qualitative structure and quantitative sentence statistics combine to produce the chosen complexity level.") }).strict();

export type SentenceStructureResult = z.infer<typeof SentenceStructureOutputSchema>;
