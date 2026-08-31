// GENERATED — do not edit directly.
// Source: ../../evals/student-facing-text/ela-reading/reference-knowledge-demands/output_schema.json
//         ../../evals/student-facing-text/ela-reading/reference-knowledge-demands/input_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

/** What this evaluator accepts, from its input schema. */
export type ReferenceKnowledgeDemandsInput = {
  /** The passage to evaluate. */
  "text": string;
  /** Target student grade level. */
  "grade_level": "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12";
};

// prettier-ignore
export const ReferenceKnowledgeDemandsOutputSchema = z.object({ "complexity_score": z.enum(["slightly_complex","moderately_complex","very_complex","exceedingly_complex"]).describe("The Reference Knowledge Demands complexity level for the target grade."), "reasoning": z.string().describe("A high-level summary of why the text is at this complexity level for the target grade."), "details": z.object({ "detailed_summary": z.array(z.object({ "factor": z.string().describe("The specific text complexity factor identified."), "description": z.string().describe("How this factor manifests in the text."), "effect_on_complexity_dimension": z.string().describe("How this factor affects the reader's ability to understand the text's specific complexity dimension.") }).strict()).describe("Individual complexity factors with descriptions and their effects."), "adjustment_and_scaffolding": z.array(z.object({ "scaffolding_need": z.string().describe("The complexity factor that requires scaffolding."), "suggestion": z.string().describe("A specific instructional strategy to support students with this factor.") }).strict()).describe("Scaffolding strategies to make the text accessible at the target grade."), "recommended_use_cases": z.array(z.object({ "opportunity": z.string().describe("An instructional opportunity related to the text."), "suggestion": z.string().describe("A specific way to leverage this text for that instructional purpose.") }).strict()).describe("Additional instructional opportunities for using this text.") }).strict().describe("Practical instructional details including scaffolding strategies and recommended use cases.") }).strict();

export type ReferenceKnowledgeDemandsResult = z.infer<typeof ReferenceKnowledgeDemandsOutputSchema>;
