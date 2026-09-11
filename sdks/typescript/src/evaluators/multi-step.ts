import type { ZodType } from 'zod';
import type { LLMProvider } from '../providers/index.js';
import type { EvaluationResult } from '../schemas/index.js';
import type { StageDetail } from '../telemetry/index.js';
import { EvaluatorError, wrapProviderError } from '../errors.js';
import { runPreprocessingStep, type PreprocessingImplementation } from '../features/preprocessing.js';
import {
  BaseEvaluator,
  Provider,
  type BaseEvaluatorConfig,
  type EvaluatorMetadata,
} from './base.js';
import { declaredCredentials, type CredentialDeclaringConfig } from './credentials.js';
import { validateInputs, primaryTextField, type DeclaredInputSchema } from './inputs.js';
import { createPromptRenderers } from '../prompts/create-prompts.js';

/** A contract's `condition`: the step or entry applies only for these input values. */
export interface DeclaredCondition {
  input: string;
  in: string[];
}

/**
 * Where a placeholder's value comes from, as the contract's `prompt.placeholders[].source`
 * spells it out: `input`, `input.<field>`, `preprocessing.<output>`, or
 * `steps.<id>.output`.
 */
export type PlaceholderSource = string;

export interface DeclaredPlaceholder {
  required?: boolean;
  source: PlaceholderSource;
}

export interface MultiStepContract extends CredentialDeclaringConfig {
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
    prompt: { placeholders: Record<string, DeclaredPlaceholder | undefined> };
    required_credentials?: string[];
  }>;
  preprocessing?: Array<{
    id: string;
    kind: string;
    input: string;
    output: string;
    source_path?: string;
    condition?: DeclaredCondition;
    implementation: { typescript: PreprocessingImplementation };
  }>;
  outcome?: { score: string; reasoning: string };
}

/**
 * One declared step's prompts, and the schema its own output is validated against.
 *
 * `schema` is required for every step but the last, whose output is the evaluator's result
 * and so is validated against the definition's `outputSchema`.
 */
export interface StepArtifacts {
  system: string;
  user: string;
  schema?: ZodType<unknown>;
}

export interface MultiStepDefinition<TResult> {
  contract: MultiStepContract;
  inputSchema: DeclaredInputSchema;
  /** The final step's schema — what `evaluate()` resolves to. */
  outputSchema: ZodType<TResult>;
  /** Prompts and per-step schema, keyed by the step id the contract declares. */
  steps: Record<string, StepArtifacts>;
  /**
   * Implementations for `custom`-kind preprocessing, keyed by the function name the
   * contract declares under `implementation.typescript.function`.
   *
   * These necessarily live in code: `custom` means the contract names a computation
   * rather than describing it. Keying on the declared name is what keeps the two honest —
   * a contract naming a function the SDK does not provide fails at construction.
   */
  computations?: Record<string, (input: unknown) => string>;
  /**
   * Text for `load_rubric_text`-kind preprocessing, keyed by the contract's `source_path`.
   * The files are sha256-pinned in the contract and checked by `scripts/check.py`.
   */
  documents?: Record<string, string>;
}

export interface MultiStepEvaluatorClass<TInput, TResult> {
  new (config: BaseEvaluatorConfig): BaseEvaluator & {
    evaluate(input: TInput): Promise<EvaluationResult<TResult>>;
  };
  readonly metadata: EvaluatorMetadata;
}

function vendorOf(provider: string, evaluatorName: string): Provider {
  const vendor = Object.values(Provider).find((p) => p === provider);
  if (!vendor) {
    throw new Error(
      `Unsupported provider "${provider}" declared by ${evaluatorName}. ` +
        `Supported: ${Object.values(Provider).join(', ')}.`,
    );
  }
  return vendor;
}

/**
 * The preprocessing entry a contract declares under `id`, or a failure naming it.
 *
 * Parallel to {@link requireStep}: an entry read by id is registry information, and a
 * contract that stops declaring it should fail at load rather than silently skip the work.
 */
export function requirePreprocessing(
  contract: {
    evaluator?: { name?: string };
    preprocessing?: Array<{ id: string; condition?: DeclaredCondition }>;
  },
  id: string,
): { id: string; condition?: DeclaredCondition } {
  const entry = contract.preprocessing?.find((p) => p.id === id);
  if (!entry) {
    // Named, as requireStep does: without it the failure does not say whose contract.
    const owner = contract.evaluator?.name ?? 'the';
    throw new Error(`Preprocessing "${id}" not found in ${owner} config.json`);
  }
  return entry;
}

/**
 * The input values a step's condition names, or a failure if it names none.
 *
 * For a step whose *routing* depends on the condition, an absent or empty one is a contract
 * regression rather than "applies always" — the caller would silently take the other
 * branch. Read at load so a broken contract fails before any inference.
 */
export function requireConditionValues(
  step: { id: string; condition?: DeclaredCondition },
  evaluatorName: string,
): readonly string[] {
  const declared = step.condition?.in;
  if (!declared || declared.length === 0) {
    throw new Error(
      `Step "${step.id}" in ${evaluatorName} config.json declares no condition.in; ` +
        'the routing that depends on it has nothing to follow.',
    );
  }
  return declared.map(String);
}

/** Whether a declared condition holds for the given inputs. No condition always holds. */
function conditionHolds(
  condition: DeclaredCondition | undefined,
  fields: Record<string, string>,
): boolean {
  if (!condition) return true;
  return condition.in.includes(fields[condition.input]);
}

/**
 * Builds the evaluator class for a contract with more than one model call.
 *
 * Steps run in declared order. A step's placeholders are resolved from the sources the
 * contract names, and any preprocessing they depend on runs first — including preprocessing
 * that reads an earlier step's output, which is what makes the ordering a consequence of the
 * contract rather than of the order someone wrote the code in.
 *
 * The single-step case has its own factory; this one is not a superset, because a lone step
 * needs none of the resolution below and reads better without it.
 */
export function defineMultiStepEvaluator<TInput extends Record<string, string>, TResult>(
  definition: MultiStepDefinition<TResult>,
): MultiStepEvaluatorClass<TInput, TResult> {
  const {
    contract,
    inputSchema,
    outputSchema,
    steps: artifacts,
    computations = {},
    documents = {},
  } = definition;

  const STEPS = contract.steps;
  const PREPROCESSING = contract.preprocessing ?? [];
  const TEXT_FIELD = primaryTextField(inputSchema);
  const LABEL = contract.evaluator.name.replace(/ Evaluator$/, '');

  if (STEPS.length < 2) {
    throw new Error(
      `${contract.evaluator.name} declares ${STEPS.length} step(s); use defineSingleStepEvaluator.`,
    );
  }

  // Resolved once so a contract naming a step, function or document the SDK does not
  // supply fails at module load rather than on the first evaluation.
  const RENDERERS = STEPS.map((step, index) => {
    const parts = artifacts[step.id];
    if (!parts) {
      throw new Error(
        `No prompts supplied for step "${step.id}" declared by ${contract.evaluator.name}.`,
      );
    }

    const isFinal = index === STEPS.length - 1;
    const schema = isFinal ? outputSchema : parts.schema;
    if (!schema) {
      throw new Error(
        `No schema supplied for step "${step.id}" declared by ${contract.evaluator.name}. ` +
          `Only the final step may omit one, taking the definition's outputSchema.`,
      );
    }

    return {
      step,
      vendor: vendorOf(step.model.provider, contract.evaluator.name),
      schema,
      prompts: createPromptRenderers(
        parts.system,
        parts.user,
        Object.entries(step.prompt.placeholders)
          .filter(([, placeholder]) => placeholder !== undefined)
          .map(([name]) => name),
      ),
    };
  });

  for (const entry of PREPROCESSING) {
    if (entry.kind === 'custom' && !computations[entry.implementation.typescript.function]) {
      throw new Error(
        `Preprocessing "${entry.id}" declares custom function ` +
          `"${entry.implementation.typescript.function}", which ${contract.evaluator.name} does not supply.`,
      );
    }
    if (entry.kind === 'load_rubric_text' && !documents[entry.source_path ?? '']) {
      throw new Error(
        `Preprocessing "${entry.id}" declares source_path "${entry.source_path}", ` +
          `which ${contract.evaluator.name} does not supply.`,
      );
    }
  }

  const VENDORS = [...new Set(RENDERERS.map((r) => r.vendor))];

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
    defaultProviders: VENDORS as readonly Provider[],
  };

  return class MultiStepEvaluator extends BaseEvaluator {
    static readonly metadata = METADATA;

    protected provider: LLMProvider;
    private readonly providers = new Map<string, LLMProvider>();

    constructor(config: BaseEvaluatorConfig) {
      super(config);

      // One client per distinct vendor+model, not per step: steps that share a model share
      // a client, so a two-step evaluator on one model builds one provider as it did before
      // this factory existed.
      const byModel = new Map<string, LLMProvider>();
      for (const { step, vendor } of RENDERERS) {
        const key = `${vendor}:${step.model.name}`;
        let provider = byModel.get(key);
        if (!provider) {
          provider = this.createConfiguredProvider(vendor, step.model.name, this.keyFor(vendor, config));
          byModel.set(key, provider);
        }
        this.providers.set(step.id, provider);
      }
      // The envelope reports one model. With every step on one it is exact; when they
      // differ it names the last, which is the step that produced the result.
      this.provider = this.providers.get(STEPS[STEPS.length - 1].id)!;
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

        const stepOutputs = new Map<string, unknown>();
        const preprocessed = new Map<string, string>();

        for (const { step, schema, prompts } of RENDERERS) {
          const promptInputs: Record<string, string> = {};
          for (const [name, placeholder] of Object.entries(step.prompt.placeholders)) {
            // A key present but undefined is an artefact of the contract's inferred type,
            // where each step carries the other steps' placeholder names.
            if (!placeholder) continue;
            promptInputs[name] = this.resolve(
              name,
              placeholder.source,
              fields,
              stepOutputs,
              preprocessed,
            );
          }

          this.logger.debug(`Running step ${step.id}`, {
            evaluator: METADATA.id,
            operation: step.id,
          });

          const provider = this.providers.get(step.id)!;
          const response = await provider.generateStructured({
            messages: [
              { role: 'system', content: prompts.getSystemPrompt(promptInputs) },
              { role: 'user', content: prompts.getUserPrompt(promptInputs) },
            ],
            schema,
            temperature: step.generation?.temperature,
          });

          stepOutputs.set(step.id, response.data);
          stageDetails.push({
            stage: step.id,
            provider: provider.label,
            latency_ms: response.latencyMs,
            token_usage: {
              input_tokens: response.usage.inputTokens,
              output_tokens: response.usage.outputTokens,
            },
          });
        }

        const latencyMs = Date.now() - startTime;
        const tokenUsage = {
          input_tokens: stageDetails.reduce((s, d) => s + (d.token_usage?.input_tokens ?? 0), 0),
          output_tokens: stageDetails.reduce((s, d) => s + (d.token_usage?.output_tokens ?? 0), 0),
        };

        const finalOutput = stepOutputs.get(STEPS[STEPS.length - 1].id) as TResult;

        const result: EvaluationResult<TResult> = {
          evaluator: METADATA.id,
          result: finalOutput,
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

        this.logger.info(`${LABEL} evaluation completed successfully`, {
          evaluator: METADATA.id,
          operation: 'evaluate',
          gradeLevel,
          score: METADATA.outcome
            ? (finalOutput as Record<string, unknown>)[METADATA.outcome.score]
            : undefined,
          processingTimeMs: latencyMs,
        });

        return result;
      } catch (error) {
        const latencyMs = Date.now() - startTime;

        // The step that was running is the one after the last completed stage. Attributing
        // to `this.provider` instead would name the final step's provider, which is the
        // wrong vendor whenever the steps do not share one.
        const failedStep = STEPS[Math.min(stageDetails.length, STEPS.length - 1)];
        const failedProvider = this.providers.get(failedStep.id) ?? this.provider;

        this.logger.error(`${LABEL} evaluation failed`, {
          evaluator: METADATA.id,
          operation: 'evaluate',
          gradeLevel,
          error: error instanceof Error ? error : undefined,
          processingTimeMs: latencyMs,
          completedStages: stageDetails.length,
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
          provider: failedProvider.label,
          tokenUsage,
          errorCode: error instanceof Error ? error.name : 'UnknownError',
          metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
          inputText: text,
        }).catch(() => undefined);

        if (error instanceof EvaluatorError) throw error;
        throw wrapProviderError(error, this.providerContext(failedProvider));
      }
    }

    /** One placeholder, from whichever source the contract names for it. */
    private resolve(
      name: string,
      source: PlaceholderSource,
      fields: Record<string, string>,
      stepOutputs: Map<string, unknown>,
      preprocessed: Map<string, string>,
    ): string {
      if (source === 'input') return fields[name] ?? '';

      if (source.startsWith('input.')) return fields[source.slice('input.'.length)] ?? '';

      if (source.startsWith('preprocessing.')) {
        return this.preprocess(source.slice('preprocessing.'.length), fields, stepOutputs, preprocessed);
      }

      if (source.startsWith('steps.')) {
        const stepId = source.slice('steps.'.length).replace(/\.output$/, '');
        if (!stepOutputs.has(stepId)) {
          throw new Error(
            `Placeholder "${name}" reads step "${stepId}", which has not run. ` +
              `Steps run in the order ${contract.evaluator.name} declares them.`,
          );
        }
        return asPromptText(stepOutputs.get(stepId));
      }

      throw new Error(`Placeholder "${name}" declares an unsupported source "${source}".`);
    }

    /**
     * The value of one preprocessing output, computed once per evaluation.
     *
     * Selected by output rather than by entry id: several entries may declare the same
     * output under mutually exclusive conditions, which is how a contract expresses
     * "pick the rubric for this grade".
     */
    private preprocess(
      output: string,
      fields: Record<string, string>,
      stepOutputs: Map<string, unknown>,
      preprocessed: Map<string, string>,
    ): string {
      const cached = preprocessed.get(output);
      if (cached !== undefined) return cached;

      const applicable = PREPROCESSING.filter(
        (entry) => entry.output === output && conditionHolds(entry.condition, fields),
      );

      // Both failures are contract bugs, and both would otherwise reach the model as an
      // empty or arbitrary placeholder rather than as an error.
      if (applicable.length === 0) {
        throw new Error(
          `No preprocessing entry produces "${output}" for these inputs in ${contract.evaluator.name}.`,
        );
      }
      if (applicable.length > 1) {
        throw new Error(
          `${applicable.length} preprocessing entries produce "${output}" for these inputs in ` +
            `${contract.evaluator.name}: ${applicable.map((e) => e.id).join(', ')}. ` +
            `Their conditions should be mutually exclusive.`,
        );
      }

      const entry = applicable[0];
      const value = this.runEntry(entry, fields, stepOutputs);
      preprocessed.set(output, value);
      return value;
    }

    private runEntry(
      entry: NonNullable<MultiStepContract['preprocessing']>[number],
      fields: Record<string, string>,
      stepOutputs: Map<string, unknown>,
    ): string {
      if (entry.kind === 'load_rubric_text') {
        return documents[entry.source_path ?? ''];
      }

      // An entry's own input may itself be a step output, which is what orders the run.
      // Checked for every kind: a library computation would otherwise run on the empty
      // string and hide a forward reference, or a typo in the step id, behind a plausible
      // number.
      let resolved: unknown;
      if (entry.input.startsWith('steps.')) {
        const stepId = entry.input.slice('steps.'.length).replace(/\.output$/, '');
        if (!stepOutputs.has(stepId)) {
          throw new Error(
            `Preprocessing "${entry.id}" reads "${entry.input}", which is not available yet.`,
          );
        }
        resolved = stepOutputs.get(stepId);
      } else {
        resolved = fields[entry.input];
      }

      if (entry.kind === 'custom') {
        return computations[entry.implementation.typescript.function](resolved);
      }

      // Everything else is a library computation over text, as single-step evaluators use.
      return String(runPreprocessingStep(String(resolved ?? ''), entry.implementation.typescript));
    }
  };
}

/** A step output reaching a prompt is JSON unless it is already a string. */
function asPromptText(value: unknown): string {
  return typeof value === 'string' ? value : JSON.stringify(value);
}
