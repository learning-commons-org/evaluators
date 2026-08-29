import {
  RevisionAccuracyEvaluator,
  RevisionActionabilityEvaluator,
  RevisionManageabilityEvaluator,
  StrengthAcknowledgmentEvaluator,
  StudentResponseSpecificityEvaluator,
  ToneAppropriatenessEvaluator,
  WithholdingAnswersEvaluator,
} from '../../evaluators/index.js';
import type { BaseEvaluatorConfig, ModelOverride, Provider } from '../../evaluators/base.js';
import type { EvaluationResult } from '../../schemas/index.js';
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
interface FeedbackEvaluator {
  evaluate(input: Record<string, string>): Promise<EvaluationResult<unknown>>;
}

type EvaluatorClass = (new (config: BaseEvaluatorConfig) => FeedbackEvaluator) & {
  metadata: {
    id: string;
    name: string;
    defaultProviders: readonly Provider[];
    outcome?: { score: string; reasoning: string };
  };
};

/**
 * The members, in report order. Everything else about them — id, display name, provider,
 * which field holds the verdict — is read off the class, which reads it off the contract.
 */
const MEMBER_CLASSES: readonly EvaluatorClass[] = [
  RevisionAccuracyEvaluator,
  RevisionActionabilityEvaluator,
  RevisionManageabilityEvaluator,
  StrengthAcknowledgmentEvaluator,
  StudentResponseSpecificityEvaluator,
  ToneAppropriatenessEvaluator,
  WithholdingAnswersEvaluator,
];

const BY_ID = new Map(MEMBER_CLASSES.map((E) => [E.metadata.id, E]));

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
      const EvaluatorClass = BY_ID.get(memberId);
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

    const { score, reasoning } = readOutcome(result, BY_ID.get(memberId)?.metadata.outcome);

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
      for (const provider of BY_ID.get(member.id)?.metadata.defaultProviders ?? []) {
        keys.add(provider);
      }
    }
    return [...keys];
  },
  createRunner(ctx: FamilyRunContext, selectedMemberIds?: string[]): FamilyRunner {
    return new FeedbackRunner(ctx, selectedMemberIds);
  },
};
