import { GraphicsAccuracyOutputSchema, type GraphicsAccuracyResult } from '../../../schemas/graphics/math/graphics-accuracy.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { InputValidationError } from '../../../errors.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import SYSTEM_PROMPT from '../../../../../../evals/graphics/math/graphics-accuracy/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/graphics/math/graphics-accuracy/user.txt';
import CONFIG from '../../../../../../evals/graphics/math/graphics-accuracy/config.json';
import INPUT_SCHEMA from '../../../../../../evals/graphics/math/graphics-accuracy/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
import type { GraphicsAccuracyInput } from '../../../schemas/graphics/math/graphics-accuracy.js';

export type { GraphicsAccuracyInput };

/**
 * Checks whether a math graphic correctly shows what its claim states.
 *
 * The claim is the specification: a statement about the image, or a question with its
 * expected answer written as `Question: "…" The answer is ….` (see
 * {@link composeGraphicsAccuracyClaim}). `image_paths` is a one-item array holding the local path of
 * the image under review; its bytes are read in the caller's environment, checked against
 * the contract's `x-image` bounds, and attached to the model request ahead of the text.
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator}; the model,
 * temperature, prompt inputs and attachment are read from `config.json`. The verdict is
 * `is_correct`; `basis` says whether a false verdict came from a derivation that disagreed
 * (`contradicted`), one that could not be completed (`unverified`), or a defect in the image
 * itself (`defective`), which `defects` lists.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares; or if the image cannot be read, is not PNG/JPEG/WebP by its bytes, or falls outside the declared size or edge bounds
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
 * Byte-for-byte the text the evaluator was measured with, so a caller who has a problem and
 * its answer key gets the measured behaviour rather than a paraphrase of it. Surrounding
 * whitespace is trimmed from both parts; nothing else is changed.
 *
 * @throws {InputValidationError} If the question or answer is blank: the composed claim would
 * still be non-empty, so the evaluator would judge the image against a claim with a part missing
 */
export function composeGraphicsAccuracyClaim(question: string, answer: string): string {
  const q = question.trim();
  const a = answer.trim();
  if (!q) throw new InputValidationError('composeGraphicsAccuracyClaim: the question is blank; a claim needs both.');
  if (!a) throw new InputValidationError('composeGraphicsAccuracyClaim: the answer is blank; a claim needs both.');
  return `Question: "${q}" The answer is ${a}.`;
}
