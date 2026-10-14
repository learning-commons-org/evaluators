import {
  GraphicsComplexityOutputSchema,
  GraphicsComplexityResponseSchema,
  type GraphicsComplexityResult,
} from '../../../schemas/graphics/ela/graphics-complexity.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import type { BaseEvaluatorConfig } from '../../base.js';
import { InputValidationError } from '../../../errors.js';
import { defineSingleStepEvaluator } from '../../single-step.js';
import SYSTEM_PROMPT from '../../../../../../evals/graphics/ela/graphics-complexity/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/graphics/ela/graphics-complexity/user.txt';
import CONFIG from '../../../../../../evals/graphics/ela/graphics-complexity/config.json';
import INPUT_SCHEMA from '../../../../../../evals/graphics/ela/graphics-complexity/input_schema.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
import type { GraphicsComplexityInput } from '../../../schemas/graphics/ela/graphics-complexity.js';

export type { GraphicsComplexityInput };

/**
 * `figure_labels` as the model reads it: one distinct label per image, in order.
 *
 * Omitted, the images are labelled "Image 1" to "Image N", as the input schema says. The
 * model rates each graphic under its label and names labels when graphics must be read
 * together, so a count that does not match the images, or a repeated label, would leave
 * it rating graphics it cannot tell apart.
 */
function withFigureLabels(input: GraphicsComplexityInput): GraphicsComplexityInput {
  const count = input.image_paths.length;
  if (input.figure_labels == null) {
    return { ...input, figure_labels: Array.from({ length: count }, (_, i) => `Image ${i + 1}`).join(', ') };
  }
  const labels = input.figure_labels.split(',').map((label) => label.trim());
  if (labels.length !== count || labels.some((label) => !label) || new Set(labels).size !== labels.length) {
    throw new InputValidationError(
      `figure_labels needs one distinct, non-empty label per image, comma-separated in image_paths order; ` +
        `received ${labels.length} for ${count} image${count === 1 ? '' : 's'}.`,
    );
  }
  return { ...input, figure_labels: labels.join(', ') };
}

/**
 * Rates how demanding a passage's graphics are for the target grade.
 *
 * `image_paths` holds one local image path per graphic in scope (up to five); each file is
 * read in the caller's environment, checked against the contract's `x-image` bounds, and
 * attached to the model request after the text. `figure_labels` optionally names them, in
 * the same order; omitted, they are "Image 1" to "Image N".
 *
 * One model call, so the flow comes from {@link defineSingleStepEvaluator}; the model,
 * temperature, preprocessing, prompt inputs and attachment are read from `config.json`.
 * The model also rates each graphic and any that must be read together; those working
 * fields are marked `x-model-only` in the contract and are not returned.
 *
 * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares; if `figure_labels` does not give one distinct label per image; or if an image cannot be read, is not PNG/JPEG/WebP by its bytes, or falls outside the declared size or edge bounds
 * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
 * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
 * @throws {LLMOutputProcessingError} If the model's response fails its output schema
 */
export class GraphicsComplexityEvaluator extends defineSingleStepEvaluator<
  GraphicsComplexityInput,
  GraphicsComplexityResult
>({
  contract: CONFIG,
  inputSchema: INPUT_SCHEMA,
  outputSchema: GraphicsComplexityOutputSchema,
  responseSchema: GraphicsComplexityResponseSchema,
  prepareInputs: withFigureLabels,
  systemPrompt: SYSTEM_PROMPT,
  userPrompt: USER_PROMPT_TEMPLATE,
}) {}

export async function evaluateGraphicsComplexity(
  input: GraphicsComplexityInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<GraphicsComplexityResult>> {
  return new GraphicsComplexityEvaluator(config).evaluate(input);
}
