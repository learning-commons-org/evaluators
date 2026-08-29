export {
  TextComplexityLevel,
  type EvaluationResult,
  type EvaluationMetadata,
  type EvaluationTokenUsage,
  type EvaluationFailure,
} from './outputs.js';

export {
  GradeLevelAppropriatenessOutputSchema,
  type GradeLevelAppropriatenessResult,
} from './student-facing-text/ela-reading/grade-level-appropriateness.js';
import type { GradeLevelAppropriatenessResult as GLAResult } from './student-facing-text/ela-reading/grade-level-appropriateness.js';

/**
 * The grade bands the contract declares, read off the generated schema.
 *
 * Was a hand-written Zod enum, which is how it came to say `11-CCR` where the contract
 * says `11-12`. Deriving it means it cannot say anything else again.
 */
export type GradeBand = GLAResult['grade_band'];

export {
  PurposeClarityOutputSchema,
  type PurposeClarityResult,
} from './student-facing-text/ela-reading/purpose-clarity.js';

export { readOutcome, type Outcome } from './outcome.js';
