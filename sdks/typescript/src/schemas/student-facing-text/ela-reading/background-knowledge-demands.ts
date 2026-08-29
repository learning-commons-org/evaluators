// GENERATED — do not edit directly.
// Source: ../../evals/student-facing-text/ela-reading/background-knowledge-demands/output_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

// prettier-ignore
export const BackgroundKnowledgeDemandsOutputSchema = z.object({ "identified_topics": z.array(z.string()).describe("The core subjects/concepts found in the text."), "curriculum_check": z.string().describe("Whether the topics are standard K-8 knowledge or specialized high-school-level knowledge."), "assumptions_and_scaffolding": z.string().describe("What the author assumes the reader already knows versus what is explained in the text."), "friction_analysis": z.string().describe("Whether difficulty comes from vocabulary/sentence structure or from actual background knowledge demands."), "complexity_score": z.enum(["slightly_complex","moderately_complex","very_complex","exceedingly_complex"]).describe("The background knowledge complexity level of the text."), "reasoning": z.string().describe("A detailed synthesis of why the text fits the chosen complexity level.") }).strict();

export type BackgroundKnowledgeDemandsResult = z.infer<typeof BackgroundKnowledgeDemandsOutputSchema>;
