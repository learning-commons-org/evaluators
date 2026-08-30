import {
  SentenceStructureOutputSchema,
  type SentenceStructureResult,
} from '../../../schemas/student-facing-text/ela-reading/sentence-structure.js';
import {
  SentenceAnalysisSchema,
  type SentenceAnalysis,
} from '../../../schemas/student-facing-text/ela-reading/sentence-structure-steps.js';
import {
  addEngineeredFeatures,
  featuresToJSON,
  formatGroundTruthCounts,
} from '../../../features/index.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineMultiStepEvaluator } from '../../multi-step.js';
import type { InputsOf } from '../../inputs.js';
import ANALYSIS_SYSTEM from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/analysis-system.txt';
import ANALYSIS_USER from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/analysis-user.txt';
import COMPLEXITY_SYSTEM from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/complexity-system.txt';
import COMPLEXITY_USER from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/complexity-user.txt';
import RUBRIC_GRADE_3 from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/rubric-grade-3.txt';
import RUBRIC_GRADE_4 from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/rubric-grade-4.txt';
import RUBRIC_GRADES_5_12 from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/rubric-grades-5-12.txt';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/config.json';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type SentenceStructureInput = InputsOf<{ properties: Record<'text' | 'grade_level', unknown> }>;

/**
 * Evaluates sentence-structure complexity in student-facing text.
 *
 * Two model calls, so the flow comes from {@link defineMultiStepEvaluator}: the first step
 * counts grammatical features, and the second classifies complexity against the rubric for
 * the grade. Which rubric that is, the order the steps run in, and the fact that the second
 * step reads the first one's output are all read from `config.json`.
 *
 * The two computations below are supplied in code because the contract declares them as
 * `custom` — it names the function rather than describing it — and are keyed by the name it
 * declares, so a contract naming something else fails at load.
 *
 * @example
 * ```typescript
 * const evaluator = new SentenceStructureEvaluator({
 *   openaiApiKey: process.env.OPENAI_API_KEY,
 * });
 *
 * const result = await evaluator.evaluate({
 *   text: 'The mitochondria is the powerhouse of the cell. It produces energy.',
 *   grade_level: '5',
 * });
 * ```
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If a step's response fails its output schema
 */
export class SentenceStructureEvaluator extends defineMultiStepEvaluator<
  SentenceStructureInput,
  SentenceStructureResult
>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: SentenceStructureOutputSchema,
  steps: {
    sentence_analysis: {
      system: ANALYSIS_SYSTEM,
      user: ANALYSIS_USER,
      schema: SentenceAnalysisSchema,
    },
    // The final step's output is the result, so its schema is `outputSchema` above.
    classify_complexity: {
      system: COMPLEXITY_SYSTEM,
      user: COMPLEXITY_USER,
    },
  },
  computations: {
    // The contract names the metrics function; the block layout is what the prompt
    // declares, so the two travel together.
    calculateReadabilityMetrics: (text) => formatGroundTruthCounts(String(text)),
    // Cast to int and single-space, matching the Python implementation's JSON.
    addEngineeredFeatures: (analysis) =>
      featuresToJSON(addEngineeredFeatures(analysis as SentenceAnalysis), 1, true),
  },
  documents: {
    'rubric-grade-3.txt': RUBRIC_GRADE_3,
    'rubric-grade-4.txt': RUBRIC_GRADE_4,
    'rubric-grades-5-12.txt': RUBRIC_GRADES_5_12,
  },
}) {}

/**
 * Functional API for sentence structure.
 *
 * @example
 * ```typescript
 * const result = await evaluateSentenceStructure(
 *   { text: 'The mitochondria is the powerhouse of the cell. It produces energy.', grade_level: '5' },
 *   { openaiApiKey: process.env.OPENAI_API_KEY },
 * );
 * ```
 */
export async function evaluateSentenceStructure(
  input: SentenceStructureInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<SentenceStructureResult>> {
  return new SentenceStructureEvaluator(config).evaluate(input);
}
