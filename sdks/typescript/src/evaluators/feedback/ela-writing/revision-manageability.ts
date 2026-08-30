import { RevisionManageabilityOutputSchema, type RevisionManageabilityResult } from '../../../schemas/feedback/ela-writing/revision-manageability.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import type { InputsOf } from '../../inputs.js';
import SYSTEM_PROMPT from '../../../../../../evals/feedback/ela-writing/revision-manageability/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/feedback/ela-writing/revision-manageability/user.txt';
import CONFIG from '../../../../../../evals/feedback/ela-writing/revision-manageability/config.json';
import INPUT_SCHEMA from '../../../../../../evals/feedback/ela-writing/revision-manageability/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type RevisionManageabilityInput = InputsOf<{ properties: Record<'student_text' | 'feedback_text', unknown> }>;

/**
 * Judges whether the revision the feedback asks for is achievable.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and the model,
 * temperature and prompt inputs are read from `config.json`.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class RevisionManageabilityEvaluator extends defineSingleStepEvaluator<RevisionManageabilityInput, RevisionManageabilityResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: RevisionManageabilityOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateRevisionManageability(
  input: RevisionManageabilityInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<RevisionManageabilityResult>> {
  return new RevisionManageabilityEvaluator(config).evaluate(input);
}
