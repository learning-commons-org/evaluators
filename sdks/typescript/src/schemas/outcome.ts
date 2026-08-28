/**
 * Reading one comparable value out of an evaluation payload.
 *
 * The result envelope carries the payload exactly as the registry declares it, so
 * there is no top-level score to read. Batch runs and reports still need a single
 * scalar per evaluation to sort, group and chart on, and this is where that is
 * derived — once, from the shape the contracts already share, rather than in a
 * per-evaluator table each SDK would have to keep in step.
 */

/** The scalar verdict and its rationale, as a report consumes them. */
export interface Outcome {
  score: string;
  reasoning: string;
}

/**
 * Evaluators whose verdict is not a `*_score` field.
 *
 * Grade Level Appropriateness answers with a grade band rather than a complexity
 * level, so its verdict field is a band and there is no score to find. It will stay
 * listed here after the rename to `grade_band`.
 *
 * Sentence Structure is listed only until its Zod schema is generated from its
 * contract, which declares `complexity_score`; the SDK currently asks the model for
 * `answer`.
 */
const VERDICT_FIELD_OVERRIDES: Readonly<Record<string, string>> = {
  'student_facing_text.ela_reading.grade_level_appropriateness': 'grade',
  'student_facing_text.ela_reading.sentence_structure': 'answer',
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/**
 * Pick the verdict and reasoning out of `result`.
 *
 * By convention every payload carries exactly one property ending in `_score`
 * (`complexity_score`, `quality_score`) plus `reasoning`; evaluators that break the
 * convention are listed above. A payload with neither yields empty strings rather
 * than throwing — a missing verdict is a reporting gap, not a reason to fail an
 * evaluation that already succeeded.
 */
export function readOutcome(evaluatorId: string, result: unknown): Outcome {
  if (!isRecord(result)) return { score: '', reasoning: '' };

  const override = VERDICT_FIELD_OVERRIDES[evaluatorId];
  const field = override ?? Object.keys(result).find((key) => key.endsWith('_score'));

  const score = field !== undefined ? result[field] : undefined;
  const reasoning = result['reasoning'];

  return {
    score: score === undefined || score === null ? '' : String(score),
    reasoning: typeof reasoning === 'string' ? reasoning : '',
  };
}
