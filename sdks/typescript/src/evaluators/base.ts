import {
  TelemetryClient,
  generateClientId,
  getSDKVersion,
  type TelemetryMetadata,
  type TokenUsage,
} from '../telemetry/index.js';
import { ValidationError } from '../errors.js';
import { createLogger, LogLevel, type Logger } from '../logger.js';

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
 * Granular telemetry configuration options
 */
export interface TelemetryOptions {
  /** Enable telemetry (default: true) */
  enabled?: boolean;

  /** Record input text in telemetry (default: false) */
  recordInputs?: boolean;
}

/**
 * Base configuration for all evaluators
 */
export interface BaseEvaluatorConfig {
  /** Google API key (for evaluators using Gemini) */
  googleApiKey?: string;

  /** OpenAI API key (for evaluators using GPT) */
  openaiApiKey?: string;

  /** Learning Commons API key for authenticated telemetry (optional) */
  apiKey?: string;

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
 * Abstract base class for all evaluators
 *
 * Provides common functionality:
 * - Telemetry setup and event sending
 * - Text validation
 * - Grade validation (with overridable default)
 * - Metadata creation
 */
export abstract class BaseEvaluator {
  protected telemetryClient?: TelemetryClient;
  protected logger: Logger;
  protected config: Required<Pick<BaseEvaluatorConfig, 'maxRetries'>> & {
    telemetry: Required<TelemetryOptions>;
  };

  constructor(config: BaseEvaluatorConfig) {
    // Initialize logger
    this.logger = createLogger(config.logger, config.logLevel ?? LogLevel.WARN);
    // Normalize telemetry config
    const telemetryConfig = this.normalizeTelemetryConfig(config.telemetry);

    // Set defaults for common config
    this.config = {
      maxRetries: config.maxRetries ?? 2,
      telemetry: telemetryConfig,
    };

    // Initialize telemetry if enabled
    if (this.config.telemetry.enabled) {
      // Use all provider keys for client ID generation
      const providerKeys = [config.googleApiKey, config.openaiApiKey].filter(
        (key): key is string => key !== undefined
      );

      this.telemetryClient = new TelemetryClient({
        endpoint: 'https://api.learningcommons.org/v1/telemetry',
        apiKey: config.apiKey,
        clientId: generateClientId(...providerKeys),
        enabled: true,
      });
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
   * Get the evaluator type identifier (e.g., "vocabulary", "sentence-structure")
   * Must be implemented by concrete evaluators
   */
  protected abstract getEvaluatorType(): string;

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
      const error = new ValidationError(
        'Text cannot be empty or contain only whitespace'
      );
      this.logger.error('Text validation failed: empty or whitespace only', {
        evaluator: this.getEvaluatorType(),
        error,
      });
      throw error;
    }

    // Check minimum length
    if (trimmedText.length < VALIDATION_LIMITS.MIN_TEXT_LENGTH) {
      const error = new ValidationError(
        `Text is too short. Minimum length is ${VALIDATION_LIMITS.MIN_TEXT_LENGTH} characters, received ${trimmedText.length} characters`
      );
      this.logger.error('Text validation failed: too short', {
        evaluator: this.getEvaluatorType(),
        error,
        minLength: VALIDATION_LIMITS.MIN_TEXT_LENGTH,
        actualLength: trimmedText.length,
      });
      throw error;
    }

    // Check maximum length
    if (trimmedText.length > VALIDATION_LIMITS.MAX_TEXT_LENGTH) {
      const error = new ValidationError(
        `Text is too long. Maximum length is ${VALIDATION_LIMITS.MAX_TEXT_LENGTH.toLocaleString()} characters, received ${trimmedText.length.toLocaleString()} characters`
      );
      this.logger.error('Text validation failed: too long', {
        evaluator: this.getEvaluatorType(),
        error,
        maxLength: VALIDATION_LIMITS.MAX_TEXT_LENGTH,
        actualLength: trimmedText.length,
      });
      throw error;
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
        return parseInt(a) - parseInt(b);
      }).join(', ');

      const error = new ValidationError(
        `Invalid grade "${grade}". Supported grades for this evaluator: ${validList}`
      );
      this.logger.error('Grade validation failed: invalid grade', {
        evaluator: this.getEvaluatorType(),
        error,
        providedGrade: grade,
        validGrades: validList,
      });
      throw error;
    }
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
    retryAttempts: number;
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
      retry_attempts: params.retryAttempts,
      token_usage: params.tokenUsage,
      metadata: params.metadata,
      // Include input text only if recording is enabled
      input_text: this.config.telemetry.recordInputs ? params.inputText : undefined,
    });
  }
}
