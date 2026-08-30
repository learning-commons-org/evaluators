import {
  RevisionAccuracyEvaluator,
  RevisionActionabilityEvaluator,
  RevisionManageabilityEvaluator,
  StrengthAcknowledgmentEvaluator,
  StudentResponseSpecificityEvaluator,
  ToneAppropriatenessEvaluator,
  WithholdingAnswersEvaluator,
} from '../../evaluators/index.js';
import type { ModelOverride } from '../../evaluators/base.js';
import { getEvaluatorClass, type RegisteredEvaluator } from '../../evaluators/registry.js';
import { readOutcome } from '../../schemas/outcome.js';
import {
  type ColumnSpec,
  type EvaluatorFamily,
  type FamilyMember,
  type FamilyRow,
  type FamilyRunContext,
  type FamilyRunner,
  type KeyKind,
  type TaskOutcome,
  resolveMembers,
} from './family.js';

/** The shape this family needs from an evaluator: named inputs in, envelope out. */
type FeedbackEvaluator = InstanceType<RegisteredEvaluator>;

/**
 * Which evaluators are in this family, and the order they report in. That is all this list
 * decides — id, display name, provider and which field holds the verdict are read off the
 * class, which reads them off the contract. Resolution by id goes through the registry.
 */
const MEMBER_CLASSES: readonly RegisteredEvaluator[] = [
  RevisionAccuracyEvaluator,
  RevisionActionabilityEvaluator,
  RevisionManageabilityEvaluator,
  StrengthAcknowledgmentEvaluator,
  StudentResponseSpecificityEvaluator,
  ToneAppropriatenessEvaluator,
  WithholdingAnswersEvaluator,
];

/** The columns a row must carry, matching what every member's input schema declares. */
export const FEEDBACK_COLUMNS: ColumnSpec[] = [
  { name: 'student_text', required: true },
  { name: 'feedback_text', required: true },
];

class FeedbackRunner implements FamilyRunner {
  readonly members: FamilyMember[];
  private readonly instances = new Map<string, FeedbackEvaluator>();

  constructor(
    private readonly ctx: FamilyRunContext,
    selectedMemberIds?: string[],
  ) {
    this.members = resolveMembers(FEEDBACK_FAMILY, selectedMemberIds);
  }

  private getEvaluator(memberId: string): FeedbackEvaluator {
    let instance = this.instances.get(memberId);
    if (!instance) {
      const EvaluatorClass = getEvaluatorClass(memberId);
      if (!EvaluatorClass) throw new Error(`Unknown feedback evaluator: ${memberId}`);
      instance = new EvaluatorClass({
        googleApiKey: this.ctx.googleApiKey,
        openaiApiKey: this.ctx.openaiApiKey,
        anthropicApiKey: this.ctx.anthropicApiKey,
        maxRetries: this.ctx.maxRetries,
        telemetry: this.ctx.telemetry,
        modelOverride: this.ctx.modelOverride,
        llmProvider: this.ctx.llmProvider,
      });
      this.instances.set(memberId, instance);
    }
    return instance;
  }

  async runTask(row: FamilyRow, memberId: string): Promise<TaskOutcome> {
    // Built explicitly rather than passed through: a row carries every column in the CSV,
    // and an evaluator rejects keys its schema does not declare.
    const result = await this.getEvaluator(memberId).evaluate({
      student_text: row.columns['student_text'],
      feedback_text: row.columns['feedback_text'],
    });

    const { score, reasoning } = readOutcome(result, getEvaluatorClass(memberId)?.metadata.outcome);

    // A report cell has to be a string, and the verdict here is the integer 0 or 1, which
    // readOutcome has already stringified. An absent verdict renders blank.
    return { score: score ?? '', reasoning };
  }
}

export const FEEDBACK_FAMILY: EvaluatorFamily = {
  id: 'feedback',
  name: 'Teacher Feedback Quality',
  description: "Evaluates written feedback on a student's writing against seven criteria",
  members: MEMBER_CLASSES.map((E) => ({ id: E.metadata.id, name: E.metadata.name })),
  columns: FEEDBACK_COLUMNS,
  maxInputRows: 50,
  requiredKeys(selectedMemberIds: string[], modelOverride?: ModelOverride): KeyKind[] {
    if (modelOverride) return [modelOverride.provider];
    const keys = new Set<KeyKind>();
    for (const member of resolveMembers(FEEDBACK_FAMILY, selectedMemberIds)) {
      // Not `?? []`: a member id that does not resolve would silently drop that member's
      // provider key from the requirement list, and the run would fail later on a missing
      // credential instead of prompting for it. These ids come from this family's own
      // member list, so an unresolvable one is a bug here, not bad input.
      const resolved = getEvaluatorClass(member.id);
      if (!resolved) throw new Error(`Feedback family member is not registered: ${member.id}`);

      for (const provider of resolved.metadata.defaultProviders) {
        keys.add(provider);
      }
    }
    return [...keys];
  },
  createRunner(ctx: FamilyRunContext, selectedMemberIds?: string[]): FamilyRunner {
    return new FeedbackRunner(ctx, selectedMemberIds);
  },
};
