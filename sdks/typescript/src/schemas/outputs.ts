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

/** Tokens consumed by an evaluation, summed across every step. */
export interface EvaluationTokenUsage {
  inputTokens: number;
  outputTokens: number;
}

/** Operational facts about how an evaluation ran, identical for every evaluator. */
export interface EvaluationMetadata {
  /** `provider:model` for the model that actually ran, including any override. */
  model: string;
  /** Wall-clock time for the whole evaluation, not just the LLM calls. */
  processingTimeMs: number;
  tokenUsage: EvaluationTokenUsage;
}

/**
 * What every `evaluate()` resolves to. The three fields are the whole envelope:
 * operational facts go in `metadata`, everything domain-specific in `result`.
 *
 * `result` is the model's structured output as the evaluator's `output_schema.json`
 * declares it, keys and values unaltered. There is no scalar score hoisted up here
 * and no casing translation, so the payload is byte-identical across SDKs. Reports
 * that need one comparable value per evaluation use `readOutcome`.
 */
export interface EvaluationResult<TResult = unknown> {
  /** The evaluator's current registry id; renames stay resolvable via `idHistory`. */
  evaluator: string;
  result: TResult;
  metadata: EvaluationMetadata;
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
