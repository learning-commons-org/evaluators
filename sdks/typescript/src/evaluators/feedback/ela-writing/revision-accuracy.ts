import { RevisionAccuracyOutputSchema, type RevisionAccuracyResult } from '../../../schemas/feedback/ela-writing/revision-accuracy.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import SYSTEM_PROMPT from '../../../../../../evals/feedback/ela-writing/revision-accuracy/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/feedback/ela-writing/revision-accuracy/user.txt';
import CONFIG from '../../../../../../evals/feedback/ela-writing/revision-accuracy/config.json';
import INPUT_SCHEMA from '../../../../../../evals/feedback/ela-writing/revision-accuracy/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
import type { RevisionAccuracyInput } from '../../../schemas/feedback/ela-writing/revision-accuracy.js';

export type { RevisionAccuracyInput };

/**
 * Judges whether the feedback correctly identifies what the student writing needs.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and the model,
 * temperature and prompt inputs are read from `config.json`.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class RevisionAccuracyEvaluator extends defineSingleStepEvaluator<RevisionAccuracyInput, RevisionAccuracyResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: RevisionAccuracyOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateRevisionAccuracy(
  input: RevisionAccuracyInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<RevisionAccuracyResult>> {
  return new RevisionAccuracyEvaluator(config).evaluate(input);
}
