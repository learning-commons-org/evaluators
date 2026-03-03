import type { LLMProvider } from '../providers/index.js';
import { createProvider } from '../providers/index.js';
import {
  VocabularyComplexitySchema,
  type VocabularyComplexity,
  type BackgroundKnowledge,
} from '../schemas/vocabulary.js';
import { calculateFleschKincaidGrade } from '../features/index.js';
import {
  getBackgroundKnowledgePrompt,
  getSystemPrompt,
  getUserPrompt,
} from '../prompts/vocabulary/index.js';
import type { EvaluationResult } from '../schemas/index.js';
import { BaseEvaluator, type BaseEvaluatorConfig } from './base.js';
import type { StageDetail } from '../telemetry/index.js';
import { ValidationError, wrapProviderError } from '../errors.js';

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
 * const evaluator = new VocabularyEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY,
 *   openaiApiKey: process.env.OPENAI_API_KEY
 * });
 *
 * const result = await evaluator.evaluate(text, "3");
 * console.log(result.score); // "moderately complex"
 * console.log(result.reasoning);
 * ```
 */
export class VocabularyEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: 'vocabulary',
    name: 'Vocabulary',
    description: 'Evaluates vocabulary complexity of educational texts relative to grade level',
    supportedGrades: ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const,
    requiresGoogleKey: true,
    requiresOpenAIKey: true,
  };

  private grades34ComplexityProvider: LLMProvider;
  private otherGradesComplexityProvider: LLMProvider;
  private backgroundKnowledgeProvider: LLMProvider;

  constructor(config: BaseEvaluatorConfig) {
    // Call base constructor for common setup (telemetry, API key validation, etc.)
    super(config);

    // Create Google Gemini provider for complexity evaluation (grades 3-4)
    this.grades34ComplexityProvider = createProvider({
      type: 'google',
      model: 'gemini-2.5-pro',
      apiKey: config.googleApiKey,
      maxRetries: this.config.maxRetries,
    });

    // Create OpenAI GPT-4.1 provider for complexity evaluation (grades 5-12)
    this.otherGradesComplexityProvider = createProvider({
      type: 'openai',
      model: 'gpt-4.1-2025-04-14',
      apiKey: config.openaiApiKey,
      maxRetries: this.config.maxRetries,
    });

    // Create OpenAI GPT-4o provider for background knowledge generation
    this.backgroundKnowledgeProvider = createProvider({
      type: 'openai',
      model: 'gpt-4o-2024-11-20',
      apiKey: config.openaiApiKey,
      maxRetries: this.config.maxRetries,
    });
  }

  /**
   * Evaluate vocabulary complexity for a given text and grade level
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
  ): Promise<EvaluationResult<string, VocabularyComplexity>> {
    this.logger.info('Starting vocabulary evaluation', {
      evaluator: 'vocabulary',
      operation: 'evaluate',
      grade,
      textLength: text.length,
    });

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];
    const complexityProviderName = (grade === '3' || grade === '4')
      ? 'google:gemini-2.5-pro'
      : 'openai:gpt-4.1-2025-04-14';

    try {
      // Validate inputs — inside try so validation errors are telemetered.
      // If partners consistently pass invalid grades/text, telemetry will surface documentation gaps.
      this.validateText(text);
      this.validateGrade(grade, new Set(VocabularyEvaluator.metadata.supportedGrades));
      this.logger.debug('Stage 1: Generating background knowledge', {
        evaluator: 'vocabulary',
        operation: 'background_knowledge',
      });
      // Stage 1: Generate background knowledge assumption
      const bgResponse = await this.getBackgroundKnowledgeAssumption(text, grade);

      stageDetails.push({
        stage: 'background_knowledge',
        provider: 'openai:gpt-4o-2024-11-20',
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
        grade,
        bgResponse.knowledge.assumption,
        fkLevel
      );

      stageDetails.push({
        stage: 'complexity_evaluation',
        provider: complexityProviderName,
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
        score: complexityResponse.data.complexity_score,
        reasoning: complexityResponse.data.reasoning,
        metadata: {
          promptVersion: '1.2.0',
          model: `openai:gpt-4o-2024-11-20 + ${complexityProviderName}`,
          timestamp: new Date(),
          processingTimeMs: latencyMs,
        },
        _internal: complexityResponse.data,
      };

      // Send success telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        grade,
        provider: `openai:gpt-4o-2024-11-20 + ${complexityProviderName}`,
        tokenUsage: totalTokenUsage,
        metadata: {
          stage_details: stageDetails,
        },
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      this.logger.info('Vocabulary evaluation completed successfully', {
        evaluator: 'vocabulary',
        operation: 'evaluate',
        grade,
        score: result.score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      // Log the error
      this.logger.error('Vocabulary evaluation failed', {
        evaluator: 'vocabulary',
        operation: 'evaluate',
        grade,
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
        grade,
        provider: `openai:gpt-4o-2024-11-20 + ${complexityProviderName}`,
        tokenUsage: totalTokenUsage,
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      // Re-throw validation errors as-is
      if (error instanceof ValidationError) {
        throw error;
      }

      // Wrap provider errors into appropriate error types
      throw wrapProviderError(error, 'Vocabulary evaluation failed');
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
    grade: string
  ): Promise<{ knowledge: BackgroundKnowledge; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const prompt = getBackgroundKnowledgePrompt(text, grade);

    const response = await this.backgroundKnowledgeProvider.generateText(
      [{ role: 'user', content: prompt }],
      0 // temperature = 0 for consistency
    );

    return {
      knowledge: {
        assumption: response.text.trim(),
        grade,
      },
      usage: response.usage,
      latencyMs: response.latencyMs,
    };
  }

  /**
   * Stage 2: Evaluate vocabulary complexity
   *
   * Uses the Qual Text Complexity rubric (SAP) and background knowledge to evaluate vocabulary complexity.
   * Grades 3-4 use Gemini 2.5 Pro; grades 5-12 use GPT-4.1.
   */
  private async evaluateComplexity(
    text: string,
    grade: string,
    backgroundKnowledge: string,
    fkLevel: number
  ): Promise<{ data: VocabularyComplexity; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const systemPrompt = getSystemPrompt(grade);
    const userPrompt = getUserPrompt(text, grade, backgroundKnowledge, fkLevel);

    const provider = (grade === '3' || grade === '4')
      ? this.grades34ComplexityProvider
      : this.otherGradesComplexityProvider;

    const response = await provider.generateStructured({
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      schema: VocabularyComplexitySchema,
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
 * const result = await evaluateVocabulary(
 *   "The mitochondria is the powerhouse of the cell.",
 *   "3",
 *   {
 *     googleApiKey: process.env.GOOGLE_API_KEY,
 *     openaiApiKey: process.env.OPENAI_API_KEY
 *   }
 * );
 * ```
 */
export async function evaluateVocabulary(
  text: string,
  grade: string,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<string, VocabularyComplexity>> {
  const evaluator = new VocabularyEvaluator(config);
  return evaluator.evaluate(text, grade);
}
