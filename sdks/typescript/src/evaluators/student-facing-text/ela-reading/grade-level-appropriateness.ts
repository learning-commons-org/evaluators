import {
  GradeLevelAppropriatenessOutputSchema,
  type GradeLevelAppropriatenessResult,
} from '../../../schemas/student-facing-text/ela-reading/grade-level-appropriateness.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import type { InputsOf } from '../../inputs.js';
import SYSTEM_PROMPT from '../../../../../../evals/student-facing-text/ela-reading/grade-level-appropriateness/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/student-facing-text/ela-reading/grade-level-appropriateness/user.txt';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/grade-level-appropriateness/config.json';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/grade-level-appropriateness/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type GradeLevelAppropriatenessInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Reports the grade band a text is appropriate for at independent reading, plus a second
 * band reachable with scaffolding.
 *
 * Takes no grade level: unlike the complexity evaluators, which judge a text *against* a
 * grade, this one determines the grade. Its `input_schema` declares only `text`, so
 * `metadata.supportedGrades` is empty by derivation rather than by assertion.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and the model,
 * temperature and prompt inputs are read from `config.json`.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class GradeLevelAppropriatenessEvaluator extends defineSingleStepEvaluator<
  GradeLevelAppropriatenessInput,
  GradeLevelAppropriatenessResult
>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: GradeLevelAppropriatenessOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateGradeLevelAppropriateness(
  input: GradeLevelAppropriatenessInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<GradeLevelAppropriatenessResult>> {
  return new GradeLevelAppropriatenessEvaluator(config).evaluate(input);
}
