import { ReferenceKnowledgeDemandsOutputSchema, type ReferenceKnowledgeDemandsResult } from '../../../schemas/student-facing-text/ela-reading/reference-knowledge-demands.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import type { InputsOf } from '../../inputs.js';
import SYSTEM_PROMPT from '../../../../../../evals/student-facing-text/ela-reading/reference-knowledge-demands/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/student-facing-text/ela-reading/reference-knowledge-demands/user.txt';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/reference-knowledge-demands/config.json';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/reference-knowledge-demands/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type ReferenceKnowledgeDemandsInput = InputsOf<{ properties: Record<'text' | 'grade_level', unknown> }>;

/**
 * Evaluates reference knowledge demands in student-facing text.
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
export class ReferenceKnowledgeDemandsEvaluator extends defineSingleStepEvaluator<ReferenceKnowledgeDemandsInput, ReferenceKnowledgeDemandsResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: ReferenceKnowledgeDemandsOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateReferenceKnowledgeDemands(
  input: ReferenceKnowledgeDemandsInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<ReferenceKnowledgeDemandsResult>> {
  return new ReferenceKnowledgeDemandsEvaluator(config).evaluate(input);
}
