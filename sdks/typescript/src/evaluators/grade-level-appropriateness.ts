import type { LLMProvider } from '../providers/index.js';
import {
  GradeLevelAppropriatenessOutputSchema,
  type GradeLevelAppropriatenessInternal,
} from '../schemas/grade-level-appropriateness.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/grade-level-appropriateness/index.js';
import type { EvaluationResult, GradeBand } from '../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from './base.js';
import { EvaluatorError, wrapProviderError } from '../errors.js';
import CONFIG from '../../../../evals/student-facing-text/ela-reading/grade-level-appropriateness/config.json';

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
 * const result = await evaluator.evaluate(text);
 * console.log(result.score); // "9-10"
 * console.log(result._internal.alternative_grade); // "6-8"
 * console.log(result._internal.scaffolding_needed);
 * ```
 */
export class GradeLevelAppropriatenessEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
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
  async evaluate(text: string): Promise<EvaluationResult<GradeBand, GradeLevelAppropriatenessInternal>> {
    this.logger.info('Starting grade level appropriateness evaluation', {
      evaluator: GradeLevelAppropriatenessEvaluator.metadata.id,
      operation: 'evaluate',
      textLength: text.length,
    });

    const startTime = Date.now();

    try {
      // Validate inputs — inside try so validation errors are telemetered.
      this.validateText(text);
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
        score: response.data.grade,
        reasoning: response.data.reasoning,
        metadata: {
          model: this.provider.label,
          processingTimeMs: latencyMs,
          inputTokens: tokenUsage.input_tokens,
          outputTokens: tokenUsage.output_tokens,
        },
        _internal: response.data,
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
        gradeLevel: result.score,
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
  text: string,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<GradeBand, GradeLevelAppropriatenessInternal>> {
  const evaluator = new GradeLevelAppropriatenessEvaluator(config);
  return evaluator.evaluate(text);
}
