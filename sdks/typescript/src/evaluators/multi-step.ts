import type { ZodType } from 'zod';
import type { LLMProvider } from '../providers/base.js';
import type { EvaluationResult } from '../schemas/index.js';
import type { StageDetail } from '../telemetry/index.js';
import { ConfigurationError, EvaluatorError, wrapProviderError } from '../errors.js';
import { runPreprocessingStep, type PreprocessingImplementation } from '../features/preprocessing.js';
import {
  BaseEvaluator,
  Provider,
  withReasoningEffort,
  type BaseEvaluatorConfig,
  type EvaluatorMetadata,
} from './base.js';
import { declaredCredentials, type CredentialDeclaringConfig } from './credentials.js';
import { validateInputs, primaryTextField, type DeclaredInputSchema } from './inputs.js';
import { createPromptRenderers } from '../prompts/create-prompts.js';

/** A contract's `condition`: the step or entry applies only for these input values. */
export interface DeclaredCondition {
  input: string;
  /** The contract schema admits numbers here; inputs arrive as strings and are compared as such. */
  in: Array<string | number>;
}

/** A condition's values as the strings the caller's inputs are compared against. */
function conditionValues(condition: DeclaredCondition): string[] {
  return condition.in.map(String);
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
    generation?: { temperature?: number | null; reasoning_effort?: string };
    /** The step runs only for these input values. Absent means it always runs. */
    condition?: DeclaredCondition;
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
 * The last step to run produces the evaluator's result, so that step's output is validated
 * against the definition's `outputSchema` and it may omit `schema`. Every step that runs
 * before it needs its own, which makes `schema` required wherever the contract's conditions
 * leave a later step still to run.
 */
export interface StepArtifacts {
  system: string;
  user: string;
  schema?: ZodType<unknown>;
}

export interface MultiStepDefinition<TResult> {
  contract: MultiStepContract;
  inputSchema: DeclaredInputSchema;
  /** The schema of whichever step ends the run — what `evaluate()` resolves to. */
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
  // Normalised, as requireConditionValues does: a contract writing `[3, 4]` means the
  // grades a caller passes as '3' and '4'.
  return conditionValues(condition).includes(fields[condition.input]);
}

/**
 * Whether the step at `index` can be the last one to run.
 *
 * Read off the conditions alone, so it can be decided at load: an unconditional step ends a
 * run only when nothing is declared after it, and a conditional step ends one when some
 * value it runs for is a value no later step runs for. A later step conditioned on a
 * different input is not counted as running, because nothing here says the two inputs
 * move together.
 */
function canEndRun(
  steps: ReadonlyArray<{ condition?: DeclaredCondition }>,
  index: number,
): boolean {
  const later = steps.slice(index + 1);
  const condition = steps[index].condition;
  if (!condition) return later.length === 0;
  if (later.some((step) => !step.condition)) return false;
  return conditionValues(condition).some(
    (value) =>
      !later.some(
        (step) =>
          step.condition?.input === condition.input &&
          conditionValues(step.condition).includes(value),
      ),
  );
}

/**
 * Builds the evaluator class for a contract with more than one model call.
 *
 * Steps run in declared order, skipping any whose `condition` does not hold for the
 * inputs — which is how one contract carries more than one validated configuration, each
 * with its own models. The output of the last step that ran is the result. A step's placeholders are resolved from the sources the
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

    // A step that never ends a run always hands its output to a later one, so there is
    // no schema it could fall back on.
    const canEnd = canEndRun(STEPS, index);
    if (!canEnd && !parts.schema) {
      throw new Error(
        `No schema supplied for step "${step.id}" declared by ${contract.evaluator.name}. ` +
          `Only a step that can end a run may omit one, taking the definition's outputSchema.`,
      );
    }

    const vendor = vendorOf(step.model.provider, contract.evaluator.name);

    return {
      step,
      vendor,
      canEnd,
      schema: parts.schema,
      reasoningEffort: step.generation?.reasoning_effort,
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
      // Outside the try so a failure can be attributed to the step that was running.
      let running: typeof RENDERERS = [];

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

        // Conditions read only the inputs, so which steps run — and which of them is
        // last — is known before the first call.
        running = RENDERERS.filter((r) => conditionHolds(r.step.condition, fields));
        const last = running[running.length - 1];

        // Both are contract gaps, and both would otherwise surface as a result that is
        // missing or is an intermediate step's output.
        if (!last) {
          throw new ConfigurationError(
            `No step of ${contract.evaluator.name} applies to these inputs; ` +
              `every step's condition excludes them.`,
          );
        }
        // A step the conditions alone say is intermediate still ends a run for inputs no
        // later step covers. That is a result when the step was declared with the output
        // schema itself, and a gap in the contract when it was not.
        if (!last.canEnd && last.schema !== outputSchema) {
          throw new ConfigurationError(
            `Step "${last.step.id}" is the last ${contract.evaluator.name} runs for these ` +
              `inputs, but its output is not the result: no later step's condition covers them.`,
          );
        }

        const stepOutputs = new Map<string, unknown>();
        const preprocessed = new Map<string, string>();

        for (const renderer of running) {
          const { step, prompts } = renderer;
          // The step that ends the run produces the result, whatever schema it carries.
          const schema = renderer === last ? outputSchema : renderer.schema;
          if (!schema) {
            throw new ConfigurationError(
              `No schema supplied for step "${step.id}" declared by ${contract.evaluator.name}, ` +
                `which does not end the run for these inputs.`,
            );
          }

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
            ...withReasoningEffort(this.effectiveReasoningEffort(renderer.reasoningEffort)),
          });

          stepOutputs.set(step.id, response.data);
          stageDetails.push({
            stage: step.id,
            provider: this.telemetryLabel(provider),
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

        const finalOutput = stepOutputs.get(last.step.id) as TResult;
        // The envelope reports one model: that of the step that produced the result. Held
        // per evaluation rather than on the instance, because which step that is depends
        // on the inputs and evaluations may overlap.
        const resultProvider = this.providers.get(last.step.id)!;

        const result: EvaluationResult<TResult> = {
          evaluator: METADATA.id,
          result: finalOutput,
          metadata: {
            model: resultProvider.label,
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
          provider: this.telemetryLabel(resultProvider),
          tokenUsage,
          metadata: { stage_details: stageDetails },
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

        // The step that was running is the one after the last completed stage, counted
        // among the steps this evaluation runs. Attributing to the final step instead
        // would name the wrong vendor whenever the steps do not share one. A failure
        // before the steps were chosen — invalid input — has no step to name, so it falls
        // back to the first declared.
        const failedStep = (
          running[Math.min(stageDetails.length, running.length - 1)] ?? RENDERERS[0]
        ).step;
        const failedProvider = this.providers.get(failedStep.id)!;

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
          provider: this.telemetryLabel(failedProvider),
          tokenUsage,
          errorCode: error instanceof Error ? error.name : 'UnknownError',
          metadata: stageDetails.length > 0 ? { stage_details: stageDetails } : undefined,
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
