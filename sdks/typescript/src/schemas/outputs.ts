import { z } from 'zod';

/**
 * Complexity levels for sentence structure evaluation
 */
export const ComplexityLevel = z.enum([
  'Slightly Complex',
  'Moderately Complex',
  'Very Complex',
  'Exceedingly Complex',
]);

export type ComplexityLevel = z.infer<typeof ComplexityLevel>;

/**
 * Grade levels for vocabulary evaluation
 */
export const GradeLevel = z.enum([
  'Below Grade Level',
  'At Grade Level',
  'Above Grade Level',
]);

export type GradeLevel = z.infer<typeof GradeLevel>;

/**
 * Metadata attached to all evaluation results
 */
export interface EvaluationMetadata {
  evaluatorVersion?: string;
  promptVersion: string;
  model: string;
  timestamp: Date;
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
