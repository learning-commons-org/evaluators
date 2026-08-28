import type { LLMProvider } from '../providers/index.js';
import { MeaningDirectnessOutputSchema, type MeaningDirectnessInternal } from '../schemas/meaning-directness.js';
import { calculateFleschKincaidGrade } from '../features/index.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/meaning-directness/index.js';
import type { EvaluationResult, TextComplexityLevel } from '../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from './base.js';
import type { StageDetail } from '../telemetry/index.js';
import { EvaluatorError, wrapProviderError } from '../errors.js';
import CONFIG from '../../../../evals/student-facing-text/ela-reading/meaning-directness/config.json';

/**
 * Meaning Directness Evaluator
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
 * const evaluator = new MeaningDirectnessEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY
 * });
 *
 * const result = await evaluator.evaluate(text, "6");
 * console.log(result.score); // "Moderately complex"
 * console.log(result.reasoning);
 * ```
 */
export class MeaningDirectnessEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
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
   * Evaluate conventionality complexity for a given text and grade level
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
  ): Promise<EvaluationResult<TextComplexityLevel, MeaningDirectnessInternal>> {
    this.logger.info('Starting Meaning Directness evaluation', {
      evaluator: MeaningDirectnessEvaluator.metadata.id,
      operation: 'evaluate',
      gradeLevel,
      textLength: text.length,
    });

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      // Validate inputs — inside try so validation errors are telemetered.
      this.validateText(text);
      this.validateGradeLevel(gradeLevel, new Set(MeaningDirectnessEvaluator.metadata.supportedGrades));

      this.logger.debug('Evaluating conventionality complexity', {
        evaluator: MeaningDirectnessEvaluator.metadata.id,
        operation: 'meaning_directness_evaluation',
      });

      const fkScore = calculateFleschKincaidGrade(text);
      const response = await this.evaluateMeaningDirectness(text, gradeLevel, fkScore);

      stageDetails.push({
        stage: 'conventionality_evaluation',
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

      this.logger.info('Meaning Directness evaluation completed successfully', {
        evaluator: MeaningDirectnessEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        score: result.score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      this.logger.error('Meaning Directness evaluation failed', {
        evaluator: MeaningDirectnessEvaluator.metadata.id,
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
   * Run the Meaning Directness evaluation LLM call
   */
  private async evaluateMeaningDirectness(
    text: string,
    gradeLevel: string,
    fkScore: number
  ): Promise<{ data: MeaningDirectnessInternal; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const response = await this.provider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPrompt() },
        { role: 'user', content: getUserPrompt(text, gradeLevel, fkScore) },
      ],
      schema: MeaningDirectnessOutputSchema,
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
 * Functional API for Meaning Directness evaluation
 *
 * @example
 * ```typescript
 * const result = await evaluateMeaningDirectness(
 *   "The author uses sustained irony to critique societal norms.",
 *   "10",
 *   { googleApiKey: process.env.GOOGLE_API_KEY }
 * );
 * ```
 */
export async function evaluateMeaningDirectness(
  text: string,
  gradeLevel: string,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<TextComplexityLevel, MeaningDirectnessInternal>> {
  const evaluator = new MeaningDirectnessEvaluator(config);
  return evaluator.evaluate(text, gradeLevel);
}
