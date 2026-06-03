/**
 * Custom error types for the Evaluators SDK
 *
 * This module provides a hierarchy of error types to help users
 * distinguish between different error scenarios and implement
 * appropriate error handling strategies.
 */

/**
 * Base error class for all evaluator errors
 */
export class EvaluatorError extends Error {
  constructor(
    message: string,
    public readonly code?: string
  ) {
    super(message);
    this.name = 'EvaluatorError';
    // Maintains proper stack trace for where error was thrown (only available on V8)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }
}

/**
 * Configuration error - thrown when the evaluator is misconfigured
 * These are developer errors (e.g. missing API keys) that should NOT be retried
 *
 * @example
 * ```typescript
 * try {
 *   const evaluator = new VocabularyEvaluator({ googleApiKey: '' });
 * } catch (error) {
 *   if (error instanceof ConfigurationError) {
 *     console.error('Check your evaluator config:', error.message);
 *   }
 * }
 * ```
 */
export class ConfigurationError extends EvaluatorError {
  constructor(message: string) {
    super(message, 'CONFIGURATION_ERROR');
    this.name = 'ConfigurationError';
  }
}

/**
 * Validation error - thrown when input validation fails
 * These are client-side errors that should NOT be retried
 *
 * @example
 * ```typescript
 * try {
 *   await evaluator.evaluate('', '5');
 * } catch (error) {
 *   if (error instanceof ValidationError) {
 *     // Show user-friendly error message
 *     console.error('Invalid input:', error.message);
 *   }
 * }
 * ```
 */
export class ValidationError extends EvaluatorError {
  constructor(message: string) {
    super(message, 'VALIDATION_ERROR');
    this.name = 'ValidationError';
  }
}

/**
 * Base API error - thrown when LLM API calls fail
 * Contains additional context about the API error
 */
export class APIError extends EvaluatorError {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly retryable: boolean = false,
    code?: string
  ) {
    super(message, code);
    this.name = 'APIError';
  }
}

/**
 * Authentication error - thrown when API keys are invalid or missing
 * HTTP 401 or 403 responses
 * Should NOT be retried
 *
 * @example
 * ```typescript
 * try {
 *   await evaluator.evaluate(text, grade);
 * } catch (error) {
 *   if (error instanceof AuthenticationError) {
 *     // Prompt user to check API keys
 *     console.error('Invalid API keys. Please check your credentials.');
 *   }
 * }
 * ```
 */
export class AuthenticationError extends APIError {
  constructor(message: string, statusCode?: number) {
    super(message, statusCode, false, 'AUTHENTICATION_ERROR');
    this.name = 'AuthenticationError';
  }
}

/**
 * Rate limit error - thrown when API rate limits are exceeded
 * HTTP 429 responses
 * Should be retried with exponential backoff
 *
 * @example
 * ```typescript
 * try {
 *   await evaluator.evaluate(text, grade);
 * } catch (error) {
 *   if (error instanceof RateLimitError) {
 *     // Wait and retry
 *     await sleep(error.retryAfter || 5000);
 *     // retry...
 *   }
 * }
 * ```
 */
export class RateLimitError extends APIError {
  constructor(
    message: string,
    public readonly retryAfter?: number // milliseconds
  ) {
    super(message, 429, true, 'RATE_LIMIT_ERROR');
    this.name = 'RateLimitError';
  }
}

/**
 * Network error - thrown when network requests fail
 * Connection timeouts, DNS failures, etc.
 * May be retryable depending on the scenario
 *
 * @example
 * ```typescript
 * try {
 *   await evaluator.evaluate(text, grade);
 * } catch (error) {
 *   if (error instanceof NetworkError) {
 *     // Check network connection and retry
 *     console.error('Network error:', error.message);
 *   }
 * }
 * ```
 */
export class NetworkError extends APIError {
  constructor(message: string, retryable: boolean = true) {
    super(message, undefined, retryable, 'NETWORK_ERROR');
    this.name = 'NetworkError';
  }
}

/**
 * Knowledge Graph error - thrown when KG API calls fail
 */
export class KnowledgeGraphError extends EvaluatorError {
  constructor(message: string, public readonly statusCode?: number) {
    super(message, 'KNOWLEDGE_GRAPH_ERROR');
    this.name = 'KnowledgeGraphError';
  }
}

/**
 * Timeout error - thrown when requests exceed timeout limits
 * Should be retried with caution
 *
 * @example
 * ```typescript
 * try {
 *   await evaluator.evaluate(text, grade);
 * } catch (error) {
 *   if (error instanceof TimeoutError) {
 *     // Retry with longer timeout or smaller text
 *     console.error('Request timed out');
 *   }
 * }
 * ```
 */
export class TimeoutError extends APIError {
  constructor(message: string = 'Request timed out') {
    super(message, 408, true, 'TIMEOUT_ERROR');
    this.name = 'TimeoutError';
  }
}

/**
 * Parse structured output from LLM provider error
 */
function parseProviderError(error: unknown): { message: string; statusCode?: number; code?: string } {
  if (error instanceof Error) {
    const message = error.message;
    const err = error as Error & { statusCode?: number; status?: number };

    // Prefer a statusCode/status property (Vercel AI SDK's APICallError sets these)
    // then fall back to parsing from the message string
    const statusMatch = message.match(/\b(4\d{2}|5\d{2})\b/);
    const statusCode =
      err.statusCode ??
      err.status ??
      (statusMatch ? parseInt(statusMatch[1]) : undefined);

    return {
      message,
      statusCode,
      code: error.name !== 'Error' ? error.name : undefined,
    };
  }

  return {
    message: String(error),
  };
}

/**
 * Wrap a provider error into the appropriate error type.
 *
 * Returns `ConfigurationError` for model-not-found responses (HTTP 404, or HTTP 400
 * with a model-related message), since those indicate a bad model ID in configuration.
 * Returns the appropriate `APIError` subclass for all other provider errors.
 *
 * @internal
 */
export function wrapProviderError(error: unknown, defaultMessage: string = 'API request failed'): EvaluatorError {
  const { message, statusCode, code } = parseProviderError(error);

  // Detect model-not-found errors (404, or 400 with model-related message)
  if (
    statusCode === 404 ||
    (statusCode === 400 && /\bmodel\b.*(not found|does not exist|invalid)/i.test(message))
  ) {
    return new ConfigurationError(
      `Model not found or invalid: ${message}. Check the model ID passed to the provider.`
    );
  }

  // Detect authentication errors (401, 403)
  if (statusCode === 401 || statusCode === 403) {
    return new AuthenticationError(
      message.includes('API key') ? message : 'Invalid API key',
      statusCode
    );
  }

  // Detect rate limit errors (429)
  if (statusCode === 429) {
    // Try to extract retry-after if present
    const retryAfterMatch = message.match(/retry[- ]after[:\s]+(\d+)/i);
    const retryAfter = retryAfterMatch ? parseInt(retryAfterMatch[1]) * 1000 : undefined;

    return new RateLimitError(
      message.includes('rate limit') ? message : 'Rate limit exceeded',
      retryAfter
    );
  }

  // Detect network errors
  if (
    message.includes('ECONNREFUSED') ||
    message.includes('ENOTFOUND') ||
    message.includes('ETIMEDOUT') ||
    message.includes('network') ||
    message.includes('Network')
  ) {
    return new NetworkError(message);
  }

  // Detect timeout errors
  if (message.includes('timeout') || message.includes('timed out')) {
    return new TimeoutError(message);
  }

  // Generic API error for everything else
  return new APIError(
    message || defaultMessage,
    statusCode,
    statusCode ? statusCode >= 500 : false, // 5xx errors are retryable
    code
  );
}
