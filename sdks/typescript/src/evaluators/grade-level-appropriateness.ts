import type { LLMProvider } from '../providers/index.js';
import { createProvider } from '../providers/index.js';
import {
  GradeLevelAppropriatenessSchema,
  type GradeLevelAppropriateness,
} from '../schemas/grade-level-appropriateness.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/grade-level-appropriateness/index.js';
import type { EvaluationResult } from '../schemas/index.js';
import { BaseEvaluator, type BaseEvaluatorConfig } from './base.js';
import { ConfigurationError, ValidationError, wrapProviderError } from '../errors.js';

/**
 * Configuration for GradeLevelAppropriatenessEvaluator
 */
export interface GradeLevelAppropriatenessEvaluatorConfig extends BaseEvaluatorConfig {
  /** Google API key for grade level evaluation (uses Gemini 2.5 Pro) */
  googleApiKey: string;
}

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
 * console.log(result.score.grade); // "9-10"
 * console.log(result.score.alternative_grade); // "6-8"
 * console.log(result.score.scaffolding_needed);
 * ```
 */
export class GradeLevelAppropriatenessEvaluator extends BaseEvaluator {
  private provider: LLMProvider;

  constructor(config: GradeLevelAppropriatenessEvaluatorConfig) {
    // Call base constructor for common setup (telemetry, etc.)
    super(config);

    // Validate required API keys
    if (!config.googleApiKey) {
      throw new ConfigurationError('Google API key is required. Pass googleApiKey in config.');
    }

    // Create Google Gemini provider
    this.provider = createProvider({
      type: 'google',
      model: 'gemini-2.5-pro',
      apiKey: config.googleApiKey,
      temperature: 0.25,
      maxRetries: this.config.maxRetries,
    });
  }

  // Implement abstract methods from BaseEvaluator
  protected getEvaluatorType(): string {
    return 'grade-level-appropriateness';
  }

  /**
   * Evaluate grade level appropriateness for a given text
   *
   * @param text - The text to evaluate
   * @returns Evaluation result with grade recommendations and scaffolding suggestions
   * @throws {ValidationError} If text is empty or too short/long
   * @throws {APIError} If LLM API calls fail (includes AuthenticationError, RateLimitError, NetworkError, TimeoutError)
   */
  async evaluate(text: string): Promise<EvaluationResult<GradeLevelAppropriateness>> {
    this.logger.info('Starting grade level appropriateness evaluation', {
      evaluator: 'grade-level-appropriateness',
      operation: 'evaluate',
      textLength: text.length,
    });

    const startTime = Date.now();

    try {
      // Validate inputs — inside try so validation errors are telemetered.
      this.validateText(text);
      this.logger.debug('Evaluating grade level appropriateness', {
        evaluator: 'grade-level-appropriateness',
        operation: 'grade_evaluation',
      });
      const userPrompt = getUserPrompt(text);

      const response = await this.provider.generateStructured({
        messages: [
          { role: 'system', content: getSystemPrompt() },
          { role: 'user', content: userPrompt },
        ],
        schema: GradeLevelAppropriatenessSchema,
        temperature: 0.25,
      });

      const latencyMs = Date.now() - startTime;

      const tokenUsage = {
        input_tokens: response.usage.inputTokens,
        output_tokens: response.usage.outputTokens,
      };

      const result = {
        score: response.data,
        reasoning: response.data.reasoning,
        metadata: {
          promptVersion: '1.2.0',
          model: 'google:gemini-2.5-pro',
          timestamp: new Date(),
          processingTimeMs: latencyMs,
        },
      };

      // Send success telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        provider: 'google:gemini-2.5-pro',
        tokenUsage,
        // No metadata.stage_details for single-stage evaluator
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      this.logger.info('Grade level appropriateness evaluation completed successfully', {
        evaluator: 'grade-level-appropriateness',
        operation: 'evaluate',
        grade: result.score.grade,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      // Log the error
      this.logger.error('Grade level appropriateness evaluation failed', {
        evaluator: 'grade-level-appropriateness',
        operation: 'evaluate',
        error: error instanceof Error ? error : undefined,
        processingTimeMs: latencyMs,
      });

      // Send failure telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'error',
        latencyMs,
        textLength: text.length,
        provider: 'google:gemini-2.5-pro',
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      // Re-throw validation errors as-is
      if (error instanceof ValidationError) {
        throw error;
      }

      // Wrap provider errors into appropriate error types
      throw wrapProviderError(error, 'Grade level appropriateness evaluation failed');
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
  config: GradeLevelAppropriatenessEvaluatorConfig
): Promise<EvaluationResult<GradeLevelAppropriateness>> {
  const evaluator = new GradeLevelAppropriatenessEvaluator(config);
  return evaluator.evaluate(text);
}
