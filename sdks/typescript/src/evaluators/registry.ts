import type { BaseEvaluatorConfig, EvaluatorMetadata } from './base.js';
import type { EvaluationResult } from '../schemas/outputs.js';

import { VocabularyComplexityEvaluator } from './student-facing-text/ela-reading/vocabulary-complexity.js';
import { SentenceStructureEvaluator } from './student-facing-text/ela-reading/sentence-structure.js';
import { GradeLevelAppropriatenessEvaluator } from './student-facing-text/ela-reading/grade-level-appropriateness.js';
import { BackgroundKnowledgeDemandsEvaluator } from './student-facing-text/ela-reading/background-knowledge-demands.js';
import { MeaningDirectnessEvaluator } from './student-facing-text/ela-reading/meaning-directness.js';
import { PurposeClarityEvaluator } from './student-facing-text/ela-reading/purpose-clarity.js';
import { ReferenceKnowledgeDemandsEvaluator } from './student-facing-text/ela-reading/reference-knowledge-demands.js';
import { OrganizationalStructureEvaluator } from './student-facing-text/ela-reading/organizational-structure.js';
import { RevisionAccuracyEvaluator } from './feedback/ela-writing/revision-accuracy.js';
import { RevisionActionabilityEvaluator } from './feedback/ela-writing/revision-actionability.js';
import { RevisionManageabilityEvaluator } from './feedback/ela-writing/revision-manageability.js';
import { StrengthAcknowledgmentEvaluator } from './feedback/ela-writing/strength-acknowledgment.js';
import { StudentResponseSpecificityEvaluator } from './feedback/ela-writing/student-response-specificity.js';
import { ToneAppropriatenessEvaluator } from './feedback/ela-writing/tone-appropriateness.js';
import { WithholdingAnswersEvaluator } from './feedback/ela-writing/withholding-answers.js';
import { MathStandardsAlignmentEvaluator } from './academic-standards-alignment/mathematics/math-standards-alignment.js';

/**
 * An evaluator class as the registry holds it: constructible, and carrying its own metadata.
 *
 * Deliberately **not** exported from the package. Resolving a class by id erases which named
 * inputs it takes — math takes `question`/`statement_code`/`jurisdiction`, the complexity
 * evaluators take `text`/`grade_level` — and no signature can express "whatever this
 * particular id declares". Publishing it would hand callers a constructor that compiles
 * against any input shape and fails only at run time, and the SDK exposes no way to discover
 * the right shape. Callers who want a specific evaluator import it by name and keep its
 * types; the id-resolved form stays internal to the batch families, which know what they
 * are passing.
 */
export interface RegisteredEvaluator {
  new (config: BaseEvaluatorConfig): {
    evaluate(input: Record<string, string>): Promise<EvaluationResult<unknown>>;
  };
  readonly metadata: EvaluatorMetadata;
}

/**
 * Every evaluator, in taxonomy order.
 *
 * Adding an evaluator means adding it here. The conformance suite compares this list against
 * the public barrel, so one exported but unregistered fails the build rather than going
 * quietly missing from `getEvaluators()`.
 *
 * Frozen because `getEvaluators()` hands it out directly and `readonly` is erased at
 * runtime, so a caller appending to it would corrupt every later lookup. The freeze is
 * shallow: it protects the list, not each class's own `metadata`.
 */
const EVALUATORS: readonly RegisteredEvaluator[] = Object.freeze([
  MathStandardsAlignmentEvaluator,
  RevisionAccuracyEvaluator,
  RevisionActionabilityEvaluator,
  RevisionManageabilityEvaluator,
  StrengthAcknowledgmentEvaluator,
  StudentResponseSpecificityEvaluator,
  ToneAppropriatenessEvaluator,
  WithholdingAnswersEvaluator,
  BackgroundKnowledgeDemandsEvaluator,
  GradeLevelAppropriatenessEvaluator,
  MeaningDirectnessEvaluator,
  OrganizationalStructureEvaluator,
  PurposeClarityEvaluator,
  ReferenceKnowledgeDemandsEvaluator,
  SentenceStructureEvaluator,
  VocabularyComplexityEvaluator,
]);

/**
 * The public projection of the list above.
 *
 * Frozen for the same reason as `EVALUATORS`: `readonly` is erased at runtime and this is
 * handed out directly. The freeze is shallow — it protects the list, not each evaluator's
 * own `metadata` object, which is the class's own static and mutable with or without this.
 */
const METADATA: readonly EvaluatorMetadata[] = Object.freeze(EVALUATORS.map((E) => E.metadata));

/**
 * Index every evaluator by its current id and by each id it used to carry.
 *
 * Throws on a collision rather than letting one win. `new Map` keeps the last entry for a
 * repeated key, so two evaluators sharing an id — most plausibly one evaluator's
 * `idHistory` entry colliding with another's current id — would silently resolve to
 * whichever was registered later, and `getEvaluator` would confidently return the wrong
 * evaluator. Exported for the collision test, which cannot introduce a real duplicate.
 *
 * @internal
 */
export function indexById(
  evaluators: readonly RegisteredEvaluator[],
): ReadonlyMap<string, RegisteredEvaluator> {
  const index = new Map<string, RegisteredEvaluator>();

  for (const E of evaluators) {
    for (const id of [E.metadata.id, ...E.metadata.idHistory]) {
      const claimed = index.get(id);
      if (claimed && claimed !== E) {
        throw new Error(
          `Registry id "${id}" is claimed by both ${claimed.metadata.name} and ` +
            `${E.metadata.name}. An id, current or historical, must name one evaluator.`,
        );
      }
      index.set(id, E);
    }
  }

  return index;
}

/** Current id, and every id that has ever meant this evaluator, to the class. */
const BY_ID = indexById(EVALUATORS);

/** Every evaluator in the SDK, in taxonomy order. */
export function getEvaluators(): readonly EvaluatorMetadata[] {
  return METADATA;
}

/**
 * The evaluator a registry id names, or `undefined` if none does.
 *
 * Renames resolve: an id an evaluator used to carry still finds it, via `idHistory`, so a
 * result stored under the old name stays identifiable. Returns `undefined` rather than
 * throwing because "not found" is a normal answer to a lookup.
 */
export function getEvaluator(id: string): EvaluatorMetadata | undefined {
  return BY_ID.get(id)?.metadata;
}

/**
 * The class behind an id, for callers that need to construct it.
 *
 * Internal: see {@link RegisteredEvaluator} for why the constructible form is not published.
 * This is what lets the batch families resolve a member id without each keeping its own
 * id-to-class map.
 *
 * @internal
 */
export function getEvaluatorClass(id: string): RegisteredEvaluator | undefined {
  return BY_ID.get(id);
}
