import { describe, it, expect } from 'vitest';
import { APICallError } from 'ai';
import {
  wrapProviderError,
  ConfigurationError,
  AuthenticationError,
  RateLimitError,
  RequestTimeoutError,
  LLMProviderError,
  DependencyError,
  EvaluatorError,
  KnowledgeGraphError,
  LLMOutputProcessingError,
  NetworkError,
  InputValidationError,
  StandardNotFoundError,
} from '../../../src/errors.js';

const CONTEXT = { dependency: 'openai' as const, model: 'gpt-4o-2024-11-20' };

const makeAPICallError = (statusCode: number, message: string) =>
  new APICallError({
    message,
    url: 'https://api.example.com/v1/chat',
    requestBodyValues: {},
    statusCode,
    responseHeaders: {},
    responseBody: message,
    isRetryable: false,
  });

describe('wrapProviderError — status-code classification', () => {
  it.each([
    [404, ConfigurationError],
    [401, AuthenticationError],
    [403, AuthenticationError],
    [429, RateLimitError],
    [408, RequestTimeoutError],
    [500, LLMProviderError],
    [503, LLMProviderError],
    [400, LLMProviderError],
  ])('maps %i to %s', (status, expected) => {
    expect(wrapProviderError(makeAPICallError(status, 'boom'), CONTEXT)).toBeInstanceOf(expected);
  });

  it('reads statusCode from a plain Error property', () => {
    const err = Object.assign(new Error('nope'), { statusCode: 401 });
    expect(wrapProviderError(err, CONTEXT)).toBeInstanceOf(AuthenticationError);
  });

  it('reads statusCode from the `status` alias', () => {
    const err = Object.assign(new Error('nope'), { status: 429 });
    expect(wrapProviderError(err, CONTEXT)).toBeInstanceOf(RateLimitError);
  });

  it('falls back to the catch-all when no status is available', () => {
    const wrapped = wrapProviderError(new Error('something opaque'), CONTEXT);
    expect(wrapped).toBeInstanceOf(LLMProviderError);
    expect((wrapped as LLMProviderError).statusCode).toBeNull();
  });

  it('handles a non-Error throw', () => {
    const wrapped = wrapProviderError('just a string', CONTEXT);
    expect(wrapped).toBeInstanceOf(LLMProviderError);
    expect(wrapped.message).toBe('just a string');
  });

  it('substitutes a default message only when the provider gave none', () => {
    expect(wrapProviderError(new Error(''), CONTEXT).message).toBe('API request failed');
    expect(wrapProviderError(new Error('upstream detail'), CONTEXT).message).toBe('upstream detail');
  });
});

describe('wrapProviderError — message text never reclassifies', () => {
  // Wording is not a contract. A 400 whose prose mentions a bad model stays the
  // catch-all; only structured signals may narrow the class.
  it('does not promote a 400 with model-not-found prose to ConfigurationError', () => {
    const err = makeAPICallError(400, "model 'gpt-fake-99' does not exist or you do not have access");
    expect(wrapProviderError(err, CONTEXT)).toBeInstanceOf(LLMProviderError);
    expect(wrapProviderError(err, CONTEXT)).not.toBeInstanceOf(ConfigurationError);
  });

  it.each([
    'ECONNREFUSED connecting to api.example.com',
    'ENOTFOUND api.example.com',
    'socket hang up: network unreachable',
    'the request timed out after 30s',
  ])('does not classify %s by prose', (message) => {
    const wrapped = wrapProviderError(new Error(message), CONTEXT);
    expect(wrapped).toBeInstanceOf(LLMProviderError);
    expect(wrapped).not.toBeInstanceOf(NetworkError);
    expect(wrapped).not.toBeInstanceOf(RequestTimeoutError);
  });
});

describe('wrapProviderError — diagnostic attribution', () => {
  it('attaches dependency, status, model and the original cause', () => {
    const original = makeAPICallError(500, 'upstream exploded');
    const wrapped = wrapProviderError(original, CONTEXT) as DependencyError;

    expect(wrapped.dependency).toBe('openai');
    expect(wrapped.statusCode).toBe(500);
    expect(wrapped.model).toBe('gpt-4o-2024-11-20');
    expect(wrapped.cause).toBe(original);
  });

  it('carries the upstream message rather than a generic substitute', () => {
    const wrapped = wrapProviderError(makeAPICallError(401, 'key sk-abc revoked on 2026-01-01'), CONTEXT);
    expect(wrapped.message).toBe('key sk-abc revoked on 2026-01-01');
  });

  it('extracts requestId from either casing', () => {
    const camel = Object.assign(new Error('x'), { statusCode: 500, requestId: 'req_camel' });
    const snake = Object.assign(new Error('x'), { statusCode: 500, request_id: 'req_snake' });

    expect((wrapProviderError(camel, CONTEXT) as DependencyError).requestId).toBe('req_camel');
    expect((wrapProviderError(snake, CONTEXT) as DependencyError).requestId).toBe('req_snake');
  });

  it('defaults model and requestId to null rather than undefined', () => {
    const wrapped = wrapProviderError(new Error('x'), { dependency: 'google' }) as DependencyError;
    expect(wrapped.model).toBeNull();
    expect(wrapped.requestId).toBeNull();
  });

  it('preserves the cause and upstream detail on the ConfigurationError path', () => {
    const original = makeAPICallError(404, 'no such model');
    const wrapped = wrapProviderError(original, CONTEXT);

    expect(wrapped.cause).toBe(original);
    expect(wrapped.message).toContain('no such model');
  });
});

describe('retryable is data', () => {
  it('is false for caller faults', () => {
    expect(new ConfigurationError('x').retryable).toBe(false);
    expect(new InputValidationError('x').retryable).toBe(false);
    expect(new StandardNotFoundError('x', '4.OA.A.1').retryable).toBe(false);
  });

  it('is true for output processing, which resamples rather than backs off', () => {
    expect(new LLMOutputProcessingError('bad shape').retryable).toBe(true);
  });

  it('follows the class default for dependency failures', () => {
    expect(new AuthenticationError('x', { dependency: 'openai' }).retryable).toBe(false);
    expect(new RateLimitError('x', { dependency: 'openai' }).retryable).toBe(true);
    expect(new NetworkError('x', { dependency: 'openai' }).retryable).toBe(true);
    expect(new RequestTimeoutError('x', { dependency: 'openai' }).retryable).toBe(true);
  });

  it('makes catch-alls retryable only on 5xx', () => {
    expect(new LLMProviderError('x', { dependency: 'openai', statusCode: 503 }).retryable).toBe(true);
    expect(new LLMProviderError('x', { dependency: 'openai', statusCode: 400 }).retryable).toBe(false);
    expect(new LLMProviderError('x', { dependency: 'openai' }).retryable).toBe(false);
    expect(new KnowledgeGraphError('x', { statusCode: 500 }).retryable).toBe(true);
    expect(new KnowledgeGraphError('x', { statusCode: 404 }).retryable).toBe(false);
  });

  it('lets an explicit override win over both the 5xx rule and the class default', () => {
    expect(
      new LLMProviderError('x', { dependency: 'openai', statusCode: 503, retryable: false }).retryable,
    ).toBe(false);
    expect(
      new AuthenticationError('x', { dependency: 'openai', retryable: true }).retryable,
    ).toBe(true);
  });
});

describe('taxonomy shape', () => {
  it('classifies by fault domain, so a bad standards code is the caller’s fault', () => {
    const err = new StandardNotFoundError('unknown code', '9.ZZ.Z.9');
    expect(err).toBeInstanceOf(InputValidationError);
    expect(err).not.toBeInstanceOf(DependencyError);
    expect(err.statementCode).toBe('9.ZZ.Z.9');
  });

  it('puts every external failure under DependencyError', () => {
    for (const err of [
      new AuthenticationError('x', { dependency: 'openai' }),
      new RateLimitError('x', { dependency: 'google' }),
      new NetworkError('x', { dependency: 'anthropic' }),
      new RequestTimeoutError('x', { dependency: 'openai' }),
      new LLMProviderError('x', { dependency: 'openai' }),
      new KnowledgeGraphError('x'),
    ]) {
      expect(err).toBeInstanceOf(DependencyError);
      expect(err).toBeInstanceOf(EvaluatorError);
    }
  });

  it('defaults the Knowledge Graph dependency without the caller naming it', () => {
    expect(new KnowledgeGraphError('x').dependency).toBe('knowledge-graph');
  });

  // `name` is the canonical error code that reports group failures on, so every
  // class must carry its own.
  it('names each class as its own canonical error code', () => {
    const dep = { dependency: 'openai' as const };
    expect(new ConfigurationError('x').name).toBe('ConfigurationError');
    expect(new InputValidationError('x').name).toBe('InputValidationError');
    expect(new StandardNotFoundError('x', 'c').name).toBe('StandardNotFoundError');
    expect(new LLMOutputProcessingError('x').name).toBe('LLMOutputProcessingError');
    expect(new AuthenticationError('x', dep).name).toBe('AuthenticationError');
    expect(new RateLimitError('x', dep).name).toBe('RateLimitError');
    expect(new NetworkError('x', dep).name).toBe('NetworkError');
    expect(new RequestTimeoutError('x', dep).name).toBe('RequestTimeoutError');
    expect(new LLMProviderError('x', dep).name).toBe('LLMProviderError');
    expect(new KnowledgeGraphError('x').name).toBe('KnowledgeGraphError');
  });

  it('exposes retryAfterMs on rate limits, null when the provider omitted it', () => {
    expect(new RateLimitError('x', { dependency: 'openai', retryAfterMs: 2500 }).retryAfterMs).toBe(2500);
    expect(new RateLimitError('x', { dependency: 'openai' }).retryAfterMs).toBeNull();
  });

  it('defaults a rate limit to 429 but lets the provider’s status win', () => {
    expect(new RateLimitError('x', { dependency: 'openai' }).statusCode).toBe(429);
    expect(new RateLimitError('x', { dependency: 'openai', statusCode: 529 }).statusCode).toBe(529);
  });

  it('exposes validationErrors on output processing failures', () => {
    const details = [{ path: 'evaluations', identifier: 'LC-1' }];
    expect(new LLMOutputProcessingError('x', details).validationErrors).toEqual(details);
    expect(new LLMOutputProcessingError('x').validationErrors).toBeNull();
  });
});
