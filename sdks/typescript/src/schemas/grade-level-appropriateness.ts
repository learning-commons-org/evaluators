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
export const GradeLevelAppropriatenessSchema = z.object({
  reasoning: z
    .string()
    .describe(
      'Your reasoning for your answer in numbered bullet points for 4 steps with a 4th bullet point for synthesis.'
    ),
  grade: GradeBand.describe('The appropriate grade level for the text'),
  alternative_grade: GradeBand.describe('An alternative grade level for the text'),
  scaffolding_needed: z
    .string()
    .describe('Scaffolding needed for the text to be appropriate for the alternative grade'),
});

export type GradeLevelAppropriateness = z.infer<typeof GradeLevelAppropriatenessSchema>;
