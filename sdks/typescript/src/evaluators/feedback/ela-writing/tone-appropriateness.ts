import { ToneAppropriatenessOutputSchema, type ToneAppropriatenessResult } from '../../../schemas/feedback/ela-writing/tone-appropriateness.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import SYSTEM_PROMPT from '../../../../../../evals/feedback/ela-writing/tone-appropriateness/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/feedback/ela-writing/tone-appropriateness/user.txt';
import CONFIG from '../../../../../../evals/feedback/ela-writing/tone-appropriateness/config.json';
import INPUT_SCHEMA from '../../../../../../evals/feedback/ela-writing/tone-appropriateness/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
import type { ToneAppropriatenessInput } from '../../../schemas/feedback/ela-writing/tone-appropriateness.js';

export type { ToneAppropriatenessInput };

/**
 * Judges whether the feedback addresses the work rather than the student.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and the model,
 * temperature and prompt inputs are read from `config.json`.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class ToneAppropriatenessEvaluator extends defineSingleStepEvaluator<ToneAppropriatenessInput, ToneAppropriatenessResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: ToneAppropriatenessOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateToneAppropriateness(
  input: ToneAppropriatenessInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<ToneAppropriatenessResult>> {
  return new ToneAppropriatenessEvaluator(config).evaluate(input);
}
