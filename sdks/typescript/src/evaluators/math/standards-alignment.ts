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
import { KnowledgeGraphClient } from '../../knowledge-graph/index.js';
import { EvaluatorError, APIError, ConfigurationError, ValidationError, wrapProviderError } from '../../errors.js';
import type { StageDetail } from '../../telemetry/index.js';

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface LearningComponentResult {
  description: string;
  reasoning: string;
  aligned: boolean;
  feedback: string;
}

export interface StandardAlignmentResult {
  statementCode: string;
  grade: string;
  learningComponents: LearningComponentResult[];
  alignedCount: number;
  totalCount: number;
  coarseFiltered?: boolean;
}

/** A single question paired with its target grade and the standards to evaluate against. */
export interface QuestionItem {
  question: string;
  grade: string;
  statementCodes: string[];
}

export interface QuestionBankResult {
  byQuestion: Array<{
    question: string;
    grade: string;
    standards: StandardAlignmentResult[];
  }>;
  byStandard: Array<{
    statementCode: string;
    coveredBy: Array<{
      question: string;
      grade: string;
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
  /** Model for coarse filter Phase 1 (default: same as detail model from config.json) */
  coarseFilterModel?: string;
  /** @internal Test seam — inject a pre-built client without a real API key */
  _kgClient?: KnowledgeGraphClient;
}

// ---------------------------------------------------------------------------
// Constants read from config.json (single source of truth)
// ---------------------------------------------------------------------------

const SUPPORTED_GRADES_SET = new Set(SUPPORTED_GRADES);
const DETAIL_MODEL: string = STEP.model.name;
const TEMPERATURE: number = STEP.generation.temperature;

// ---------------------------------------------------------------------------
// Evaluator
// ---------------------------------------------------------------------------

export class MathStandardsAlignmentEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: EVALUATOR_ID,
    name: 'Math Standards Alignment',
    description: 'Evaluates whether an assessment question aligns to a CCSS math standard via learning-component analysis',
    supportedGrades: SUPPORTED_GRADES as string[],
    defaultProviders: [Provider.OpenAI] as const,
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
      Provider.OpenAI,
      DETAIL_MODEL,
      config.openaiApiKey,
    );

    this.coarseProvider = this.createConfiguredProvider(
      Provider.OpenAI,
      config.coarseFilterModel ?? DETAIL_MODEL,
      config.openaiApiKey,
    );
  }

  // -------------------------------------------------------------------------
  // evaluate — single question × single standard (the primitive)
  // -------------------------------------------------------------------------

  async evaluate(question: string, grade: string, statementCode: string): Promise<StandardAlignmentResult> {
    this.validateQuestion(question);
    this.validateGradeInput(grade);
    this.validateStatementCode(statementCode);

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      const { components } = await this.kgClient.getLearningComponentsByCode(statementCode);

      if (components.length === 0) {
        return { statementCode, grade, learningComponents: [], alignedCount: 0, totalCount: 0 };
      }

      const lcList = components
        .map((lc, i) => `${i + 1}. ${lc.description}`)
        .join('\n');

      const inputs = {
        question,
        grade,
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

      if (evaluations.length !== components.length) {
        throw new APIError(
          `Expected ${components.length} evaluations from LLM, got ${evaluations.length}. ` +
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

      const learningComponents: LearningComponentResult[] = components.map((lc, i) => ({
        description: lc.description,
        reasoning: evaluations[i].reasoning,
        aligned: evaluations[i].aligned,
        feedback: evaluations[i].feedback,
      }));

      const alignedCount = learningComponents.filter((lc) => lc.aligned).length;

      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: question.length,
        grade,
        provider: this.detailProvider.label,
        tokenUsage,
        metadata: { stage_details: stageDetails },
        inputText: question,
      }).catch(() => undefined);

      return { statementCode, grade, learningComponents, alignedCount, totalCount: components.length };
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
        grade,
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

  // -------------------------------------------------------------------------
  // evaluateItems — M questions each with their own pre-mapped standards
  //
  // Use this when each question already has specific standards assigned to it
  // (e.g. tagging validation — "does this question actually cover its mapped standards?").
  // Each item carries its own grade since a question bank may span multiple grades.
  // -------------------------------------------------------------------------

  async evaluateItems(
    items: QuestionItem[],
    options?: QuestionBankOptions,
  ): Promise<Array<{ question: string; grade: string; standards: StandardAlignmentResult[] }>> {
    if (items.length === 0) return [];
    items.forEach((item) => {
      this.validateQuestion(item.question);
      this.validateGradeInput(item.grade);
    });

    const bankLimit = pLimit(options?.concurrency ?? this.llmConcurrency);
    const total = items.reduce((sum, item) => sum + item.statementCodes.length, 0);
    let completed = 0;

    const settled = await Promise.allSettled(
      items.map(async (item) => {
        const standardSettled = await Promise.allSettled(
          item.statementCodes.map(async (code) => {
            const result = await bankLimit(() => this.evaluate(item.question, item.grade, code));
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
          grade: item.grade,
          standards: standardSettled.map((s) =>
            s.status === 'fulfilled' ? s.value : { statementCode: '', grade: item.grade, learningComponents: [], alignedCount: 0, totalCount: 0 }
          ),
        };
      }),
    );

    const errors = settled
      .filter((s): s is PromiseRejectedResult => s.status === 'rejected')
      .map((s) => s.reason instanceof Error ? s.reason : new Error(String(s.reason)));
    if (errors.length > 0) throw errors[0];

    return (settled as Array<PromiseFulfilledResult<{ question: string; grade: string; standards: StandardAlignmentResult[] }>>).map((s) => s.value);
  }

  // -------------------------------------------------------------------------
  // evaluateQuestionBank — M questions × N standards (true cross-product)
  //
  // Use this when you have a set of questions and a target set of standards
  // and want to know which questions cover which standards (coverage/gap analysis).
  // All questions share the same statementCodes list. Each question carries its
  // own grade since a bank may span multiple grades.
  // -------------------------------------------------------------------------

  async evaluateQuestionBank(
    questions: Array<{ question: string; grade: string }>,
    statementCodes: string[],
    options?: QuestionBankOptions,
  ): Promise<QuestionBankResult> {
    if (questions.length === 0) throw new ValidationError('questions array must not be empty');
    if (statementCodes.length === 0) throw new ValidationError('statementCodes array must not be empty');

    questions.forEach((q) => {
      this.validateQuestion(q.question);
      this.validateGradeInput(q.grade);
    });

    // Deduplicate statementCodes so each standard is evaluated exactly once per question
    // and progress totals stay accurate.
    const uniqueStatementCodes = [...new Set(statementCodes)];

    // useCoarseFilter defaults to false — full evaluation for correctness.
    // Set to true for a cost-reduction pre-filter (may miss aligned standards at scale).
    const useCoarseFilter = options?.useCoarseFilter ?? false;
    const bankLimit = pLimit(options?.concurrency ?? this.llmConcurrency);

    // Phase 1 — coarse filter: one LLM call per question over all standards
    // Keyed by question index (not text) so duplicate question strings don't overwrite each other.
    let relevanceMap: Map<number, Set<string>>;

    if (!useCoarseFilter) {
      relevanceMap = new Map(questions.map((_, i) => [i, new Set(uniqueStatementCodes)]));
    } else {
      const filterResults = await Promise.all(
        questions.map((q) => bankLimit(() => this.runCoarseFilter(q.question, uniqueStatementCodes))),
      );
      relevanceMap = new Map(questions.map((_, i) => [i, filterResults[i]]));
    }

    // Pre-fetch LC data for coarse-filtered standards (needed only for totalCount in skipped results)
    const total = questions.reduce((sum, _, i) => sum + (relevanceMap.get(i)?.size ?? 0), 0);
    let completed = 0;

    type LcCacheEntry = Awaited<ReturnType<KnowledgeGraphClient['getLearningComponentsByCode']>>;
    const lcCache = new Map<string, LcCacheEntry>();

    if (useCoarseFilter) {
      await Promise.all(
        uniqueStatementCodes.map((code) =>
          this.kgClient.getLearningComponentsByCode(code)
            .then((result) => lcCache.set(code, result))
            .catch(() => undefined),
        ),
      );
    }

    // Phase 2 — detail eval for pairs that survived the coarse filter
    const questionSettled = await Promise.allSettled(
      questions.map(async (q, i) => {
        const relevant = relevanceMap.get(i) ?? new Set(uniqueStatementCodes);

        const standardSettled = await Promise.allSettled(
          uniqueStatementCodes.map(async (code): Promise<StandardAlignmentResult> => {
            if (!relevant.has(code)) {
              const cached = lcCache.get(code);
              return {
                statementCode: code,
                grade: q.grade,
                learningComponents: [],
                alignedCount: 0,
                totalCount: cached?.components.length ?? 0,
                coarseFiltered: true,
              };
            }

            const result = await bankLimit(() => this.evaluate(q.question, q.grade, code));
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
          question: q.question,
          grade: q.grade,
          standards: standardSettled.map((s) =>
            s.status === 'fulfilled' ? s.value : { statementCode: '', grade: q.grade, learningComponents: [], alignedCount: 0, totalCount: 0 }
          ),
        };
      }),
    );

    const questionErrors = questionSettled
      .filter((s): s is PromiseRejectedResult => s.status === 'rejected')
      .map((s) => s.reason instanceof Error ? s.reason : new Error(String(s.reason)));
    if (questionErrors.length > 0) throw questionErrors[0];

    const byQuestion = (questionSettled as Array<PromiseFulfilledResult<{ question: string; grade: string; standards: StandardAlignmentResult[] }>>).map((s) => s.value);

    const byStandard = uniqueStatementCodes.map((code) => {
      const coveredBy = byQuestion
        .flatMap(({ question, grade, standards }) => {
          const result = standards.find((s) => s.statementCode === code);
          if (!result || result.alignedCount === 0) return [];
          return [{ question, grade, alignedCount: result.alignedCount, totalCount: result.totalCount }];
        });
      return { statementCode: code, coveredBy, coverageCount: coveredBy.length };
    });

    return { byQuestion, byStandard };
  }

  // -------------------------------------------------------------------------
  // evaluateByGrade — convenience wrapper over evaluateQuestionBank
  //
  // Fetches all CCSS math standards for a grade from KG, then runs the full
  // M×N evaluation. Use when you don't have a predetermined standards list.
  // -------------------------------------------------------------------------

  async evaluateByGrade(
    questions: Array<{ question: string; grade: string }> | string[],
    grade: string,
    options?: QuestionBankOptions,
  ): Promise<QuestionBankResult> {
    this.validateGrade(grade, new Set(SUPPORTED_GRADES));

    const normalised = (questions as Array<string | { question: string; grade: string }>).map((q) =>
      typeof q === 'string' ? { question: q, grade } : q,
    );

    const academicStandards = await this.kgClient.getStandardsByGrade(grade);
    // statementCode is nullable in the spec — skip standards without one
    const codes = academicStandards
      .map((s) => s.statementCode)
      .filter((c): c is string => c != null);

    if (codes.length === 0) {
      return {
        byQuestion: normalised.map((q) => ({ ...q, standards: [] })),
        byStandard: [],
      };
    }

    return this.evaluateQuestionBank(normalised, codes, options);
  }

  // -------------------------------------------------------------------------
  // Private helpers
  // -------------------------------------------------------------------------

  private async runCoarseFilter(question: string, statementCodes: string[]): Promise<Set<string>> {
    try {
      // Fetch standard descriptions concurrently so the model has real content to
      // reason about rather than opaque codes like "3.MD.C.7.d".
      const infos = await Promise.all(
        statementCodes.map((code) => this.kgClient.getStandardInfo(code).catch(() => ({ uuid: '', description: undefined }))),
      );
      const standardList = statementCodes
        .map((code, i) => {
          const desc = infos[i].description;
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

  private validateGradeInput(grade: string): void {
    if (!SUPPORTED_GRADES_SET.has(grade)) {
      throw new ValidationError(
        `Invalid grade "${grade}". Supported: ${[...SUPPORTED_GRADES].join(', ')}`,
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
  grade: string,
  statementCode: string,
  config: MathStandardsAlignmentEvaluatorConfig,
): Promise<StandardAlignmentResult> {
  return new MathStandardsAlignmentEvaluator(config).evaluate(question, grade, statementCode);
}
