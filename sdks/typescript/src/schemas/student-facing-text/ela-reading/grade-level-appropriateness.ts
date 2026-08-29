import { z } from 'zod';

/**
 * Valid grade bands for grade level appropriateness evaluation
 */
export const GradeBand = z.enum(['K-1', '2-3', '4-5', '6-8', '9-10', '11-CCR']);

export type GradeBand = z.infer<typeof GradeBand>;

/**
 * Output schema for Grade Level Appropriateness evaluation
 * Matches Python OutputRanges model
 */
export const GradeLevelAppropriatenessOutputSchema = z.object({
  reasoning: z
    .string()
    .describe(
      'Your reasoning for your answer in numbered bullet points for 4 steps with a 4th bullet point for synthesis.'
    ),
  grade_band: GradeBand.describe('Target grade band for the text at independent reading.'),
  alternative_grade_band: GradeBand.describe(
    'A second grade band that could read and comprehend the text with the scaffolding named in scaffolding_needed, or as a read-aloud.',
  ),
  scaffolding_needed: z
    .string()
    .describe('Scaffolding needed for the text to be appropriate for the alternative grade'),
});

export type GradeLevelAppropriatenessInternal = z.infer<typeof GradeLevelAppropriatenessOutputSchema>;
