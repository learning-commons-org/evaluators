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
import {
  APICallError,
  JSONParseError,
  NoObjectGeneratedError,
  TypeValidationError,
} from 'ai';

/**
 * Canonical ID of an external system, for `DependencyError.dependency`.
 *
 * Closed on purpose: an integration we add must be named here rather than
 * landing in a catch-all. `custom` is not that catch-all — it means the caller
 * injected their own `llmProvider`, so the vendor is theirs to know, not ours.
 * A `modelOverride` still reports its real vendor, since it is one of ours.
 *
 * The provider arm must stay in step with the `Provider` enum, which cannot be
 * imported here without a cycle.
 */
export type DependencyId = 'openai' | 'google' | 'anthropic' | 'knowledge-graph' | 'custom';

/**
 * The subset of {@link DependencyId} that can appear as an LLM provider label's
 * prefix. `knowledge-graph` never does — that client raises its own errors — and
 * `custom` is the fallback for a label none of these match, not a match itself.
 */
export const PROVIDER_DEPENDENCIES: ReadonlySet<DependencyId> = new Set<DependencyId>([
  'openai',
  'google',
  'anthropic',
]);

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
    // Spread first, then default: a present-but-undefined statusCode must not
    // clobber the 429 this class implies.
    super(message, true, { ...options, statusCode: options.statusCode ?? 429 });
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

/** Connection-level failures, by Node errno rather than message text. */
const NETWORK_CODES = new Set([
  'ECONNREFUSED',
  'ECONNRESET',
  'ENOTFOUND',
  'EAI_AGAIN',
  'EPIPE',
  'EHOSTUNREACH',
  'ENETUNREACH',
]);

/** Timeouts, by Node errno or the DOMException name `AbortSignal.timeout` raises. */
const TIMEOUT_CODES = new Set(['ETIMEDOUT', 'UND_ERR_HEADERS_TIMEOUT', 'UND_ERR_BODY_TIMEOUT']);
const TIMEOUT_NAMES = new Set(['TimeoutError', 'AbortError']);

/** Header names providers use for the request ID, in preference order. */
const REQUEST_ID_HEADERS = ['x-request-id', 'request-id', 'x-amzn-requestid'];

interface ProviderSignals {
  message: string;
  statusCode: number | null;
  requestId: string | null;
  /** The provider's own retryability verdict, when it gave one. */
  retryable?: boolean;
  retryAfterMs: number | null;
}

/** Walk the cause chain so a wrapped provider error is still classifiable. */
function* causeChain(error: unknown): Generator<unknown> {
  let current = error;
  for (let depth = 0; current != null && depth < 10; depth++) {
    yield current;
    current = (current as { cause?: unknown }).cause;
  }
}

function readRetryAfterMs(headers: Record<string, string> | undefined): number | null {
  const seconds = headers?.['retry-after'];
  if (seconds !== undefined) {
    const parsed = Number(seconds);
    if (Number.isFinite(parsed)) return Math.round(parsed * 1000);
  }
  const ms = headers?.['retry-after-ms'];
  if (ms !== undefined) {
    const parsed = Number(ms);
    if (Number.isFinite(parsed)) return Math.round(parsed);
  }
  return null;
}

/**
 * Read structured fields off whatever was thrown. Message text is carried for
 * diagnosis but never used to classify.
 */
function readProviderSignals(error: unknown): ProviderSignals {
  const base: ProviderSignals = {
    message: error instanceof Error ? error.message : String(error),
    statusCode: null,
    requestId: null,
    retryAfterMs: null,
  };

  for (const link of causeChain(error)) {
    if (!APICallError.isInstance(link)) continue;
    const headers = link.responseHeaders;
    return {
      ...base,
      statusCode: link.statusCode ?? null,
      requestId: REQUEST_ID_HEADERS.map((h) => headers?.[h]).find((v) => v != null) ?? null,
      retryable: link.isRetryable,
      retryAfterMs: readRetryAfterMs(headers),
    };
  }

  // Not an AI SDK error: fall back to the loose properties other clients set.
  const loose = error as { statusCode?: number; status?: number };
  return { ...base, statusCode: loose?.statusCode ?? loose?.status ?? null };
}

/** Schema/parse failures are the model's fault, not the dependency's. */
function isOutputProcessingFailure(error: unknown): boolean {
  for (const link of causeChain(error)) {
    if (
      NoObjectGeneratedError.isInstance(link) ||
      TypeValidationError.isInstance(link) ||
      JSONParseError.isInstance(link)
    ) {
      return true;
    }
  }
  return false;
}

function findTransportFailure(error: unknown): 'network' | 'timeout' | null {
  for (const link of causeChain(error)) {
    const { code, name } = (link ?? {}) as { code?: string; name?: string };
    if (code !== undefined && TIMEOUT_CODES.has(code)) return 'timeout';
    if (name !== undefined && TIMEOUT_NAMES.has(name)) return 'timeout';
    if (code !== undefined && NETWORK_CODES.has(code)) return 'network';
  }
  return null;
}

/**
 * Map a dependency failure onto the taxonomy.
 *
 * Classification uses structured signals only — status codes, typed AI SDK
 * errors, and Node errnos, each searched along the cause chain. Message text is
 * never matched: wording is not a contract, and the catch-all is safer than a
 * wrong class.
 */
export function wrapProviderError(
  error: unknown,
  context: { dependency: DependencyId; model?: string | null }
): EvaluatorError {
  const signals = readProviderSignals(error);
  const { message, statusCode } = signals;
  const options: DependencyErrorOptions = {
    dependency: context.dependency,
    statusCode,
    requestId: signals.requestId,
    model: context.model ?? null,
    retryable: signals.retryable,
    cause: error,
  };

  // The model returned something unusable — our fault to re-sample, not the
  // dependency's to fix, so this outranks any transport signal.
  if (isOutputProcessingFailure(error)) {
    return new LLMOutputProcessingError(message, null, error);
  }

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
    return new RateLimitError(message, { ...options, retryAfterMs: signals.retryAfterMs });
  }

  const transport = statusCode === 408 ? 'timeout' : findTransportFailure(error);
  if (transport === 'timeout') return new RequestTimeoutError(message, options);
  if (transport === 'network') return new NetworkError(message, options);

  return new LLMProviderError(message || 'API request failed', options);
}
