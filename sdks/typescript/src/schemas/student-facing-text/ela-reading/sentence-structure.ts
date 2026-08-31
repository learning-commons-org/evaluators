// GENERATED — do not edit directly.
// Source: ../../evals/student-facing-text/ela-reading/sentence-structure/output_schema.json
//         ../../evals/student-facing-text/ela-reading/sentence-structure/input_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

/** What this evaluator accepts, from its input schema. */
export type SentenceStructureInput = {
  /** The passage to evaluate. */
  "text": string;
  /** Target student grade level. Selects which of the three rubric_grade_* preprocessing entries supplies {rubric}. */
  "grade_level": "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12";
};

// prettier-ignore
export const SentenceStructureOutputSchema = z.object({ "complexity_score": z.enum(["slightly_complex","moderately_complex","very_complex","exceedingly_complex"]).describe("The sentence structure complexity level of the text."), "reasoning": z.string().describe("Detailed, pedagogically appropriate reasoning explaining how the qualitative structure and quantitative sentence statistics combine to produce the chosen complexity level.") }).strict();

export type SentenceStructureResult = z.infer<typeof SentenceStructureOutputSchema>;
