import pLimit from 'p-limit';
import {
  VocabularyEvaluator,
  SentenceStructureEvaluator,
  GradeLevelAppropriatenessEvaluator,
} from '../evaluators/index.js';
import type { BaseEvaluatorConfig } from '../evaluators/base.js';
import type { EvaluationResult } from '../schemas/index.js';
import type {
  BatchInput,
  BatchTask,
  BatchResult,
  BatchOutput,
  BatchConfig,
  BatchSummary,
  EvaluatorGroup,
} from './types.js';

interface SimpleEvaluator {
  evaluate(text: string, grade: string): Promise<EvaluationResult<string, unknown>>;
}

type EvaluatorConstructor = new (config: BaseEvaluatorConfig) => SimpleEvaluator;

/**
 * Map of evaluator IDs to their constructors — internal to this module.
 */
const EVALUATOR_MAP = new Map<string, EvaluatorConstructor>([
  [VocabularyEvaluator.metadata.id, VocabularyEvaluator],
  [SentenceStructureEvaluator.metadata.id, SentenceStructureEvaluator],
  [GradeLevelAppropriatenessEvaluator.metadata.id, GradeLevelAppropriatenessEvaluator],
]);

/**
 * Evaluator groups available for batch processing.
 * Each group runs a fixed set of evaluators and maps to a specific HTML report format.
 */
const EVALUATOR_GROUPS: EvaluatorGroup[] = [
  {
    id: 'text-complexity',
    name: 'Text Complexity Analysis',
    description: 'Evaluates vocabulary complexity, sentence structure, and grade-level appropriateness',
    evaluatorIds: [
      VocabularyEvaluator.metadata.id,
      SentenceStructureEvaluator.metadata.id,
      GradeLevelAppropriatenessEvaluator.metadata.id,
    ],
    requiresGoogleKey: true,
    requiresOpenAIKey: true,
    maxInputRows: 50,
  },
];

/**
 * Returns the available evaluator groups.
 */
export function getAvailableGroups(): EvaluatorGroup[] {
  return [...EVALUATOR_GROUPS];
}

/**
 * Batch evaluator class
 *
 * Processes multiple texts in parallel using all evaluators in a group.
 */
export class BatchEvaluator {
  private config: BatchConfig;
  private limit: ReturnType<typeof pLimit>;
  private evaluatorInstances = new Map<string, SimpleEvaluator>();
  private isCancelled = false;
  private completedResults: BatchResult[] = [];

  constructor(config: BatchConfig) {
    this.config = {
      concurrency: 3,
      maxRetries: 2,
      telemetry: false,
      ...config,
    };

    this.limit = pLimit(this.config.concurrency!);
  }

  /**
   * Cancel ongoing evaluation.
   * Returns partial results collected so far.
   */
  cancel(): BatchResult[] {
    this.isCancelled = true;
    return [...this.completedResults];
  }

  /**
   * Initialize evaluator instances for the given IDs
   */
  private initializeEvaluators(evaluatorIds: readonly string[]): void {
    for (const id of evaluatorIds) {
      if (this.evaluatorInstances.has(id)) continue;

      const EvaluatorClass = EVALUATOR_MAP.get(id);
      if (!EvaluatorClass) {
        throw new Error(`Unknown evaluator: ${id}`);
      }

      const evaluator = new EvaluatorClass({
        googleApiKey: this.config.googleApiKey,
        openaiApiKey: this.config.openaiApiKey,
        maxRetries: this.config.maxRetries,
        telemetry: this.config.telemetry,
      });

      this.evaluatorInstances.set(id, evaluator);
    }
  }

  /**
   * Create tasks from inputs and evaluator IDs
   */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private createTasks(inputs: BatchInput[], evaluatorIds: readonly string[]): Array<BatchTask & { originalRow: Record<string, unknown> }> {
    const tasks: Array<BatchTask & { originalRow: Record<string, unknown> }> = [];

    for (const input of inputs) {
      for (const evaluatorId of evaluatorIds) {
        tasks.push({
          text: input.text,
          grade: input.grade,
          evaluatorId,
          rowIndex: input.rowIndex,
          originalRow: input.originalRow,
        });
      }
    }

    return tasks;
  }

  /**
   * Execute a single evaluation task
   */
  private async executeTask(
    task: BatchTask & { originalRow: Record<string, unknown> },
    onProgress?: (result: BatchResult) => void
  ): Promise<BatchResult> {
    // Check if cancelled before starting
    if (this.isCancelled) {
      const batchResult: BatchResult = {
        rowIndex: task.rowIndex,
        text: task.text,
        grade: task.grade,
        evaluatorId: task.evaluatorId,
        status: 'error',
        error: 'Cancelled by user',
        processingTimeMs: 0,
        originalRow: task.originalRow,
      };
      return batchResult;
    }

    const startTime = Date.now();
    const evaluator = this.evaluatorInstances.get(task.evaluatorId);

    if (!evaluator) {
      const batchResult: BatchResult = {
        rowIndex: task.rowIndex,
        text: task.text,
        grade: task.grade,
        evaluatorId: task.evaluatorId,
        status: 'error',
        error: `Evaluator not initialized: ${task.evaluatorId}`,
        processingTimeMs: 0,
        originalRow: task.originalRow,
      };
      this.completedResults.push(batchResult);
      if (onProgress) onProgress(batchResult);
      return batchResult;
    }

    try {
      const result = await evaluator.evaluate(task.text, task.grade);

      const batchResult: BatchResult = {
        rowIndex: task.rowIndex,
        text: task.text,
        grade: task.grade,
        evaluatorId: task.evaluatorId,
        status: 'success',
        score: result.score,
        reasoning: result.reasoning,
        processingTimeMs: Date.now() - startTime,
        originalRow: task.originalRow,
      };

      // Store completed result
      this.completedResults.push(batchResult);

      // Report progress
      if (onProgress) onProgress(batchResult);

      return batchResult;
    } catch (error) {
      const batchResult: BatchResult = {
        rowIndex: task.rowIndex,
        text: task.text,
        grade: task.grade,
        evaluatorId: task.evaluatorId,
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
        processingTimeMs: Date.now() - startTime,
        originalRow: task.originalRow,
      };

      // Store completed result (even errors)
      this.completedResults.push(batchResult);

      // Report progress
      if (onProgress) onProgress(batchResult);

      return batchResult;
    }
  }

  /**
   * Calculate summary statistics
   */
  private calculateSummary(results: BatchResult[], durationMs: number): BatchSummary {
    const summary: BatchSummary = {
      totalTasks: results.length,
      successful: results.filter((r) => r.status === 'success').length,
      failed: results.filter((r) => r.status === 'error').length,
      durationMs,
      resultsPerEvaluator: {},
    };

    // Calculate per-evaluator stats
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
   * Run batch evaluation for an evaluator group.
   *
   * @param inputs - Array of input rows
   * @param groupId - The evaluator group to run (see getAvailableGroups())
   * @param onProgress - Optional callback invoked after each task completes
   * @returns Batch evaluation results and summary
   */
  async evaluate(
    inputs: BatchInput[],
    groupId: string,
    onProgress?: (result: BatchResult) => void
  ): Promise<BatchOutput> {
    const startTime = Date.now();

    // Resolve group
    const group = EVALUATOR_GROUPS.find((g) => g.id === groupId);
    if (!group) {
      throw new Error(
        `Unknown evaluator group: "${groupId}". Available: ${EVALUATOR_GROUPS.map((g) => g.id).join(', ')}`
      );
    }

    // Enforce per-group row limit
    if (inputs.length > group.maxInputRows) {
      throw new Error(
        `Input exceeds limit for "${group.id}": ${inputs.length} rows (max ${group.maxInputRows}). Split into smaller batches.`
      );
    }

    // Reset state
    this.isCancelled = false;
    this.completedResults = [];

    // Initialize evaluator instances
    this.initializeEvaluators(group.evaluatorIds);

    // Create all tasks (flattened: inputs × evaluators)
    const tasks = this.createTasks(inputs, group.evaluatorIds);

    // Execute all tasks with concurrency control
    // Use allSettled to get partial results even if cancelled
    const settledResults = await Promise.allSettled(
      tasks.map((task) => this.limit(() => this.executeTask(task, onProgress)))
    );

    // Extract fulfilled results (skip rejected)
    const results = settledResults
      .filter((r): r is PromiseFulfilledResult<BatchResult> => r.status === 'fulfilled')
      .map((r) => r.value);

    // Calculate summary
    const durationMs = Date.now() - startTime;
    const summary = this.calculateSummary(results, durationMs);

    return { results, summary };
  }
}
