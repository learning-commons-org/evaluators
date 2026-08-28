import { z } from 'zod';
import { TextComplexityLevel } from './outputs.js';

/**
 * Vocabulary evaluation output schema
 */
export const VocabularyComplexityOutputSchema = z.object({
  tier_2_words: z.string().describe('List of Tier 2 words (academic words)'),
  tier_3_words: z.string().describe('List of Tier 3 words (domain-specific)'),
  archaic_words: z.string().describe('List of Archaic words'),
  other_complex_words: z.string().describe('List of Other Complex words'),
  complexity_score: TextComplexityLevel.describe(
    'The complexity of the text vocabulary'
  ),
  reasoning: z.string().describe('Detailed reasoning for the complexity rating'),
});

export type VocabularyComplexityInternal = z.infer<typeof VocabularyComplexityOutputSchema>;

/**
 * Background knowledge assumption for a student at a given grade level
 * This is generated in Stage 1 and used as input for Stage 2
 */
export interface BackgroundKnowledge {
  assumption: string;
  gradeLevel: string;
}
