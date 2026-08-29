/**
 * Batch evaluation types
 */
import type { TelemetryOptions, ModelOverride } from '../evaluators/base.js';
import type { LLMProvider } from '../providers/index.js';
import type { FamilyRow } from './families/family.js';

/**
 * Input row from CSV: canonical columns (validated + defaults applied by the
 * selected family) plus the untouched original row for passthrough into outputs.
 */
export interface BatchInput {
  rowIndex: number;
  columns: Record<string, string>;
  originalRow: Record<string, unknown>; // Preserve all original CSV columns
}

/**
 * Individual evaluation task: one family member run against one input row.
 */
export interface BatchTask {
  row: FamilyRow;
  memberId: string;
}

/**
 * Result from a single evaluation.
 *
 * `text`/`gradeLevel` are convenience projections of the corresponding columns when
 * present (used by the text-complexity report); `payload` carries the full
 * structured verdict for families whose output isn't a scalar score.
 */
export interface BatchResult {
  rowIndex: number;
  text: string;
  gradeLevel: string;
  evaluatorId: string;
  status: 'success' | 'error';
  score?: string;
  reasoning?: string;
  error?: string;
  payload?: unknown;
  processingTimeMs: number;
  /** Canonical columns after family normalization (aliases + defaults applied).
   * Absent on a hand-built result; empty for a row that failed normalization. */
  columns?: Record<string, string>;
  originalRow: Record<string, unknown>; // Preserve all original CSV columns
}

/**
 * Summary statistics for batch evaluation
 */
export interface BatchSummary {
  totalTasks: number;
  successful: number;
  failed: number;
  durationMs: number;
  resultsPerEvaluator: Record<string, { successful: number; failed: number }>;
}

/**
 * Complete batch evaluation output
 */
export interface BatchOutput {
  results: BatchResult[];
  summary: BatchSummary;
}

/**
 * The pre-family projection of an {@link EvaluatorFamily}.
 * @deprecated Prefer EvaluatorFamily, which is the unit of selection; produced only by
 * getAvailableGroups().
 */
export interface EvaluatorGroup {
  id: string;
  name: string;
  description: string;
  /** IDs of the evaluators that belong to this group */
  evaluatorIds: readonly string[];
  requiresGoogleKey: boolean;
  requiresOpenAIKey: boolean;
  /** Maximum number of input rows allowed for this group */
  maxInputRows: number;
}

/**
 * Configuration for batch evaluation
 */
export interface BatchConfig {
  googleApiKey?: string;
  openaiApiKey?: string;
  anthropicApiKey?: string;
  /** Learning Commons API key — required for families that hit the Knowledge Graph. */
  learningCommonsApiKey?: string;
  concurrency?: number;
  maxRetries?: number;
  /** Max concurrent Knowledge Graph HTTP calls, for families that use it. */
  kgConcurrency?: number;
  telemetry?: boolean | TelemetryOptions;
  bypassRowLimit?: boolean;
  modelOverride?: ModelOverride;

  /**
   * Bring your own LLM provider for every evaluator in the batch.
   * See {@link BaseEvaluatorConfig.llmProvider}. When set, no API keys are
   * required; mutually exclusive with modelOverride (setting both throws).
   */
  llmProvider?: LLMProvider;
}
