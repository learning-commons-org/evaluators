import { describe, it, expect } from 'vitest';
import { APICallError } from 'ai';
import { wrapProviderError, ConfigurationError, AuthenticationError, RateLimitError, APIError } from '../../../src/errors.js';

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

describe('wrapProviderError — model-not-found detection', () => {
  it('returns ConfigurationError for a 404 APICallError', () => {
    const err = makeAPICallError(404, "The model 'gpt-fake' does not exist");
    expect(wrapProviderError(err)).toBeInstanceOf(ConfigurationError);
  });

  it('returns ConfigurationError for a 400 APICallError with model-related message', () => {
    const err = makeAPICallError(400, 'model gpt-fake-99 does not exist or you do not have access');
    expect(wrapProviderError(err)).toBeInstanceOf(ConfigurationError);
  });

  it('does NOT return ConfigurationError for a 400 without model-related message', () => {
    const err = makeAPICallError(400, 'Invalid request: missing required field');
    expect(wrapProviderError(err)).not.toBeInstanceOf(ConfigurationError);
    expect(wrapProviderError(err)).toBeInstanceOf(APIError);
  });

  it('returns ConfigurationError for a plain Error with statusCode: 404 property', () => {
    const err = Object.assign(new Error("The model 'gpt-fake' does not exist"), { statusCode: 404 });
    expect(wrapProviderError(err)).toBeInstanceOf(ConfigurationError);
  });
});

describe('wrapProviderError — existing error type detection (regression)', () => {
  it('returns AuthenticationError for 401', () => {
    const err = makeAPICallError(401, 'Invalid API key');
    expect(wrapProviderError(err)).toBeInstanceOf(AuthenticationError);
  });

  it('returns AuthenticationError for 403', () => {
    const err = makeAPICallError(403, 'Forbidden');
    expect(wrapProviderError(err)).toBeInstanceOf(AuthenticationError);
  });

  it('returns RateLimitError for 429', () => {
    const err = makeAPICallError(429, 'Rate limit exceeded');
    expect(wrapProviderError(err)).toBeInstanceOf(RateLimitError);
  });

  it('returns generic APIError for 500', () => {
    const err = makeAPICallError(500, 'Internal server error');
    expect(wrapProviderError(err)).toBeInstanceOf(APIError);
    expect(wrapProviderError(err)).not.toBeInstanceOf(ConfigurationError);
  });
});
