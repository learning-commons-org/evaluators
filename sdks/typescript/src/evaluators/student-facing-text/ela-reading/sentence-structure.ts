import type { LLMProvider } from '../../../providers/index.js';
import {
  SentenceStructureOutputSchema,
  type SentenceStructureResult,
} from '../../../schemas/student-facing-text/ela-reading/sentence-structure.js';
import {
  SentenceAnalysisSchema,
  type SentenceAnalysis,
  type SentenceFeatures,
} from '../../../schemas/student-facing-text/ela-reading/sentence-structure-steps.js';
import { calculateReadabilityMetrics, addEngineeredFeatures, featuresToJSON } from '../../../features/index.js';
import {
  getSystemPromptAnalysis,
  getUserPromptAnalysis,
  getSystemPromptComplexity,
  getUserPromptComplexity,
} from '../../../prompts/sentence-structure/index.js';
import type { EvaluationResult } from '../../../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from '../../base.js';
import { validateInputs, type InputsOf } from '../../inputs.js';
import { requireStep } from '../../single-step.js';
import { declaredCredentials } from '../../credentials.js';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/input_schema.json';
import type { StageDetail } from '../../../telemetry/index.js';
import { EvaluatorError, wrapProviderError } from '../../../errors.js';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/sentence-structure/config.json';


/** The two declared steps, so each stage's temperature comes from the contract. */
const ANALYSIS_STEP = requireStep(CONFIG.steps, 'sentence_analysis', CONFIG.evaluator.name);
const CLASSIFY_STEP = requireStep(CONFIG.steps, 'classify_complexity', CONFIG.evaluator.name);

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type SentenceStructureInput = InputsOf<typeof INPUT_SCHEMA>;

/**
 * Sentence Structure Evaluator
 *
 * Judges how demanding a text's sentence construction is for a target grade, in two
 * stages: the first analyses grammatical structure, and the second classifies complexity
 * from those features against the rubric its grade selects.
 *
 * The complexity levels are whatever `output_schema.json` declares — currently
 * `slightly_complex` through `exceedingly_complex` — and are returned verbatim.
 *
 * @example
 * ```typescript
 * const evaluator = new SentenceStructureEvaluator({
 *   openaiApiKey: process.env.OPENAI_API_KEY,
 * });
 *
 * const result = await evaluator.evaluate({ text, grade_level: '3' });
 * console.log(result.result.complexity_score); // "moderately_complex"
 * console.log(result.result.reasoning);
 * ```
 */
export class SentenceStructureEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    outcome: CONFIG.outcome,
    requiredCredentials: declaredCredentials(CONFIG),
    supportedGrades: INPUT_SCHEMA.properties.grade_level.enum,
    defaultProviders: [Provider.OpenAI] as const,
  };

  private provider: LLMProvider;

  constructor(config: BaseEvaluatorConfig) {
    // Call base constructor for common setup (telemetry, API key validation, etc.)
    super(config);

    // Both stages use the same model — share a single provider instance
    this.provider = this.createConfiguredProvider(Provider.OpenAI, 'gpt-4o-2024-08-06', config.openaiApiKey);
  }

  /**
   * Evaluate sentence structure complexity.
   *
   * @param input - The inputs declared in this evaluator's `input_schema.json`
   * @returns Evaluation result with the complexity level and its reasoning
   * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
   * @throws {LLMOutputProcessingError} If the model's response fails its output schema
   */
  async evaluate(input: SentenceStructureInput): Promise<EvaluationResult<SentenceStructureResult>> {
    let text = '';
    let gradeLevel = '';
    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      // Inside the try so a validation failure is telemetered as an error event,
      // and before the inputs are read so a non-object is reported as one.
      validateInputs(input, INPUT_SCHEMA);
      ({ text, grade_level: gradeLevel } = input);

      this.logger.info('Starting sentence structure evaluation', {
        evaluator: SentenceStructureEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        textLength: text.length,
      });

      this.logger.debug('Stage 1: Analyzing sentence structure', {
        evaluator: SentenceStructureEvaluator.metadata.id,
        operation: 'sentence_analysis',
      });
      // Stage 1: Analyze sentence structure
      const analysisResponse = await this.analyzeSentenceStructure(text);

      stageDetails.push({
        stage: 'sentence_analysis',
        provider: this.provider.label,
        latency_ms: analysisResponse.latencyMs,
        token_usage: {
          input_tokens: analysisResponse.usage.inputTokens,
          output_tokens: analysisResponse.usage.outputTokens,
        },
      });

      // Compute engineered features
      const features = addEngineeredFeatures(analysisResponse.data);

      this.logger.debug('Stage 2: Classifying complexity', {
        evaluator: SentenceStructureEvaluator.metadata.id,
        operation: 'complexity_classification',
      });
      // Stage 2: Classify complexity
      const complexityResponse = await this.classifyComplexity(features, gradeLevel, text);

      stageDetails.push({
        stage: 'complexity_classification',
        provider: this.provider.label,
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
        evaluator: SentenceStructureEvaluator.metadata.id,
        result: complexityResponse.data,
        metadata: {
          model: this.provider.label,
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
        provider: this.provider.label,
        tokenUsage: totalTokenUsage,
        metadata: {
          stage_details: stageDetails,
        },
        inputText: text,
      }).catch(() => {
        // Ignore telemetry errors
      });

      this.logger.info('Sentence structure evaluation completed successfully', {
        evaluator: SentenceStructureEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        score: complexityResponse.data.complexity_score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      // Log the error
      this.logger.error('Sentence structure evaluation failed', {
        evaluator: SentenceStructureEvaluator.metadata.id,
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
        provider: this.provider.label,
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

      // Wrap provider errors into appropriate error types
      throw wrapProviderError(error, this.providerContext(this.provider));
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

    const response = await this.provider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPromptAnalysis() },
        { role: 'user', content: userPrompt },
      ],
      schema: SentenceAnalysisSchema,
      temperature: ANALYSIS_STEP.generation.temperature,
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
   * Uses engineered features and grade-level-specific rubric to classify complexity level
   */
  private async classifyComplexity(
    features: SentenceFeatures,
    gradeLevel: string,
    excerpt: string
  ): Promise<{ data: SentenceStructureResult; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    // Convert features to JSON string (cast to int by default, matching Python)
    const featuresJSON = featuresToJSON(features, 1, true);

    const userPrompt = getUserPromptComplexity(featuresJSON, gradeLevel, excerpt);

    const response = await this.provider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPromptComplexity() },
        { role: 'user', content: userPrompt },
      ],
      schema: SentenceStructureOutputSchema,
      temperature: CLASSIFY_STEP.generation.temperature,
    });

    return {
      data: response.data,
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
  input: SentenceStructureInput,
  config: BaseEvaluatorConfig
): Promise<EvaluationResult<SentenceStructureResult>> {
  const evaluator = new SentenceStructureEvaluator(config);
  return evaluator.evaluate(input);
}
