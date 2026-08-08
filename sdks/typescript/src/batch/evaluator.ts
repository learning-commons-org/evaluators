import pLimit from 'p-limit';
import { Provider } from '../evaluators/base.js';
import type {
  BatchInput,
  BatchTask,
  BatchResult,
  BatchOutput,
  BatchConfig,
  BatchSummary,
  EvaluatorGroup,
} from './types.js';
import {
  type EvaluatorFamily,
  type FamilyRow,
  type FamilyRunContext,
  type FamilyRunner,
  normalizeRow,
  resolveMembers,
  validateRequiredColumns,
} from './families/family.js';
import { getFamilies, getFamily } from './families/registry.js';

export { getFamilies, getFamily } from './families/registry.js';

/**
 * Backward-compatible view of families as the older "evaluator group" shape.
 * @deprecated Use {@link getFamilies} — retained for the current CLI wiring.
 */
export function getAvailableGroups(): EvaluatorGroup[] {
  return getFamilies().map((family) => {
    const keys = family.requiredKeys(family.members.map((m) => m.id));
    return {
      id: family.id,
      name: family.name,
      description: family.description,
      evaluatorIds: family.members.map((m) => m.id),
      requiresGoogleKey: keys.includes(Provider.Google),
      requiresOpenAIKey: keys.includes(Provider.OpenAI),
      maxInputRows: family.maxInputRows,
    };
  });
}

export interface BatchRunOptions {
  selectedMemberIds?: string[];
  onProgress?: (result: BatchResult) => void;
}

/**
 * Batch evaluator: runs the selected members of one family over a set of input
 * rows. Owns orchestration — concurrency, cancellation, timing, error handling
 * — while each family owns how to invoke its evaluators and what columns/keys
 * it needs.
 */
export class BatchEvaluator {
  private config: BatchConfig;
  private limit: ReturnType<typeof pLimit>;
  private isCancelled = false;
  private completedResults: BatchResult[] = [];

  constructor(config: BatchConfig) {
    this.config = {
      concurrency: 3,
      maxRetries: 2,
      telemetry: true, // Opt out with --no-telemetry
      bypassRowLimit: false,
      ...config,
    };
    this.limit = pLimit(this.config.concurrency ?? 3);
  }

  /** Cancel ongoing evaluation. Returns partial results collected so far. */
  cancel(): BatchResult[] {
    this.isCancelled = true;
    return [...this.completedResults];
  }

  private buildContext(): FamilyRunContext {
    return {
      googleApiKey: this.config.googleApiKey,
      openaiApiKey: this.config.openaiApiKey,
      anthropicApiKey: this.config.anthropicApiKey,
      platformApiKey: this.config.platformApiKey,
      maxRetries: this.config.maxRetries,
      telemetry: this.config.telemetry,
      modelOverride: this.config.modelOverride,
      llmProvider: this.config.llmProvider,
      concurrency: this.config.concurrency,
      kgConcurrency: this.config.kgConcurrency,
    };
  }

  private errorResult(
    row: FamilyRow,
    memberId: string,
    error: string,
    processingTimeMs = 0,
  ): BatchResult {
    return {
      rowIndex: row.rowIndex,
      text: row.columns.text ?? row.columns.question ?? '',
      grade: row.columns.grade ?? '',
      evaluatorId: memberId,
      status: 'error',
      error,
      processingTimeMs,
      originalRow: row.originalRow,
    };
  }

  private async executeTask(
    runner: FamilyRunner,
    task: BatchTask,
    onProgress?: (result: BatchResult) => void,
  ): Promise<BatchResult> {
    const row = task.row;

    if (this.isCancelled) {
      const cancelled = this.errorResult(row, task.memberId, 'Cancelled by user');
      this.completedResults.push(cancelled);
      onProgress?.(cancelled);
      return cancelled;
    }

    const startTime = Date.now();
    try {
      const outcome = await runner.runTask(row, task.memberId);
      const result: BatchResult = {
        rowIndex: row.rowIndex,
        text: row.columns.text ?? row.columns.question ?? '',
        grade: row.columns.grade ?? '',
        evaluatorId: task.memberId,
        status: 'success',
        score: outcome.score,
        reasoning: outcome.reasoning,
        payload: outcome.payload,
        processingTimeMs: Date.now() - startTime,
        originalRow: row.originalRow,
      };
      this.completedResults.push(result);
      onProgress?.(result);
      return result;
    } catch (error) {
      const result = this.errorResult(
        row,
        task.memberId,
        error instanceof Error ? error.message : String(error),
        Date.now() - startTime,
      );
      this.completedResults.push(result);
      onProgress?.(result);
      return result;
    }
  }

  private calculateSummary(results: BatchResult[], durationMs: number): BatchSummary {
    const summary: BatchSummary = {
      totalTasks: results.length,
      successful: results.filter((r) => r.status === 'success').length,
      failed: results.filter((r) => r.status === 'error').length,
      durationMs,
      resultsPerEvaluator: {},
    };

    const evaluatorIds = Array.from(new Set(results.map((r) => r.evaluatorId)));
    for (const id of evaluatorIds) {
      const evalResults = results.filter((r) => r.evaluatorId === id);
      summary.resultsPerEvaluator[id] = {
        successful: evalResults.filter((r) => r.status === 'success').length,
        failed: evalResults.filter((r) => r.status === 'error').length,
      };
    }
    return summary;
  }

  /**
   * Run batch evaluation for a family.
   *
   * @param inputs - Raw input rows (columns keyed by CSV header)
   * @param family - The family to run: an id (see getFamilies()) or a family object
   * @param options - Member selection and progress callback. For backward
   *   compatibility a bare `onProgress` callback is also accepted here.
   */
  async evaluate(
    inputs: BatchInput[],
    family: string | EvaluatorFamily,
    options: BatchRunOptions | BatchRunOptions['onProgress'] = {},
  ): Promise<BatchOutput> {
    const startTime = Date.now();
    // Back-compat: the previous signature took an onProgress callback as the
    // third argument; treat a function here as `{ onProgress }`.
    const opts: BatchRunOptions = typeof options === 'function' ? { onProgress: options } : options;
    const resolvedFamily: EvaluatorFamily = typeof family === 'string' ? getFamily(family) : family;
    return this.run(inputs, resolvedFamily, opts, startTime);
  }

  private async run(
    inputs: BatchInput[],
    family: EvaluatorFamily,
    options: BatchRunOptions,
    startTime: number,
  ): Promise<BatchOutput> {

    if (!this.config.bypassRowLimit && inputs.length > family.maxInputRows) {
      throw new Error(
        `Input exceeds limit for "${family.id}": ${inputs.length} rows (max ${family.maxInputRows}). ` +
          `Split into smaller batches, or pass { bypassRowLimit: true } in BatchConfig (use --bypass-row-limit on the CLI).`,
      );
    }

    // Reset state
    this.isCancelled = false;
    this.completedResults = [];

    if (inputs.length === 0) {
      return { results: [], summary: this.calculateSummary([], Date.now() - startTime) };
    }

    // Fail fast on a missing required column (header-level), then normalize
    // each row. A row that fails normalization becomes an error result rather
    // than aborting the whole run.
    validateRequiredColumns(family, Object.keys(inputs[0].columns));
    const members = resolveMembers(family, options.selectedMemberIds);
    const runner = family.createRunner(this.buildContext(), options.selectedMemberIds);

    const rows: FamilyRow[] = [];
    const preFailed: BatchResult[] = [];
    for (const input of inputs) {
      try {
        rows.push(normalizeRow(input, family));
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const badRow: FamilyRow = { rowIndex: input.rowIndex, columns: {}, originalRow: input.originalRow };
        for (const member of members) {
          const failed = this.errorResult(badRow, member.id, message);
          preFailed.push(failed);
          this.completedResults.push(failed);
          options.onProgress?.(failed);
        }
      }
    }

    const tasks: BatchTask[] = [];
    for (const row of rows) {
      for (const member of members) {
        tasks.push({ row, memberId: member.id });
      }
    }

    const settled = await Promise.allSettled(
      tasks.map((task) => this.limit(() => this.executeTask(runner, task, options.onProgress))),
    );
    const results = [
      ...preFailed,
      ...settled
        .filter((r): r is PromiseFulfilledResult<BatchResult> => r.status === 'fulfilled')
        .map((r) => r.value),
    ];

    const durationMs = Date.now() - startTime;
    return { results, summary: this.calculateSummary(results, durationMs) };
  }
}
