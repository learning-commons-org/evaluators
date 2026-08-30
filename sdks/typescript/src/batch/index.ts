/**
 * Batch evaluation module
 *
 * Programmatic API for running an evaluator group over a set of texts.
 *
 * @example
 * ```typescript
 * import { BatchEvaluator, getFamilies, parseCSV, formatAsCSV } from '@learning-commons/evaluators/batch';
 *
 * const [family] = getFamilies(); // 'text-complexity'
 * const inputs = parseCSV('./texts.csv');
 * const evaluator = new BatchEvaluator({ googleApiKey, openaiApiKey });
 * const output = await evaluator.evaluate(inputs, group.id);
 * console.log(formatAsCSV(output));
 * ```
 */

export { BatchEvaluator, getFamilies, getFamily } from './evaluator.js';
export type { BatchRunOptions } from './evaluator.js';
export { parseCSV } from './csv.js';
export { formatAsCSV, formatAsHTML, formatAsJSON } from './formatters.js';
export type { ReportMeta } from './formatters.js';
export { renderOutputs } from './output.js';
export type { OutputBundle } from './output.js';
export type {
  EvaluatorFamily,
  FamilyMember,
  FamilyRow,
  ColumnSpec,
  KeyKind,
} from './families/family.js';
export type {
  BatchInput,
  BatchResult,
  BatchOutput,
  BatchConfig,
  BatchSummary,
} from './types.js';
export { Provider, type ModelOverride } from '../evaluators/base.js';
