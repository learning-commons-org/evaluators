/**
 * Canonical error taxonomy.
 *
 * Errors classify by **fault domain** — who must act — not by mechanism:
 * caller (`ConfigurationError`, `InputValidationError`), our own evaluation
 * logic (`EvaluationError`), or an external system (`DependencyError`).
 *
 * `retryable` is data, not hierarchy: callers read the flag rather than
 * memorizing which classes retry. Strategy follows the category — dependency
 * failures back off, evaluation failures resample immediately.
 */

/** Canonical ID of an external system, for `DependencyError.dependency`. */
export type DependencyId = 'openai' | 'google' | 'anthropic' | 'knowledge-graph';

export interface DependencyErrorOptions {
  dependency: DependencyId;
  statusCode?: number | null;
  requestId?: string | null;
  /** Model in use, when the dependency is an LLM provider. */
  model?: string | null;
  /** Overrides the class default; a 5xx forces `true`. */
  retryable?: boolean;
  cause?: unknown;
}

export abstract class EvaluatorError extends Error {
  readonly retryable: boolean;

  constructor(message: string, retryable: boolean, cause?: unknown) {
    super(message, cause === undefined ? undefined : { cause });
    this.retryable = retryable;
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }
}

/** Caller: missing or invalid key, unknown provider or model, malformed settings. */
export class ConfigurationError extends EvaluatorError {
  constructor(message: string, cause?: unknown) {
    super(message, false, cause);
    this.name = 'ConfigurationError';
  }
}

/**
 * Caller: text or grade failed validation. Also covers caller-supplied
 * identifiers a dependency rejects — fault domain decides, not subsystem.
 */
export class InputValidationError extends EvaluatorError {
  constructor(message: string, cause?: unknown) {
    super(message, false, cause);
    this.name = 'InputValidationError';
  }
}

/** A caller-supplied standards code that does not exist in the jurisdiction. */
export class StandardNotFoundError extends InputValidationError {
  constructor(message: string, readonly statementCode: string, cause?: unknown) {
    super(message, cause);
    this.name = 'StandardNotFoundError';
  }
}

/** Our own evaluation logic failed after the dependency call succeeded. */
export abstract class EvaluationError extends EvaluatorError {}

/**
 * Model response failed parsing, normalization, or its output schema.
 * Retryable immediately: the failure is sampling variance, so backing off
 * only adds latency.
 */
export class LLMOutputProcessingError extends EvaluationError {
  constructor(
    message: string,
    readonly validationErrors: unknown[] | null = null,
    cause?: unknown
  ) {
    super(message, true, cause);
    this.name = 'LLMOutputProcessingError';
  }
}

/** An external system failed. Which system is data (`dependency`), not a class. */
export abstract class DependencyError extends EvaluatorError {
  readonly dependency: DependencyId;
  readonly statusCode: number | null;
  readonly requestId: string | null;
  readonly model: string | null;

  constructor(message: string, classRetryable: boolean, options: DependencyErrorOptions) {
    const statusCode = options.statusCode ?? null;
    const is5xx = statusCode !== null && statusCode >= 500;
    super(message, options.retryable ?? (is5xx || classRetryable), options.cause);
    this.dependency = options.dependency;
    this.statusCode = statusCode;
    this.requestId = options.requestId ?? null;
    this.model = options.model ?? null;
  }
}

export class AuthenticationError extends DependencyError {
  constructor(message: string, options: DependencyErrorOptions) {
    super(message, false, options);
    this.name = 'AuthenticationError';
  }
}

export class RateLimitError extends DependencyError {
  readonly retryAfterMs: number | null;

  constructor(message: string, options: DependencyErrorOptions & { retryAfterMs?: number | null }) {
    super(message, true, { statusCode: 429, ...options });
    this.name = 'RateLimitError';
    this.retryAfterMs = options.retryAfterMs ?? null;
  }
}

export class NetworkError extends DependencyError {
  constructor(message: string, options: DependencyErrorOptions) {
    super(message, true, options);
    this.name = 'NetworkError';
  }
}

export class RequestTimeoutError extends DependencyError {
  constructor(message: string, options: DependencyErrorOptions) {
    super(message, true, options);
    this.name = 'RequestTimeoutError';
  }
}

/** Catch-all for LLM-provider failures not mapped above. Retryable iff 5xx. */
export class LLMProviderError extends DependencyError {
  constructor(message: string, options: DependencyErrorOptions) {
    super(message, false, options);
    this.name = 'LLMProviderError';
  }
}

/** Catch-all for Knowledge Graph failures not mapped above. Retryable iff 5xx. */
export class KnowledgeGraphError extends DependencyError {
  constructor(message: string, options: Omit<DependencyErrorOptions, 'dependency'> = {}) {
    super(message, false, { ...options, dependency: 'knowledge-graph' });
    this.name = 'KnowledgeGraphError';
  }
}

/**
 * Extract what the provider told us, preferring structured fields over the
 * message. Message text is not a contract — it is carried through for
 * diagnosis but never used to reclassify.
 */
function readProviderError(error: unknown): {
  message: string;
  statusCode: number | null;
  requestId: string | null;
} {
  if (!(error instanceof Error)) {
    return { message: String(error), statusCode: null, requestId: null };
  }
  const err = error as Error & {
    statusCode?: number;
    status?: number;
    requestId?: string;
    request_id?: string;
  };
  return {
    message: error.message,
    statusCode: err.statusCode ?? err.status ?? null,
    requestId: err.requestId ?? err.request_id ?? null,
  };
}

/**
 * Map a dependency failure onto the taxonomy.
 *
 * Classification uses status codes only. Free-text matching is deliberately
 * absent: wording is not a contract, and the catch-all is safer than a wrong
 * class. Text-only failures therefore land on `LLMProviderError`.
 */
export function wrapProviderError(
  error: unknown,
  context: { dependency: DependencyId; model?: string | null }
): EvaluatorError {
  const { message, statusCode, requestId } = readProviderError(error);
  const options: DependencyErrorOptions = {
    dependency: context.dependency,
    statusCode,
    requestId,
    model: context.model ?? null,
    cause: error,
  };

  if (statusCode === 404) {
    return new ConfigurationError(
      `Model not found or invalid: ${message}. Check the model ID passed to the provider.`,
      error
    );
  }
  if (statusCode === 401 || statusCode === 403) {
    return new AuthenticationError(message, options);
  }
  if (statusCode === 429) {
    return new RateLimitError(message, options);
  }
  if (statusCode === 408) {
    return new RequestTimeoutError(message, options);
  }
  return new LLMProviderError(message || 'API request failed', options);
}
