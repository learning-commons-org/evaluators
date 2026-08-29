import { WithholdingAnswersOutputSchema, type WithholdingAnswersResult } from '../../../schemas/feedback/ela-writing/withholding-answers.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import type { InputsOf } from '../../inputs.js';
import SYSTEM_PROMPT from '../../../../../../evals/feedback/ela-writing/withholding-answers/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/feedback/ela-writing/withholding-answers/user.txt';
import CONFIG from '../../../../../../evals/feedback/ela-writing/withholding-answers/config.json';
import INPUT_SCHEMA from '../../../../../../evals/feedback/ela-writing/withholding-answers/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type WithholdingAnswersInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Judges whether the feedback guides revision without writing it for the student.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and the model,
 * temperature and prompt inputs are read from `config.json`.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class WithholdingAnswersEvaluator extends defineSingleStepEvaluator<WithholdingAnswersInput, WithholdingAnswersResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: WithholdingAnswersOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateWithholdingAnswers(
  input: WithholdingAnswersInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<WithholdingAnswersResult>> {
  return new WithholdingAnswersEvaluator(config).evaluate(input);
}
