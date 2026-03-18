import { z } from 'zod';
import { TextComplexityLevel } from './outputs.js';

/**
 * Subject Matter Knowledge evaluation output schema
 */
export const SmkOutputSchema = z.object({
  identified_topics: z.array(z.string()).describe('List of major subjects/concepts found in the text.'),
  curriculum_check: z.string().describe('Whether the topics are standard K-8 or specialized high school level.'),
  assumptions_and_scaffolding: z.string().describe('What the author assumes the reader knows vs. what is explained.'),
  friction_analysis: z.string().describe('Whether difficulty comes from vocabulary/structure or actual knowledge demands.'),
  complexity_score: TextComplexityLevel.describe('The subject matter knowledge complexity level of the text'),
  reasoning: z.string().describe('A brief synthesis of why the text fits the chosen complexity level.'),
});

export type SmkInternal = z.infer<typeof SmkOutputSchema>;
