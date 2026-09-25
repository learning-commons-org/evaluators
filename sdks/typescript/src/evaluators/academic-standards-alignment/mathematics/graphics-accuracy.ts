import { GraphicsAccuracyOutputSchema, type GraphicsAccuracyResult } from '../../../schemas/academic-standards-alignment/mathematics/graphics-accuracy.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import SYSTEM_PROMPT from '../../../../../../evals/academic-standards-alignment/mathematics/graphics-accuracy/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/academic-standards-alignment/mathematics/graphics-accuracy/user.txt';
import CONFIG from '../../../../../../evals/academic-standards-alignment/mathematics/graphics-accuracy/config.json';
import INPUT_SCHEMA from '../../../../../../evals/academic-standards-alignment/mathematics/graphics-accuracy/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
import type { GraphicsAccuracyInput } from '../../../schemas/academic-standards-alignment/mathematics/graphics-accuracy.js';

export type { GraphicsAccuracyInput };

/**
 * Checks whether a math visual correctly shows what its specification states.
 *
 * The specification is the `claim`: a statement about the image, or a question with its
 * expected answer written as `Question: "…" The answer is ….` (see
 * {@link composeSpecification}). The `image` is a local path or http(s) URL; its bytes are
 * read in the caller's environment and attached to the model request ahead of the text.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator} and the model,
 * temperature and prompt inputs are read from `config.json`. The verdict is `is_correct`;
 * `basis` says whether a false verdict came from a derivation that disagreed (`contradicted`)
 * or one that could not be completed (`unverified`).
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares; or if the image cannot be read, is not PNG/JPEG/WEBP, or exceeds 10 MB
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class GraphicsAccuracyEvaluator extends defineSingleStepEvaluator<GraphicsAccuracyInput, GraphicsAccuracyResult>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: GraphicsAccuracyOutputSchema,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
  attachments: [{ input: 'image', kind: 'image' }],
}) {}

export async function evaluateGraphicsAccuracy(
  input: GraphicsAccuracyInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<GraphicsAccuracyResult>> {
  return new GraphicsAccuracyEvaluator(config).evaluate(input);
}

/**
 * The `claim` text for a question with an expected answer.
 *
 * Byte-for-byte the text the evaluator was benchmarked on, so a caller who has a problem and
 * its answer key gets the measured behaviour rather than a paraphrase of it.
 */
export function composeSpecification(question: string, answer: string): string {
  return `Question: "${question.trim()}" The answer is ${answer.trim()}.`;
}
