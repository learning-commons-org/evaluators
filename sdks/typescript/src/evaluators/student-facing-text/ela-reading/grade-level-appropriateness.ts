import type { LLMProvider } from '../../../providers/index.js';
import {
  GradeLevelAppropriatenessOutputSchema,
  type GradeLevelAppropriatenessResult,
} from '../../../schemas/student-facing-text/ela-reading/grade-level-appropriateness.js';
import { getSystemPrompt, getUserPrompt } from '../../../prompts/grade-level-appropriateness/index.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from '../../base.js';
import { validateInputs, type InputsOf } from '../../inputs.js';
import { declaredCredentials } from '../../credentials.js';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/grade-level-appropriateness/input_schema.json';
import { EvaluatorError, wrapProviderError } from '../../../errors.js';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/grade-level-appropriateness/config.json';

/**
 * Grade Level Appropriateness Evaluator
 *
 * Evaluates whether AI-generated text is suitable for a given grade band.
 * Uses a structured 4-step analysis process:
 * 1. Quantitative analysis (word count, Flesch-Kincaid)
 * 2. Qualitative complexity (text structure, language, purpose, knowledge demands)
 * 3. Background knowledge assessment
 * 4. Synthesis and final recommendation
 *
 * Returns:
 * - Target grade band (K-1, 2-3, 4-5, 6-8, 9-10, 11-CCR)
 * - Alternative grade band (with scaffolding)
 * - Specific scaffolding recommendations
 *
 * @example
 * ```typescript
 * const evaluator = new GradeLevelAppropriatenessEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY
 * });
 *
 * const result = await evaluator.evaluate({ text });
 * console.log(result.result.grade_band); // "9-10"
 * console.log(result.result.alternative_grade_band); // "6-8"
 * console.log(result.result.scaffolding_needed);
 * ```
 */
/** What this evaluator accepts, taken from its `input_schema.json`. */
export type GradeLevelAppropriatenessInput = InputsOf<typeof INPUT_SCHEMA>;

export class GradeLevelAppropriatenessEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    outcome: CONFIG.outcome,
    requiredCredentials: declaredCredentials(CONFIG),
    supportedGrades: [] as const, // No gradeLevel parameter required - evaluates what grade level the text is appropriate for
    defaultProviders: [Provider.Google] as const,
  };

  private provider: LLMProvider;

  constructor(config: BaseEvaluatorConfig) {
    // Call base constructor for common setup (telemetry, API key validation, etc.)
    super(config);

    this.provider = this.createConfiguredProvider(
      Provider.Google, 'gemini-2.5-pro', config.googleApiKey
    );
  }

  /**
   * Evaluate grade level appropriateness for a given text
   *
   * @param text - The text to evaluate
   * @returns Evaluation result with grade level recommendations and scaffolding suggestions
   * @throws {InputValidationError} If text is empty or too short/long
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
   * @throws {LLMOutputProcessingError} If the model's response fails its output schema
   */
  async evaluate(input: GradeLevelAppropriatenessInput): Promise<EvaluationResult<GradeLevelAppropriatenessResult>> {
    let text = '';
    const startTime = Date.now();

    try {
      // Inside the try so a validation failure is telemetered as an error event,
      // and before the inputs are read so a non-object is reported as one.
      validateInputs(input, INPUT_SCHEMA);
      ({ text } = input);

      this.logger.info('Starting grade level appropriateness evaluation', {
        evaluator: GradeLevelAppropriatenessEvaluator.metadata.id,
        operation: 'evaluate',
        textLength: text.length,
      });

      this.logger.debug('Evaluating grade level appropriateness', {
        evaluator: GradeLevelAppropriatenessEvaluator.metadata.id,
        operation: 'grade_evaluation',
      });
      const userPrompt = getUserPrompt(text);

      const response = await this.provider.generateStructured({
        messages: [
          { role: 'system', content: getSystemPrompt() },
          { role: 'user', content: userPrompt },
        ],
        schema: GradeLevelAppropriatenessOutputSchema,
        temperature: 0.25,
      });

      const latencyMs = Date.now() - startTime;

      const tokenUsage = {
        input_tokens: response.usage.inputTokens,
        output_tokens: response.usage.outputTokens,
      };

      const result = {
        // `grade` is the model's output field, declared in the eval's schema —
        // not the SDK's parameter name.
        evaluator: GradeLevelAppropriatenessEvaluator.metadata.id,
        result: response.data,
        metadata: {
          model: this.provider.label,
          processingTimeMs: latencyMs,
          tokenUsage: {
            inputTokens: tokenUsage.input_tokens,
            outputTokens: tokenUsage.output_tokens,
          },
        },
      };

      // Send success telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        provider: this.provider.label,
        tokenUsage,
        // No metadata.stage_details for single-stage evaluator
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      this.logger.info('Grade level appropriateness evaluation completed successfully', {
        evaluator: GradeLevelAppropriatenessEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel: response.data.grade_band,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      // Log the error
      this.logger.error('Grade level appropriateness evaluation failed', {
        evaluator: GradeLevelAppropriatenessEvaluator.metadata.id,
        operation: 'evaluate',
        error: error instanceof Error ? error : undefined,
        processingTimeMs: latencyMs,
      });

      // Send failure telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'error',
        latencyMs,
        textLength: text.length,
        provider: this.provider.label,
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      // Re-throw validation errors as-is
      if (error instanceof EvaluatorError) {
        throw error;
      }

      // Wrap provider errors into appropriate error types
      throw wrapProviderError(error, this.providerContext(this.provider));
    }
  }
}

/**
 * Functional API for grade level appropriateness evaluation
 *
 * @example
 * ```typescript
 * const result = await evaluateGradeLevelAppropriateness(
 *   "Tides are the rise and fall of sea levels...",
 *   {
 *     googleApiKey: process.env.GOOGLE_API_KEY
 *   }
 * );
 * ```
 */
export async function evaluateGradeLevelAppropriateness(
  input: GradeLevelAppropriatenessInput,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<GradeLevelAppropriatenessResult>> {
  const evaluator = new GradeLevelAppropriatenessEvaluator(config);
  return evaluator.evaluate(input);
}
