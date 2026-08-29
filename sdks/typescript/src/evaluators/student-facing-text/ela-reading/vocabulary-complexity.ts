import type { LLMProvider } from '../../../providers/index.js';
import {
  VocabularyComplexityOutputSchema,
  type VocabularyComplexityResult,
} from '../../../schemas/student-facing-text/ela-reading/vocabulary-complexity.js';
import { calculateFleschKincaidGrade } from '../../../features/index.js';
import {
  getBackgroundKnowledgePrompt,
  getSystemPrompt,
  getUserPrompt,
} from '../../../prompts/vocabulary-complexity/index.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from '../../base.js';
import { validateInputs, type InputsOf } from '../../inputs.js';
import { declaredCredentials } from '../../credentials.js';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/input_schema.json';
import type { StageDetail } from '../../../telemetry/index.js';
import { EvaluatorError, wrapProviderError } from '../../../errors.js';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/config.json';

/**
 * Vocabulary Evaluator
 *
 * Evaluates vocabulary complexity of educational texts relative to grade level.
 * Uses a 2-stage process:
 * 1. Generate background knowledge assumption for the student's grade level
 * 2. Evaluate vocabulary complexity using that background knowledge
 *
 * Based on Qual Text Complexity rubric (SAP) with 4 levels:
 * - Slightly complex
 * - Moderately complex
 * - Very complex
 * - Exceedingly complex
 *
 * @example
 * ```typescript
 * const evaluator = new VocabularyComplexityEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY,
 *   openaiApiKey: process.env.OPENAI_API_KEY
 * });
 *
 * const result = await evaluator.evaluate(text, "3");
 * console.log(result.result.complexity_score); // "Moderately complex"
 * console.log(result.result.reasoning);
 * ```
 */
/** What this evaluator accepts, taken from its `input_schema.json`. */
export type VocabularyComplexityInput = InputsOf<typeof INPUT_SCHEMA>;

/** The vocabulary evaluator's stage-1 output, fed to stage 2 as prompt input. */
export interface BackgroundKnowledge {
  assumption: string;
  gradeLevel: string;
}

export class VocabularyComplexityEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    outcome: CONFIG.outcome,
    requiredCredentials: declaredCredentials(CONFIG),
    supportedGrades: ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const,
    defaultProviders: [Provider.Google, Provider.OpenAI] as const,
  };

  private grades34ComplexityProvider: LLMProvider;
  private otherGradesComplexityProvider: LLMProvider;
  private backgroundKnowledgeProvider: LLMProvider;

  constructor(config: BaseEvaluatorConfig) {
    // Call base constructor for common setup (telemetry, API key validation, etc.)
    super(config);

    // Create Google Gemini provider for complexity evaluation (grade levels 3-4)
    this.grades34ComplexityProvider = this.createConfiguredProvider(
      Provider.Google, 'gemini-2.5-pro', config.googleApiKey
    );

    // Create OpenAI GPT-4.1 provider for complexity evaluation (grade levels 5-12)
    this.otherGradesComplexityProvider = this.createConfiguredProvider(
      Provider.OpenAI, 'gpt-4.1-2025-04-14', config.openaiApiKey
    );

    // Create OpenAI GPT-4o provider for background knowledge generation
    this.backgroundKnowledgeProvider = this.createConfiguredProvider(
      Provider.OpenAI, 'gpt-4o-2024-11-20', config.openaiApiKey
    );
  }

  /**
   * Evaluate vocabulary complexity for a given text and grade level
   *
   * @param text - The text to evaluate
   * @param gradeLevel - The target grade level (3-12)
   * @returns Evaluation result with complexity score and detailed analysis
   * @throws {InputValidationError} If text is empty, too short/long, or gradeLevel is invalid
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
   * @throws {LLMOutputProcessingError} If the model's response fails its output schema
   */
  async evaluate(input: VocabularyComplexityInput): Promise<EvaluationResult<VocabularyComplexityResult>> {
    let text = '';
    let gradeLevel = '';
    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];
    const complexityProvider = (gradeLevel === '3' || gradeLevel === '4')
      ? this.grades34ComplexityProvider
      : this.otherGradesComplexityProvider;
    const complexityProviderLabel = complexityProvider.label;
    const backgroundProviderLabel = this.backgroundKnowledgeProvider.label;
    // When override is active all providers resolve to the same model — show a single label.
    const modelLabel = this.config.modelOverride
      ? backgroundProviderLabel
      : `${backgroundProviderLabel}+${complexityProviderLabel}`;

    try {
      // Inside the try so a validation failure is telemetered as an error event,
      // and before the inputs are read so a non-object is reported as one.
      validateInputs(input, INPUT_SCHEMA);
      ({ text, grade_level: gradeLevel } = input);

      this.logger.info('Starting Vocabulary Complexity evaluation', {
        evaluator: VocabularyComplexityEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        textLength: text.length,
      });
      // If partners consistently pass invalid grade levels/text, telemetry will surface documentation gaps.
      this.logger.debug('Stage 1: Generating background knowledge', {
        evaluator: VocabularyComplexityEvaluator.metadata.id,
        operation: 'background_knowledge',
      });
      // Stage 1: Generate background knowledge assumption
      const bgResponse = await this.getBackgroundKnowledgeAssumption(text, gradeLevel);

      stageDetails.push({
        stage: 'background_knowledge',
        provider: backgroundProviderLabel,
        latency_ms: bgResponse.latencyMs,
        token_usage: {
          input_tokens: bgResponse.usage.inputTokens,
          output_tokens: bgResponse.usage.outputTokens,
        },
      });

      // Calculate Flesch-Kincaid grade level
      const fkLevel = calculateFleschKincaidGrade(text);

      // Stage 2: Evaluate vocabulary complexity
      const complexityResponse = await this.evaluateComplexity(
        text,
        gradeLevel,
        bgResponse.knowledge.assumption,
        fkLevel
      );

      stageDetails.push({
        stage: 'complexity_evaluation',
        provider: complexityProviderLabel,
        latency_ms: complexityResponse.latencyMs,
        token_usage: {
          input_tokens: complexityResponse.usage.inputTokens,
          output_tokens: complexityResponse.usage.outputTokens,
        },
      });

      const latencyMs = Date.now() - startTime;

      // Aggregate token usage
      const totalTokenUsage = {
        input_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.input_tokens || 0), 0),
        output_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.output_tokens || 0), 0),
      };

      const result = {
        evaluator: VocabularyComplexityEvaluator.metadata.id,
        result: complexityResponse.data,
        metadata: {
          model: modelLabel,
          processingTimeMs: latencyMs,
          tokenUsage: {
            inputTokens: totalTokenUsage.input_tokens,
            outputTokens: totalTokenUsage.output_tokens,
          },
        },
      };

      // Send success telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        gradeLevel,
        provider: modelLabel,
        tokenUsage: totalTokenUsage,
        metadata: {
          stage_details: stageDetails,
        },
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      this.logger.info('Vocabulary Complexity evaluation completed successfully', {
        evaluator: VocabularyComplexityEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        score: complexityResponse.data.complexity_score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      // Log the error
      this.logger.error('Vocabulary Complexity evaluation failed', {
        evaluator: VocabularyComplexityEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        error: error instanceof Error ? error : undefined,
        processingTimeMs: latencyMs,
        completedStages: stageDetails.length,
      });

      // Aggregate metrics from completed stages
      const totalTokenUsage = stageDetails.length > 0 ? {
        input_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.input_tokens || 0), 0),
        output_tokens: stageDetails.reduce((sum, s) => sum + (s.token_usage?.output_tokens || 0), 0),
      } : undefined;

      // Send failure telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'error',
        latencyMs,
        textLength: text.length,
        gradeLevel,
        provider: modelLabel,
        tokenUsage: totalTokenUsage,
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      // Re-throw validation errors as-is
      if (error instanceof EvaluatorError) {
        throw error;
      }

      // An empty stageDetails means stage 1 (background knowledge) is what
      // failed; otherwise it completed and stage 2 (complexity) did. Attribute
      // to the provider that actually failed rather than a combined label.
      const failed =
        stageDetails.length === 0 ? this.backgroundKnowledgeProvider : complexityProvider;
      throw wrapProviderError(error, this.providerContext(failed));
    }
  }

  /**
   * Stage 1: Generate background knowledge assumption
   *
   * Estimates what topics the student at the given grade level would be familiar with
   * based on Common Core curriculum progression.
   */
  private async getBackgroundKnowledgeAssumption(
    text: string,
    gradeLevel: string
  ): Promise<{ knowledge: BackgroundKnowledge; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const prompt = getBackgroundKnowledgePrompt(text, gradeLevel);

    const response = await this.backgroundKnowledgeProvider.generateText(
      [{ role: 'user', content: prompt }],
      0 // temperature = 0 for consistency
    );

    return {
      knowledge: {
        assumption: response.text.trim(),
        gradeLevel,
      },
      usage: response.usage,
      latencyMs: response.latencyMs,
    };
  }

  /**
   * Stage 2: Evaluate vocabulary complexity
   *
   * Uses the Qual Text Complexity rubric (SAP) and background knowledge to evaluate vocabulary complexity.
   * Grades 3-4 use Gemini 2.5 Pro; grade levels 5-12 use GPT-4.1.
   */
  private async evaluateComplexity(
    text: string,
    gradeLevel: string,
    backgroundKnowledge: string,
    fkLevel: number
  ): Promise<{ data: VocabularyComplexityResult; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const systemPrompt = getSystemPrompt(gradeLevel);
    const userPrompt = getUserPrompt(text, gradeLevel, backgroundKnowledge, fkLevel);

    const provider = (gradeLevel === '3' || gradeLevel === '4')
      ? this.grades34ComplexityProvider
      : this.otherGradesComplexityProvider;

    const response = await provider.generateStructured({
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      schema: VocabularyComplexityOutputSchema,
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
 * Functional API for vocabulary evaluation
 *
 * @example
 * ```typescript
 * const result = await evaluateVocabularyComplexity(
 *   "The mitochondria is the powerhouse of the cell.",
 *   "3",
 *   {
 *     googleApiKey: process.env.GOOGLE_API_KEY,
 *     openaiApiKey: process.env.OPENAI_API_KEY
 *   }
 * );
 * ```
 */
export async function evaluateVocabularyComplexity(
  input: VocabularyComplexityInput,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<VocabularyComplexityResult>> {
  const evaluator = new VocabularyComplexityEvaluator(config);
  return evaluator.evaluate(input);
}
