import type { LLMProvider } from '../providers/index.js';
import { SmkOutputSchema, type SmkInternal } from '../schemas/smk.js';
import { calculateFleschKincaidGrade } from '../features/index.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/subject-matter-knowledge/index.js';
import type { EvaluationResult, TextComplexityLevel } from '../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from './base.js';
import type { StageDetail } from '../telemetry/index.js';
import { EvaluatorError, wrapProviderError } from '../errors.js';

/**
 * Subject Matter Knowledge (SMK) Evaluator
 *
 * Evaluates the background knowledge demands of educational texts relative to grade level.
 * Determines how much prior subject knowledge a student needs to comprehend the text.
 *
 * Based on the Common Core Qualitative Text Complexity Rubric with 4 levels:
 * - Slightly complex
 * - Moderately complex
 * - Very complex
 * - Exceedingly complex
 *
 * @example
 * ```typescript
 * const evaluator = new SmkEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY
 * });
 *
 * const result = await evaluator.evaluate(text, "6");
 * console.log(result.score); // "Moderately complex"
 * console.log(result.reasoning);
 * ```
 */
export class SmkEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: 'subject-matter-knowledge',
    name: 'Subject Matter Knowledge',
    description: 'Evaluates background knowledge demands of educational texts relative to grade level',
    supportedGrades: ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const,
    defaultProviders: [Provider.Google] as const,
  };

  private provider: LLMProvider;

  constructor(config: BaseEvaluatorConfig) {
    super(config);

    this.provider = this.createConfiguredProvider(
      Provider.Google, 'gemini-3-flash-preview', config.googleApiKey
    );
  }

  /**
   * Evaluate subject matter knowledge complexity for a given text and grade level
   *
   * @param text - The text to evaluate
   * @param gradeLevel - The target grade level (3-12)
   * @returns Evaluation result with complexity score and detailed analysis
   * @throws {InputValidationError} If text is empty, too short/long, or gradeLevel is invalid
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
   * @throws {LLMOutputProcessingError} If the model's response fails its output schema
   */
  async evaluate(
    text: string,
    gradeLevel: string
  ): Promise<EvaluationResult<TextComplexityLevel, SmkInternal>> {
    this.logger.info('Starting SMK evaluation', {
      evaluator: 'subject-matter-knowledge',
      operation: 'evaluate',
      gradeLevel,
      textLength: text.length,
    });

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      // Validate inputs — inside try so validation errors are telemetered.
      this.validateText(text);
      this.validateGradeLevel(gradeLevel, new Set(SmkEvaluator.metadata.supportedGrades));

      this.logger.debug('Evaluating subject matter knowledge complexity', {
        evaluator: 'subject-matter-knowledge',
        operation: 'smk_evaluation',
      });

      const fkScore = calculateFleschKincaidGrade(text);
      const response = await this.evaluateSmk(text, gradeLevel, fkScore);

      stageDetails.push({
        stage: 'smk_evaluation',
        provider: this.provider.label,
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
          model: this.provider.label,
          processingTimeMs: latencyMs,
          inputTokens: totalTokenUsage.input_tokens,
          outputTokens: totalTokenUsage.output_tokens,
        },
        _internal: response.data,
      };

      // Send success telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        gradeLevel,
        provider: this.provider.label,
        tokenUsage: totalTokenUsage,
        metadata: {
          stage_details: stageDetails,
        },
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      this.logger.info('SMK evaluation completed successfully', {
        evaluator: 'subject-matter-knowledge',
        operation: 'evaluate',
        gradeLevel,
        score: result.score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      this.logger.error('SMK evaluation failed', {
        evaluator: 'subject-matter-knowledge',
        operation: 'evaluate',
        gradeLevel,
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
        gradeLevel,
        provider: this.provider.label,
        tokenUsage: totalTokenUsage,
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      if (error instanceof EvaluatorError) {
        throw error;
      }

      throw wrapProviderError(error, this.providerContext(this.provider));
    }
  }

  /**
   * Run the SMK evaluation LLM call
   */
  private async evaluateSmk(
    text: string,
    gradeLevel: string,
    fkScore: number
  ): Promise<{ data: SmkInternal; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const response = await this.provider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPrompt() },
        { role: 'user', content: getUserPrompt(text, gradeLevel, fkScore) },
      ],
      schema: SmkOutputSchema,
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
 * Functional API for SMK evaluation
 *
 * @example
 * ```typescript
 * const result = await evaluateSmk(
 *   "Hydraulic propulsion works by sucking water at the bow and forcing it sternward.",
 *   "10",
 *   { googleApiKey: process.env.GOOGLE_API_KEY }
 * );
 * ```
 */
export async function evaluateSmk(
  text: string,
  gradeLevel: string,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<TextComplexityLevel, SmkInternal>> {
  const evaluator = new SmkEvaluator(config);
  return evaluator.evaluate(text, gradeLevel);
}
