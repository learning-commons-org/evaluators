import type { LLMProvider } from '../../../providers/index.js';
import { MeaningDirectnessOutputSchema, type MeaningDirectnessResult } from '../../../schemas/student-facing-text/ela-reading/meaning-directness.js';
import { calculateFleschKincaidGrade } from '../../../features/index.js';
import { getSystemPrompt, getUserPrompt } from '../../../prompts/meaning-directness/index.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from '../../base.js';
import { validateInputs, type InputsOf } from '../../inputs.js';
import { declaredCredentials } from '../../credentials.js';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/meaning-directness/input_schema.json';
import type { StageDetail } from '../../../telemetry/index.js';
import { EvaluatorError, wrapProviderError } from '../../../errors.js';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/meaning-directness/config.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type MeaningDirectnessInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Meaning Directness Evaluator
 *
 * Evaluates how explicit, literal, and straightforward a text's meaning is versus
 * how abstract, ironic, figurative, or archaic it is for the target grade level.
 *
 * Based on the Qualitative Text Complexity rubric.
 *
 * The complexity levels are whatever `output_schema.json` declares — currently
 * `slightly_complex` through `exceedingly_complex` — and are returned verbatim.
 *
 * @example
 * ```typescript
 * const evaluator = new MeaningDirectnessEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY
 * });
 *
 * const result = await evaluator.evaluate({
 *   text: 'The author uses sustained irony to critique societal norms.',
 *   grade_level: '10',
 * });
 * console.log(result.result.complexity_score); // "moderately_complex"
 * console.log(result.result.reasoning);
 * ```
 */
export class MeaningDirectnessEvaluator extends BaseEvaluator {
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
   * Evaluate meaning directness for a text at a grade level
   *
   * @param input - The inputs declared in this evaluator's `input_schema.json`
   * @returns Evaluation result with complexity score and detailed analysis
   * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
   * @throws {LLMOutputProcessingError} If the model's response fails its output schema
   */
  async evaluate(input: MeaningDirectnessInput): Promise<EvaluationResult<MeaningDirectnessResult>> {
    let text = '';
    let gradeLevel = '';
    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      // Inside the try so a validation failure is telemetered as an error event,
      // and before the inputs are read so a non-object is reported as one.
      validateInputs(input, INPUT_SCHEMA);
      ({ text, grade_level: gradeLevel } = input);

      this.logger.info('Starting Meaning Directness evaluation', {
        evaluator: MeaningDirectnessEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        textLength: text.length,
      });

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

      const totalTokenUsage = {
        input_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.input_tokens || 0), 0),
        output_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.output_tokens || 0), 0),
      };

      const result = {
        evaluator: MeaningDirectnessEvaluator.metadata.id,
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

      this.logger.info('Meaning Directness evaluation completed successfully', {
        evaluator: MeaningDirectnessEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        score: response.data.complexity_score,
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
  ): Promise<{ data: MeaningDirectnessResult; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
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
 *   { text: 'The author uses sustained irony to critique societal norms.', grade_level: '10' },
 *   { googleApiKey: process.env.GOOGLE_API_KEY },
 * );
 * ```
 */
export async function evaluateMeaningDirectness(
  input: MeaningDirectnessInput,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<MeaningDirectnessResult>> {
  const evaluator = new MeaningDirectnessEvaluator(config);
  return evaluator.evaluate(input);
}
