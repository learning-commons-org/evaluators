import type { z } from 'zod';
import type { LLMProvider } from '../providers/index.js';
import { runPreprocessingStep, type PreprocessingImplementation } from '../features/preprocessing.js';
import type { EvaluationResult } from '../schemas/index.js';
import { BaseEvaluator, Provider, type BaseEvaluatorConfig } from './base.js';
import type { StageDetail } from '../telemetry/index.js';
import { ValidationError, wrapProviderError } from '../errors.js';

/**
 * Minimum shape every single-step rubric evaluator's LLM output must have.
 * Concrete evaluators narrow `complexity_score` to their schema's enum.
 */
export interface RubricOutput {
  complexity_score: string;
  reasoning: string;
}

/** Structural subset of an evaluator config.json used by the shared helpers. */
interface RubricConfig {
  evaluator: { id: string };
  steps: Array<{ id: string }>;
}

/**
 * Locate the evaluation step by convention: "evaluate_{slug}" where slug is
 * the last dot-segment of evaluator.id.
 */
export function findEvaluationStep<C extends RubricConfig>(config: C): C['steps'][number] {
  const stepId = `evaluate_${config.evaluator.id.split('.').pop()}`;
  const step = config.steps.find(s => s.id === stepId);
  if (!step) throw new Error(`Step "${stepId}" not found in ${config.evaluator.id} config.json`);
  return step;
}

/** Locate the fk_score preprocessing step's TypeScript implementation. */
export function findFkImplementation(config: {
  evaluator: { id: string };
  preprocessing: Array<{ id: string; implementation: { typescript: PreprocessingImplementation } }>;
}): PreprocessingImplementation {
  const fkStep = config.preprocessing.find(p => p.id === 'fk_score');
  if (!fkStep) throw new Error(`fk_score preprocessing step not found in ${config.evaluator.id} config.json`);
  return fkStep.implementation.typescript;
}

/** Expand an inclusive integer grade range into the SDK's string-grade list. */
export function supportedGradesFrom(gradeMin: number, gradeMax: number): string[] {
  return Array.from({ length: gradeMax - gradeMin + 1 }, (_, i) => String(gradeMin + i));
}

/**
 * Everything that distinguishes one single-step rubric evaluator from another.
 * Values are typically derived from the evaluator's config.json and schemas
 * at module load; the shared class contains all runtime behavior.
 */
export interface SingleStepRubricSpec<TScore extends string, TInternal extends RubricOutput> {
  /** Evaluator ID from config.json (e.g. "literacy.gla.intertextuality"). */
  id: string;
  /** Human-readable name used in log and error messages (e.g. "Intertextuality"). */
  displayName: string;
  step: {
    id: string;
    model: { name: string };
    generation: { temperature: number };
  };
  gradeMin: number;
  gradeMax: number;
  defaultProvider: Provider;
  fkImplementation: PreprocessingImplementation;
  outputSchema: z.ZodSchema<TInternal>;
  /** Maps the schema's snake_case complexity_score → SDK-standard sentence case score. */
  scoreDisplay: Record<TInternal['complexity_score'], TScore>;
  getSystemPrompt: (inputs: Record<string, string>) => string;
  getUserPrompt: (inputs: Record<string, string>) => string;
}

/**
 * Shared engine for config-driven evaluators with the shape:
 * validate input → compute fk_score → render prompts → one structured LLM
 * call → map to a 4-level rubric score.
 *
 * Concrete evaluators supply a {@link SingleStepRubricSpec} plus their own
 * static `metadata`; they contain no runtime logic of their own.
 */
export abstract class SingleStepRubricEvaluator<
  TScore extends string,
  TInternal extends RubricOutput,
> extends BaseEvaluator {
  private readonly spec: SingleStepRubricSpec<TScore, TInternal>;
  private provider: LLMProvider;

  protected constructor(config: BaseEvaluatorConfig, spec: SingleStepRubricSpec<TScore, TInternal>) {
    super(config);
    this.spec = spec;

    const defaultApiKey = {
      [Provider.Google]: config.googleApiKey,
      [Provider.OpenAI]: config.openaiApiKey,
      [Provider.Anthropic]: config.anthropicApiKey,
    }[spec.defaultProvider];

    this.provider = this.createConfiguredProvider(
      spec.defaultProvider, spec.step.model.name, defaultApiKey
    );
  }

  /**
   * Evaluate the rubric dimension for a given text and grade level
   *
   * @param text - The text to evaluate
   * @param grade - The target grade level
   * @returns Evaluation result with complexity score and detailed analysis
   * @throws {ValidationError} If text is empty, too short/long, or grade is invalid
   * @throws {ConfigurationError} If modelOverride specifies a model ID that the provider rejects
   * @throws {APIError} If LLM API calls fail (includes AuthenticationError, RateLimitError, NetworkError, TimeoutError)
   */
  async evaluate(text: string, grade: string): Promise<EvaluationResult<TScore, TInternal>> {
    this.logger.info(`Starting ${this.spec.displayName} evaluation`, {
      evaluator: this.spec.id,
      operation: 'evaluate',
      grade,
      textLength: text.length,
    });

    const startTime = Date.now();
    const stageDetails: StageDetail[] = [];

    try {
      this.validateText(text);
      const gradeNum = this.parseAndValidateGrade(grade);

      const fkScore = runPreprocessingStep(text, this.spec.fkImplementation);
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
        stage: this.spec.step.id,
        provider: this.provider.label,
        latency_ms: response.latencyMs,
        token_usage: tokenUsage,
      });

      const result: EvaluationResult<TScore, TInternal> = {
        score: this.spec.scoreDisplay[response.data.complexity_score as TInternal['complexity_score']],
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
        grade: String(gradeNum),
        provider: this.provider.label,
        tokenUsage,
        metadata: { stage_details: stageDetails },
        inputText: text,
      }).catch(() => undefined);

      this.logger.info(`${this.spec.displayName} evaluation completed successfully`, {
        evaluator: this.spec.id,
        operation: 'evaluate',
        grade: gradeNum,
        score: result.score,
        processingTimeMs: latencyMs,
      });

      return result;
    } catch (error) {
      const latencyMs = Date.now() - startTime;

      this.logger.error(`${this.spec.displayName} evaluation failed`, {
        evaluator: this.spec.id,
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
        provider: this.provider.label,
        tokenUsage,
        errorCode: error instanceof Error ? error.name : 'UnknownError',
        metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
        inputText: text,
      }).catch(() => undefined);

      if (error instanceof ValidationError) throw error;
      throw wrapProviderError(error, `${this.spec.displayName} evaluation failed`);
    }
  }

  private parseAndValidateGrade(grade: string): number {
    const num = Number(grade.trim());
    if (!Number.isInteger(num) || num < this.spec.gradeMin || num > this.spec.gradeMax) {
      throw new ValidationError(
        `Invalid grade "${grade}". ${this.spec.displayName} evaluator supports integer grades ${this.spec.gradeMin}–${this.spec.gradeMax}.`,
      );
    }
    return num;
  }

  private async callLLM(
    inputs: Record<string, string>,
  ): Promise<{ data: TInternal; usage: { inputTokens: number; outputTokens: number }; latencyMs: number }> {
    const response = await this.provider.generateStructured({
      messages: [
        { role: 'system', content: this.spec.getSystemPrompt(inputs) },
        { role: 'user', content: this.spec.getUserPrompt(inputs) },
      ],
      schema: this.spec.outputSchema,
      temperature: this.spec.step.generation.temperature,
    });

    return { data: response.data, usage: response.usage, latencyMs: response.latencyMs };
  }
}
