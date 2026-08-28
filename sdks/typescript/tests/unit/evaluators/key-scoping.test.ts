import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MathStandardsAlignmentEvaluator } from '../../../src/evaluators/math/standards-alignment.js';
import { MeaningDirectnessEvaluator } from '../../../src/evaluators/meaning-directness.js';
import { ConfigurationError } from '../../../src/errors.js';
import type { LLMProvider } from '../../../src/providers/base.js';

const mockProvider: LLMProvider = {
  label: 'google:gemini-3-flash-preview',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
};

vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn(() => mockProvider),
}));

// The real client, so header assembly is exercised rather than mocked away.
const fetchMock = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockResolvedValue({ ok: true, status: 200, text: () => Promise.resolve('') });
  vi.mocked(mockProvider.generateStructured).mockResolvedValue({
    data: { complexity_level: 'Very complex', reasoning: 'why' },
    model: 'gemini-3-flash-preview',
    usage: { inputTokens: 1, outputTokens: 1 },
    latencyMs: 1,
  });
});

const TEXT = 'The author sustains irony throughout to critique civilized society.';

async function telemetryHeaders(
  telemetry: ConstructorParameters<typeof MeaningDirectnessEvaluator>[0]['telemetry']
) {
  await new MeaningDirectnessEvaluator({
    googleApiKey: 'k',
    learningCommonsApiKey: 'lc-key',
    telemetry,
  }).evaluate(TEXT, '10');

  // Telemetry is fire-and-forget, so let the microtask queue drain.
  await new Promise((resolve) => setImmediate(resolve));
  return (fetchMock.mock.calls[0]?.[1]?.headers ?? {}) as Record<string, string>;
}

describe('credentials are purpose-scoped', () => {
  // The core of the change: a key given for API access must not become an
  // identity. Previously the KG key silently authenticated telemetry too.
  it('does not authenticate telemetry with the top-level API key', async () => {
    const headers = await telemetryHeaders(true);

    expect(fetchMock).toHaveBeenCalled();
    expect(headers).not.toHaveProperty('X-API-Key');
    expect(Object.values(headers)).not.toContain('lc-key');
  });

  it('authenticates telemetry only when the key is declared under telemetry', async () => {
    const headers = await telemetryHeaders({ learningCommonsApiKey: 'lc-key' });

    expect(headers['X-API-Key']).toBe('lc-key');
  });

  // Anonymous events still identify the install, just not the partner.
  it('sends the client id either way', async () => {
    expect(await telemetryHeaders(true)).toHaveProperty('X-Client-ID');
  });

  it('sends nothing at all when telemetry is off', async () => {
    await telemetryHeaders(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('MathStandardsAlignmentEvaluator key requirement', () => {
  it('requires the Learning Commons key by name', () => {
    expect(() => new MathStandardsAlignmentEvaluator({ anthropicApiKey: 'sk-ant' })).toThrow(
      ConfigurationError
    );
    expect(() => new MathStandardsAlignmentEvaluator({ anthropicApiKey: 'sk-ant' })).toThrow(
      /learningCommonsApiKey/
    );
  });

  // A telemetry-scoped key authorizes telemetry, not the Knowledge Graph — the
  // fallback used to run the other way and made this construction succeed.
  it('is not satisfied by a telemetry-scoped key', () => {
    expect(
      () =>
        new MathStandardsAlignmentEvaluator({
          anthropicApiKey: 'sk-ant',
          telemetry: { learningCommonsApiKey: 'lc-key' },
        })
    ).toThrow(ConfigurationError);
  });

  it('constructs with the top-level key', () => {
    expect(
      () =>
        new MathStandardsAlignmentEvaluator({
          anthropicApiKey: 'sk-ant',
          learningCommonsApiKey: 'lc-key',
        })
    ).not.toThrow();
  });
});
