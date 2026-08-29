import {
  TelemetryClient,
  generateClientId,
  getSDKVersion,
  type TelemetryMetadata,
  type TokenUsage,
} from '../telemetry/index.js';
import {
  ConfigurationError,
  InputValidationError,
  PROVIDER_DEPENDENCIES,
  type DependencyId,
} from '../errors.js';
import { createLogger, LogLevel, type Logger } from '../logger.js';
import { configFieldFor } from './credentials.js';
import { createProvider } from '../providers/index.js';
import type { LLMProvider } from '../providers/index.js';

/**
 * Supported LLM providers
 */
export enum Provider {
  OpenAI = 'openai',
  Google = 'google',
  Anthropic = 'anthropic',
}

/**
 * Granular telemetry configuration options
 */
export interface TelemetryOptions {
  /** Enable telemetry (default: true) */
  enabled?: boolean;

  /** Record input text in telemetry (default: false) */
  recordInputs?: boolean;

  /**
   * Learning Commons key authorizing identified telemetry: events are attributed
   * to your Learning Commons user. Unset → events are anonymous.
   */
  learningCommonsApiKey?: string;
}

/**
 * Telemetry options after defaults are applied. The key remains optional.
 */
type NormalizedTelemetryOptions = Required<Pick<TelemetryOptions, 'enabled' | 'recordInputs'>> &
  Pick<TelemetryOptions, 'learningCommonsApiKey'>;

/**
 * Override the provider and model used by an evaluator.
 *
 * When set, all LLM calls use this provider and model instead of the defaults.
 * The evaluator's normal key requirements are bypassed — provide the key for
 * the chosen provider via the matching top-level config field
 * (e.g. `anthropicApiKey` for `Provider.Anthropic`).
 *
 * Both `provider` and `model` are required. An empty or missing `model` throws
 * `ConfigurationError` at construction time. An unrecognised model ID throws
 * `ConfigurationError` at evaluation time when the provider rejects it.
 *
 * Results may vary; evaluators are validated against their recommended models.
 *
 * Two things to know before overriding:
 *
 * - The override is evaluator-wide, not per call site. `VocabularyComplexityEvaluator`
 *   deliberately uses three models (Gemini 2.5 Pro for grade levels 3-4, GPT-4.1 for
 *   5-12, GPT-4o for background knowledge); an override collapses all three.
 * - Every evaluator on `defineSingleStepEvaluator` takes its model from its own contract
 *   (`evals/<domain>/<skill>/<evaluator>/config.json`), so an override diverges from the
 *   shared cross-language config rather than from an SDK default.
 */
export interface ModelOverride {
  provider: Provider;
  model: string;
}

/**
 * Base configuration for all evaluators
 */
export interface BaseEvaluatorConfig {
  /** Google API key (for evaluators using Gemini) */
  googleApiKey?: string;

  /** OpenAI API key (for evaluators using GPT) */
  openaiApiKey?: string;

  /** Anthropic API key (for evaluators using Claude) */
  anthropicApiKey?: string;

  /**
   * Learning Commons key authorizing Learning Commons API calls, such as the
   * Knowledge Graph. For identified telemetry, see
   * {@link TelemetryOptions.learningCommonsApiKey}.
   */
  learningCommonsApiKey?: string;

  /**
   * Override the provider and model used by this evaluator.
   * When set, all LLM calls use this provider and model instead of the defaults.
   * See {@link ModelOverride} for details.
   */
  modelOverride?: ModelOverride;

  /**
   * Bring your own LLM provider.
   *
   * Inject any object implementing {@link LLMProvider} and the evaluator routes
   * every LLM call through it, skipping the built-in OpenAI/Google/Anthropic
   * API-key adapters entirely. Use this to run the evaluators on a provider you
   * already have wired — Google Vertex AI, Amazon Bedrock, an AI-SDK gateway,
   * or an eval framework's model system — with no separate API keys.
   *
   * When set, API-key validation is skipped (the injected provider manages its
   * own model, auth, and retries). It is mutually exclusive with
   * {@link BaseEvaluatorConfig.modelOverride}: setting both throws
   * `ConfigurationError`. Ambient API keys, if present, are simply unused.
   */
  llmProvider?: LLMProvider;

  /**
   * Maximum number of retries for failed API calls (default: 2)
   * Set to 0 to disable retries.
   *
   * Note: With maxRetries=2, a failed call will be attempted up to 3 times total
   * (1 initial attempt + 2 retries)
   */
  maxRetries?: number;

  /**
   * Telemetry configuration (default: enabled, without input recording)
   *
   * Can be:
   * - `true`: Enable with defaults (recordInputs: false)
   * - `false`: Disable completely
   * - `TelemetryOptions`: Granular control
   */
  telemetry?: boolean | TelemetryOptions;

  /**
   * Custom logger implementation (optional)
   * If not provided, uses console logger with specified logLevel
   */
  logger?: Logger;

  /**
   * Log level for default console logger (default: WARN)
   * Only used if custom logger is not provided
   *
   * - DEBUG: Very verbose, shows all operations
   * - INFO: Normal operations
   * - WARN: Warnings only (default)
   * - ERROR: Errors only
   * - SILENT: No logging
   */
  logLevel?: LogLevel;
}

/**
 * Evaluator metadata interface
 * Each evaluator must provide this metadata as static properties
 */
export interface EvaluatorMetadata {
  /**
   * Current dotted registry id, e.g.
   * `student_facing_text.ela_reading.vocabulary_complexity`. Appears in results and
   * telemetry. May be renamed — the name is not the identity.
   */
  readonly id: string;
  /**
   * Immutable UUID assigned at the evaluator's creation. The identity that survives
   * renames; consumers aggregating across time key on this rather than on `id`.
   */
  readonly stableId: string;
  /** Prior `id` values, oldest first, so old names remain resolvable. */
  readonly idHistory: readonly string[];
  /** Human-readable name (e.g., 'Vocabulary Complexity Evaluator') */
  readonly name: string;
  /** Brief description of what the evaluator does */
  readonly description: string;
  /** Supported grade levels (e.g., ['3', '4', '5', ...]) */
  readonly supportedGrades: readonly string[];
  /**
   * Which output properties carry the verdict and its rationale, as the evaluator's
   * contract declares them. Absent for an evaluator whose output is not a single
   * judgement, which is why {@link readOutcome} can report no verdict.
   */
  readonly outcome?: { readonly score: string; readonly reasoning: string };
  /**
   * Canonical config keys for non-LLM services this evaluator calls, from its
   * contract. LLM keys are not listed — those follow `defaultProviders`, which a model
   * override narrows; these it does not touch.
   */
  readonly requiredCredentials?: readonly string[];
  /** Providers required by this evaluator's default configuration */
  readonly defaultProviders: readonly Provider[];
}

/**
 * Abstract base class for all evaluators
 *
 * Provides credential and modelOverride validation, provider construction, telemetry, and
 * grade-level validation for the bulk math paths that still need it.
 *
 * Input validation lives in `inputs.ts` (`validateInputs`), driven by each contract's
 * `input_schema.json`; metadata is a static block each evaluator declares.
 *
 * Concrete evaluators must implement:
 * - static metadata: Provide evaluator metadata (see EvaluatorMetadata interface)
 */
export abstract class BaseEvaluator {
  protected telemetryClient?: TelemetryClient;
  protected logger: Logger;
  protected config: Required<Pick<BaseEvaluatorConfig, 'maxRetries'>> & {
    telemetry: NormalizedTelemetryOptions;
    modelOverride?: ModelOverride;
    googleApiKey?: string;
    openaiApiKey?: string;
    anthropicApiKey?: string;
    llmProvider?: LLMProvider;
  };

  /**
   * Static metadata for the evaluator
   *
   * Concrete evaluators MUST define this property.
   *
   * @example
   * ```typescript
   * class MyEvaluator extends BaseEvaluator {
   *   static readonly metadata = {
   *     id: 'student_facing_text.ela_reading.my_evaluator',
   *     stableId: '00000000-0000-0000-0000-000000000000',
   *     idHistory: [],
   *     name: 'My Evaluator',
   *     description: 'Does something useful',
   *     supportedGrades: ['3', '4', '5'],
   *     defaultProviders: [Provider.Google],
   *   };
   * }
   * ```
   */
  static readonly metadata: EvaluatorMetadata;

  /**
   * @throws {ConfigurationError} If the subclass has not defined static metadata
   * @throws {ConfigurationError} If modelOverride has an invalid provider or empty model
   * @throws {ConfigurationError} If a required API key is missing
   */
  constructor(config: BaseEvaluatorConfig) {
    // Initialize logger
    this.logger = createLogger(config.logger, config.logLevel ?? LogLevel.WARN);

    // An injected llmProvider replaces the built-in adapters entirely.
    // Treat "provided" as `!== undefined` so a falsy-but-present value (e.g.
    // `null` from an untyped JS caller) fails fast with an llmProvider error
    // rather than falling through to a misleading "missing API key" error.
    if (config.llmProvider !== undefined) {
      this.validateLlmProvider(config.llmProvider);

      // modelOverride is a contradictory directive — it configures a built-in
      // adapter that llmProvider bypasses. Fail fast rather than silently
      // ignoring one. (API keys, by contrast, are ambient and simply unused.)
      if (config.modelOverride) {
        throw new ConfigurationError(
          'Cannot set both llmProvider and modelOverride: llmProvider replaces the built-in provider entirely, so modelOverride does not apply. Set one or the other.'
        );
      }
      // It manages its own model and auth, so API-key and override checks do not apply.
    } else {
      // Validate modelOverride shape before key checks
      this.validateModelOverride(config);

      // Validate required API keys based on metadata
      this.validateApiKeys(config);
    }

    // Normalize telemetry config
    const telemetryConfig = this.normalizeTelemetryConfig(config.telemetry);

    // Set defaults for common config
    this.config = {
      maxRetries: config.maxRetries ?? 2,
      telemetry: telemetryConfig,
      modelOverride: config.modelOverride,
      googleApiKey: config.googleApiKey,
      openaiApiKey: config.openaiApiKey,
      anthropicApiKey: config.anthropicApiKey,
      llmProvider: config.llmProvider,
    };

    if (config.modelOverride) {
      this.logger.warn(
        `modelOverride is active: using ${config.modelOverride.provider}:${config.modelOverride.model} instead of the default model. ` +
        'Evaluation quality may differ from recommended defaults.'
      );
    }

    // Initialize telemetry if enabled
    if (this.config.telemetry.enabled) {
      this.telemetryClient = new TelemetryClient({
        endpoint: 'https://api.learningcommons.org/evaluators-telemetry/v1/events',
        learningCommonsApiKey: this.config.telemetry.learningCommonsApiKey,
        clientId: generateClientId(),
        enabled: true,
        logger: this.logger,
      });
    }
  }

  /**
   * Get metadata for this evaluator instance
   * @throws {ConfigurationError} If the subclass has not defined static metadata
   */
  protected get metadata(): EvaluatorMetadata {
    const meta = (this.constructor as typeof BaseEvaluator).metadata;
    if (!meta) {
      throw new ConfigurationError(
        `${this.constructor.name} must define a static readonly metadata block.`
      );
    }
    return meta;
  }

  /**
   * Validate that an injected llmProvider implements the LLMProvider contract:
   * a string `label` and `generateStructured` / `generateText` methods.
   * @throws {ConfigurationError} If the provider is missing required members
   */
  private validateLlmProvider(provider: unknown): void {
    if (provider === null || typeof provider !== 'object') {
      throw new ConfigurationError(
        'llmProvider must be an object implementing the LLMProvider interface; received ' +
          (provider === null ? 'null' : typeof provider) + '.'
      );
    }
    const p = provider as Partial<LLMProvider>;
    if (
      typeof p.label !== 'string' ||
      typeof p.generateStructured !== 'function' ||
      typeof p.generateText !== 'function'
    ) {
      throw new ConfigurationError(
        'llmProvider must implement the LLMProvider interface: a string `label` and `generateStructured` / `generateText` methods.'
      );
    }
  }

  /**
   * Validate modelOverride shape: provider must be a known Provider value and
   * model must be a non-empty string.
   * @throws {ConfigurationError} If the override is malformed
   */
  private validateModelOverride(config: BaseEvaluatorConfig): void {
    if (!config.modelOverride) return;

    const validProviders = Object.values(Provider) as string[];
    if (!validProviders.includes(config.modelOverride.provider as string)) {
      throw new ConfigurationError(
        `Invalid provider "${config.modelOverride.provider}" in modelOverride. Valid providers are: ${validProviders.join(', ')}.`
      );
    }

    if (!config.modelOverride.model || config.modelOverride.model.trim() === '') {
      throw new ConfigurationError(
        `modelOverride.model is required. Specify the model ID for provider "${config.modelOverride.provider}".`
      );
    }
  }

  /**
   * Validate that every credential this evaluator needs was supplied.
   *
   * Requirements are derived, not listed: the LLM keys come from the providers its
   * steps use, and the non-LLM ones from the contract's `required_credentials`. A model
   * override replaces the former and leaves the latter alone, so an override cannot
   * skip a credential for a service the evaluator still calls.
   *
   * @throws {ConfigurationError} If a required credential is missing
   */
  private validateApiKeys(config: BaseEvaluatorConfig): void {
    // The one table that has to exist: these are the SDK's own config fields, which
    // cannot be indexed dynamically. Names and messages are derived from the canonical
    // key, so no per-provider table.
    const provided: Record<string, string | undefined> = {
      openaiApiKey: config.openaiApiKey,
      googleApiKey: config.googleApiKey,
      anthropicApiKey: config.anthropicApiKey,
      learningCommonsApiKey: config.learningCommonsApiKey,
    };

    const providers = config.modelOverride
      ? [config.modelOverride.provider]
      : this.metadata.defaultProviders;

    const satisfied = new Set(this.credentialsSatisfiedByInjection(config));
    const required = [
      ...providers.map((provider) => `${provider}_api_key`),
      ...(this.metadata.requiredCredentials ?? []).filter((key) => !satisfied.has(key)),
    ];

    for (const canonical of required) {
      const field = configFieldFor(canonical);
      if (!provided[field]?.trim()) {
        throw new ConfigurationError(
          `Missing required credential: ${field}. Required by ${this.metadata.name}.`,
        );
      }
    }
  }

  /**
   * Credentials a subclass no longer needs because the caller injected the client that
   * would have used them.
   *
   * Reads only `config`, since this runs from the base constructor before the subclass
   * is initialised. Same rule as an injected `llmProvider`: whoever supplies the client
   * owns its auth.
   */
  protected credentialsSatisfiedByInjection(_config: BaseEvaluatorConfig): readonly string[] {
    return [];
  }

  /**
   * Normalize telemetry config to standard format
   */
  private normalizeTelemetryConfig(
    telemetry: boolean | TelemetryOptions | undefined
  ): NormalizedTelemetryOptions {
    // Handle boolean shortcuts
    if (telemetry === false) {
      return {
        enabled: false,
        recordInputs: false,
      };
    }

    if (telemetry === true || telemetry === undefined) {
      return {
        enabled: true,
        recordInputs: false,
      };
    }

    // Handle granular config object
    return {
      enabled: telemetry.enabled ?? true,
      recordInputs: telemetry.recordInputs ?? false,
      learningCommonsApiKey: telemetry.learningCommonsApiKey,
    };
  }

  /**
   * Get the evaluator type identifier from metadata
   * @returns The dotted registry id, e.g. "student_facing_text.ela_reading.sentence_structure"
   */
  protected getEvaluatorType(): string {
    return this.metadata.id;
  }

  /**
   * Dependency attribution for errors raised while calling `provider`.
   *
   * The label is `provider:model`, and its prefix is a `Provider` value on both
   * the default and `modelOverride` paths, so those report their real vendor. An
   * injected `llmProvider` can label itself anything; that reports `custom`
   * rather than guessing a vendor we never called. The label is always kept as
   * `model`, so the caller's own identifier is never lost.
   */
  protected providerContext(provider: LLMProvider): {
    dependency: DependencyId;
    model: string;
  } {
    const label = provider.label;
    const separator = label.indexOf(':');
    const prefix = separator === -1 ? label : label.slice(0, separator);

    // An unrecognised prefix means a caller-supplied provider, whose vendor is
    // theirs to know; the label is the only identifier we have, so keep it whole.
    if (!PROVIDER_DEPENDENCIES.has(prefix)) {
      return { dependency: 'custom', model: label };
    }

    // The vendor is already reported as `dependency`, so `model` need only carry
    // the model id. Slicing past a missing separator yields the whole label,
    // which is also the right answer when there is no model id to strip.
    const model = label.slice(separator + 1);
    return { dependency: prefix as DependencyId, model: model === '' ? label : model };
  }

  /**
   * Validate gradeLevel is in supported range
   * Default implementation - can be overridden by concrete evaluators
   *
   * @param gradeLevel - Grade level to validate
   * @param validGradeLevels - Set of valid grade levels for this evaluator
   * @throws {InputValidationError} If gradeLevel is invalid
   */
  protected validateGradeLevel(gradeLevel: string, validGradeLevels: Set<string>): void {
    this.logger.debug('Validating grade level input', {
      evaluator: this.getEvaluatorType(),
      operation: 'validateGradeLevel',
      gradeLevel,
    });

    // Check if gradeLevel is in valid set
    if (!validGradeLevels.has(gradeLevel)) {
      const validList = Array.from(validGradeLevels).sort((a, b) => {
        // Sort K first, then numerically
        if (a === 'K') return -1;
        if (b === 'K') return 1;
        return parseInt(a, 10) - parseInt(b, 10);
      }).join(', ');

      throw new InputValidationError(
        `Invalid grade level "${gradeLevel}". Supported grade levels for this evaluator: ${validList}`
      );
    }
  }

  /**
   * Create an LLM provider, honouring llmProvider then modelOverride if set.
   * An injected llmProvider wins outright and is returned as-is. Otherwise, when
   * override is active, the key for the override provider is resolved from the
   * matching top-level config field (e.g. anthropicApiKey for Anthropic).
   */
  protected createConfiguredProvider(
    defaultType: Provider,
    defaultModel: string,
    defaultApiKey: string | undefined,
  ): LLMProvider {
    if (this.config.llmProvider) {
      return this.config.llmProvider;
    }
    const override = this.config.modelOverride;
    if (override) {
      const apiKeyFor: Record<Provider, string | undefined> = {
        [Provider.OpenAI]: this.config.openaiApiKey,
        [Provider.Google]: this.config.googleApiKey,
        [Provider.Anthropic]: this.config.anthropicApiKey,
      };
      return createProvider({
        type: override.provider,
        model: override.model,
        apiKey: apiKeyFor[override.provider],
        maxRetries: this.config.maxRetries,
      });
    }
    return createProvider({
      type: defaultType,
      model: defaultModel,
      apiKey: defaultApiKey,
      maxRetries: this.config.maxRetries,
    });
  }

  /**
   * Send telemetry event to analytics service
   * Common helper for all evaluators
   */
  protected async sendTelemetry(params: {
    status: 'success' | 'error';
    latencyMs: number;
    textLength: number;
    gradeLevel?: string;
    provider: string;
    errorCode?: string;
    tokenUsage?: TokenUsage;
    metadata?: TelemetryMetadata;
    inputText?: string;
  }): Promise<void> {
    if (!this.telemetryClient) {
      return;
    }

    await this.telemetryClient.send({
      timestamp: new Date().toISOString(),
      sdk_version: getSDKVersion(),
      evaluator_type: this.getEvaluatorType(),
      // Wire field stays `grade` until the telemetry schema is renamed with the
      // rest of the event fields; the collector reads this name today.
      grade: params.gradeLevel,
      status: params.status,
      error_code: params.errorCode,
      latency_ms: params.latencyMs,
      text_length_chars: params.textLength,
      provider: params.provider,
      token_usage: params.tokenUsage,
      metadata: params.metadata,
      model_override: this.config.modelOverride ? true : undefined,
      // Include input text only if recording is enabled
      input_text: this.config.telemetry.recordInputs ? params.inputText : undefined,
    });
  }
}
