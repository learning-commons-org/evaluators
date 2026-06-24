import { z } from 'zod';

// Each LC evaluation echoes back the KG identifier of the LC it evaluated.
// The evaluator verifies this matches what was sent — detecting silent mismatches.
export const LCEvaluationSchema = z.object({
  lc_id: z.string(),
  reasoning: z.string(),
  aligned: z.boolean(),
  feedback: z.string(),
});

export const BatchedLCEvaluationSchema = z.object({
  evaluations: z.array(LCEvaluationSchema),
});

export const CoarseFilterEntrySchema = z.object({
  standard: z.string(),
  relevant: z.boolean(),
});

export const CoarseFilterSchema = z.object({
  standards: z.array(CoarseFilterEntrySchema),
});

export type LCEvaluation = z.infer<typeof LCEvaluationSchema>;
export type BatchedLCEvaluation = z.infer<typeof BatchedLCEvaluationSchema>;
export type CoarseFilterEntry = z.infer<typeof CoarseFilterEntrySchema>;
export type CoarseFilterResult = z.infer<typeof CoarseFilterSchema>;
