import pLimit from 'p-limit';
import { VocabularyComplexityEvaluator } from './vocabulary-complexity.js';
import { SentenceStructureEvaluator } from './sentence-structure.js';
import { BackgroundKnowledgeDemandsEvaluator } from './background-knowledge-demands.js';
import { MeaningDirectnessEvaluator } from './meaning-directness.js';
import type { SentenceStructureInternal } from '../schemas/sentence-structure.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from './base.js';
import type { EvaluationResult, TextComplexityLevel } from '../schemas/index.js';
import type { VocabularyComplexityInternal } from '../schemas/vocabulary-complexity.js';
import type { BackgroundKnowledgeDemandsInternal } from '../schemas/background-knowledge-demands.js';
import type { MeaningDirectnessInternal } from '../schemas/meaning-directness.js';

/**
 * Result map returned by TextComplexityEvaluator.
 * Each key holds the full evaluation result from its sub-evaluator, or an error if it failed.
 */
export interface TextComplexityResult {
  vocabularyComplexity: EvaluationResult<TextComplexityLevel, VocabularyComplexityInternal> | { error: Error };
  sentenceStructure: EvaluationResult<TextComplexityLevel, SentenceStructureInternal> | { error: Error };
  backgroundKnowledgeDemands: EvaluationResult<TextComplexityLevel, BackgroundKnowledgeDemandsInternal> | { error: Error };
  meaningDirectness: EvaluationResult<TextComplexityLevel, MeaningDirectnessInternal> | { error: Error };
}

/**
 * Text Complexity Evaluator
 *
 * Composite evaluator that analyzes vocabulary complexity, sentence structure, background knowledge demands, and meaning directness.
 * Runs all evaluations in parallel with concurrency control to avoid rate limiting.
 *
 * Uses:
 * - VocabularyComplexityEvaluator (Google Gemini 2.5 Pro + OpenAI GPT-4o)
 * - SentenceStructureEvaluator (OpenAI GPT-4o)
 * - BackgroundKnowledgeDemandsEvaluator (Google Gemini 3 Flash Preview)
 * - MeaningDirectnessEvaluator (Google Gemini 3 Flash Preview)
 *
 * @example
 * ```typescript
 * const evaluator = new TextComplexityEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY,
 *   openaiApiKey: process.env.OPENAI_API_KEY
 * });
 *
 * const result = await evaluator.evaluate(text, "5");
 * if (!('error' in result.vocabularyComplexity)) {
 *   console.log(result.vocabularyComplexity.score); // "Moderately complex"
 * }
 * ```
 */
export class TextComplexityEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: 'text-complexity',
    name: 'Text Complexity',
    description: 'Composite evaluator analyzing vocabulary complexity, sentence structure, background knowledge demands, and meaning directness',
    supportedGrades: ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const,
    defaultProviders: [Provider.Google, Provider.OpenAI] as const,
  };

  private vocabularyEvaluator: VocabularyComplexityEvaluator;
  private sentenceStructureEvaluator: SentenceStructureEvaluator;
  private backgroundKnowledgeDemandsEvaluator: BackgroundKnowledgeDemandsEvaluator;
  private meaningDirectnessEvaluator: MeaningDirectnessEvaluator;
  private limit: ReturnType<typeof pLimit>;

  constructor(config: BaseEvaluatorConfig) {
    // Call base constructor for common setup (telemetry, API key validation, etc.)
    super(config);

    // Create child evaluators with same config
    this.vocabularyEvaluator = new VocabularyComplexityEvaluator(config);
    this.sentenceStructureEvaluator = new SentenceStructureEvaluator(config);
    this.backgroundKnowledgeDemandsEvaluator = new BackgroundKnowledgeDemandsEvaluator(config);
    this.meaningDirectnessEvaluator = new MeaningDirectnessEvaluator(config);

    // Create concurrency limiter (max 3 concurrent operations)
    this.limit = pLimit(3);
  }

  /**
   * Evaluate text complexity for a given text and grade level
   *
   * Runs vocabulary, sentence structure, and SMK evaluations in parallel with concurrency control.
   * If all three sub-evaluators fail, throws an error. Otherwise returns a result map where
   * failed sub-evaluators are represented as `{ error: Error }`.
   *
   * @param text - The text to evaluate
   * @param gradeLevel - The target grade level (3-12)
   * @returns Map of sub-evaluator results
   * @throws {InputValidationError} If text is empty, too short/long, or gradeLevel is invalid
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {Error} If all sub-evaluators fail
   */
  async evaluate(text: string, gradeLevel: string): Promise<TextComplexityResult> {
    this.logger.info('Starting text complexity evaluation', {
      evaluator: TextComplexityEvaluator.metadata.id,
      operation: 'evaluate',
      gradeLevel,
      textLength: text.length,
    });

    // Use inherited validation methods
    this.validateText(text);
    this.validateGradeLevel(gradeLevel, new Set(TextComplexityEvaluator.metadata.supportedGrades));

    const startTime = Date.now();

    // Run all evaluators in parallel with concurrency control
    const [vocabResult, sentenceResult, backgroundKnowledgeDemandsResult, meaningDirectnessResult]: [
      EvaluationResult<TextComplexityLevel, VocabularyComplexityInternal> | { error: Error },
      EvaluationResult<TextComplexityLevel, SentenceStructureInternal> | { error: Error },
      EvaluationResult<TextComplexityLevel, BackgroundKnowledgeDemandsInternal> | { error: Error },
      EvaluationResult<TextComplexityLevel, MeaningDirectnessInternal> | { error: Error },
    ] = await Promise.all([
      this.limit(() => this.runSubEvaluator(this.vocabularyEvaluator, text, gradeLevel)),
      this.limit(() => this.runSubEvaluator(this.sentenceStructureEvaluator, text, gradeLevel)),
      this.limit(() => this.runSubEvaluator(this.backgroundKnowledgeDemandsEvaluator, text, gradeLevel)),
      this.limit(() => this.runSubEvaluator(this.meaningDirectnessEvaluator, text, gradeLevel)),
    ]);

    const latencyMs = Date.now() - startTime;
    const vocabFailed = 'error' in vocabResult;
    const sentenceFailed = 'error' in sentenceResult;
    const backgroundKnowledgeDemandsFailed = 'error' in backgroundKnowledgeDemandsResult;
    const meaningDirectnessFailed = 'error' in meaningDirectnessResult;
    const hasFailures = vocabFailed || sentenceFailed || backgroundKnowledgeDemandsFailed || meaningDirectnessFailed;

    if (hasFailures) {
      const errors: string[] = [];
      if (vocabFailed) errors.push(`Vocabulary complexity: ${vocabResult.error.message}`);
      if (sentenceFailed) errors.push(`Sentence structure: ${sentenceResult.error.message}`);
      if (backgroundKnowledgeDemandsFailed) errors.push(`Background knowledge demands: ${backgroundKnowledgeDemandsResult.error.message}`);
      if (meaningDirectnessFailed) errors.push(`Meaning directness: ${meaningDirectnessResult.error.message}`);

      this.logger.error('Text complexity evaluation completed with errors', {
        evaluator: TextComplexityEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        errors,
        processingTimeMs: latencyMs,
      });

      if (vocabFailed && sentenceFailed && backgroundKnowledgeDemandsFailed && meaningDirectnessFailed) {
        throw new Error(`Text complexity evaluation failed: ${errors.join('; ')}`);
      }
    }

    // Send telemetry (fire-and-forget)
    this.sendTelemetry({
      status: hasFailures ? 'error' : 'success',
      latencyMs,
      textLength: text.length,
      gradeLevel,
      provider: this.config.modelOverride
        ? `${this.config.modelOverride.provider}:${this.config.modelOverride.model}`
        : 'composite:google+openai',
      errorCode: hasFailures ? 'PartialFailure' : undefined,
      inputText: text,
    }).catch(() => {
      // Ignore telemetry errors
    });

    this.logger.info('Text complexity evaluation completed', {
      evaluator: TextComplexityEvaluator.metadata.id,
      operation: 'evaluate',
      gradeLevel,
      processingTimeMs: latencyMs,
      hasFailures,
    });

    return { vocabularyComplexity: vocabResult, sentenceStructure: sentenceResult, backgroundKnowledgeDemands: backgroundKnowledgeDemandsResult, meaningDirectness: meaningDirectnessResult };
  }

  /**
   * Run a sub-evaluator with error handling.
   * Returns the evaluation result or `{ error: Error }` if the evaluator throws.
   */
  private async runSubEvaluator<TScore, TInternal>(
    evaluator: { evaluate(text: string, gradeLevel: string): Promise<EvaluationResult<TScore, TInternal>> },
    text: string,
    gradeLevel: string
  ): Promise<EvaluationResult<TScore, TInternal> | { error: Error }> {
    try {
      return await evaluator.evaluate(text, gradeLevel);
    } catch (error) {
      return { error: error instanceof Error ? error : new Error(String(error)) };
    }
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
  gradeLevel: string,
  config: BaseEvaluatorConfig
): Promise<TextComplexityResult> {
  const evaluator = new TextComplexityEvaluator(config);
  return evaluator.evaluate(text, gradeLevel);
}
