import pLimit from 'p-limit';
import { VocabularyEvaluator } from './vocabulary.js';
import { SentenceStructureEvaluator } from './sentence-structure.js';
import type { BaseEvaluatorConfig } from './base.js';
import { BaseEvaluator } from './base.js';
import type { EvaluationResult } from '../schemas/index.js';
import { ValidationError } from '../errors.js';

/**
 * Internal data structure for text complexity evaluation
 * Stores either successful evaluation results or errors from sub-evaluators
 */
export interface TextComplexityInternal {
  vocabulary: EvaluationResult<string> | { error: Error };
  sentenceStructure: EvaluationResult<string> | { error: Error };
}

/**
 * Composite score for text complexity
 */
export interface TextComplexityScore {
  /** Overall complexity assessment */
  overall: string;
  /** Vocabulary complexity score */
  vocabulary: string;
  /** Sentence structure complexity score */
  sentenceStructure: string;
}

/**
 * Text Complexity Evaluator
 *
 * Composite evaluator that analyzes both vocabulary and sentence structure complexity.
 * Runs both evaluations in parallel with concurrency control to avoid rate limiting.
 *
 * Uses:
 * - VocabularyEvaluator (Google Gemini 2.5 Pro + OpenAI GPT-4o)
 * - SentenceStructureEvaluator (OpenAI GPT-4o)
 *
 * @example
 * ```typescript
 * const evaluator = new TextComplexityEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY,
 *   openaiApiKey: process.env.OPENAI_API_KEY
 * });
 *
 * const result = await evaluator.evaluate(text, "5");
 * console.log(result.score.overall);
 * console.log(result.score.vocabulary);
 * console.log(result.score.sentenceStructure);
 * ```
 */
export class TextComplexityEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: 'text-complexity',
    name: 'Text Complexity',
    description: 'Composite evaluator analyzing vocabulary and sentence structure complexity',
    supportedGrades: ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const,
    requiresGoogleKey: true,
    requiresOpenAIKey: true,
  };

  private vocabularyEvaluator: VocabularyEvaluator;
  private sentenceStructureEvaluator: SentenceStructureEvaluator;
  private limit: ReturnType<typeof pLimit>;

  constructor(config: BaseEvaluatorConfig) {
    // Call base constructor for common setup (telemetry, API key validation, etc.)
    super(config);

    // Create child evaluators with same config
    this.vocabularyEvaluator = new VocabularyEvaluator(config);
    this.sentenceStructureEvaluator = new SentenceStructureEvaluator(config);

    // Create concurrency limiter (max 3 concurrent operations)
    this.limit = pLimit(3);
  }

  /**
   * Evaluate text complexity for a given text and grade level
   *
   * Runs vocabulary and sentence structure evaluations in parallel with concurrency control.
   *
   * @param text - The text to evaluate
   * @param grade - The target grade level (3-12)
   * @returns Evaluation result with composite complexity score
   * @throws {Error} If text is empty or grade is invalid
   */
  async evaluate(
    text: string,
    grade: string
  ): Promise<EvaluationResult<TextComplexityScore, TextComplexityInternal>> {
    this.logger.info('Starting text complexity evaluation', {
      evaluator: 'text-complexity',
      operation: 'evaluate',
      grade,
      textLength: text.length,
    });

    // Use inherited validation methods
    this.validateText(text);
    this.validateGrade(grade, new Set(TextComplexityEvaluator.metadata.supportedGrades));

    const startTime = Date.now();

    // Run both evaluators in parallel with concurrency control
    const [vocabResult, sentenceResult] = await Promise.all([
      this.limit(() => this.runSubEvaluator(this.vocabularyEvaluator, text, grade)),
      this.limit(() => this.runSubEvaluator(this.sentenceStructureEvaluator, text, grade)),
    ]);

    const latencyMs = Date.now() - startTime;

    // Determine overall complexity
    const overall = this.determineOverallComplexity(vocabResult, sentenceResult);

    // Build combined reasoning
    const reasoning = this.buildCombinedReasoning(vocabResult, sentenceResult);

    // Check if any evaluations failed
    const vocabFailed = 'error' in vocabResult;
    const sentenceFailed = 'error' in sentenceResult;
    const hasFailures = vocabFailed || sentenceFailed;

    if (hasFailures) {
      const errors: string[] = [];
      if (vocabFailed) {
        errors.push(`Vocabulary evaluation failed: ${vocabResult.error.message}`);
      }
      if (sentenceFailed) {
        errors.push(`Sentence structure evaluation failed: ${sentenceResult.error.message}`);
      }

      this.logger.error('Text complexity evaluation completed with errors', {
        evaluator: 'text-complexity',
        operation: 'evaluate',
        grade,
        errors,
        processingTimeMs: latencyMs,
      });

      // If both failed, throw error
      if (vocabFailed && sentenceFailed) {
        throw new Error(
          `Text complexity evaluation failed: ${errors.join('; ')}`
        );
      }
    }

    const result = {
      score: {
        overall,
        vocabulary: vocabFailed ? 'N/A' : vocabResult.score,
        sentenceStructure: sentenceFailed ? 'N/A' : sentenceResult.score,
      },
      reasoning,
      metadata: {
        promptVersion: '1.0',
        model: 'composite:gemini-2.5-pro+gpt-4o',
        timestamp: new Date(),
        processingTimeMs: latencyMs,
      },
      _internal: {
        vocabulary: vocabResult,
        sentenceStructure: sentenceResult,
      },
    };

    // Send telemetry (fire-and-forget)
    this.sendTelemetry({
      status: hasFailures ? 'error' : 'success',
      latencyMs,
      textLength: text.length,
      grade,
      provider: 'composite:google+openai',
      retryAttempts: -1, // Composite evaluator doesn't track retries
      errorCode: hasFailures ? 'PartialFailure' : undefined,
      inputText: text,
    }).catch(() => {
      // Ignore telemetry errors
    });

    this.logger.info('Text complexity evaluation completed', {
      evaluator: 'text-complexity',
      operation: 'evaluate',
      grade,
      overall: result.score.overall,
      processingTimeMs: latencyMs,
      hasFailures,
    });

    return result;
  }

  /**
   * Run a sub-evaluator with error handling
   * Returns the evaluation result or an error object
   */
  private async runSubEvaluator(
    evaluator: { evaluate(text: string, grade: string): Promise<EvaluationResult<string>> },
    text: string,
    grade: string
  ): Promise<EvaluationResult<string> | { error: Error }> {
    try {
      return await evaluator.evaluate(text, grade);
    } catch (error) {
      return {
        error: error instanceof Error ? error : new Error(String(error)),
      };
    }
  }

  /**
   * Determine overall complexity from individual results
   *
   * Logic: Take the higher (more complex) of the two scores
   * Order: Slightly < Moderately < Very < Exceedingly
   */
  private determineOverallComplexity(
    vocabResult: EvaluationResult<string> | { error: Error },
    sentenceResult: EvaluationResult<string> | { error: Error }
  ): string {
    // If either failed, use the successful one or return error
    if ('error' in vocabResult) {
      return 'error' in sentenceResult ? 'Error' : sentenceResult.score;
    }
    if ('error' in sentenceResult) {
      return vocabResult.score;
    }

    // Both succeeded - take the higher complexity
    const complexityOrder = [
      'slightly complex',
      'moderately complex',
      'very complex',
      'exceedingly complex',
    ];

    const vocabIndex = complexityOrder.indexOf(vocabResult.score.toLowerCase());
    const sentenceIndex = complexityOrder.indexOf(sentenceResult.score.toLowerCase());

    // Return the higher complexity (or vocabulary if equal)
    return vocabIndex >= sentenceIndex ? vocabResult.score : sentenceResult.score;
  }

  /**
   * Build combined reasoning from individual results
   */
  private buildCombinedReasoning(
    vocabResult: EvaluationResult<string> | { error: Error },
    sentenceResult: EvaluationResult<string> | { error: Error }
  ): string {
    const parts: string[] = [];

    if ('error' in vocabResult) {
      parts.push(`**Vocabulary Complexity:** Evaluation failed - ${vocabResult.error.message}`);
    } else {
      parts.push(`**Vocabulary Complexity (${vocabResult.score}):**\n${vocabResult.reasoning}`);
    }

    if ('error' in sentenceResult) {
      parts.push(`**Sentence Structure Complexity:** Evaluation failed - ${sentenceResult.error.message}`);
    } else {
      parts.push(`**Sentence Structure Complexity (${sentenceResult.score}):**\n${sentenceResult.reasoning}`);
    }

    return parts.join('\n\n');
  }
}

/**
 * Functional API for text complexity evaluation
 *
 * @example
 * ```typescript
 * const result = await evaluateTextComplexity(
 *   "The cat sat on the mat.",
 *   "5",
 *   {
 *     googleApiKey: process.env.GOOGLE_API_KEY,
 *     openaiApiKey: process.env.OPENAI_API_KEY
 *   }
 * );
 * ```
 */
export async function evaluateTextComplexity(
  text: string,
  grade: string,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<TextComplexityScore, TextComplexityInternal>> {
  const evaluator = new TextComplexityEvaluator(config);
  return evaluator.evaluate(text, grade);
}
