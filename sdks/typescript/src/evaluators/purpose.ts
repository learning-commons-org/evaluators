import type { LLMProvider, ProviderConfig } from '../providers/index.js';
import { createProvider, Providers } from '../providers/index.js';
import { PurposeOutputSchema, type PurposeInternal } from '../schemas/purpose.js';
import { runPreprocessingStep } from '../features/preprocessing.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/purpose/index.js';
import type { EvaluationResult } from '../schemas/index.js';
import { BaseEvaluator, type BaseEvaluatorConfig } from './base.js';
import type { StageDetail } from '../telemetry/index.js';
import { ValidationError, wrapProviderError } from '../errors.js';
import CONFIG from '../../../../evals/prompts/purpose/config.json';
import INPUT_SCHEMA from '../../../../evals/prompts/purpose/input_schema.json';

// Step ID convention: "evaluate_{slug}" where slug is the last segment of evaluator.id.
const STEP_ID = `evaluate_${CONFIG.evaluator.id.split('.').pop()}`;
const _step = CONFIG.steps.find(s => s.id === STEP_ID);
if (!_step) throw new Error(`Step "${STEP_ID}" not found in purpose config.json`);
const STEP = _step;

// Grade range from input_schema — needed for static metadata, so defined at module level.
const GRADE_MIN = INPUT_SCHEMA.properties.grade_level.minimum;
const GRADE_MAX = INPUT_SCHEMA.properties.grade_level.maximum;
const SUPPORTED_GRADES = Array.from({ length: GRADE_MAX - GRADE_MIN + 1 }, (_, i) => String(GRADE_MIN + i));

export type PurposeComplexityLevel = PurposeInternal['complexity_score'];

export class PurposeEvaluator extends BaseEvaluator {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    supportedGrades: SUPPORTED_GRADES,
    requiresGoogleKey: CONFIG.steps.some(s => s.model.provider === Providers.google),
    requiresOpenAIKey: CONFIG.steps.some(s => s.model.provider === Providers.openai),
  };

  private static readonly MODEL_ID = `${STEP.model.provider}:${STEP.model.name}`;
  private static readonly TEMPERATURE = STEP.generation.temperature;

  private static computeFkScore(text: string): number {
    const fkStep = CONFIG.preprocessing.find(p => p.id === 'fk_score');
    if (!fkStep) throw new Error('fk_score preprocessing step not found in purpose config.json');
    return runPreprocessingStep(text, fkStep.implementation.typescript);
  }

  private provider: LLMProvider;

  constructor(config: BaseEvaluatorConfig) {
    super(config);

    const providerType = STEP.model.provider as ProviderConfig['type'];
    const apiKey = providerType === Providers.google ? config.googleApiKey : config.openaiApiKey;

    this.provider = createProvider({
      type: providerType,
      model: STEP.model.name,
      apiKey,
      maxRetries: this.config.maxRetries,
    });
  }

  async evaluate(text: string, grade: string): Promise<EvaluationResult<PurposeComplexityLevel, PurposeInternal>> {
    this.logger.info('Starting Purpose evaluation', {
      evaluator: PurposeEvaluator.metadata.id,
      operation: 'evaluate',
      grade,
      textLength: text.length,
    });

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      this.validateText(text);
      const gradeNum = this.parseAndValidateGrade(grade);

      const fkScore = PurposeEvaluator.computeFkScore(text);
      const inputs: Record<string, string> = {
        text,
        grade_level: String(gradeNum),
        fk_score: String(fkScore),
      };
      const response = await this.callLLM(inputs);

      stageDetails.push({
        stage: STEP.id,
        provider: PurposeEvaluator.MODEL_ID,
        latency_ms: response.latencyMs,
        token_usage: {
          input_tokens: response.usage.inputTokens,
          output_tokens: response.usage.outputTokens,
        },
      });

      const latencyMs = Date.now() - startTime;
      const tokenUsage = {
        input_tokens: response.usage.inputTokens,
        output_tokens: response.usage.outputTokens,
      };

      const result: EvaluationResult<PurposeComplexityLevel, PurposeInternal> = {
        score: response.data.complexity_score,
        reasoning: response.data.reasoning,
        metadata: {
          model: PurposeEvaluator.MODEL_ID,
          processingTimeMs: latencyMs,
        },
        _internal: response.data,
      };

      this.sendTelemetry({
        status: 'success',
        latencyMs,
        textLength: text.length,
        grade: String(gradeNum),
        provider: PurposeEvaluator.MODEL_ID,
        tokenUsage,
        metadata: { stage_details: stageDetails },
        inputText: text,
      }).catch(() => undefined);

      this.logger.info('Purpose evaluation completed successfully', {
        evaluator: PurposeEvaluator.metadata.id,
        operation: 'evaluate',
        grade: gradeNum,
        score: result.score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      this.logger.error('Purpose evaluation failed', {
        evaluator: PurposeEvaluator.metadata.id,
        operation: 'evaluate',
        grade,
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
        grade: String(grade),
        provider: PurposeEvaluator.MODEL_ID,
        tokenUsage,
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
        inputText: text,
      }).catch(() => undefined);

      if (error instanceof ValidationError) throw error;
      throw wrapProviderError(error, 'Purpose evaluation failed');
    }
  }

  private parseAndValidateGrade(grade: string): number {
    const num = Number(grade.trim());
    if (!Number.isInteger(num) || num < GRADE_MIN || num > GRADE_MAX) {
      throw new ValidationError(
        `Invalid grade "${grade}". Purpose evaluator supports integer grades ${GRADE_MIN}–${GRADE_MAX}.`,
      );
    }
    return num;
  }

  private async callLLM(
    inputs: Record<string, string>,
  ): Promise<{ data: PurposeInternal; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const response = await this.provider.generateStructured({
      messages: [
        { role: 'system', content: getSystemPrompt(inputs) },
        { role: 'user', content: getUserPrompt(inputs) },
      ],
      schema: PurposeOutputSchema,
      temperature: PurposeEvaluator.TEMPERATURE,
    });

    return { data: response.data, usage: response.usage, latencyMs: response.latencyMs };
  }
}

export async function evaluatePurpose(
  text: string,
  grade: string,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<PurposeComplexityLevel, PurposeInternal>> {
  return new PurposeEvaluator(config).evaluate(text, grade);
}
