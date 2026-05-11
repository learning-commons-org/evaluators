/**
 * Batch evaluation types
 */
import type { TelemetryOptions } from '../evaluators/base.js';

/**
 * Input row from CSV
 */
export interface BatchInput {
  text: string;
  grade: string;
  rowIndex: number;
  originalRow: Record<string, unknown>; // Preserve all original CSV columns
}

/**
 * Individual evaluation task
 */
export interface BatchTask {
  text: string;
  grade: string;
  evaluatorId: string;
  rowIndex: number;
}

/**
 * Result from a single evaluation
 */
export interface BatchResult {
  rowIndex: number;
  text: string;
  grade: string;
  evaluatorId: string;
  status: 'success' | 'error';
  score?: string;
  reasoning?: string;
  error?: string;
  processingTimeMs: number;
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
 * A named group of evaluators that run together and share an HTML report format.
 * This is the unit of selection exposed to users.
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
  litellmApiKey?: string;
  litellmBaseURL?: string;
  concurrency?: number;
  maxRetries?: number;
  telemetry?: boolean | TelemetryOptions;
}
