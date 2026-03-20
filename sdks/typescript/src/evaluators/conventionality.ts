import type { LLMProvider } from '../providers/index.js';
import { createProvider } from '../providers/index.js';
import { ConventionalityOutputSchema, type ConventionalityInternal } from '../schemas/conventionality.js';
import { calculateFleschKincaidGrade } from '../features/index.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/conventionality/index.js';
import type { EvaluationResult, TextComplexityLevel } from '../schemas/index.js';
import { BaseEvaluator, type BaseEvaluatorConfig } from './base.js';
import type { StageDetail } from '../telemetry/index.js';
import { ValidationError, wrapProviderError } from '../errors.js';

/**
 * Conventionality Evaluator
 *
 * Evaluates how explicit, literal, and straightforward a text's meaning is versus
 * how abstract, ironic, figurative, or archaic it is for the target grade level.
 *
 * Based on the Common Core Qualitative Text Complexity Rubric with 4 levels:
 * - Slightly complex
 * - Moderately complex
 * - Very complex
 * - Exceedingly complex
 *
 * @example
 * ```typescript
 * const evaluator = new ConventionalityEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY
 * });
 *
 * const result = await evaluator.evaluate(text, "6");
 * console.log(result.score); // "Moderately complex"
 * console.log(result.reasoning);
 * ```
 */
export class ConventionalityEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: 'conventionality',
    name: 'Conventionality',
    description: 'Evaluates how explicit, literal, and straightforward a text\'s meaning is relative to grade level',
    supportedGrades: ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const,
    requiresGoogleKey: true,
    requiresOpenAIKey: false,
  };

  private provider: LLMProvider;

  constructor(config: BaseEvaluatorConfig) {
    super(config);

    this.provider = createProvider({
      type: 'google',
      model: 'gemini-3-flash-preview',
      apiKey: config.googleApiKey,
      maxRetries: this.config.maxRetries,
    });
  }

  /**
   * Evaluate conventionality complexity for a given text and grade level
   *
   * @param text - The text to evaluate
   * @param grade - The target grade level (3-12)
   * @returns Evaluation result with complexity score and detailed analysis
   * @throws {ValidationError} If text is empty, too short/long, or grade is invalid
   * @throws {APIError} If LLM API calls fail (includes AuthenticationError, RateLimitError, NetworkError, TimeoutError)
   */
  async evaluate(
    text: string,
    grade: string
  ): Promise<EvaluationResult<TextComplexityLevel, ConventionalityInternal>> {
    this.logger.info('Starting Conventionality evaluation', {
      evaluator: 'conventionality',
      operation: 'evaluate',
      grade,
      textLength: text.length,
    });

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      // Validate inputs — inside try so validation errors are telemetered.
      this.validateText(text);
      this.validateGrade(grade, new Set(ConventionalityEvaluator.metadata.supportedGrades));

      this.logger.debug('Evaluating conventionality complexity', {
        evaluator: 'conventionality',
        operation: 'conventionality_evaluation',
      });

      const fkScore = calculateFleschKincaidGrade(text);
      const response = await this.evaluateConventionality(text, grade, fkScore);

      stageDetails.push({
        stage: 'conventionality_evaluation',
        provider: 'google:gemini-3-flash-preview',
        latency_ms: response.latencyMs,
        token_usage: {
          input_tokens: response.usage.inputTokens,
          output_tokens: response.usage.outputTokens,
        },
      });

      const latencyMs = Date.now() - startTime;

      // Aggregate token usage
      const totalTokenUsage = {
        input_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.input_tokens || 0), 0),
        output_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.output_tokens || 0), 0),
      };

      const result = {
        score: response.data.complexity_score,
        reasoning: response.data.reasoning,
        metadata: {
          model: 'google:gemini-3-flash-preview',
          processingTimeMs: latencyMs,
        },
        _internal: response.data,
      };

      // Send success telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        grade,
        provider: 'google:gemini-3-flash-preview',
        tokenUsage: totalTokenUsage,
        metadata: {
          stage_details: stageDetails,
        },
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      this.logger.info('Conventionality evaluation completed successfully', {
        evaluator: 'conventionality',
        operation: 'evaluate',
        grade,
        score: result.score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      this.logger.error('Conventionality evaluation failed', {
        evaluator: 'conventionality',
        operation: 'evaluate',
        grade,
        error: error instanceof Error ? error : undefined,
        processingTimeMs: latencyMs,
        completedStages: stageDetails.length,
      });

      const totalTokenUsage = stageDetails.length > 0 ? {
        input_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.input_tokens || 0), 0),
        output_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.output_tokens || 0), 0),
      } : undefined;

      this.sendTelemetry({
        status: 'error',
        latencyMs,
        textLength: text.length,
        grade,
        provider: 'google:gemini-3-flash-preview',
        tokenUsage: totalTokenUsage,
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      if (error instanceof ValidationError) {
        throw error;
      }

      throw wrapProviderError(error, 'Conventionality evaluation failed');
    }
  }

  /**
   * Run the Conventionality evaluation LLM call
   */
  private async evaluateConventionality(
    text: string,
    grade: string,
    fkScore: number
  ): Promise<{ data: ConventionalityInternal; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const response = await this.provider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPrompt() },
        { role: 'user', content: getUserPrompt(text, grade, fkScore) },
      ],
      schema: ConventionalityOutputSchema,
      temperature: 0,
    });

    return {
      data: response.data,
      usage: response.usage,
      latencyMs: response.latencyMs,
    };
  }
}

/**
 * Functional API for Conventionality evaluation
 *
 * @example
 * ```typescript
 * const result = await evaluateConventionality(
 *   "The author uses sustained irony to critique societal norms.",
 *   "10",
 *   { googleApiKey: process.env.GOOGLE_API_KEY }
 * );
 * ```
 */
export async function evaluateConventionality(
  text: string,
  grade: string,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<TextComplexityLevel, ConventionalityInternal>> {
  const evaluator = new ConventionalityEvaluator(config);
  return evaluator.evaluate(text, grade);
}
