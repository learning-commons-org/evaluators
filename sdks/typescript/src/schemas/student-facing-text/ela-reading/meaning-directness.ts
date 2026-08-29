import { z } from 'zod';
import { TextComplexityLevel } from '../../outputs.js';

/**
 * Meaning Directness evaluation output schema
 */
export const MeaningDirectnessOutputSchema = z.object({
  conventionality_features: z.array(z.string()).describe('The specific language features driving the complexity (e.g., literal narrative, concrete actions, sustained irony, abstract qualities) with direct quotes from the text.'),
  grade_context: z.string().describe('How the conventionality demands compare to general expectations for the provided target grade.'),
  instructional_insights: z.string().describe('Actionable pedagogical suggestions for scaffolding the conventionality features in the classroom.'),
  complexity_score: TextComplexityLevel.describe('The conventionality complexity level of the text'),
  reasoning: z.string().describe('A detailed explanation of the rating, citing specific features in the text and referencing the expert guardrails.'),
});

export type MeaningDirectnessResult = z.infer<typeof MeaningDirectnessOutputSchema>;
