/**
 * Reading one comparable value out of an evaluation payload.
 *
 * The result envelope carries the payload exactly as the registry declares it, so
 * there is no top-level score to read. Batch runs and reports still need a single
 * scalar per evaluation to sort, group and chart on, and this is where that is
 * read from the evaluator's declared `outcome` block, so no SDK keeps a per-evaluator
 * table of which field holds the verdict.
 */

import type { EvaluationResult } from './outputs.js';

/** The `outcome` block an evaluator's contract declares. */
export interface DeclaredOutcome {
  readonly score: string;
  readonly reasoning: string;
}

/**
 * The scalar verdict and its rationale, as a report consumes them.
 *
 * `score` is undefined when the payload carries no verdict field. That is a reporting
 * gap rather than an evaluation failure, so it is surfaced as absent for the caller to
 * handle, not quietly rendered as an empty string here.
 */
export interface Outcome {
  score: string | undefined;
  reasoning: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Pick the verdict and reasoning out of an evaluation's payload.
 *
 * `outcome` is the evaluator's declared `outcome` block, naming which payload
 * properties hold them — so this reads the contract rather than guessing from a field
 * suffix, and a new evaluator needs no registration here at all.
 *
 * An evaluator with no declared outcome, or a payload missing the declared property,
 * yields an undefined score rather than throwing: a missing verdict is a reporting gap,
 * not a reason to fail an evaluation that already succeeded.
 */
export function readOutcome(
  { result }: EvaluationResult,
  outcome: DeclaredOutcome | undefined,
): Outcome {
  if (!isRecord(result) || !outcome) return { score: undefined, reasoning: '' };

  const score = result[outcome.score];
  const reasoning = result[outcome.reasoning];

  return {
    score: score === undefined || score === null ? undefined : String(score),
    reasoning: typeof reasoning === 'string' ? reasoning : '',
  };
}
