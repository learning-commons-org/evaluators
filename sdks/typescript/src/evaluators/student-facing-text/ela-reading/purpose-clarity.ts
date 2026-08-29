import { PurposeClarityOutputSchema, type PurposeClarityResult } from '../../../schemas/student-facing-text/ela-reading/purpose-clarity.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import type { InputsOf } from '../../inputs.js';
import SYSTEM_PROMPT from '../../../../../../evals/student-facing-text/ela-reading/purpose-clarity/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/student-facing-text/ela-reading/purpose-clarity/user.txt';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/purpose-clarity/config.json';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/purpose-clarity/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type PurposeClarityInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Evaluates purpose clarity in student-facing text.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and
 * model, temperature, preprocessing and prompt inputs come from `config.json`; the
 * accepted inputs and grades come from `input_schema.json`.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class PurposeClarityEvaluator extends defineSingleStepEvaluator<PurposeClarityInput, PurposeClarityResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: PurposeClarityOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluatePurposeClarity(
  input: PurposeClarityInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<PurposeClarityResult>> {
  return new PurposeClarityEvaluator(config).evaluate(input);
}
