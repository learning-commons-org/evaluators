import { CriticalThinkingOutputSchema, type CriticalThinkingResult } from '../../../schemas/durable-skills/ela-writing/critical-thinking.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import SYSTEM_PROMPT from '../../../../../../evals/durable-skills/ela-writing/critical-thinking/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/durable-skills/ela-writing/critical-thinking/user.txt';
import CONFIG from '../../../../../../evals/durable-skills/ela-writing/critical-thinking/config.json';
import INPUT_SCHEMA from '../../../../../../evals/durable-skills/ela-writing/critical-thinking/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
import type { CriticalThinkingInput } from '../../../schemas/durable-skills/ela-writing/critical-thinking.js';

export type { CriticalThinkingInput };

/**
 * Rates a grade 8–10 argumentative essay for Critical Thinking.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and the model,
 * temperature and prompt inputs are read from `config.json`.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class CriticalThinkingEvaluator extends defineSingleStepEvaluator<CriticalThinkingInput, CriticalThinkingResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: CriticalThinkingOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateCriticalThinking(
  input: CriticalThinkingInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<CriticalThinkingResult>> {
  return new CriticalThinkingEvaluator(config).evaluate(input);
}
