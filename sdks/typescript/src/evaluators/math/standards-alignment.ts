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
  SUPPORTED_GRADES,
} from '../../prompts/math/standards-alignment/index.js';
import { KnowledgeGraphClient, Jurisdiction } from '../../knowledge-graph/index.js';
import { EvaluatorError, DependencyError, ConfigurationError, InputValidationError, LLMOutputProcessingError, wrapProviderError } from '../../errors.js';
import type { StageDetail } from '../../telemetry/index.js';
import CONFIG from '../../../../../evals/academic-standards-alignment/mathematics/math-standards-alignment/config.json';
import INPUT_SCHEMA from '../../../../../evals/academic-standards-alignment/mathematics/math-standards-alignment/input_schema.json';
import { validateInputs, type InputsOf } from '../inputs.js';

const EVALUATOR_ID = CONFIG.evaluator.id;

/**
 * What this evaluator accepts, taken from its `input_schema.json`.
 *
 * `jurisdiction` keeps the narrow union: the schema supplies the key set, and the
 * SDK has a stronger type for that field than an imported JSON can carry.
 */
/** The question alone, for validating one item of a bulk request. */
const QUESTION_ONLY_SCHEMA = {
  properties: { question: INPUT_SCHEMA.properties.question },
  required: ['question'],
};

export type MathStandardsAlignmentInput = InputsOf<typeof INPUT_SCHEMA> & {
  jurisdiction: Jurisdiction;
};

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
  /**
   * Set when this pair could not be evaluated. Produced only by evaluateItems and
   * evaluateByGradeLevel; evaluate() throws instead.
   *
   * Not evidence of non-alignment: alignedCount is 0 because nothing was
   * measured, not because nothing aligned.
   *
   * `name` is the error class, which is what a report groups failures on.
   */
  error?: {
    message: string;
    name?: string;
    statusCode?: number;
    retryable?: boolean;
  };
}

export interface QuestionItem {
  question: string;
  statementCodes: string[];
}

/** One question's results. `error` is set when the question itself could not be used. */
export interface QuestionResult {
  question: string;
  standards: StandardAlignmentResult[];
  error?: StandardAlignmentResult['error'];
}

export interface QuestionBankResult {
  byQuestion: QuestionResult[];
  byStandard: Array<{
    statementCode: string;
    coveredBy: Array<{
      question: string;
      alignedCount: number;
      totalCount: number;
    }>;
    coverageCount: number;
    /**
     * Denominators for coverageCount. The four sum to the number of questions, so a
     * zero coverageCount can be attributed: measured and unaligned (evaluatedCount),
     * never measured (errorCount, filteredCount, noComponentsCount).
     */
    evaluatedCount: number;
    errorCount: number;
    filteredCount: number;
    /** Standard exists but nothing is authored against it, so nothing was measurable. */
    noComponentsCount: number;
  }>;
}

export interface QuestionBankOptions {
  /**
   * Max concurrent LLM calls for this call only. Omit to share the evaluator-wide
   * limit (config.concurrency); supplying it lets N concurrent calls each run this
   * many in flight.
   */
  concurrency?: number;
  useCoarseFilter?: boolean;
  onProgress?: (completed: number, total: number) => void;
}

export interface MathStandardsAlignmentEvaluatorConfig extends BaseEvaluatorConfig {
  /** Learning Commons API key — required by this evaluator, for Knowledge Graph access */
  learningCommonsApiKey?: string;
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
const TEMPERATURE: number | null = STEP.generation.temperature;
const KG_SUBJECT = 'Mathematics';
/**
 * Above this many question/standard pairs, evaluateByGradeLevel warns. A grade level can carry
 * over a thousand standards in some jurisdictions, so a handful of questions is
 * enough to run into five figures of LLM calls.
 */
const BY_GRADE_WARN_PAIRS = 500;

/** Flattens a thrown value into the reportable shape, keeping what a report can group on. */
function describeFailure(err: unknown): NonNullable<StandardAlignmentResult['error']> {
  if (!(err instanceof Error)) return { message: String(err) };
  // `name` is the canonical error code, so there is no separate code field.
  return {
    message: err.message,
    name: err.name,
    ...(err instanceof DependencyError && err.statusCode !== null
      ? { statusCode: err.statusCode }
      : {}),
    ...(err instanceof EvaluatorError ? { retryable: err.retryable } : {}),
  };
}

// ---------------------------------------------------------------------------
// Evaluator
// ---------------------------------------------------------------------------

export class MathStandardsAlignmentEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    supportedGrades: SUPPORTED_GRADES as string[],
    defaultProviders: [Provider.Anthropic] as const,
  };

  private readonly kgClient: KnowledgeGraphClient;
  private readonly detailProvider: LLMProvider;
  private readonly coarseProvider: LLMProvider;
  // Instance-wide so concurrent evaluateItems calls share one budget.
  private readonly llmLimit: ReturnType<typeof pLimit>;

  constructor(config: MathStandardsAlignmentEvaluatorConfig) {
    super(config);

    if (!config.learningCommonsApiKey && !config._kgClient) {
      throw new ConfigurationError(
        'MathStandardsAlignmentEvaluator requires a learningCommonsApiKey to access the Learning Commons Knowledge Graph.',
      );
    }

    this.kgClient =
      config._kgClient ??
      new KnowledgeGraphClient(config.learningCommonsApiKey!, config.kgConcurrency ?? 20);
    this.llmLimit = pLimit(config.concurrency ?? 10);

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

  async evaluate(input: MathStandardsAlignmentInput): Promise<StandardAlignmentResult> {
    validateInputs(input, INPUT_SCHEMA);
    return this._evaluateCore(input.question, input.statementCode, input.jurisdiction);
  }

  // -------------------------------------------------------------------------
  // evaluateItems — M questions × per-question standards
  //
  // Each item specifies its own statementCodes list. Use this for:
  //   - Tagging validation: verify a question covers its pre-mapped standards
  //   - Grade-level coverage: pass the same codes to all items (evaluateByGradeLevel does this)
  //
  // Set options.useCoarseFilter to true to run a fast pre-filter before the
  // full per-LC evaluation — reduces LLM calls at scale, slight recall trade-off.
  // -------------------------------------------------------------------------

  async evaluateItems(
    items: QuestionItem[],
    jurisdiction: Jurisdiction,
    options?: QuestionBankOptions,
  ): Promise<QuestionResult[]> {
    if (items.length === 0) return [];

    // Per item, not a precondition for the whole call — an invalid item's
    // standards come back carrying the error.
    const dedupedItems = items.map((item) => {
      let validationError: EvaluatorError | undefined;
      try {
        validateInputs({ question: item.question }, QUESTION_ONLY_SCHEMA);
      } catch (err) {
        // Only a domain error is a per-item validation failure. Anything else is a
        // bug here, and turning it into a InputValidationError would report it as bad
        // user input.
        if (!(err instanceof EvaluatorError)) throw err;
        validationError = err;
      }
      return {
        question: item.question,
        statementCodes: [...new Set(item.statementCodes)],
        validationError,
      };
    });

    const useCoarseFilter = options?.useCoarseFilter ?? false;
    const bankLimit = options?.concurrency != null ? pLimit(options.concurrency) : this.llmLimit;

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

    // Coarse filter: per-item, against that item's own statementCodes. Invalid
    // items get an empty set so they stay out of the progress denominator.
    let relevanceMaps: Map<number, Set<string>>;
    if (!useCoarseFilter) {
      relevanceMaps = new Map(
        dedupedItems.map((item, i) => [i, item.validationError ? new Set<string>() : new Set(item.statementCodes)]),
      );
    } else {
      const filterResults = await Promise.all(
        dedupedItems.map((item) =>
          item.validationError
            ? Promise.resolve(new Set<string>())
            : bankLimit(() => this.runCoarseFilter(item.question, item.statementCodes, jurisdiction)),
        ),
      );
      relevanceMaps = new Map(dedupedItems.map((_, i) => [i, filterResults[i]]));
    }

    const total = dedupedItems.reduce((sum, _, i) => sum + (relevanceMaps.get(i)?.size ?? 0), 0);
    let completed = 0;

    // Failures are isolated to the pair that caused them.
    return Promise.all(
      dedupedItems.map(async (item, i) => {
        if (item.validationError) {
          const failure = describeFailure(item.validationError);
          return {
            question: item.question,
            // Also at item level: an item with no statement codes has nowhere else to
            // carry the failure, and the question itself is what failed.
            error: failure,
            standards: item.statementCodes.map((statementCode) => ({
              statementCode,
              learningComponents: [],
              alignedCount: 0,
              totalCount: 0,
              error: failure,
            })),
          };
        }

        const relevant = relevanceMaps.get(i) ?? new Set(item.statementCodes);

        const standards = await Promise.all(
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
            let result: StandardAlignmentResult;
            try {
              result = await bankLimit(() => this._evaluateCore(item.question, code, jurisdiction));
            } catch (err) {
              result = {
                statementCode: code,
                learningComponents: [],
                alignedCount: 0,
                // Report the real component count when the pre-fetch knows it, so an
                // errored pair is not mistaken for a standard with no components.
                totalCount: lcCache.get(code)?.components.length ?? 0,
                error: describeFailure(err),
              };
            }

            // Outside the try: counting inside it let a throwing callback discard a
            // finished result, count the pair twice, and reject the whole call.
            completed++;
            this.notifyProgress(options?.onProgress, completed, total);
            return result;
          }),
        );

        return { question: item.question, standards };
      }),
    );
  }

  // -------------------------------------------------------------------------
  // evaluateByGradeLevel — fetches all math standards for a grade level, then evaluates
  //
  // Use when you don't have a predetermined standards list. Jurisdiction
  // determines which state's adopted standards are fetched from the KG.
  // Returns both a by-question and by-standard view of coverage.
  // -------------------------------------------------------------------------

  async evaluateByGradeLevel(
    questions: string[],
    gradeLevel: string,
    jurisdiction: Jurisdiction,
    options?: QuestionBankOptions,
  ): Promise<QuestionBankResult> {
    if (questions.length === 0) throw new InputValidationError('questions array must not be empty');
    this.validateGradeLevel(gradeLevel, new Set(SUPPORTED_GRADES));

    const academicStandards = await this.kgClient.getStandardsByGradeLevel(gradeLevel, {
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
        gradeLevel,
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
      const results = byQuestion.map(({ question, standards }) => ({
        question,
        result: standards.find((s) => s.statementCode === code),
      }));

      const coveredBy = results.flatMap(({ question, result }) => {
        // An errored pair measured nothing, so it is neither coverage nor
        // evidence against it.
        if (!result || result.error || result.alignedCount === 0) return [];
        return [{ question, alignedCount: result.alignedCount, totalCount: result.totalCount }];
      });

      return {
        statementCode: code,
        coveredBy,
        coverageCount: coveredBy.length,
        // totalCount > 0 required: a standard with no learning components measured
        // nothing, so counting it as evaluated would make "0 aligned of 1 evaluated"
        // read as a judgement rather than an absence of data.
        evaluatedCount: results.filter(
          ({ result }) => result && !result.error && !result.coarseFiltered && result.totalCount > 0,
        ).length,
        errorCount: results.filter(({ result }) => result?.error).length,
        filteredCount: results.filter(({ result }) => result?.coarseFiltered).length,
        noComponentsCount: results.filter(
          ({ result }) => result && !result.error && !result.coarseFiltered && result.totalCount === 0,
        ).length,
      };
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
        throw new LLMOutputProcessingError(
          `LLM response missing verified evaluations for LC identifiers: ${missingIds.join(', ')}. ` +
          `Standard: ${statementCode}`,
          missingIds.map((identifier) => ({ path: 'evaluations', identifier })),
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
      throw wrapProviderError(error, this.providerContext(this.detailProvider));
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
        temperature: TEMPERATURE,
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

  /** A caller's progress callback must not be able to fail an evaluation. */
  private notifyProgress(
    onProgress: ((completed: number, total: number) => void) | undefined,
    completed: number,
    total: number,
  ): void {
    if (!onProgress) return;
    try {
      onProgress(completed, total);
    } catch (err) {
      this.logger.warn('onProgress callback threw; continuing', {
        evaluator: EVALUATOR_ID,
        error: err instanceof Error ? err : new Error(String(err)),
      });
    }
  }

}

export async function evaluateMathStandardsAlignment(
  input: MathStandardsAlignmentInput,
  config: MathStandardsAlignmentEvaluatorConfig,
): Promise<StandardAlignmentResult> {
  return new MathStandardsAlignmentEvaluator(config).evaluate(input);
}
