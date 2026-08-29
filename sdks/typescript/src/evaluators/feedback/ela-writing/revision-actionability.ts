import { RevisionActionabilityOutputSchema, type RevisionActionabilityResult } from '../../../schemas/feedback/ela-writing/revision-actionability.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import type { InputsOf } from '../../inputs.js';
import SYSTEM_PROMPT from '../../../../../../evals/feedback/ela-writing/revision-actionability/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/feedback/ela-writing/revision-actionability/user.txt';
import CONFIG from '../../../../../../evals/feedback/ela-writing/revision-actionability/config.json';
import INPUT_SCHEMA from '../../../../../../evals/feedback/ela-writing/revision-actionability/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type RevisionActionabilityInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Judges whether the feedback tells the student what to actually do next.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and the model,
 * temperature and prompt inputs are read from `config.json`.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class RevisionActionabilityEvaluator extends defineSingleStepEvaluator<RevisionActionabilityInput, RevisionActionabilityResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: RevisionActionabilityOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateRevisionActionability(
  input: RevisionActionabilityInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<RevisionActionabilityResult>> {
  return new RevisionActionabilityEvaluator(config).evaluate(input);
}
