import { BackgroundKnowledgeDemandsOutputSchema, type BackgroundKnowledgeDemandsResult } from '../../../schemas/student-facing-text/ela-reading/background-knowledge-demands.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import type { InputsOf } from '../../inputs.js';
import SYSTEM_PROMPT from '../../../../../../evals/student-facing-text/ela-reading/background-knowledge-demands/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/student-facing-text/ela-reading/background-knowledge-demands/user.txt';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/background-knowledge-demands/config.json';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/background-knowledge-demands/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type BackgroundKnowledgeDemandsInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Evaluates how much prior subject knowledge a student needs to comprehend a text,
 * relative to its grade level. Based on the Qualitative Text Complexity rubric.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and
 * model, temperature, preprocessing and prompt inputs come from `config.json`; the
 * accepted inputs and grades come from `input_schema.json`. The complexity levels are
 * whatever `output_schema.json` declares, returned verbatim.
 *
 * @example
 * ```typescript
 * const evaluator = new BackgroundKnowledgeDemandsEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY,
 * });
 *
 * const result = await evaluator.evaluate({
 *   text: 'Hydraulic propulsion works by sucking water at the bow and forcing it sternward.',
 *   grade_level: '10',
 * });
 * ```
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class BackgroundKnowledgeDemandsEvaluator extends defineSingleStepEvaluator<BackgroundKnowledgeDemandsInput, BackgroundKnowledgeDemandsResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: BackgroundKnowledgeDemandsOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

/**
 * Functional API for background knowledge demands.
 *
 * @example
 * ```typescript
 * const result = await evaluateBackgroundKnowledgeDemands(
 *   { text: 'Hydraulic propulsion works by sucking water at the bow and forcing it sternward.', grade_level: '10' },
 *   { googleApiKey: process.env.GOOGLE_API_KEY },
 * );
 * ```
 */
export async function evaluateBackgroundKnowledgeDemands(
  input: BackgroundKnowledgeDemandsInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<BackgroundKnowledgeDemandsResult>> {
  return new BackgroundKnowledgeDemandsEvaluator(config).evaluate(input);
}
