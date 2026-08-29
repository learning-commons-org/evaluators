import { ReferenceKnowledgeDemandsOutputSchema, type ReferenceKnowledgeDemandsResult } from '../../../schemas/student-facing-text/ela-reading/reference-knowledge-demands.js';
import { getSystemPrompt, getUserPrompt } from '../../../prompts/reference-knowledge-demands/index.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import type { InputsOf } from '../../inputs.js';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/reference-knowledge-demands/config.json';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/reference-knowledge-demands/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type ReferenceKnowledgeDemandsInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Evaluates reference knowledge demands in student-facing text.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and
 * everything that varies — model, temperature, grades, preprocessing, prompt inputs —
 * is read from `config.json`.
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
  prompts: { getSystemPrompt, getUserPrompt },
}) {}

export async function evaluateReferenceKnowledgeDemands(
  input: ReferenceKnowledgeDemandsInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<ReferenceKnowledgeDemandsResult>> {
  return new ReferenceKnowledgeDemandsEvaluator(config).evaluate(input);
}
