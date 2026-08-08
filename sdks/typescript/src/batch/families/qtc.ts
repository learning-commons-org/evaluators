import {
  VocabularyEvaluator,
  SentenceStructureEvaluator,
  GradeLevelAppropriatenessEvaluator,
  SmkEvaluator,
  ConventionalityEvaluator,
  PurposeEvaluator,
} from '../../evaluators/index.js';
import type { BaseEvaluatorConfig, ModelOverride } from '../../evaluators/base.js';
import { Provider } from '../../evaluators/base.js';
import type { EvaluationResult } from '../../schemas/index.js';
import {
  type ColumnSpec,
  type EvaluatorFamily,
  type FamilyRow,
  type FamilyRunContext,
  type FamilyRunner,
  type KeyKind,
  type TaskOutcome,
  resolveMembers,
} from './family.js';

interface SimpleEvaluator {
  evaluate(text: string, grade: string): Promise<EvaluationResult<string, unknown>>;
}
type EvaluatorConstructor = new (config: BaseEvaluatorConfig) => SimpleEvaluator;

const EVALUATOR_MAP = new Map<string, EvaluatorConstructor>([
  [GradeLevelAppropriatenessEvaluator.metadata.id, GradeLevelAppropriatenessEvaluator],
  [SmkEvaluator.metadata.id, SmkEvaluator],
  [VocabularyEvaluator.metadata.id, VocabularyEvaluator],
  [SentenceStructureEvaluator.metadata.id, SentenceStructureEvaluator],
  [ConventionalityEvaluator.metadata.id, ConventionalityEvaluator],
  [PurposeEvaluator.metadata.id, PurposeEvaluator],
]);

const MEMBERS = [
  { id: GradeLevelAppropriatenessEvaluator.metadata.id, name: GradeLevelAppropriatenessEvaluator.metadata.name },
  { id: SmkEvaluator.metadata.id, name: SmkEvaluator.metadata.name },
  { id: VocabularyEvaluator.metadata.id, name: VocabularyEvaluator.metadata.name },
  { id: SentenceStructureEvaluator.metadata.id, name: SentenceStructureEvaluator.metadata.name },
  { id: ConventionalityEvaluator.metadata.id, name: ConventionalityEvaluator.metadata.name },
  { id: PurposeEvaluator.metadata.id, name: PurposeEvaluator.metadata.name },
];

const COLUMNS: ColumnSpec[] = [
  { name: 'text', required: true },
  { name: 'grade', required: true },
];

/**
 * Per-member providers, so selecting a subset doesn't demand keys the run won't
 * use. Only `vocabulary` and `sentence-structure` reach OpenAI.
 */
const PROVIDERS_BY_MEMBER = new Map<string, readonly Provider[]>([
  [GradeLevelAppropriatenessEvaluator.metadata.id, GradeLevelAppropriatenessEvaluator.metadata.defaultProviders],
  [SmkEvaluator.metadata.id, SmkEvaluator.metadata.defaultProviders],
  [VocabularyEvaluator.metadata.id, VocabularyEvaluator.metadata.defaultProviders],
  [SentenceStructureEvaluator.metadata.id, SentenceStructureEvaluator.metadata.defaultProviders],
  [ConventionalityEvaluator.metadata.id, ConventionalityEvaluator.metadata.defaultProviders],
  [PurposeEvaluator.metadata.id, PurposeEvaluator.metadata.defaultProviders],
]);

class QtcRunner implements FamilyRunner {
  readonly members;
  private readonly instances = new Map<string, SimpleEvaluator>();

  constructor(private readonly ctx: FamilyRunContext, selectedMemberIds?: string[]) {
    this.members = resolveMembers(QTC_FAMILY, selectedMemberIds);
  }

  private getEvaluator(memberId: string): SimpleEvaluator {
    let instance = this.instances.get(memberId);
    if (!instance) {
      const EvaluatorClass = EVALUATOR_MAP.get(memberId);
      if (!EvaluatorClass) throw new Error(`Unknown QTC evaluator: ${memberId}`);
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
    const result = await this.getEvaluator(memberId).evaluate(row.columns.text, row.columns.grade);
    return { score: result.score, reasoning: result.reasoning };
  }
}

export const QTC_FAMILY: EvaluatorFamily = {
  id: 'text-complexity',
  name: 'Text Complexity Analysis',
  description: 'Evaluates all dimensions of the Qualitative Text Complexity rubric',
  members: MEMBERS,
  columns: COLUMNS,
  maxInputRows: 50,
  requiredKeys(selectedMemberIds: string[], modelOverride?: ModelOverride): KeyKind[] {
    if (modelOverride) return [modelOverride.provider];
    const keys = new Set<KeyKind>();
    for (const member of resolveMembers(QTC_FAMILY, selectedMemberIds)) {
      for (const provider of PROVIDERS_BY_MEMBER.get(member.id) ?? []) keys.add(provider);
    }
    return [...keys];
  },
  createRunner(ctx: FamilyRunContext, selectedMemberIds?: string[]): FamilyRunner {
    return new QtcRunner(ctx, selectedMemberIds);
  },
};
