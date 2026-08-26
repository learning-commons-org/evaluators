import {
  MathStandardsAlignmentEvaluator,
  type StandardAlignmentResult,
} from '../../evaluators/math/standards-alignment.js';
import { Jurisdiction } from '../../knowledge-graph/index.js';
import { Provider } from '../../evaluators/base.js';
import type { ModelOverride } from '../../evaluators/base.js';
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

const EVALUATOR_ID = MathStandardsAlignmentEvaluator.metadata.id;

const MEMBERS = [{ id: EVALUATOR_ID, name: MathStandardsAlignmentEvaluator.metadata.name }];

// question + statementCode are load-bearing; jurisdiction defaults to CCSS
// (Multi-State); grade + id are passthrough metadata (report slicing / joining).
export const STANDARDS_COLUMNS: ColumnSpec[] = [
  { name: 'question', aliases: ['text'], required: true },
  { name: 'statementCode', aliases: ['statement_code', 'ccss_standard', 'standard'], required: true },
  { name: 'jurisdiction', required: false, default: Jurisdiction.MultiState },
  { name: 'grade', required: false },
  { name: 'id', aliases: ['item_id'], required: false },
];

const VALID_JURISDICTIONS = new Set<string>(Object.values(Jurisdiction));

function resolveJurisdiction(raw: string | undefined): Jurisdiction {
  const value = (raw ?? Jurisdiction.MultiState).trim();
  if (!VALID_JURISDICTIONS.has(value)) {
    throw new Error(
      `Invalid jurisdiction "${value}". Expected one of the Learning Commons jurisdictions ` +
        `(e.g. "${Jurisdiction.MultiState}").`,
    );
  }
  return value as Jurisdiction;
}

/** Structured verdict carried on BatchResult.payload for standards rows. */
export interface StandardsVerdict extends StandardAlignmentResult {
  question: string;
  jurisdiction: Jurisdiction;
}

class StandardsRunner implements FamilyRunner {
  readonly members;
  private readonly evaluator: MathStandardsAlignmentEvaluator;

  constructor(ctx: FamilyRunContext, selectedMemberIds?: string[]) {
    this.members = resolveMembers(STANDARDS_FAMILY, selectedMemberIds);
    this.evaluator = new MathStandardsAlignmentEvaluator({
      learningCommonsApiKey: ctx.learningCommonsApiKey,
      anthropicApiKey: ctx.anthropicApiKey,
      // Forwarded so a `--model google:…`/`openai:…` override has its key.
      googleApiKey: ctx.googleApiKey,
      openaiApiKey: ctx.openaiApiKey,
      maxRetries: ctx.maxRetries,
      telemetry: ctx.telemetry,
      modelOverride: ctx.modelOverride,
      llmProvider: ctx.llmProvider,
      concurrency: ctx.concurrency,
      kgConcurrency: ctx.kgConcurrency,
    });
  }

  async runTask(row: FamilyRow, _memberId?: string): Promise<TaskOutcome> {
    const jurisdiction = resolveJurisdiction(row.columns.jurisdiction);
    const result = await this.evaluator.evaluate(
      row.columns.question,
      row.columns.statementCode,
      jurisdiction,
    );
    const verdict: StandardsVerdict = { ...result, question: row.columns.question, jurisdiction };
    return {
      score: `${result.alignedCount}/${result.totalCount}`,
      reasoning: `${result.alignedCount} of ${result.totalCount} learning components aligned`,
      payload: verdict,
    };
  }
}

export const STANDARDS_FAMILY: EvaluatorFamily = {
  id: 'math-standards-alignment',
  name: 'Math Standards Alignment',
  description:
    'Evaluates whether each item aligns to its tagged math standard, component by component',
  members: MEMBERS,
  columns: STANDARDS_COLUMNS,
  maxInputRows: 5000,
  requiredKeys(_selectedMemberIds: string[], modelOverride?: ModelOverride): KeyKind[] {
    // The platform key (Knowledge Graph) is always required; the LLM provider
    // is Anthropic unless a model override redirects it.
    return [modelOverride?.provider ?? Provider.Anthropic, 'learning-commons'];
  },
  createRunner(ctx: FamilyRunContext, selectedMemberIds?: string[]): FamilyRunner {
    return new StandardsRunner(ctx, selectedMemberIds);
  },
};
