export {
  type EvaluationResult,
  type EvaluationMetadata,
  type EvaluationTokenUsage,
} from './outputs.js';

export {
  GradeLevelAppropriatenessOutputSchema,
  type GradeLevelAppropriatenessResult,
} from './student-facing-text/ela-reading/grade-level-appropriateness.js';
import type { GradeLevelAppropriatenessResult as GLAResult } from './student-facing-text/ela-reading/grade-level-appropriateness.js';

/** The grade bands the contract declares, derived from the generated schema so it cannot drift. */
export type GradeBand = GLAResult['grade_band'];

export {
  PurposeClarityOutputSchema,
  type PurposeClarityResult,
} from './student-facing-text/ela-reading/purpose-clarity.js';

export { readOutcome, type Outcome } from './outcome.js';
