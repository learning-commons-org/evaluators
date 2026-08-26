import { describe, it, expect } from 'vitest';
import { APICallError, JSONParseError, TypeValidationError } from 'ai';
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

// isRetryable is deliberately left to the AI SDK's own default (408/409/429/5xx),
// so these fixtures behave like errors the provider actually produces.
const makeAPICallError = (statusCode: number, message: string) =>
  new APICallError({
    message,
    url: 'https://api.example.com/v1/chat',
    requestBodyValues: {},
    statusCode,
    responseHeaders: {},
    responseBody: message,
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

describe('wrapProviderError — retryability comes through end to end', () => {
  // The gap that let a regression through: retryability was only ever tested by
  // direct construction, never through the function every evaluator calls.
  it('keeps a 5xx retryable', () => {
    expect(wrapProviderError(makeAPICallError(503, 'unavailable'), CONTEXT).retryable).toBe(true);
  });

  it('keeps a 429 retryable', () => {
    expect(wrapProviderError(makeAPICallError(429, 'slow down'), CONTEXT).retryable).toBe(true);
  });

  it('keeps a 400 non-retryable', () => {
    expect(wrapProviderError(makeAPICallError(400, 'bad request'), CONTEXT).retryable).toBe(false);
  });

  it('keeps auth failures non-retryable', () => {
    expect(wrapProviderError(makeAPICallError(401, 'nope'), CONTEXT).retryable).toBe(false);
  });

  it("honours the provider's own isRetryable verdict over the status heuristic", () => {
    const err = new APICallError({
      message: 'permanent server-side rejection',
      url: 'https://api.example.com/v1/chat',
      requestBodyValues: {},
      statusCode: 500,
      responseHeaders: {},
      responseBody: '',
      isRetryable: false,
    });

    expect(wrapProviderError(err, CONTEXT).retryable).toBe(false);
  });
});

describe('wrapProviderError — transport failures stay classified and retryable', () => {
  const transport = (props: Record<string, unknown>) =>
    Object.assign(new Error('boom'), props);

  it.each(['ECONNREFUSED', 'ECONNRESET', 'ENOTFOUND', 'EAI_AGAIN', 'EPIPE'])(
    'maps errno %s to a retryable NetworkError',
    (code) => {
      const wrapped = wrapProviderError(transport({ code }), CONTEXT);
      expect(wrapped).toBeInstanceOf(NetworkError);
      expect(wrapped.retryable).toBe(true);
    },
  );

  it.each(['ETIMEDOUT', 'UND_ERR_HEADERS_TIMEOUT'])(
    'maps errno %s to a retryable RequestTimeoutError',
    (code) => {
      const wrapped = wrapProviderError(transport({ code }), CONTEXT);
      expect(wrapped).toBeInstanceOf(RequestTimeoutError);
      expect(wrapped.retryable).toBe(true);
    },
  );

  it('maps an AbortSignal timeout by its DOMException name', () => {
    const wrapped = wrapProviderError(new DOMException('aborted', 'TimeoutError'), CONTEXT);
    expect(wrapped).toBeInstanceOf(RequestTimeoutError);
    expect(wrapped.retryable).toBe(true);
  });

  it('maps a 408 to RequestTimeoutError', () => {
    expect(wrapProviderError(makeAPICallError(408, 'too slow'), CONTEXT)).toBeInstanceOf(
      RequestTimeoutError,
    );
  });

  it('finds a transport failure nested in the cause chain', () => {
    const nested = Object.assign(new Error('fetch failed'), {
      cause: Object.assign(new Error('inner'), { code: 'ECONNREFUSED' }),
    });

    expect(wrapProviderError(nested, CONTEXT)).toBeInstanceOf(NetworkError);
  });
});

describe('wrapProviderError — unusable model output is our fault, not the dependency’s', () => {
  it('maps a schema type-validation failure to LLMOutputProcessingError', () => {
    const err = new TypeValidationError({ value: { nope: true }, cause: new Error('bad shape') });
    const wrapped = wrapProviderError(err, CONTEXT);

    expect(wrapped).toBeInstanceOf(LLMOutputProcessingError);
    expect(wrapped).not.toBeInstanceOf(DependencyError);
    // Sampling variance, so it resamples immediately rather than backing off.
    expect(wrapped.retryable).toBe(true);
  });

  it('maps unparseable JSON to LLMOutputProcessingError', () => {
    const err = new JSONParseError({ text: '{"a":', cause: new Error('unexpected end') });
    expect(wrapProviderError(err, CONTEXT)).toBeInstanceOf(LLMOutputProcessingError);
  });

  it('outranks a status code carried alongside it', () => {
    const parse = new JSONParseError({ text: 'nope', cause: new Error('bad') });
    const wrapped = wrapProviderError(
      Object.assign(makeAPICallError(500, 'server'), { cause: parse }),
      CONTEXT,
    );

    expect(wrapped).toBeInstanceOf(LLMOutputProcessingError);
  });
});

describe('wrapProviderError — structured diagnostics from the provider', () => {
  const withHeaders = (headers: Record<string, string>, status = 429) =>
    new APICallError({
      message: 'rate limited',
      url: 'https://api.example.com/v1/chat',
      requestBodyValues: {},
      statusCode: status,
      responseHeaders: headers,
      responseBody: '',
      isRetryable: true,
    });

  it('reads retryAfterMs from the retry-after header, converting seconds', () => {
    const wrapped = wrapProviderError(withHeaders({ 'retry-after': '3' }), CONTEXT) as RateLimitError;
    expect(wrapped.retryAfterMs).toBe(3000);
  });

  it('reads retryAfterMs from retry-after-ms when present', () => {
    const wrapped = wrapProviderError(
      withHeaders({ 'retry-after-ms': '1500' }),
      CONTEXT,
    ) as RateLimitError;
    expect(wrapped.retryAfterMs).toBe(1500);
  });

  it('leaves retryAfterMs null when the provider sent no hint', () => {
    const wrapped = wrapProviderError(withHeaders({}), CONTEXT) as RateLimitError;
    expect(wrapped.retryAfterMs).toBeNull();
  });

  it('reads requestId from the response headers, which is where providers put it', () => {
    const wrapped = wrapProviderError(
      withHeaders({ 'x-request-id': 'req_abc123' }, 500),
      CONTEXT,
    ) as DependencyError;
    expect(wrapped.requestId).toBe('req_abc123');
  });
});

describe('wrapProviderError — classification boundaries', () => {
  const withCode = (code: string) => Object.assign(new Error('boom'), { code });

  it.each(['EHOSTUNREACH', 'ENETUNREACH'])(
    'maps host/net unreachable errno %s to NetworkError',
    (code) => {
      expect(wrapProviderError(withCode(code), CONTEXT)).toBeInstanceOf(NetworkError);
    },
  );

  it('maps UND_ERR_BODY_TIMEOUT to RequestTimeoutError', () => {
    expect(wrapProviderError(withCode('UND_ERR_BODY_TIMEOUT'), CONTEXT)).toBeInstanceOf(
      RequestTimeoutError,
    );
  });

  it('maps an AbortError name to RequestTimeoutError', () => {
    const aborted = Object.assign(new Error('aborted'), { name: 'AbortError' });
    expect(wrapProviderError(aborted, CONTEXT)).toBeInstanceOf(RequestTimeoutError);
  });

  // An errno we do not recognise must fall to the catch-all, not be guessed at.
  it.each(['EACCES', 'ENOENT', 'EWHATEVER'])('does not treat errno %s as transport', (code) => {
    const wrapped = wrapProviderError(withCode(code), CONTEXT);
    expect(wrapped).toBeInstanceOf(LLMProviderError);
    expect(wrapped).not.toBeInstanceOf(NetworkError);
    expect(wrapped).not.toBeInstanceOf(RequestTimeoutError);
  });
});

describe('wrapProviderError — hostile inputs', () => {
  it.each([null, undefined, 0, false])('survives a thrown %s', (thrown) => {
    const wrapped = wrapProviderError(thrown, CONTEXT);
    expect(wrapped).toBeInstanceOf(LLMProviderError);
  });

  it('terminates on a self-referencing cause chain', () => {
    const loop = new Error('round and round') as Error & { cause?: unknown };
    loop.cause = loop;

    expect(wrapProviderError(loop, CONTEXT)).toBeInstanceOf(LLMProviderError);
  });
});

describe('wrapProviderError — retry-after parsing', () => {
  const withHeader = (headers: Record<string, string>) =>
    new APICallError({
      message: 'rate limited',
      url: 'https://api.example.com/v1/chat',
      requestBodyValues: {},
      statusCode: 429,
      responseHeaders: headers,
      responseBody: '',
    });

  // Retry-After may legally be an HTTP-date, which we cannot use as a delay.
  it('ignores a non-numeric Retry-After rather than emitting NaN', () => {
    const wrapped = withHeader({ 'retry-after': 'Wed, 21 Oct 2026 07:28:00 GMT' });
    expect((wrapProviderError(wrapped, CONTEXT) as RateLimitError).retryAfterMs).toBeNull();
  });

  it('prefers retry-after seconds over retry-after-ms when both are present', () => {
    const wrapped = withHeader({ 'retry-after': '2', 'retry-after-ms': '9999' });
    expect((wrapProviderError(wrapped, CONTEXT) as RateLimitError).retryAfterMs).toBe(2000);
  });

  it('rounds fractional seconds to whole milliseconds', () => {
    const wrapped = withHeader({ 'retry-after': '0.25' });
    expect((wrapProviderError(wrapped, CONTEXT) as RateLimitError).retryAfterMs).toBe(250);
  });
});

describe('wrapProviderError — requestId header fallbacks', () => {
  const withHeaders = (headers: Record<string, string>) =>
    new APICallError({
      message: 'server error',
      url: 'https://api.example.com/v1/chat',
      requestBodyValues: {},
      statusCode: 500,
      responseHeaders: headers,
      responseBody: '',
    });

  it.each([
    ['x-request-id', 'req_x'],
    ['request-id', 'req_plain'],
    ['x-amzn-requestid', 'req_amzn'],
  ])('reads %s', (header, value) => {
    const wrapped = wrapProviderError(withHeaders({ [header]: value }), CONTEXT) as DependencyError;
    expect(wrapped.requestId).toBe(value);
  });

  it('is null when no known header is present', () => {
    const wrapped = wrapProviderError(withHeaders({ 'x-other': 'nope' }), CONTEXT) as DependencyError;
    expect(wrapped.requestId).toBeNull();
  });
});

describe('wrapProviderError — provider errors without response headers', () => {
  // responseHeaders is optional on APICallError, so every header read must
  // tolerate its absence rather than throwing while classifying an error.
  const headerless = new APICallError({
    message: 'rate limited',
    url: 'https://api.example.com/v1/chat',
    requestBodyValues: {},
    statusCode: 429,
    responseBody: '',
  });

  it('classifies without crashing', () => {
    expect(wrapProviderError(headerless, CONTEXT)).toBeInstanceOf(RateLimitError);
  });

  it('leaves retryAfterMs and requestId null', () => {
    const wrapped = wrapProviderError(headerless, CONTEXT) as RateLimitError;
    expect(wrapped.retryAfterMs).toBeNull();
    expect(wrapped.requestId).toBeNull();
  });

  it('ignores a non-numeric retry-after-ms', () => {
    const bad = new APICallError({
      message: 'rate limited',
      url: 'https://api.example.com/v1/chat',
      requestBodyValues: {},
      statusCode: 429,
      responseHeaders: { 'retry-after-ms': 'soon' },
      responseBody: '',
    });

    expect((wrapProviderError(bad, CONTEXT) as RateLimitError).retryAfterMs).toBeNull();
  });
});
