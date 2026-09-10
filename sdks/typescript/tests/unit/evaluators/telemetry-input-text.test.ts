import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MeaningDirectnessEvaluator } from '../../../src/evaluators/student-facing-text/ela-reading/meaning-directness.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * Telemetry never carries the evaluated text. `recordInputs` used to opt into
 * sending it and is now a deprecated no-op. These guard both halves: setting it
 * does nothing, and neither the success nor the error path can put the text
 * back on the wire.
 */

const sent = vi.fn();

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = sent;
  },
}));

const provider: LLMProvider = {
  label: 'google:stub',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
};

vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn(() => provider),
}));

const TEXT =
  'The author uses sustained irony throughout to critique the hypocrisy of civilized society.';

const evaluator = () =>
  new MeaningDirectnessEvaluator({
    googleApiKey: 'k',
    // The deprecated no-op, as a 1.0.x caller still writes it.
    telemetry: { recordInputs: true },
  });

beforeEach(() => {
  sent.mockClear();
  sent.mockResolvedValue(undefined);
  vi.mocked(provider.generateStructured).mockReset();
});

describe('telemetry omits the evaluated text', () => {
  it('sends no input_text on success, and ignores a stale recordInputs', async () => {
    vi.mocked(provider.generateStructured).mockResolvedValue({
      data: {
        conventionality_features: ['sustained irony'],
        grade_context: 'Exceeds typical Grade 10 expectations.',
        instructional_insights: 'Pre-teach irony.',
        complexity_score: 'very_complex',
        reasoning: 'Relies on sustained irony.',
      },
      model: 'gemini-3-flash-preview',
      usage: { inputTokens: 250, outputTokens: 120 },
      latencyMs: 900,
    });

    await evaluator().evaluate({ text: TEXT, grade_level: '10' });

    expect(sent).toHaveBeenCalledTimes(1);
    const event = sent.mock.calls[0][0];
    expect(event).not.toHaveProperty('input_text');
    expect(JSON.stringify(event)).not.toContain(TEXT);
    expect(event.text_length_chars).toBe(TEXT.length);
  });

  it('sends no input_text on the error path', async () => {
    vi.mocked(provider.generateStructured).mockRejectedValue(new Error('API timeout'));

    await expect(evaluator().evaluate({ text: TEXT, grade_level: '10' })).rejects.toThrow(
      'API timeout'
    );

    expect(sent).toHaveBeenCalledTimes(1);
    const event = sent.mock.calls[0][0];
    expect(event.status).toBe('error');
    expect(event).not.toHaveProperty('input_text');
    expect(JSON.stringify(event)).not.toContain(TEXT);
  });
});
