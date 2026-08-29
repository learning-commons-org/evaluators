import { MeaningDirectnessOutputSchema, type MeaningDirectnessResult } from '../../../schemas/student-facing-text/ela-reading/meaning-directness.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import type { InputsOf } from '../../inputs.js';
import SYSTEM_PROMPT from '../../../../../../evals/student-facing-text/ela-reading/meaning-directness/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/student-facing-text/ela-reading/meaning-directness/user.txt';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/meaning-directness/config.json';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/meaning-directness/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type MeaningDirectnessInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Evaluates meaning directness in student-facing text.
 *
* Evaluates how directly a text states its meaning, as against relying on inference,
* relative to its grade level. Based on the Qualitative Text Complexity rubric.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and
 * model, temperature, preprocessing and prompt inputs come from `config.json`; the
 * accepted inputs and grades come from `input_schema.json`. The complexity levels are
 * whatever `output_schema.json` declares, returned verbatim.
 *
 * @example
 * ```typescript
 * const evaluator = new MeaningDirectnessEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY,
 * });
 *
 * const result = await evaluator.evaluate({
 *   text: 'The old man and the sea were one, bound by a rope of years.',
 *   grade_level: '8',
 * });
 * ```
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class MeaningDirectnessEvaluator extends defineSingleStepEvaluator<MeaningDirectnessInput, MeaningDirectnessResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: MeaningDirectnessOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

/**
 * Functional API for meaning directness.
 *
 * @example
 * ```typescript
 * const result = await evaluateMeaningDirectness(
 *   { text: 'The old man and the sea were one, bound by a rope of years.', grade_level: '8' },
 *   { googleApiKey: process.env.GOOGLE_API_KEY },
 * );
 * ```
 */
export async function evaluateMeaningDirectness(
  input: MeaningDirectnessInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<MeaningDirectnessResult>> {
  return new MeaningDirectnessEvaluator(config).evaluate(input);
}
