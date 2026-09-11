import {
  VocabularyComplexityEvaluator,
  SentenceStructureEvaluator,
  GradeLevelAppropriatenessEvaluator,
  BackgroundKnowledgeDemandsEvaluator,
  MeaningDirectnessEvaluator,
  PurposeClarityEvaluator,
  OrganizationalStructureEvaluator,
  ReferenceKnowledgeDemandsEvaluator,
} from '../../evaluators/index.js';
import type { ModelOverride } from '../../evaluators/base.js';
import { Provider } from '../../evaluators/base.js';
import { getEvaluatorClass, type RegisteredEvaluator } from '../../evaluators/registry.js';
import { readOutcome } from '../../schemas/outcome.js';
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

/**
 * The shape this family needs from an evaluator: named inputs in, envelope out.
 *
 * Typed loosely on purpose -- members declare different input keys (GLA takes no
 * grade), and the family builds each object from the evaluator's own schema below.
 */
type SimpleEvaluator = InstanceType<RegisteredEvaluator>;

const MEMBERS = [
  { id: GradeLevelAppropriatenessEvaluator.metadata.id, name: GradeLevelAppropriatenessEvaluator.metadata.name },
  { id: BackgroundKnowledgeDemandsEvaluator.metadata.id, name: BackgroundKnowledgeDemandsEvaluator.metadata.name },
  { id: VocabularyComplexityEvaluator.metadata.id, name: VocabularyComplexityEvaluator.metadata.name },
  { id: SentenceStructureEvaluator.metadata.id, name: SentenceStructureEvaluator.metadata.name },
  { id: MeaningDirectnessEvaluator.metadata.id, name: MeaningDirectnessEvaluator.metadata.name },
  { id: PurposeClarityEvaluator.metadata.id, name: PurposeClarityEvaluator.metadata.name },
  { id: OrganizationalStructureEvaluator.metadata.id, name: OrganizationalStructureEvaluator.metadata.name },
  { id: ReferenceKnowledgeDemandsEvaluator.metadata.id, name: ReferenceKnowledgeDemandsEvaluator.metadata.name },
];

const COLUMNS: ColumnSpec[] = [
  { name: 'text', required: true },
  { name: 'grade_level', required: true },
];

/**
 * Per-member providers, so selecting a subset doesn't demand keys the run won't
 * use. Only `vocabulary` and `sentence-structure` reach OpenAI.
 */
const PROVIDERS_BY_MEMBER = new Map<string, readonly Provider[]>([
  [GradeLevelAppropriatenessEvaluator.metadata.id, GradeLevelAppropriatenessEvaluator.metadata.defaultProviders],
  [BackgroundKnowledgeDemandsEvaluator.metadata.id, BackgroundKnowledgeDemandsEvaluator.metadata.defaultProviders],
  [VocabularyComplexityEvaluator.metadata.id, VocabularyComplexityEvaluator.metadata.defaultProviders],
  [SentenceStructureEvaluator.metadata.id, SentenceStructureEvaluator.metadata.defaultProviders],
  [MeaningDirectnessEvaluator.metadata.id, MeaningDirectnessEvaluator.metadata.defaultProviders],
  [PurposeClarityEvaluator.metadata.id, PurposeClarityEvaluator.metadata.defaultProviders],
  [OrganizationalStructureEvaluator.metadata.id, OrganizationalStructureEvaluator.metadata.defaultProviders],
  [ReferenceKnowledgeDemandsEvaluator.metadata.id, ReferenceKnowledgeDemandsEvaluator.metadata.defaultProviders],
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
      const EvaluatorClass = getEvaluatorClass(memberId);
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
    // Built explicitly rather than passed through: a row carries every column in the
    // CSV, and an evaluator rejects keys its schema does not declare.
    const inputs: Record<string, string> = { text: row.columns.text };
    if (memberId !== GradeLevelAppropriatenessEvaluator.metadata.id) {
      inputs.grade_level = row.columns['grade_level'];
    }

    const result = await this.getEvaluator(memberId).evaluate(inputs);
    const declared = getEvaluatorClass(memberId)?.metadata.outcome;
    const { score, reasoning } = readOutcome(result, declared);

    // A report cell has to be a string. An absent verdict renders blank, and doing
    // that here rather than inside readOutcome keeps the gap visible to any other caller.
    return { score: score ?? '', reasoning };
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
