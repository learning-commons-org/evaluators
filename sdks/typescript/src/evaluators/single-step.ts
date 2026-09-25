import type { ZodType } from 'zod';
import type { ImageAttachment, LLMProvider } from '../providers/index.js';
import { loadImage } from '../features/image-source.js';
import type { EvaluationResult } from '../schemas/index.js';
import type { StageDetail } from '../telemetry/index.js';
import { ConfigurationError, EvaluatorError, wrapProviderError } from '../errors.js';
import { runPreprocessingStep } from '../features/preprocessing.js';
import {
  BaseEvaluator,
  Provider,
  type BaseEvaluatorConfig,
  type EvaluatorMetadata,
} from './base.js';
import { declaredCredentials, type CredentialDeclaringConfig } from './credentials.js';
import { validateInputs, primaryTextField, type DeclaredInputSchema } from './inputs.js';
import { createPromptRenderers } from '../prompts/create-prompts.js';

/**
 * The parts of a contract a single-step evaluator runs on. Everything the flow needs is
 * declared, so the only per-evaluator code left is naming the four artefacts below.
 */
export interface SingleStepContract extends CredentialDeclaringConfig {
  evaluator: {
    id: string;
    stable_id: string;
    id_history: string[];
    name: string;
    description: string;
    /** Required of every contract, so a config.json omitting it fails to compile here. */
    supported_grades: string[];
  };
  steps: Array<{
    id: string;
    model: { provider: string; name: string };
    generation?: { temperature?: number };
    prompt: { placeholders: Record<string, unknown> };
    required_credentials?: string[];
    optional?: boolean;
  }>;
  preprocessing?: Array<{
    id: string;
    implementation: { typescript: { library: string; function: string; post_transform?: { type: string; precision?: number } } };
    required_credentials?: string[];
  }>;
  outcome?: { score: string; reasoning: string };
}

/**
 * An input the model receives as an attached image rather than as text in the prompt.
 *
 * The contract declares the input as a string naming where the image lives (a file path or
 * URL). The shared config schema has no field for this yet, so the declaration sits here
 * until it does; the SDK reads the image in the caller's environment and hands it to the
 * provider as a request attachment, placed ahead of the rendered user prompt.
 */
export interface Attachment {
  /** The input field, as declared in `input_schema.json`. */
  input: string;
  kind: 'image';
}

export interface SingleStepDefinition<TResult> {
  contract: SingleStepContract;
  inputSchema: DeclaredInputSchema;
  outputSchema: ZodType<TResult>;
  /** The contract's `system.txt`, verbatim. Placeholders are substituted per call. */
  systemPrompt: string;
  /** The contract's `user.txt`, verbatim. */
  userPrompt: string;
  /** Inputs attached to the user turn as content parts. Empty for a text-only evaluator. */
  attachments?: readonly Attachment[];
}

/**
 * The class `defineSingleStepEvaluator` returns.
 *
 * Spelled out rather than inferred because an anonymous class cannot carry the base's
 * protected members into the emitted declarations (TS4094).
 */
export interface SingleStepEvaluatorClass<TInput, TResult> {
  new (config: BaseEvaluatorConfig): BaseEvaluator & {
    evaluate(input: TInput): Promise<EvaluationResult<TResult>>;
  };
  readonly metadata: EvaluatorMetadata;
}

/**
 * The step a contract declares under `id`, or a failure naming the one that was expected.
 *
 * Shared because a multi-step evaluator needs the same lookup for each of its steps, and a
 * second copy is a second thing that can disagree about what a missing step means.
 */
export function requireStep<T extends { id: string }>(
  steps: readonly T[],
  id: string,
  evaluatorName: string,
): T {
  const step = steps.find((s) => s.id === id);
  if (!step) {
    throw new Error(`Step "${id}" not found in ${evaluatorName} config.json`);
  }
  return step;
}

/** Step id convention: `evaluate_{slug}`, where slug is the last segment of the id. */
function stepFor(contract: SingleStepContract) {
  const id = `evaluate_${contract.evaluator.id.split('.').pop()}`;
  return requireStep(contract.steps, id, contract.evaluator.name);
}

function vendorOf(step: { model: { provider: string } }, name: string): Provider {
  const vendor = Object.values(Provider).find((p) => p === step.model.provider);
  if (!vendor) {
    throw new Error(
      `Unsupported provider "${step.model.provider}" declared by ${name}. ` +
        `Supported: ${Object.values(Provider).join(', ')}.`,
    );
  }
  return vendor;
}

/**
 * Builds the evaluator class for a contract with one model call.
 *
 * The flow: validate, preprocess, render, call, envelope, telemetry, error wrap. Anything
 * that varies is read from the contract rather than passed in, so an evaluator cannot
 * drift from what its contract declares.
 *
 * @example
 * ```typescript
 * export class PurposeClarityEvaluator extends defineSingleStepEvaluator<
 *   PurposeClarityInput,
 *   PurposeClarityResult
 * >({
 *   contract: CONFIG,
 *   inputSchema: INPUT_SCHEMA,
 *   outputSchema: PurposeClarityOutputSchema,
 *   systemPrompt: SYSTEM_PROMPT,
 *   userPrompt: USER_PROMPT_TEMPLATE,
 * }) {}
 * ```
 */
export function defineSingleStepEvaluator<TInput extends Record<string, string>, TResult>(
  definition: SingleStepDefinition<TResult>,
): SingleStepEvaluatorClass<TInput, TResult> {
  const { contract, inputSchema, outputSchema, systemPrompt, userPrompt } = definition;
  const ATTACHMENTS = definition.attachments ?? [];

  const STEP = stepFor(contract);
  const VENDOR = vendorOf(STEP, contract.evaluator.name);
  const PREPROCESSING = contract.preprocessing ?? [];
  // An attached input is a path or URL, not prose; the primary text is the first field that
  // is neither attached nor an enum.
  const ATTACHED_FIELDS = new Set(ATTACHMENTS.map((a) => a.input));
  const TEXT_FIELD = primaryTextField({
    ...inputSchema,
    properties: Object.fromEntries(
      Object.entries(inputSchema.properties).filter(([name]) => !ATTACHED_FIELDS.has(name)),
    ),
  });
  const PROMPTS = createPromptRenderers(
    systemPrompt,
    userPrompt,
    Object.keys(STEP.prompt.placeholders),
  );

  // The contract names every evaluator "<Thing> Evaluator"; logs read as "<Thing>".
  const LABEL = contract.evaluator.name.replace(/ Evaluator$/, '');

  const METADATA = {
    id: contract.evaluator.id,
    stableId: contract.evaluator.stable_id,
    idHistory: contract.evaluator.id_history,
    name: contract.evaluator.name,
    description: contract.evaluator.description,
    outcome: contract.outcome,
    requiredCredentials: declaredCredentials(contract),
    // What the evaluator targets, which its contract states outright. Deriving it from the
    // grade input instead published `[]` for every evaluator that takes no grade — the
    // feedback family and Grade Level Appropriateness — asserting they target no grades.
    // The accepted set is still the input enum, and `validateInputs` is what enforces it.
    supportedGrades: contract.evaluator.supported_grades as readonly string[],
    defaultProviders: [VENDOR] as const,
  };

  return class SingleStepEvaluator extends BaseEvaluator {
    static readonly metadata = METADATA;

    protected provider: LLMProvider;

    constructor(config: BaseEvaluatorConfig) {
      super(config);
      this.provider = this.createConfiguredProvider(VENDOR, STEP.model.name, this.keyFor(VENDOR, config));
      // Refused here, not at call time: a provider that ignores attachments would otherwise
      // judge the claim with no image and return a confident verdict about nothing.
      if (ATTACHMENTS.length > 0 && !this.provider.supportsAttachments) {
        throw new ConfigurationError(
          `${LABEL} attaches an image to each request, and the configured provider ` +
            `"${this.provider.label}" does not declare support for attachments.`,
        );
      }
    }

    private keyFor(vendor: Provider, config: BaseEvaluatorConfig): string | undefined {
      const keys: Record<Provider, string | undefined> = {
        [Provider.OpenAI]: config.openaiApiKey,
        [Provider.Google]: config.googleApiKey,
        [Provider.Anthropic]: config.anthropicApiKey,
      };
      return keys[vendor];
    }

    async evaluate(input: TInput): Promise<EvaluationResult<TResult>> {
      let text = '';
      let gradeLevel = '';
      const startTime = Date.now();
      const stageDetails: StageDetail[] = [];

      try {
        // Inside the try so a validation failure is telemetered as an error event,
        // and before the inputs are read so a non-object is reported as one.
        validateInputs(input, inputSchema);
        const fields = input as Record<string, string>;
        text = TEXT_FIELD ? fields[TEXT_FIELD] : '';
        gradeLevel = fields.grade_level ?? '';

        this.logger.info(`Starting ${LABEL} evaluation`, {
          evaluator: METADATA.id,
          operation: 'evaluate',
          gradeLevel,
          textLength: text.length,
        });

        // Each declared preprocessing step becomes a prompt input under its own id, so
        // adding one to a contract needs no code here.
        const promptInputs: Record<string, string> = { ...fields };
        for (const step of PREPROCESSING) {
          promptInputs[step.id] = String(runPreprocessingStep(text, step.implementation.typescript));
        }

        // Attached inputs are read here, after validation and before any paid call; the
        // provider places them on the user turn ahead of the text.
        const attachments: ImageAttachment[] = [];
        for (const attachment of ATTACHMENTS) {
          attachments.push(await loadImage(attachment.input, fields[attachment.input]));
        }

        const response = await this.provider.generateStructured({
          messages: [
            { role: 'system', content: PROMPTS.getSystemPrompt(promptInputs) },
            { role: 'user', content: PROMPTS.getUserPrompt(promptInputs) },
          ],
          ...(attachments.length ? { attachments } : {}),
          schema: outputSchema,
          temperature: STEP.generation?.temperature,
        });

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

        const result: EvaluationResult<TResult> = {
          evaluator: METADATA.id,
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
        }).catch(() => undefined);

        this.logger.info(`${LABEL} evaluation completed successfully`, {
          evaluator: METADATA.id,
          operation: 'evaluate',
          gradeLevel,
          score: METADATA.outcome
            ? (response.data as Record<string, unknown>)[METADATA.outcome.score]
            : undefined,
          processingTimeMs: latencyMs,
        });

        return result;
      } catch (error) {
        const latencyMs = Date.now() - startTime;

        this.logger.error(`${LABEL} evaluation failed`, {
          evaluator: METADATA.id,
          operation: 'evaluate',
          gradeLevel,
          error: error instanceof Error ? error : undefined,
          processingTimeMs: latencyMs,
        });

        const tokenUsage =
          stageDetails.length > 0
            ? {
                input_tokens: stageDetails.reduce((s, d) => s + (d.token_usage?.input_tokens ?? 0), 0),
                output_tokens: stageDetails.reduce((s, d) => s + (d.token_usage?.output_tokens ?? 0), 0),
              }
            : undefined;

        this.sendTelemetry({
          status: 'error',
          latencyMs,
          textLength: text.length,
          gradeLevel,
          provider: this.provider.label,
          tokenUsage,
          errorCode: error instanceof Error ? error.name : 'UnknownError',
          metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
        }).catch(() => undefined);

        if (error instanceof EvaluatorError) throw error;
        throw wrapProviderError(error, this.providerContext(this.provider));
      }
    }
  };
}
