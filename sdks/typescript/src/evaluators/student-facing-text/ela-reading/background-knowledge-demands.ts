import type { LLMProvider } from '../../../providers/index.js';
import { BackgroundKnowledgeDemandsOutputSchema, type BackgroundKnowledgeDemandsResult } from '../../../schemas/student-facing-text/ela-reading/background-knowledge-demands.js';
import { calculateFleschKincaidGrade } from '../../../features/index.js';
import { getSystemPrompt, getUserPrompt } from '../../../prompts/background-knowledge-demands/index.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from '../../base.js';
import { validateInputs, type InputsOf } from '../../inputs.js';
import { declaredCredentials } from '../../credentials.js';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/background-knowledge-demands/input_schema.json';
import type { StageDetail } from '../../../telemetry/index.js';
import { EvaluatorError, wrapProviderError } from '../../../errors.js';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/background-knowledge-demands/config.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type BackgroundKnowledgeDemandsInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Background Knowledge Demands Evaluator
 *
 * Evaluates the background knowledge demands of educational texts relative to grade level.
 * Determines how much prior subject knowledge a student needs to comprehend the text.
 *
 * Based on the Qualitative Text Complexity rubric.
 *
 * The complexity levels are whatever `output_schema.json` declares — currently
 * `slightly_complex` through `exceedingly_complex` — and are returned verbatim.
 *
 * @example
 * ```typescript
 * const evaluator = new BackgroundKnowledgeDemandsEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY
 * });
 *
 * const result = await evaluator.evaluate({ text, grade_level: '6' });
 * console.log(result.result.complexity_score); // "moderately_complex"
 * console.log(result.result.reasoning);
 * ```
 */
export class BackgroundKnowledgeDemandsEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    outcome: CONFIG.outcome,
    requiredCredentials: declaredCredentials(CONFIG),
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
   * Evaluate background knowledge demands for a text at a grade level
   *
   * @param input - The inputs declared in this evaluator's `input_schema.json`
   * @returns Evaluation result with complexity score and detailed analysis
   * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
   * @throws {LLMOutputProcessingError} If the model's response fails its output schema
   */
  async evaluate(input: BackgroundKnowledgeDemandsInput): Promise<EvaluationResult<BackgroundKnowledgeDemandsResult>> {
    let text = '';
    let gradeLevel = '';
    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      // Inside the try so a validation failure is telemetered as an error event,
      // and before the inputs are read so a non-object is reported as one.
      validateInputs(input, INPUT_SCHEMA);
      ({ text, grade_level: gradeLevel } = input);

      this.logger.info('Starting Background Knowledge Demands evaluation', {
        evaluator: BackgroundKnowledgeDemandsEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        textLength: text.length,
      });

      this.logger.debug('Evaluating subject matter knowledge complexity', {
        evaluator: BackgroundKnowledgeDemandsEvaluator.metadata.id,
        operation: 'background_knowledge_demands_evaluation',
      });

      const fkScore = calculateFleschKincaidGrade(text);
      const response = await this.evaluateBackgroundKnowledgeDemands(text, gradeLevel, fkScore);

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

      const totalTokenUsage = {
        input_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.input_tokens || 0), 0),
        output_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.output_tokens || 0), 0),
      };

      const result = {
        evaluator: BackgroundKnowledgeDemandsEvaluator.metadata.id,
        result: response.data,
        metadata: {
          model: this.provider.label,
          processingTimeMs: latencyMs,
          tokenUsage: {
            inputTokens: totalTokenUsage.input_tokens,
            outputTokens: totalTokenUsage.output_tokens,
          },
        },
      };

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
      });

      this.logger.info('Background Knowledge Demands evaluation completed successfully', {
        evaluator: BackgroundKnowledgeDemandsEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        score: response.data.complexity_score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      this.logger.error('Background Knowledge Demands evaluation failed', {
        evaluator: BackgroundKnowledgeDemandsEvaluator.metadata.id,
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
      });

      if (error instanceof EvaluatorError) {
        throw error;
      }

      throw wrapProviderError(error, this.providerContext(this.provider));
    }
  }

  /**
   * Run the background-knowledge-demands LLM call
   */
  private async evaluateBackgroundKnowledgeDemands(
    text: string,
    gradeLevel: string,
    fkScore: number
  ): Promise<{ data: BackgroundKnowledgeDemandsResult; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const response = await this.provider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPrompt() },
        { role: 'user', content: getUserPrompt(text, gradeLevel, fkScore) },
      ],
      schema: BackgroundKnowledgeDemandsOutputSchema,
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
 * Functional API for background knowledge demands
 *
 * @example
 * ```typescript
 * const result = await evaluateBackgroundKnowledgeDemands(
 *   { text, grade_level: '10' },
 *   { googleApiKey: process.env.GOOGLE_API_KEY },
 * );
 * ```
 */
export async function evaluateBackgroundKnowledgeDemands(
  input: BackgroundKnowledgeDemandsInput,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<BackgroundKnowledgeDemandsResult>> {
  const evaluator = new BackgroundKnowledgeDemandsEvaluator(config);
  return evaluator.evaluate(input);
}
