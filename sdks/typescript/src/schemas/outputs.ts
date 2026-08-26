import { z } from 'zod';

/**
 * Shared complexity levels used across all text complexity evaluators
 * (Vocabulary, Sentence Structure, and any future sub-evaluators)
 */
export const TextComplexityLevel = z.enum([
  'Slightly complex',
  'Moderately complex',
  'Very complex',
  'Exceedingly complex',
]);

export type TextComplexityLevel = z.infer<typeof TextComplexityLevel>;

/**
 * Metadata attached to all evaluation results
 */
export interface EvaluationMetadata {
  model: string;
  processingTimeMs: number;
  inputTokens: number;
  outputTokens: number;
}

/**
 * Base evaluation result structure
 */
export interface EvaluationResult<TScore = string, TInternal = unknown> {
  score: TScore;
  reasoning: string;
  metadata: EvaluationMetadata;
  _internal?: TInternal;
}

/**
 * Batch evaluation summary statistics
 */
export interface BatchSummary {
  total: number;
  successful: number;
  failed: number;
  averageProcessingTimeMs: number;
}

/**
 * A failed slot in a batch result. Named to leave `EvaluationError` free for the
 * canonical error class.
 */
export interface EvaluationFailure {
  error: string;
  input: {
    text: string;
    gradeLevel?: string;
  };
}

/**
 * Batch evaluation result
 */
export interface BatchEvaluationResult<T = EvaluationResult> {
  results: Array<T | EvaluationFailure>;
  summary: BatchSummary;
}
