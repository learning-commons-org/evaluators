import type { LLMProvider } from '../providers/index.js';
import {
  OrganizationalStructureOutputSchema,
  type OrganizationalStructureInternal,
} from '../schemas/organizational-structure.js';
import { runPreprocessingStep } from '../features/preprocessing.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/organizational-structure/index.js';
import type { EvaluationResult } from '../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from './base.js';
import { validateInputs, type InputsOf } from './inputs.js';
import { declaredCredentials } from './credentials.js';
import type { StageDetail } from '../telemetry/index.js';
import { EvaluatorError, wrapProviderError } from '../errors.js';
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

/** What this evaluator accepts, taken from its `input_schema.json`. */
export type OrganizationalStructureInput = InputsOf<typeof INPUT_SCHEMA>;

export class OrganizationalStructureEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    stableId: CONFIG.evaluator.stable_id,
    idHistory: CONFIG.evaluator.id_history,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    outcome: CONFIG.outcome,
    requiredCredentials: declaredCredentials(CONFIG),
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
  async evaluate(input: OrganizationalStructureInput): Promise<EvaluationResult<OrganizationalStructureInternal>> {
    let text = '';
    let gradeLevel = '';
    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      // Inside the try so a validation failure is telemetered as an error event,
      // and before the inputs are read so a non-object is reported as one.
      validateInputs(input, INPUT_SCHEMA);
      ({ text, grade_level: gradeLevel } = input);

      this.logger.info('Starting Organizational Structure evaluation', {
        evaluator: OrganizationalStructureEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        textLength: text.length,
      });

      const fkScore = OrganizationalStructureEvaluator.computeFkScore(text);
      const promptInputs: Record<string, string> = {
        ...input,
        fk_score: String(fkScore),
      };
      const response = await this.callLLM(promptInputs);

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

      const result: EvaluationResult<OrganizationalStructureInternal> = {
        evaluator: OrganizationalStructureEvaluator.metadata.id,
        result: response.data,
        metadata: {
          model: this.provider.label,
          processingTimeMs: latencyMs,
          tokenUsage: {
            inputTokens: tokenUsage.input_tokens,
            outputTokens: tokenUsage.output_tokens,
          },
        },
      };

      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        gradeLevel,
        provider: this.provider.label,
        tokenUsage,
        metadata: { stage_details: stageDetails },
        inputText: text,
      }).catch(() => undefined);

      this.logger.info('Organizational Structure evaluation completed successfully', {
        evaluator: OrganizationalStructureEvaluator.metadata.id,
        operation: 'evaluate',
        gradeLevel,
        score: response.data.complexity_score,
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
  input: OrganizationalStructureInput,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<OrganizationalStructureInternal>> {
  return new OrganizationalStructureEvaluator(config).evaluate(input);
}
