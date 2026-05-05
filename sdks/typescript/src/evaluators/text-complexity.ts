import pLimit from 'p-limit';
import { VocabularyEvaluator } from './vocabulary.js';
import { SentenceStructureEvaluator } from './sentence-structure.js';
import { SmkEvaluator } from './smk.js';
import { ConventionalityEvaluator } from './conventionality.js';
import type { SentenceStructureInternal } from '../schemas/sentence-structure.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from './base.js';
import type { EvaluationResult, TextComplexityLevel } from '../schemas/index.js';
import type { VocabularyInternal } from '../schemas/vocabulary.js';
import type { SmkInternal } from '../schemas/smk.js';
import type { ConventionalityInternal } from '../schemas/conventionality.js';

/**
 * Result map returned by TextComplexityEvaluator.
 * Each key holds the full evaluation result from its sub-evaluator, or an error if it failed.
 */
export interface TextComplexityResult {
  vocabulary: EvaluationResult<TextComplexityLevel, VocabularyInternal> | { error: Error };
  sentenceStructure: EvaluationResult<TextComplexityLevel, SentenceStructureInternal> | { error: Error };
  subjectMatterKnowledge: EvaluationResult<TextComplexityLevel, SmkInternal> | { error: Error };
  conventionality: EvaluationResult<TextComplexityLevel, ConventionalityInternal> | { error: Error };
}

/**
 * Text Complexity Evaluator
 *
 * Composite evaluator that analyzes vocabulary, sentence structure, subject matter knowledge, and conventionality.
 * Runs all evaluations in parallel with concurrency control to avoid rate limiting.
 *
 * Uses:
 * - VocabularyEvaluator (Google Gemini 2.5 Pro + OpenAI GPT-4o)
 * - SentenceStructureEvaluator (OpenAI GPT-4o)
 * - SmkEvaluator (Google Gemini 3 Flash Preview)
 * - ConventionalityEvaluator (Google Gemini 3 Flash Preview)
 *
 * @example
 * ```typescript
 * const evaluator = new TextComplexityEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY,
 *   openaiApiKey: process.env.OPENAI_API_KEY
 * });
 *
 * const result = await evaluator.evaluate(text, "5");
 * if (!('error' in result.vocabulary)) {
 *   console.log(result.vocabulary.score); // "Moderately complex"
 * }
 * ```
 */
export class TextComplexityEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: 'text-complexity',
    name: 'Text Complexity',
    description: 'Composite evaluator analyzing vocabulary, sentence structure, subject matter knowledge, and conventionality complexity',
    supportedGrades: ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const,
    defaultProviders: [Provider.Google, Provider.OpenAI] as const,
  };

  private vocabularyEvaluator: VocabularyEvaluator;
  private sentenceStructureEvaluator: SentenceStructureEvaluator;
  private smkEvaluator: SmkEvaluator;
  private conventionalityEvaluator: ConventionalityEvaluator;
  private limit: ReturnType<typeof pLimit>;

  constructor(config: BaseEvaluatorConfig) {
    // Call base constructor for common setup (telemetry, API key validation, etc.)
    super(config);

    // Create child evaluators with same config
    this.vocabularyEvaluator = new VocabularyEvaluator(config);
    this.sentenceStructureEvaluator = new SentenceStructureEvaluator(config);
    this.smkEvaluator = new SmkEvaluator(config);
    this.conventionalityEvaluator = new ConventionalityEvaluator(config);

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
   * @param grade - The target grade level (3-12)
   * @returns Map of sub-evaluator results
   * @throws {ValidationError} If text is empty or grade is invalid
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {Error} If all sub-evaluators fail
   */
  async evaluate(text: string, grade: string): Promise<TextComplexityResult> {
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

    // Run all evaluators in parallel with concurrency control
    const [vocabResult, sentenceResult, smkResult, conventionalityResult]: [
      EvaluationResult<TextComplexityLevel, VocabularyInternal> | { error: Error },
      EvaluationResult<TextComplexityLevel, SentenceStructureInternal> | { error: Error },
      EvaluationResult<TextComplexityLevel, SmkInternal> | { error: Error },
      EvaluationResult<TextComplexityLevel, ConventionalityInternal> | { error: Error },
    ] = await Promise.all([
      this.limit(() => this.runSubEvaluator(this.vocabularyEvaluator, text, grade)),
      this.limit(() => this.runSubEvaluator(this.sentenceStructureEvaluator, text, grade)),
      this.limit(() => this.runSubEvaluator(this.smkEvaluator, text, grade)),
      this.limit(() => this.runSubEvaluator(this.conventionalityEvaluator, text, grade)),
    ]);

    const latencyMs = Date.now() - startTime;
    const vocabFailed = 'error' in vocabResult;
    const sentenceFailed = 'error' in sentenceResult;
    const smkFailed = 'error' in smkResult;
    const conventionalityFailed = 'error' in conventionalityResult;
    const hasFailures = vocabFailed || sentenceFailed || smkFailed || conventionalityFailed;

    if (hasFailures) {
      const errors: string[] = [];
      if (vocabFailed) errors.push(`Vocabulary: ${vocabResult.error.message}`);
      if (sentenceFailed) errors.push(`Sentence structure: ${sentenceResult.error.message}`);
      if (smkFailed) errors.push(`Subject matter knowledge: ${smkResult.error.message}`);
      if (conventionalityFailed) errors.push(`Conventionality: ${conventionalityResult.error.message}`);

      this.logger.error('Text complexity evaluation completed with errors', {
        evaluator: 'text-complexity',
        operation: 'evaluate',
        grade,
        errors,
        processingTimeMs: latencyMs,
      });

      if (vocabFailed && sentenceFailed && smkFailed && conventionalityFailed) {
        throw new Error(`Text complexity evaluation failed: ${errors.join('; ')}`);
      }
    }

    // Send telemetry (fire-and-forget)
    this.sendTelemetry({
      status: hasFailures ? 'error' : 'success',
      latencyMs,
      textLength: text.length,
      grade,
      provider: this.config.modelOverride
        ? `${this.config.modelOverride.provider}:${this.config.modelOverride.model}`
        : 'composite:google+openai',
      errorCode: hasFailures ? 'PartialFailure' : undefined,
      inputText: text,
    }).catch(() => {
      // Ignore telemetry errors
    });

    this.logger.info('Text complexity evaluation completed', {
      evaluator: 'text-complexity',
      operation: 'evaluate',
      grade,
      processingTimeMs: latencyMs,
      hasFailures,
    });

    return { vocabulary: vocabResult, sentenceStructure: sentenceResult, subjectMatterKnowledge: smkResult, conventionality: conventionalityResult };
  }

  /**
   * Run a sub-evaluator with error handling.
   * Returns the evaluation result or `{ error: Error }` if the evaluator throws.
   */
  private async runSubEvaluator<TScore, TInternal>(
    evaluator: { evaluate(text: string, grade: string): Promise<EvaluationResult<TScore, TInternal>> },
    text: string,
    grade: string
  ): Promise<EvaluationResult<TScore, TInternal> | { error: Error }> {
    try {
      return await evaluator.evaluate(text, grade);
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
  grade: string,
  config: BaseEvaluatorConfig
): Promise<TextComplexityResult> {
  const evaluator = new TextComplexityEvaluator(config);
  return evaluator.evaluate(text, grade);
}
