import {
  TelemetryClient,
  generateClientId,
  getSDKVersion,
  type TelemetryMetadata,
  type TokenUsage,
} from '../telemetry/index.js';
import { ConfigurationError, ValidationError } from '../errors.js';
import { createLogger, LogLevel, type Logger } from '../logger.js';
import { createProvider } from '../providers/index.js';
import type { LLMProvider } from '../providers/index.js';

/**
 * Validation constants for input text
 */
export const VALIDATION_LIMITS = {
  /** Minimum text length in characters */
  MIN_TEXT_LENGTH: 10,
  /** Maximum text length in characters (100K chars ≈ 25K tokens) */
  MAX_TEXT_LENGTH: 100_000,
} as const;

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
}

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

  /** Learning Commons partner key for authenticated telemetry (optional) */
  partnerKey?: string;

  /**
   * Override the provider and model used by this evaluator.
   * When set, all LLM calls use this provider and model instead of the defaults.
   * See {@link ModelOverride} for details.
   */
  modelOverride?: ModelOverride;

  /**
   * Maximum number of retries for failed API calls (default: 2)
   * Set to 0 to disable retries.
   *
   * Note: With maxRetries=2, a failed call will be attempted up to 3 times total
   * (1 initial attempt + 2 retries)
   */
  maxRetries?: number;

  /**
   * Telemetry configuration (default: all enabled)
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
  /** Unique identifier for the evaluator (e.g., 'vocabulary', 'sentence-structure') */
  readonly id: string;
  /** Human-readable name (e.g., 'Vocabulary', 'Sentence Structure') */
  readonly name: string;
  /** Brief description of what the evaluator does */
  readonly description: string;
  /** Supported grade levels (e.g., ['3', '4', '5', ...]) */
  readonly supportedGrades: readonly string[];
  /** Providers required by this evaluator's default configuration */
  readonly defaultProviders: readonly Provider[];
}

/**
 * Abstract base class for all evaluators
 *
 * Provides common functionality:
 * - Telemetry setup and event sending
 * - Text validation
 * - Grade validation (with overridable default)
 * - Metadata creation
 *
 * Concrete evaluators must implement:
 * - static metadata: Provide evaluator metadata (see EvaluatorMetadata interface)
 */
export abstract class BaseEvaluator {
  protected telemetryClient?: TelemetryClient;
  protected logger: Logger;
  protected config: Required<Pick<BaseEvaluatorConfig, 'maxRetries'>> & {
    telemetry: Required<TelemetryOptions>;
    modelOverride?: ModelOverride;
    googleApiKey?: string;
    openaiApiKey?: string;
    anthropicApiKey?: string;
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
   *     id: 'my-evaluator',
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

    // Validate modelOverride shape before key checks
    this.validateModelOverride(config);

    // Validate required API keys based on metadata
    this.validateApiKeys(config);

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
        partnerKey: config.partnerKey,
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
   * Validate that the required API key is present.
   * When modelOverride is set, checks the override provider's key.
   * Otherwise checks the keys required by the evaluator's default providers.
   * @throws {ConfigurationError} If a required key is missing
   */
  private validateApiKeys(config: BaseEvaluatorConfig): void {
    const keyFor: Record<Provider, string | undefined> = {
      [Provider.OpenAI]: config.openaiApiKey?.trim() || undefined,
      [Provider.Google]: config.googleApiKey?.trim() || undefined,
      [Provider.Anthropic]: config.anthropicApiKey?.trim() || undefined,
    };
    const humanName: Record<Provider, string> = {
      [Provider.OpenAI]: 'OpenAI API key',
      [Provider.Google]: 'Google API key',
      [Provider.Anthropic]: 'Anthropic API key',
    };
    const configKey: Record<Provider, string> = {
      [Provider.OpenAI]: 'openaiApiKey',
      [Provider.Google]: 'googleApiKey',
      [Provider.Anthropic]: 'anthropicApiKey',
    };

    if (config.modelOverride) {
      if (!keyFor[config.modelOverride.provider]) {
        throw new ConfigurationError(
          `${humanName[config.modelOverride.provider]} is required when using modelOverride with provider "${config.modelOverride.provider}". Pass ${configKey[config.modelOverride.provider]} in config.`
        );
      }
      return;
    }

    for (const provider of this.metadata.defaultProviders) {
      if (!keyFor[provider]) {
        throw new ConfigurationError(
          `${humanName[provider]} is required for ${this.metadata.name} evaluator. Pass ${configKey[provider]} in config.`
        );
      }
    }
  }

  /**
   * Normalize telemetry config to standard format
   */
  private normalizeTelemetryConfig(
    telemetry: boolean | TelemetryOptions | undefined
  ): Required<TelemetryOptions> {
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
    };
  }

  /**
   * Get the evaluator type identifier from metadata
   * @returns The evaluator type ID (e.g., "vocabulary", "sentence-structure")
   */
  protected getEvaluatorType(): string {
    return this.metadata.id;
  }

  /**
   * Validate text meets requirements
   * Default implementation - can be overridden by concrete evaluators
   *
   * @throws {ValidationError} If text is invalid
   */
  protected validateText(text: string): void {
    this.logger.debug('Validating text input', {
      evaluator: this.getEvaluatorType(),
      operation: 'validateText',
      textLength: text.length,
    });

    // Check if text is empty or only whitespace
    const trimmedText = text.trim();
    if (!trimmedText) {
      throw new ValidationError('Text cannot be empty or contain only whitespace');
    }

    // Check minimum length
    if (trimmedText.length < VALIDATION_LIMITS.MIN_TEXT_LENGTH) {
      throw new ValidationError(
        `Text is too short. Minimum length is ${VALIDATION_LIMITS.MIN_TEXT_LENGTH} characters, received ${trimmedText.length} characters`
      );
    }

    // Check maximum length
    if (trimmedText.length > VALIDATION_LIMITS.MAX_TEXT_LENGTH) {
      throw new ValidationError(
        `Text is too long. Maximum length is ${VALIDATION_LIMITS.MAX_TEXT_LENGTH.toLocaleString()} characters, received ${trimmedText.length.toLocaleString()} characters`
      );
    }
  }

  /**
   * Validate grade is in supported range
   * Default implementation - can be overridden by concrete evaluators
   *
   * @param grade - Grade level to validate
   * @param validGrades - Set of valid grades for this evaluator
   * @throws {ValidationError} If grade is invalid
   */
  protected validateGrade(grade: string, validGrades: Set<string>): void {
    this.logger.debug('Validating grade input', {
      evaluator: this.getEvaluatorType(),
      operation: 'validateGrade',
      grade,
    });

    // Check if grade is in valid set
    if (!validGrades.has(grade)) {
      const validList = Array.from(validGrades).sort((a, b) => {
        // Sort K first, then numerically
        if (a === 'K') return -1;
        if (b === 'K') return 1;
        return parseInt(a, 10) - parseInt(b, 10);
      }).join(', ');

      throw new ValidationError(
        `Invalid grade "${grade}". Supported grades for this evaluator: ${validList}`
      );
    }
  }

  /**
   * Create an LLM provider, honouring modelOverride if set.
   * When override is active, the key for the override provider is resolved
   * from the matching top-level config field (e.g. anthropicApiKey for Anthropic).
   */
  protected createConfiguredProvider(
    defaultType: Provider,
    defaultModel: string,
    defaultApiKey: string | undefined,
  ): LLMProvider {
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
    grade?: string;
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
      grade: params.grade,
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
