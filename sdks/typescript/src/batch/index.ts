/**
 * Batch evaluation module
 *
 * Programmatic API for running an evaluator group over a set of texts.
 *
 * @example
 * ```typescript
 * import { BatchEvaluator, getAvailableGroups, parseCSV, formatAsCSV } from '@learning-commons/evaluators/batch';
 *
 * const [group] = getAvailableGroups(); // 'text-complexity'
 * const inputs = parseCSV('./texts.csv');
 * const evaluator = new BatchEvaluator({ googleApiKey, openaiApiKey });
 * const output = await evaluator.evaluate(inputs, group.id);
 * console.log(formatAsCSV(output));
 * ```
 */

export { BatchEvaluator, getAvailableGroups } from './evaluator.js';
export { parseCSV } from './csv.js';
export { formatAsCSV, formatAsHTML } from './formatters.js';
export type { ReportMeta } from './formatters.js';
export type {
  EvaluatorGroup,
  BatchInput,
  BatchResult,
  BatchOutput,
  BatchConfig,
  BatchSummary,
} from './types.js';
export { Provider, type ModelOverride } from '../evaluators/base.js';
