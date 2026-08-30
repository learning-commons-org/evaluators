import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TelemetryClient } from '../../../src/telemetry/client.js';
import type { TelemetryConfig, TelemetryEvent } from '../../../src/telemetry/types.js';
import type { Logger } from '../../../src/logger.js';

/**
 * The telemetry client had no tests of its own — every evaluator suite mocks it away. Its
 * whole contract is negative: it must never throw into an evaluation, never block one, and
 * never log noise for failures that are expected. None of that was covered.
 */

/** A complete event, so a required field added to the type shows up here as a build error. */
const EVENT: TelemetryEvent = {
  timestamp: '2026-08-29T00:00:00.000Z',
  sdk_version: '0.8.0',
  evaluator_type: 'student_facing_text.ela_reading.vocabulary_complexity',
  status: 'success',
  latency_ms: 1234,
  text_length_chars: 512,
  provider: 'google:gemini-2.5-flash',
};

let logger: Logger;
let fetchMock: ReturnType<typeof vi.fn>;

function makeClient(overrides: Partial<TelemetryConfig> = {}): TelemetryClient {
  return new TelemetryClient({
    enabled: true,
    endpoint: 'https://telemetry.example/v1/events',
    clientId: 'client-abc',
    logger,
    ...overrides,
  });
}

beforeEach(() => {
  logger = { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() };
  fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, statusText: 'OK' });
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('TelemetryClient.send', () => {
  it('posts the event as JSON to the configured endpoint', async () => {
    await makeClient().send(EVENT);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    // A successful send is silent; warning here would fire on every evaluation.
    expect(logger.warn).not.toHaveBeenCalled();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('https://telemetry.example/v1/events');
    expect(init.method).toBe('POST');
    // Byte-for-byte: the collector's schema is the wire format, so a field silently
    // dropped or renamed in transit is the failure this catches.
    expect(JSON.parse(init.body)).toEqual(EVENT);
    expect(init.body).toBe(JSON.stringify(EVENT));
  });

  it('identifies the client and declares the content type', async () => {
    await makeClient().send(EVENT);

    expect(fetchMock.mock.calls[0][1].headers).toEqual({
      'Content-Type': 'application/json',
      'X-Client-ID': 'client-abc',
    });
  });

  it('sends no API key header when none is configured', async () => {
    // Identified telemetry is opt-in, so an absent key must stay absent rather than
    // becoming an empty or "undefined" header.
    await makeClient().send(EVENT);

    expect(fetchMock.mock.calls[0][1].headers).not.toHaveProperty('X-API-Key');
  });

  it('attaches the API key when one is configured', async () => {
    await makeClient({ learningCommonsApiKey: 'partner-key' }).send(EVENT);

    expect(fetchMock.mock.calls[0][1].headers['X-API-Key']).toBe('partner-key');
  });

  it('gives up rather than hanging on a slow network', async () => {
    // Without a signal a stalled collector would keep an evaluation's process alive.
    await makeClient().send(EVENT);

    expect(fetchMock.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
  });

  it('does nothing at all when telemetry is disabled', async () => {
    await makeClient({ enabled: false }).send(EVENT);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(logger.warn).not.toHaveBeenCalled();
  });

  it('warns with the status when the collector rejects the event', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 503, statusText: 'Service Unavailable' });

    await makeClient().send(EVENT);

    expect(vi.mocked(logger.warn).mock.calls[0][0]).toContain('503 Service Unavailable');
  });

  it('resolves rather than throwing when the request fails outright', async () => {
    // This is the whole point of the module: telemetry must never fail an evaluation.
    fetchMock.mockRejectedValue(new Error('getaddrinfo ENOTFOUND'));

    await expect(makeClient().send(EVENT)).resolves.toBeUndefined();
    expect(vi.mocked(logger.warn).mock.calls[0][0]).toContain('getaddrinfo ENOTFOUND');
  });

  it.each(['TimeoutError', 'AbortError'])('stays quiet about an expected %s', async (name) => {
    // A slow network is not a defect worth a line in a partner's logs on every evaluation.
    const error = new Error('aborted');
    error.name = name;
    fetchMock.mockRejectedValue(error);

    await expect(makeClient().send(EVENT)).resolves.toBeUndefined();
    expect(logger.warn).not.toHaveBeenCalled();
  });

  it('swallows a rejection that is not an Error at all', async () => {
    // `fetch` polyfills and mocks have been known to reject with strings.
    fetchMock.mockRejectedValue('not an error object');

    await expect(makeClient().send(EVENT)).resolves.toBeUndefined();
    expect(logger.warn).not.toHaveBeenCalled();
  });
});
