import type { LLMProvider } from '../providers/index.js';
import { createProvider } from '../providers/index.js';
import {
  SentenceAnalysisSchema,
  ComplexityClassificationSchema,
  type SentenceAnalysis,
  type SentenceFeatures,
  type ComplexityClassification,
} from '../schemas/sentence-structure.js';
import { calculateReadabilityMetrics, addEngineeredFeatures, featuresToJSON } from '../features/index.js';
import {
  getSystemPromptAnalysis,
  getUserPromptAnalysis,
  getSystemPromptComplexity,
  getUserPromptComplexity,
} from '../prompts/sentence-structure/index.js';
import type { EvaluationResult, ComplexityLevel } from '../schemas/index.js';
import { BaseEvaluator, type BaseEvaluatorConfig } from './base.js';
import type { StageDetail } from '../telemetry/index.js';
import { ValidationError, wrapProviderError } from '../errors.js';

/**
 * Internal data structure for sentence structure evaluation
 */
interface SentenceStructureInternal {
  sentenceAnalysis: SentenceAnalysis;
  features: SentenceFeatures;
  complexity: ComplexityClassification;
}

/**
 * Normalize complexity label to handle LLM output variations
 * Ported from Python normalize_label function
 */
function normalizeLabel(label: string | null | undefined): string | null {
  if (!label) {
    return null;
  }

  const normalized = label.trim().toLowerCase();
  const mapping: Record<string, string> = {
    'slightly complex': 'Slightly Complex',
    'moderately complex': 'Moderately Complex',
    'very complex': 'Very Complex',
    'exceedingly complex': 'Exceedingly Complex',
    'extremely complex': 'Exceedingly Complex', // Maps to Exceedingly Complex
  };

  return mapping[normalized] || null; // Return null if no mapping found
}

/**
 * Sentence Structure Evaluator
 *
 * Evaluates sentence structure complexity of educational texts relative to grade level.
 * Uses a 2-stage process:
 * 1. Analyze grammatical structure (sentence types, clauses, phrases, etc.)
 * 2. Classify complexity using features and grade-specific rubric
 *
 * Based on SCASS Text Complexity rubric with 4 levels:
 * - Slightly Complex
 * - Moderately Complex
 * - Very Complex
 * - Exceedingly Complex
 *
 * @example
 * ```typescript
 * const evaluator = new SentenceStructureEvaluator({
 *   openaiApiKey: process.env.OPENAI_API_KEY
 * });
 *
 * const result = await evaluator.evaluate(text, "3");
 * console.log(result.score); // "Moderately Complex"
 * console.log(result.reasoning);
 * ```
 */
export class SentenceStructureEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: 'sentence-structure',
    name: 'Sentence Structure',
    description: 'Evaluates sentence structure complexity based on grammatical features',
    supportedGrades: ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const,
    requiresGoogleKey: false,
    requiresOpenAIKey: true,
  };

  private analysisProvider: LLMProvider;
  private complexityProvider: LLMProvider;

  constructor(config: BaseEvaluatorConfig) {
    // Call base constructor for common setup (telemetry, API key validation, etc.)
    super(config);

    // Create OpenAI GPT-4o provider for both stages
    this.analysisProvider = createProvider({
      type: 'openai',
      model: 'gpt-4o',
      apiKey: config.openaiApiKey,
      maxRetries: this.config.maxRetries,
    });

    this.complexityProvider = createProvider({
      type: 'openai',
      model: 'gpt-4o',
      apiKey: config.openaiApiKey,
      maxRetries: this.config.maxRetries,
    });
  }

  /**
   * Evaluate sentence structure complexity for a given text and grade level
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
  ): Promise<EvaluationResult<string, SentenceStructureInternal>> {
    this.logger.info('Starting sentence structure evaluation', {
      evaluator: 'sentence-structure',
      operation: 'evaluate',
      grade,
      textLength: text.length,
    });

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      // Validate inputs — inside try so validation errors are telemetered.
      this.validateText(text);
      this.validateGrade(grade, new Set(SentenceStructureEvaluator.metadata.supportedGrades));
      this.logger.debug('Stage 1: Analyzing sentence structure', {
        evaluator: 'sentence-structure',
        operation: 'sentence_analysis',
      });
      // Stage 1: Analyze sentence structure
      const analysisResponse = await this.analyzeSentenceStructure(text);

      stageDetails.push({
        stage: 'sentence_analysis',
        provider: 'openai:gpt-4o',
        latency_ms: analysisResponse.latencyMs,
        token_usage: {
          input_tokens: analysisResponse.usage.inputTokens,
          output_tokens: analysisResponse.usage.outputTokens,
        },
      });

      // Compute engineered features
      const features = addEngineeredFeatures(analysisResponse.data);

      this.logger.debug('Stage 2: Classifying complexity', {
        evaluator: 'sentence-structure',
        operation: 'complexity_classification',
      });
      // Stage 2: Classify complexity
      const complexityResponse = await this.classifyComplexity(features, grade, text);

      stageDetails.push({
        stage: 'complexity_classification',
        provider: 'openai:gpt-4o',
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
        score: complexityResponse.data.answer,
        reasoning: complexityResponse.data.reasoning,
        metadata: {
          promptVersion: '1.2.0',
          model: 'openai:gpt-4o',
          timestamp: new Date(),
          processingTimeMs: latencyMs,
        },
        _internal: {
          sentenceAnalysis: analysisResponse.data,
          features,
          complexity: complexityResponse.data,
        },
      };

      // Send success telemetry (fire-and-forget)
      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        grade,
        provider: 'openai:gpt-4o',
        tokenUsage: totalTokenUsage,
        metadata: {
          stage_details: stageDetails,
        },
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      this.logger.info('Sentence structure evaluation completed successfully', {
        evaluator: 'sentence-structure',
        operation: 'evaluate',
        grade,
        score: result.score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      // Log the error
      this.logger.error('Sentence structure evaluation failed', {
        evaluator: 'sentence-structure',
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
        provider: 'openai:gpt-4o',
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
      throw wrapProviderError(error, 'Sentence structure evaluation failed');
    }
  }

  /**
   * Stage 1: Analyze sentence grammatical structure
   *
   * Analyzes sentence types, clauses, phrases, transitions, and other grammatical features
   */
  private async analyzeSentenceStructure(
    text: string
  ): Promise<{ data: SentenceAnalysis; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    // Compute ground truth counts
    const metrics = calculateReadabilityMetrics(text);

    const gtCountsStr = [
      `num_sentences: ${metrics.sentenceCount}`,
      `num_words: ${metrics.wordCount}`,
      `num_char: ${metrics.characterCount}`,
      `num_syllable: ${metrics.syllableCount}`,
      `flesch_kincaid_grade: ${metrics.fleschKincaidGrade}`,
    ].join('\n');

    const userPrompt = getUserPromptAnalysis(text, gtCountsStr);

    const response = await this.analysisProvider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPromptAnalysis() },
        { role: 'user', content: userPrompt },
      ],
      schema: SentenceAnalysisSchema,
      temperature: 0,
    });

    return {
      data: response.data,
      usage: response.usage,
      latencyMs: response.latencyMs,
    };
  }

  /**
   * Stage 2: Classify sentence structure complexity
   *
   * Uses engineered features and grade-specific rubric to classify complexity level
   */
  private async classifyComplexity(
    features: SentenceFeatures,
    grade: string,
    excerpt: string
  ): Promise<{ data: ComplexityClassification; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    // Convert features to JSON string (cast to int by default, matching Python)
    const featuresJSON = featuresToJSON(features, 1, true);

    const userPrompt = getUserPromptComplexity(featuresJSON, grade, excerpt);

    const response = await this.complexityProvider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPromptComplexity() },
        { role: 'user', content: userPrompt },
      ],
      schema: ComplexityClassificationSchema,
      temperature: 0,
    });

    // Normalize label to handle LLM output variations
    const normalizedAnswer = normalizeLabel(response.data.answer);

    if (!normalizedAnswer) {
      throw new Error(
        `Failed to normalize complexity label. Received unexpected value: "${response.data.answer}". ` +
        `Expected one of: Slightly Complex, Moderately Complex, Very Complex, Exceedingly Complex, Extremely Complex.`
      );
    }

    return {
      data: {
        ...response.data,
        answer: normalizedAnswer as ComplexityLevel,
      },
      usage: response.usage,
      latencyMs: response.latencyMs,
    };
  }
}

/**
 * Functional API for sentence structure evaluation
 *
 * @example
 * ```typescript
 * const result = await evaluateSentenceStructure(
 *   "The cat sat on the mat. It was sleeping peacefully.",
 *   "3",
 *   {
 *     openaiApiKey: process.env.OPENAI_API_KEY
 *   }
 * );
 * ```
 */
export async function evaluateSentenceStructure(
  text: string,
  grade: string,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<string, SentenceStructureInternal>> {
  const evaluator = new SentenceStructureEvaluator(config);
  return evaluator.evaluate(text, grade);
}
