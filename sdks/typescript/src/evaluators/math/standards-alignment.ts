import pLimit from 'p-limit';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from '../base.js';
import type { LLMProvider } from '../../providers/index.js';
import {
  BatchedLCEvaluationSchema,
  CoarseFilterSchema,
} from '../../schemas/math/standards-alignment.js';
import {
  getSystemPrompt,
  getUserPrompt,
  getCoarseFilterPrompt,
  STEP,
  EVALUATOR_ID,
  SUPPORTED_GRADES,
  MAX_QUESTION_LENGTH,
} from '../../prompts/math/standards-alignment/index.js';
import { KnowledgeGraphClient, Jurisdiction } from '../../knowledge-graph/index.js';
import { EvaluatorError, APIError, ConfigurationError, ValidationError, wrapProviderError } from '../../errors.js';
import type { StageDetail } from '../../telemetry/index.js';

export { Jurisdiction } from '../../knowledge-graph/index.js';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface LearningComponentResult {
  identifier: string;
  description: string;
  reasoning: string;
  aligned: boolean;
  feedback: string;
}

export interface StandardAlignmentResult {
  statementCode: string;
  learningComponents: LearningComponentResult[];
  alignedCount: number;
  totalCount: number;
  coarseFiltered?: boolean;
}

export interface QuestionItem {
  question: string;
  statementCodes: string[];
}

export interface QuestionBankResult {
  byQuestion: Array<{
    question: string;
    standards: StandardAlignmentResult[];
  }>;
  byStandard: Array<{
    statementCode: string;
    coveredBy: Array<{
      question: string;
      alignedCount: number;
      totalCount: number;
    }>;
    coverageCount: number;
  }>;
}

export interface QuestionBankOptions {
  concurrency?: number;
  useCoarseFilter?: boolean;
  onProgress?: (completed: number, total: number) => void;
}

export interface MathStandardsAlignmentEvaluatorConfig extends BaseEvaluatorConfig {
  /** Learning Commons platform API key — required for Knowledge Graph access */
  platformApiKey?: string;
  /** Max concurrent LLM calls (default: 10) */
  concurrency?: number;
  /** Max concurrent KG HTTP calls (default: 20) */
  kgConcurrency?: number;
  /**
   * Override the Anthropic model used for evaluation (default: claude-haiku-4-5-20251001).
   * Also used for the coarse filter unless coarseFilterModel is set separately.
   */
  coarseFilterModel?: string;
  /** @internal Test seam — inject a pre-built client without a real API key */
  _kgClient?: KnowledgeGraphClient;
}

// ---------------------------------------------------------------------------
// Constants read from config.json (single source of truth)
// ---------------------------------------------------------------------------

const DETAIL_MODEL: string = STEP.model.name;
const TEMPERATURE: number = STEP.generation.temperature;
const KG_SUBJECT = 'Mathematics';
/**
 * Above this many question/standard pairs, evaluateByGrade warns. A grade can carry
 * over a thousand standards in some jurisdictions, so a handful of questions is
 * enough to run into five figures of LLM calls.
 */
const BY_GRADE_WARN_PAIRS = 500;

// ---------------------------------------------------------------------------
// Evaluator
// ---------------------------------------------------------------------------

export class MathStandardsAlignmentEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: EVALUATOR_ID,
    name: 'Math Standards Alignment',
    description: 'Evaluates whether an assessment question aligns to a math standard via learning-component analysis',
    supportedGrades: SUPPORTED_GRADES as string[],
    defaultProviders: [Provider.Anthropic] as const,
  };

  private readonly kgClient: KnowledgeGraphClient;
  private readonly detailProvider: LLMProvider;
  private readonly coarseProvider: LLMProvider;
  private readonly llmConcurrency: number;

  constructor(config: MathStandardsAlignmentEvaluatorConfig) {
    // If partnerKey isn't set, fall back to platformApiKey — same LC platform key,
    // different API surfaces (KG vs telemetry).
    super({ ...config, partnerKey: config.partnerKey ?? config.platformApiKey });

    if (!config.platformApiKey && !config._kgClient) {
      throw new ConfigurationError(
        'MathStandardsAlignmentEvaluator requires a platformApiKey to access the Learning Commons Knowledge Graph.',
      );
    }

    this.kgClient = config._kgClient ?? new KnowledgeGraphClient(config.platformApiKey!, config.kgConcurrency ?? 20);
    this.llmConcurrency = config.concurrency ?? 10;

    this.detailProvider = this.createConfiguredProvider(
      Provider.Anthropic,
      DETAIL_MODEL,
      config.anthropicApiKey,
    );

    this.coarseProvider = this.createConfiguredProvider(
      Provider.Anthropic,
      config.coarseFilterModel ?? DETAIL_MODEL,
      config.anthropicApiKey,
    );
  }

  // -------------------------------------------------------------------------
  // evaluate — single question × single standard (the primitive)
  // -------------------------------------------------------------------------

  async evaluate(
    question: string,
    statementCode: string,
    jurisdiction: Jurisdiction,
  ): Promise<StandardAlignmentResult> {
    return this._evaluateCore(question, statementCode, jurisdiction);
  }

  // -------------------------------------------------------------------------
  // evaluateItems — M questions × per-question standards
  //
  // Each item specifies its own statementCodes list. Use this for:
  //   - Tagging validation: verify a question covers its pre-mapped standards
  //   - Grade-level coverage: pass the same codes to all items (evaluateByGrade does this)
  //
  // Set options.useCoarseFilter to true to run a fast pre-filter before the
  // full per-LC evaluation — reduces LLM calls at scale, slight recall trade-off.
  // -------------------------------------------------------------------------

  async evaluateItems(
    items: QuestionItem[],
    jurisdiction: Jurisdiction,
    options?: QuestionBankOptions,
  ): Promise<Array<{ question: string; standards: StandardAlignmentResult[] }>> {
    if (items.length === 0) return [];
    items.forEach((item) => this.validateQuestion(item.question));

    const dedupedItems = items.map((item) => ({
      question: item.question,
      statementCodes: [...new Set(item.statementCodes)],
    }));

    const useCoarseFilter = options?.useCoarseFilter ?? false;
    const bankLimit = pLimit(options?.concurrency ?? this.llmConcurrency);

    // Pre-fetch LC data for all unique codes — needed to report totalCount on coarse-filtered results.
    const allCodes = [...new Set(dedupedItems.flatMap((i) => i.statementCodes))];
    type LcCacheEntry = Awaited<ReturnType<KnowledgeGraphClient['getLearningComponentsByCode']>>;
    const lcCache = new Map<string, LcCacheEntry>();

    if (useCoarseFilter) {
      await Promise.all(
        allCodes.map((code) =>
          this.kgClient.getLearningComponentsByCode(code, { jurisdiction, academicSubject: KG_SUBJECT })
            .then((result) => lcCache.set(code, result))
            .catch(() => undefined),
        ),
      );
    }

    // Coarse filter: per-item, against that item's own statementCodes.
    let relevanceMaps: Map<number, Set<string>>;
    if (!useCoarseFilter) {
      relevanceMaps = new Map(dedupedItems.map((item, i) => [i, new Set(item.statementCodes)]));
    } else {
      const filterResults = await Promise.all(
        dedupedItems.map((item) => bankLimit(() => this.runCoarseFilter(item.question, item.statementCodes, jurisdiction))),
      );
      relevanceMaps = new Map(dedupedItems.map((_, i) => [i, filterResults[i]]));
    }

    const total = dedupedItems.reduce((sum, _, i) => sum + (relevanceMaps.get(i)?.size ?? 0), 0);
    let completed = 0;

    const settled = await Promise.allSettled(
      dedupedItems.map(async (item, i) => {
        const relevant = relevanceMaps.get(i) ?? new Set(item.statementCodes);

        const standardSettled = await Promise.allSettled(
          item.statementCodes.map(async (code): Promise<StandardAlignmentResult> => {
            if (!relevant.has(code)) {
              const cached = lcCache.get(code);
              return {
                statementCode: code,
                learningComponents: [],
                alignedCount: 0,
                totalCount: cached?.components.length ?? 0,
                coarseFiltered: true,
              };
            }
            const result = await bankLimit(() => this._evaluateCore(item.question, code, jurisdiction));
            completed++;
            options?.onProgress?.(completed, total);
            return result;
          }),
        );

        const errors = standardSettled
          .filter((s): s is PromiseRejectedResult => s.status === 'rejected')
          .map((s) => s.reason instanceof Error ? s.reason : new Error(String(s.reason)));
        if (errors.length > 0) throw errors[0];

        return {
          question: item.question,
          standards: standardSettled.map((s) =>
            s.status === 'fulfilled' ? s.value : { statementCode: '', learningComponents: [], alignedCount: 0, totalCount: 0 }
          ),
        };
      }),
    );

    const errors = settled
      .filter((s): s is PromiseRejectedResult => s.status === 'rejected')
      .map((s) => s.reason instanceof Error ? s.reason : new Error(String(s.reason)));
    if (errors.length > 0) throw errors[0];

    return (settled as Array<PromiseFulfilledResult<{ question: string; standards: StandardAlignmentResult[] }>>).map((s) => s.value);
  }

  // -------------------------------------------------------------------------
  // evaluateByGrade — fetches all math standards for a grade, then evaluates
  //
  // Use when you don't have a predetermined standards list. Jurisdiction
  // determines which state's adopted standards are fetched from the KG.
  // Returns both a by-question and by-standard view of coverage.
  // -------------------------------------------------------------------------

  async evaluateByGrade(
    questions: string[],
    grade: string,
    jurisdiction: Jurisdiction,
    options?: QuestionBankOptions,
  ): Promise<QuestionBankResult> {
    if (questions.length === 0) throw new ValidationError('questions array must not be empty');
    this.validateGrade(grade, new Set(SUPPORTED_GRADES));

    const academicStandards = await this.kgClient.getStandardsByGrade(grade, {
      jurisdiction,
      academicSubject: KG_SUBJECT,
    });
    // statementCode is nullable in the spec — skip standards without one. Deduped
    // because a jurisdiction reusing a code across courses returns one item per
    // course, which would otherwise repeat that code in byStandard.
    const codes = [...new Set(
      academicStandards
        .map((s) => s.statementCode)
        .filter((c): c is string => c != null),
    )];

    const pairs = questions.length * codes.length;
    if (pairs > BY_GRADE_WARN_PAIRS) {
      this.logger.warn('Large grade-wide evaluation; each pair costs an LLM call', {
        evaluator: EVALUATOR_ID,
        grade,
        jurisdiction,
        questions: questions.length,
        standards: codes.length,
        pairs,
      });
    }

    if (codes.length === 0) {
      return {
        byQuestion: questions.map((q) => ({ question: q, standards: [] })),
        byStandard: [],
      };
    }

    const items = questions.map((q) => ({ question: q, statementCodes: codes }));
    const byQuestion = await this.evaluateItems(items, jurisdiction, options);

    const byStandard = codes.map((code) => {
      const coveredBy = byQuestion.flatMap(({ question, standards }) => {
        const result = standards.find((s) => s.statementCode === code);
        if (!result || result.alignedCount === 0) return [];
        return [{ question, alignedCount: result.alignedCount, totalCount: result.totalCount }];
      });
      return { statementCode: code, coveredBy, coverageCount: coveredBy.length };
    });

    return { byQuestion, byStandard };
  }

  // -------------------------------------------------------------------------
  // Private helpers
  // -------------------------------------------------------------------------

  private async _evaluateCore(
    question: string,
    statementCode: string,
    jurisdiction: Jurisdiction,
  ): Promise<StandardAlignmentResult> {
    this.validateQuestion(question);
    this.validateStatementCode(statementCode);

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      const { components, ambiguous, uuid, description } = await this.kgClient.getLearningComponentsByCode(
        statementCode,
        { jurisdiction, academicSubject: KG_SUBJECT },
      );

      // Interim: first match wins until candidate resolution lands. Warn so the
      // choice, not the model, is the suspect when a result looks wrong.
      if (ambiguous) {
        this.logger.warn('Statement code matched multiple standards; evaluating the first', {
          evaluator: EVALUATOR_ID,
          statementCode,
          jurisdiction,
          chosenUuid: uuid,
          chosenDescription: description,
        });
      }

      if (components.length === 0) {
        return { statementCode, learningComponents: [], alignedCount: 0, totalCount: 0 };
      }

      // Include the KG identifier in brackets so the model can echo it back,
      // allowing us to verify each evaluation maps to the correct LC.
      const lcList = components
        .map((lc, i) => `${i + 1}. [${lc.identifier}] ${lc.description}`)
        .join('\n');

      const inputs: Record<string, string> = {
        question,
        learning_components: lcList,
        n: String(components.length),
      };

      const response = await this.detailProvider.generateStructured({
        messages: [
          { role: 'system', content: getSystemPrompt(inputs) },
          { role: 'user', content: getUserPrompt(inputs) },
        ],
        schema: BatchedLCEvaluationSchema,
        temperature: TEMPERATURE,
      });

      const { evaluations } = response.data;

      // Index by the KG identifier the model echoed back.
      const sentIds = new Set(components.map((lc) => lc.identifier));
      const evalById = new Map(
        evaluations
          .filter((e: { lc_id: string }) => sentIds.has(e.lc_id))
          .map((e: { lc_id: string; reasoning: string; answer: 'Yes' | 'No'; feedback: string }) =>
            [e.lc_id, e]
          )
      );

      // Verify every LC we sent has a verified response.
      const missingIds = components
        .map((lc) => lc.identifier)
        .filter((id) => !evalById.has(id));

      if (missingIds.length > 0) {
        throw new APIError(
          `LLM response missing verified evaluations for LC identifiers: ${missingIds.join(', ')}. ` +
          `Standard: ${statementCode}`,
        );
      }

      const latencyMs = Date.now() - startTime;
      const tokenUsage = {
        input_tokens: response.usage.inputTokens,
        output_tokens: response.usage.outputTokens,
      };

      stageDetails.push({
        stage: STEP.id,
        provider: this.detailProvider.label,
        latency_ms: response.latencyMs,
        token_usage: tokenUsage,
      });

      const learningComponents: LearningComponentResult[] = components.map((lc) => {
        const ev = evalById.get(lc.identifier)!;
        return {
          identifier: lc.identifier,
          description: lc.description,
          reasoning: ev.reasoning,
          aligned: ev.answer === 'Yes',
          feedback: ev.feedback,
        };
      });

      const alignedCount = learningComponents.filter((lc) => lc.aligned).length;

      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: question.length,
        provider: this.detailProvider.label,
        tokenUsage,
        metadata: { stage_details: stageDetails },
        inputText: question,
      }).catch(() => undefined);

      return { statementCode, learningComponents, alignedCount, totalCount: components.length };
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      const tokenUsage = stageDetails.length > 0
        ? {
            input_tokens: stageDetails.reduce((s, d) => s + (d.token_usage?.input_tokens ?? 0), 0),
            output_tokens: stageDetails.reduce((s, d) => s + (d.token_usage?.output_tokens ?? 0), 0),
          }
        : undefined;

      this.sendTelemetry({
        status: 'error',
        latencyMs,
        textLength: question.length,
        provider: this.detailProvider.label,
        tokenUsage,
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
        inputText: question,
      }).catch(() => undefined);

      if (error instanceof EvaluatorError) throw error;
      throw wrapProviderError(error, 'Math standards alignment evaluation failed');
    }
  }

  private async runCoarseFilter(
    question: string,
    statementCodes: string[],
    jurisdiction: Jurisdiction,
  ): Promise<Set<string>> {
    try {
      // Fetch standard descriptions concurrently so the model has real content to
      // reason about rather than opaque codes like "3.MD.C.7.d".
      const infos = await Promise.all(
        statementCodes.map((code) =>
          this.kgClient.getStandardInfo(code, { jurisdiction, academicSubject: KG_SUBJECT })
            .catch(() => null)
        ),
      );
      const standardList = statementCodes
        .map((code, i) => {
          const desc = infos[i]?.description;
          return desc ? `${code}: ${desc}` : code;
        })
        .join('\n');

      const response = await this.coarseProvider.generateStructured({
        messages: [
          { role: 'user', content: getCoarseFilterPrompt({ question, standards: standardList }) },
        ],
        schema: CoarseFilterSchema,
      });

      const relevant = new Set<string>();
      for (const entry of response.data.standards) {
        if (entry.relevant) relevant.add(entry.standard);
      }
      // Any code the model omitted is treated as relevant to avoid silent false negatives.
      const returnedCodes = new Set(response.data.standards.map((e) => e.standard));
      for (const code of statementCodes) {
        if (!returnedCodes.has(code)) relevant.add(code);
      }
      // An ambiguous code was described by one arbitrary candidate, so filtering on
      // that description could drop a code a sibling candidate makes relevant. Fail
      // open and let detail evaluation decide, which also surfaces the warning.
      statementCodes.forEach((code, i) => {
        if (infos[i]?.ambiguous) relevant.add(code);
      });
      return relevant;
    } catch (err) {
      this.logger.warn('Coarse filter failed, passing all standards to detail eval', {
        evaluator: MathStandardsAlignmentEvaluator.metadata.id,
        operation: 'runCoarseFilter',
        error: err instanceof Error ? err : new Error(String(err)),
      });
      return new Set(statementCodes);
    }
  }

  private validateQuestion(question: string): void {
    if (question.trim().length === 0) {
      throw new ValidationError('question must not be empty');
    }
    if (question.length > MAX_QUESTION_LENGTH) {
      throw new ValidationError(
        `question exceeds maximum length of ${MAX_QUESTION_LENGTH} characters (got ${question.length})`,
      );
    }
  }

  private validateStatementCode(code: string): void {
    if (code.trim().length === 0) {
      throw new ValidationError('statementCode must not be empty');
    }
  }
}

export async function evaluateMathStandardsAlignment(
  question: string,
  statementCode: string,
  jurisdiction: Jurisdiction,
  config: MathStandardsAlignmentEvaluatorConfig,
): Promise<StandardAlignmentResult> {
  return new MathStandardsAlignmentEvaluator(config).evaluate(question, statementCode, jurisdiction);
}
