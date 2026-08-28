import type { LLMProvider } from '../providers/index.js';
import {
  OrganizationalStructureOutputSchema,
  type OrganizationalStructureInternal,
} from '../schemas/organizational-structure.js';
import { runPreprocessingStep } from '../features/preprocessing.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/organizational-structure/index.js';
import type { EvaluationResult, TextComplexityLevel } from '../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from './base.js';
import type { StageDetail } from '../telemetry/index.js';
import { EvaluatorError, InputValidationError, wrapProviderError } from '../errors.js';
import CONFIG from '../../../../evals/student-facing-text/ela-reading/organizational-structure/config.json';
import INPUT_SCHEMA from '../../../../evals/student-facing-text/ela-reading/organizational-structure/input_schema.json';

// Step ID convention: "evaluate_{slug}" where slug is the last segment of evaluator.id.
const STEP_ID = `evaluate_${CONFIG.evaluator.id.split('.').pop()}`;
const _step = CONFIG.steps.find(s => s.id === STEP_ID);
if (!_step) throw new Error(`Step "${STEP_ID}" not found in organizational-structure config.json`);
const STEP = _step;

// Supported grades from input_schema — needed for static metadata, so defined at
// module level. The enum is the declared set, so it is used verbatim rather than
// reconstructed from bounds; that also admits non-numeric tokens such as "K".
const SUPPORTED_GRADES: readonly string[] = INPUT_SCHEMA.properties.grade_level.enum;

// Maps snake_case LLM output → SDK-standard sentence case score.
const COMPLEXITY_SCORE_DISPLAY: Record<OrganizationalStructureInternal['complexity_score'], TextComplexityLevel> = {
  'slightly_complex': 'Slightly complex',
  'moderately_complex': 'Moderately complex',
  'very_complex': 'Very complex',
  'exceedingly_complex': 'Exceedingly complex',
};

export class OrganizationalStructureEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    supportedGrades: SUPPORTED_GRADES,
    defaultProviders: [Provider.Google] as const,
  };

  private static readonly TEMPERATURE = STEP.generation.temperature;

  private static computeFkScore(text: string): number {
    const fkStep = CONFIG.preprocessing.find(p => p.id === 'fk_score');
    if (!fkStep) throw new Error('fk_score preprocessing step not found in organizational-structure config.json');
    return runPreprocessingStep(text, fkStep.implementation.typescript);
  }

  private provider: LLMProvider;

  constructor(config: BaseEvaluatorConfig) {
    super(config);

    this.provider = this.createConfiguredProvider(
      Provider.Google, STEP.model.name, config.googleApiKey
    );
  }

  /**
   * Evaluate organizational structure complexity for a given text and grade level
   *
   * @param text - The text to evaluate
   * @param gradeLevel - The target grade level (3-12)
   * @returns Evaluation result with complexity score and detailed analysis
   * @throws {InputValidationError} If text is empty, too short/long, or gradeLevel is invalid
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {DependencyError} If the provider call fails (AuthenticationError, RateLimitError, NetworkError, RequestTimeoutError, LLMProviderError)
   * @throws {LLMOutputProcessingError} If the model's response fails its output schema
   */
  async evaluate(text: string, gradeLevel: string): Promise<EvaluationResult<TextComplexityLevel, OrganizationalStructureInternal>> {
    this.logger.info('Starting Organizational Structure evaluation', {
      evaluator: OrganizationalStructureEvaluator.metadata.id,
      operation: 'evaluate',
      gradeLevel,
      textLength: text.length,
    });

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      this.validateText(text);
      const gradeNum = this.parseAndValidateGrade(gradeLevel);

      const fkScore = OrganizationalStructureEvaluator.computeFkScore(text);
      const inputs: Record<string, string> = {
        text,
        grade_level: String(gradeNum),
        fk_score: String(fkScore),
      };
      const response = await this.callLLM(inputs);

      const latencyMs = Date.now() - startTime;
      const tokenUsage = {
        input_tokens: response.usage.inputTokens,
        output_tokens: response.usage.outputTokens,
      };

      stageDetails.push({
        stage: STEP.id,
        provider: this.provider.label,
        latency_ms: response.latencyMs,
        token_usage: tokenUsage,
      });

      const result: EvaluationResult<TextComplexityLevel, OrganizationalStructureInternal> = {
        score: COMPLEXITY_SCORE_DISPLAY[response.data.complexity_score],
        reasoning: response.data.reasoning,
        metadata: {
          model: this.provider.label,
          processingTimeMs: latencyMs,
          inputTokens: tokenUsage.input_tokens,
          outputTokens: tokenUsage.output_tokens,
        },
        _internal: response.data,
      };

      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        gradeLevel: String(gradeNum),
        provider: this.provider.label,
        tokenUsage,
        metadata: { stage_details: stageDetails },
        inputText: text,
      }).catch(() => undefined);

      this.logger.info('Organizational Structure evaluation completed successfully', {
        evaluator: OrganizationalStructureEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel: gradeNum,
        score: result.score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      this.logger.error('Organizational Structure evaluation failed', {
        evaluator: OrganizationalStructureEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        error: error instanceof Error ? error : undefined,
        processingTimeMs: latencyMs,
      });

      const tokenUsage = stageDetails.length > 0
        ? {
            input_tokens: stageDetails.reduce((s, d) => s + (d.token_usage?.input_tokens ?? 0), 0),
            output_tokens: stageDetails.reduce((s, d) => s + (d.token_usage?.output_tokens ?? 0), 0),
          }
        : undefined;

      this.sendTelemetry({
        status: 'error',
        latencyMs,
        textLength: text.length,
        gradeLevel: String(gradeLevel),
        provider: this.provider.label,
        tokenUsage,
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
        inputText: text,
      }).catch(() => undefined);

      if (error instanceof EvaluatorError) throw error;
      throw wrapProviderError(error, this.providerContext(this.provider));
    }
  }

  private parseAndValidateGrade(gradeLevel: string): number {
    const trimmed = gradeLevel.trim();
    if (!SUPPORTED_GRADES.includes(trimmed)) {
      throw new InputValidationError(
        `Invalid grade level "${gradeLevel}". Organizational Structure evaluator supports grade levels ${SUPPORTED_GRADES.join(', ')}.`,
      );
    }
    return Number(trimmed);
  }

  private async callLLM(
    inputs: Record<string, string>,
  ): Promise<{ data: OrganizationalStructureInternal; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const response = await this.provider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPrompt(inputs) },
        { role: 'user', content: getUserPrompt(inputs) },
      ],
      schema: OrganizationalStructureOutputSchema,
      temperature: OrganizationalStructureEvaluator.TEMPERATURE,
    });

    return { data: response.data, usage: response.usage, latencyMs: response.latencyMs };
  }
}

export async function evaluateOrganizationalStructure(
  text: string,
  gradeLevel: string,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<TextComplexityLevel, OrganizationalStructureInternal>> {
  return new OrganizationalStructureEvaluator(config).evaluate(text, gradeLevel);
}
