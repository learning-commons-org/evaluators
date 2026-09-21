export {
  type EvaluationResult,
  type EvaluationMetadata,
  type EvaluationTokenUsage,
} from './outputs.js';

export {
  GradeLevelAppropriatenessOutputSchema,
  type GradeLevelAppropriatenessResult,
} from './text-complexity/ela-reading/grade-level-appropriateness.js';
import type { GradeLevelAppropriatenessResult as GLAResult } from './text-complexity/ela-reading/grade-level-appropriateness.js';

/** The grade bands the contract declares, derived from the generated schema so it cannot drift. */
export type GradeBand = GLAResult['grade_band'];

export {
  PurposeClarityOutputSchema,
  type PurposeClarityResult,
} from './text-complexity/ela-reading/purpose-clarity.js';

export { readOutcome, type Outcome, type DeclaredOutcome } from './outcome.js';
