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
import { requireStep } from '../../single-step.js';
import { declaredCredentials } from '../../credentials.js';
import INPUT_SCHEMA from '../../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/input_schema.json';
import type { StageDetail } from '../../../telemetry/index.js';
import { EvaluatorError, wrapProviderError } from '../../../errors.js';
import CONFIG from '../../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/config.json';

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type VocabularyComplexityInput = InputsOf<typeof INPUT_SCHEMA>;

/** The vocabulary evaluator's stage-1 output, fed to stage 2 as prompt input. */
export interface BackgroundKnowledge {
  assumption: string;
  gradeLevel: string;
}

/**
 * Vocabulary Complexity Evaluator
 *
 * Evaluates vocabulary complexity of educational texts relative to grade level.
 * Uses a 2-stage process:
 * 1. Generate background knowledge assumption for the student's grade level
 * 2. Evaluate vocabulary complexity using that background knowledge
 *
 * Based on the Qualitative Text Complexity rubric.
 *
 * The complexity levels are whatever `output_schema.json` declares — currently
 * `slightly_complex` through `exceedingly_complex` — and are returned verbatim.
 *
 * @example
 * ```typescript
 * const evaluator = new VocabularyComplexityEvaluator({
 *   googleApiKey: process.env.GOOGLE_API_KEY,
 *   openaiApiKey: process.env.OPENAI_API_KEY
 * });
 *
 * const result = await evaluator.evaluate({
 *   text: 'The mitochondria is the powerhouse of the cell.',
 *   grade_level: '3',
 * });
 * console.log(result.result.complexity_score); // "moderately_complex"
 * console.log(result.result.reasoning);
 * ```
 */
/**
 * The three declared steps. Read here rather than restated so a model or temperature
 * re-pin in `config.json` takes effect without a second edit — the hardcoded copies these
 * replace matched the contract, so nothing would have failed if it had drifted.
 */
const BACKGROUND_STEP = requireStep(CONFIG.steps, 'background_knowledge', CONFIG.evaluator.name);
const GRADES_34_STEP = requireStep(
  CONFIG.steps,
  'vocab_complexity_grades_3_4',
  CONFIG.evaluator.name,
);
const OTHER_GRADES_STEP = requireStep(
  CONFIG.steps,
  'vocab_complexity_other_grades',
  CONFIG.evaluator.name,
);

/**
 * The grades the grades-3-4 branch declares, so the routing follows the contract.
 *
 * Absent or empty is a contract regression rather than "applies always": every grade would
 * route to the other-grades branch, quietly evaluating grades 3-4 on the wrong model. The
 * branching depends on this condition, so it fails at load rather than at inference.
 */
const GRADES_34: readonly string[] = (() => {
  const declared = GRADES_34_STEP.condition?.in;
  if (!declared || declared.length === 0) {
    throw new Error(
      `Step "${GRADES_34_STEP.id}" in ${CONFIG.evaluator.name} config.json declares no ` +
        'condition.in; the grade routing has nothing to follow.',
    );
  }
  return declared.map(String);
})();

export class VocabularyComplexityEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    outcome: CONFIG.outcome,
    requiredCredentials: declaredCredentials(CONFIG),
    supportedGrades: (INPUT_SCHEMA.properties.grade_level?.enum ?? []) as readonly string[],
    defaultProviders: [Provider.Google, Provider.OpenAI] as const,
  };

  private grades34ComplexityProvider: LLMProvider;
  private otherGradesComplexityProvider: LLMProvider;
  private backgroundKnowledgeProvider: LLMProvider;

  /**
   * The complexity model for a grade. Grades 3-4 and 5-12 use different models, so
   * every caller must agree on the choice — including the one that reports it.
   */
  private complexityProviderFor(gradeLevel: string): LLMProvider {
    return GRADES_34.includes(gradeLevel)
      ? this.grades34ComplexityProvider
      : this.otherGradesComplexityProvider;
  }

  constructor(config: BaseEvaluatorConfig) {
    super(config);

    this.grades34ComplexityProvider = this.createConfiguredProvider(
      Provider.Google, GRADES_34_STEP.model.name, config.googleApiKey
    );

    this.otherGradesComplexityProvider = this.createConfiguredProvider(
      Provider.OpenAI, OTHER_GRADES_STEP.model.name, config.openaiApiKey
    );

    this.backgroundKnowledgeProvider = this.createConfiguredProvider(
      Provider.OpenAI, BACKGROUND_STEP.model.name, config.openaiApiKey
    );
  }

  /**
   * Evaluate vocabulary complexity for a given text and grade level
   *
   * @param input - The inputs declared in this evaluator's `input_schema.json`
   * @returns Evaluation result with complexity score and detailed analysis
   * @throws {InputValidationError} If an input is missing, unknown, or outside the bounds its schema declares
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
   * @throws {LLMOutputProcessingError} If the model's response fails its output schema
   */
  async evaluate(input: VocabularyComplexityInput): Promise<EvaluationResult<VocabularyComplexityResult>> {
    let text = '';
    let gradeLevel = '';
    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];
    const backgroundProviderLabel = this.backgroundKnowledgeProvider.label;
    // Only the background model is known before the grade is read; if validation fails
    // no complexity model runs, so the error event reports just this one.
    let modelLabel = backgroundProviderLabel;

    try {
      // Inside the try so a validation failure is telemetered as an error event,
      // and before the inputs are read so a non-object is reported as one.
      validateInputs(input, INPUT_SCHEMA);
      ({ text, grade_level: gradeLevel } = input);

      // When override is active all providers resolve to the same model — show a single label.
      modelLabel = this.config.modelOverride
        ? backgroundProviderLabel
        : `${backgroundProviderLabel}+${this.complexityProviderFor(gradeLevel).label}`;

      this.logger.info('Starting Vocabulary Complexity evaluation', {
        evaluator: VocabularyComplexityEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        textLength: text.length,
      });
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
        provider: this.complexityProviderFor(gradeLevel).label,
        latency_ms: complexityResponse.latencyMs,
        token_usage: {
          input_tokens: complexityResponse.usage.inputTokens,
          output_tokens: complexityResponse.usage.outputTokens,
        },
      });

      const latencyMs = Date.now() - startTime;

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
      });

      if (error instanceof EvaluatorError) {
        throw error;
      }

      // An empty stageDetails means stage 1 (background knowledge) is what
      // failed; otherwise it completed and stage 2 (complexity) did. Attribute
      // to the provider that actually failed rather than a combined label.
      const failed =
        stageDetails.length === 0
          ? this.backgroundKnowledgeProvider
          : this.complexityProviderFor(gradeLevel);
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
      BACKGROUND_STEP.generation.temperature,
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

    const provider = this.complexityProviderFor(gradeLevel);

    const response = await provider.generateStructured({
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      schema: VocabularyComplexityOutputSchema,
      temperature: GRADES_34.includes(gradeLevel)
        ? GRADES_34_STEP.generation.temperature
        : OTHER_GRADES_STEP.generation.temperature,
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
 *   { text: 'The mitochondria is the powerhouse of the cell.', grade_level: '3' },
 *   { googleApiKey: process.env.GOOGLE_API_KEY,
 *     openaiApiKey: process.env.OPENAI_API_KEY },
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
