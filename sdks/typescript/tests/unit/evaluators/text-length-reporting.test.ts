import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MeaningDirectnessEvaluator } from '../../../src/evaluators/meaning-directness.js';
import { VALIDATION_LIMITS } from '../../../src/evaluators/base.js';
import { InputValidationError } from '../../../src/errors.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * One length, measured on the caller's text, used for the bounds, the log line,
 * the telemetry event and the prompt. The SDK does not normalize input: padding
 * is the caller's to remove, not ours to repair behind their back.
 */

const mockProvider: LLMProvider = {
  label: 'google:gemini-3-flash-preview',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
};

vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn(() => mockProvider),
}));

// Captures what would go on the wire, rather than the argument passed in.
const sent: Array<Record<string, unknown>> = [];
vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class MockTelemetryClient {
    send = vi.fn(async (event: Record<string, unknown>) => {
      sent.push(event);
    });
  },
}));

const CORE = 'The author sustains irony throughout to critique civilized society.';
const evaluator = () => new MeaningDirectnessEvaluator({ googleApiKey: 'k' });

beforeEach(() => {
  vi.clearAllMocks();
  sent.length = 0;
  vi.mocked(mockProvider.generateStructured).mockResolvedValue({
    data: { complexity_level: 'Very complex', reasoning: 'irony' },
    model: 'gemini-3-flash-preview',
    usage: { inputTokens: 10, outputTokens: 5 },
    latencyMs: 1,
  });
});

describe('text_length_chars is the length of what the caller sent', () => {
  it('counts padding, because the model receives it too', async () => {
    const padded = `\n\n   ${CORE}   \n\n`;
    await evaluator().evaluate(padded, '10');

    expect(sent).toHaveLength(1);
    expect(sent[0].text_length_chars).toBe(padded.length);
    expect(sent[0].text_length_chars).not.toBe(CORE.length);
  });

  it('reports the same length on the failure path', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValue(new Error('upstream'));
    const padded = `   ${CORE}   `;

    await evaluator().evaluate(padded, '10').catch(() => undefined);

    expect(sent).toHaveLength(1);
    expect(sent[0].status).toBe('error');
    expect(sent[0].text_length_chars).toBe(padded.length);
  });

  // The reported number has to describe the payload, so it must agree with what
  // the prompt actually carried.
  it('agrees with the text sent to the model', async () => {
    const padded = `   ${CORE}   `;
    await evaluator().evaluate(padded, '10');

    const prompt = vi.mocked(mockProvider.generateStructured).mock.calls[0][0].messages
      .map((m) => m.content)
      .join('');
    expect(prompt).toContain(padded);
    expect(sent[0].text_length_chars).toBe(padded.length);
  });
});

describe('validation measures the caller\'s text, unmodified', () => {
  it('is 10,000 characters', () => {
    expect(VALIDATION_LIMITS.MAX_TEXT_LENGTH).toBe(10_000);
  });

  it('accepts text exactly at the bound', async () => {
    const atBound = 'a'.repeat(VALIDATION_LIMITS.MAX_TEXT_LENGTH);
    await expect(evaluator().evaluate(atBound, '10')).resolves.toBeDefined();
  });

  it('rejects one character past the bound', async () => {
    const overBound = 'a'.repeat(VALIDATION_LIMITS.MAX_TEXT_LENGTH + 1);
    await expect(evaluator().evaluate(overBound, '10')).rejects.toThrow(InputValidationError);
  });

  // The deliberate consequence: padding is not silently absorbed. Text that
  // only fits once trimmed is rejected, and the caller is told the real length.
  it('rejects text pushed past the bound by padding alone', async () => {
    const atBound = 'a'.repeat(VALIDATION_LIMITS.MAX_TEXT_LENGTH);
    await expect(evaluator().evaluate(`  ${atBound}  `, '10')).rejects.toThrow(
      /Maximum length is 10,000 characters, received 10,004 characters/
    );
  });

  // The minimum carries no product opinion: it excludes empty input and nothing
  // else, so padding has nothing to sneak past. Meaningful minimums belong to
  // each evaluator's input schema.
  it('has a minimum of 1', () => {
    expect(VALIDATION_LIMITS.MIN_TEXT_LENGTH).toBe(1);
  });

  it('accepts a single character', async () => {
    await expect(evaluator().evaluate('a', '10')).resolves.toBeDefined();
  });

  // Trim survives as a validity test only: whitespace-only is rejected outright
  // rather than being measured as content.
  it.each(['   ', '\n\t\n', ' '.repeat(VALIDATION_LIMITS.MIN_TEXT_LENGTH + 5)])(
    'rejects whitespace-only input (%j)',
    async (blank) => {
      await expect(evaluator().evaluate(blank, '10')).rejects.toThrow(
        'Text cannot be empty or contain only whitespace'
      );
    }
  );
});
