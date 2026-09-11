import { StudentResponseSpecificityOutputSchema, type StudentResponseSpecificityResult } from '../../../schemas/feedback/ela-writing/student-response-specificity.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import SYSTEM_PROMPT from '../../../../../../evals/feedback/ela-writing/student-response-specificity/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/feedback/ela-writing/student-response-specificity/user.txt';
import CONFIG from '../../../../../../evals/feedback/ela-writing/student-response-specificity/config.json';
import INPUT_SCHEMA from '../../../../../../evals/feedback/ela-writing/student-response-specificity/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
import type { StudentResponseSpecificityInput } from '../../../schemas/feedback/ela-writing/student-response-specificity.js';

export type { StudentResponseSpecificityInput };

/**
 * Judges whether the feedback engages this student's actual writing.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and the model,
 * temperature and prompt inputs are read from `config.json`.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class StudentResponseSpecificityEvaluator extends defineSingleStepEvaluator<StudentResponseSpecificityInput, StudentResponseSpecificityResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: StudentResponseSpecificityOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateStudentResponseSpecificity(
  input: StudentResponseSpecificityInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<StudentResponseSpecificityResult>> {
  return new StudentResponseSpecificityEvaluator(config).evaluate(input);
}
