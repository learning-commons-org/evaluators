import { z } from 'zod';

/**
 * Vocabulary complexity levels matching Qual Text Complexity rubric (SAP)
 */
export const VocabularyComplexityLevel = z.enum([
  'slightly complex',
  'moderately complex',
  'very complex',
  'exceedingly complex',
]);

export type VocabularyComplexityLevel = z.infer<typeof VocabularyComplexityLevel>;

/**
 * Vocabulary complexity evaluation output
 * Ported from Python Output BaseModel
 */
export const VocabularyComplexitySchema = z.object({
  tier_2_words: z.string().describe('List of Tier 2 words (academic words)'),
  tier_3_words: z.string().describe('List of Tier 3 words (domain-specific)'),
  archaic_words: z.string().describe('List of Archaic words'),
  other_complex_words: z.string().describe('List of Other Complex words'),
  complexity_score: VocabularyComplexityLevel.describe(
    'The complexity of the text vocabulary'
  ),
  reasoning: z.string().describe('Detailed reasoning for the complexity rating'),
});

export type VocabularyComplexity = z.infer<typeof VocabularyComplexitySchema>;

/**
 * Background knowledge assumption for a student at a given grade level
 * This is generated in Stage 1 and used as input for Stage 2
 */
export interface BackgroundKnowledge {
  assumption: string;
  grade: string;
}
