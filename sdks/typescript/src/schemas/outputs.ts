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
  evaluatorVersion?: string;
  model: string;
  processingTimeMs: number;
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
 * Error type for failed evaluations
 */
export interface EvaluationError {
  error: string;
  input: {
    text: string;
    grade?: string;
  };
  timestamp: Date;
}

/**
 * Batch evaluation result
 */
export interface BatchEvaluationResult<T = EvaluationResult> {
  results: Array<T | EvaluationError>;
  summary: BatchSummary;
}
