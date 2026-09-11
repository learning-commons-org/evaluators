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
