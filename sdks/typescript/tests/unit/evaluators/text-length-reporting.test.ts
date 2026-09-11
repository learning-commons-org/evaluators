import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MeaningDirectnessEvaluator } from '../../../src/evaluators/student-facing-text/ela-reading/meaning-directness.js';
import { InputValidationError } from '../../../src/errors.js';
import INPUT_SCHEMA from '../../../../../evals/student-facing-text/ela-reading/meaning-directness/input_schema.json';

/**
 * Text bounds come from the evaluator's own `input_schema.json`, so the numbers here are
 * read from the contract rather than restated. A single global pair would let an
 * evaluator silently accept input its contract rejects, which is what these guard.
 */

const { minLength: MIN, maxLength: MAX } = INPUT_SCHEMA.properties.text;

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn(() => ({
      label: 'google:stub',
      generateStructured: vi.fn(async () => ({
        data: { complexity_score: 'Slightly complex', reasoning: 'r' },
        model: 'stub',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 1,
      })),
      generateText: vi.fn(),
    })),
  };
});

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

const evaluator = () => new MeaningDirectnessEvaluator({ googleApiKey: 'k', telemetry: false });

beforeEach(() => {
  vi.clearAllMocks();
});

describe('text bounds come from the contract', () => {
  it('accepts text exactly at the declared minimum', async () => {
    await expect(
      evaluator().evaluate({ text: 'a'.repeat(MIN), grade_level: '10' }),
    ).resolves.toBeDefined();
  });

  it('rejects text one character under the declared minimum', async () => {
    await expect(
      evaluator().evaluate({ text: 'a'.repeat(MIN - 1), grade_level: '10' }),
    ).rejects.toThrow(`text is too short. Minimum length is ${MIN} characters.`);
  });

  it('accepts text exactly at the declared maximum', async () => {
    await expect(
      evaluator().evaluate({ text: 'a'.repeat(MAX), grade_level: '10' }),
    ).resolves.toBeDefined();
  });

  it('rejects text one character over the declared maximum', async () => {
    await expect(
      evaluator().evaluate({ text: 'a'.repeat(MAX + 1), grade_level: '10' }),
    ).rejects.toThrow(`text is too long. Maximum length is ${MAX} characters.`);
  });
});

describe('text is measured as the caller sent it', () => {
  // Trimming decides only whether the value is blank. Padding that pushes text past the
  // bound is rejected rather than silently trimmed to fit, because the string that is
  // measured is the string that reaches the model.
  it('rejects text pushed past the bound by padding alone', async () => {
    const atBound = 'a'.repeat(MAX);

    await expect(
      evaluator().evaluate({ text: `  ${atBound}  `, grade_level: '10' }),
    ).rejects.toThrow(`text is too long. Maximum length is ${MAX} characters.`);
  });

  it.each(['   ', '\n\t\n', ' '.repeat(MIN + 5)])(
    'rejects whitespace-only input (%j)',
    async (blank) => {
      await expect(evaluator().evaluate({ text: blank, grade_level: '10' })).rejects.toThrow(
        'text cannot be empty or contain only whitespace',
      );
    },
  );

  it('reports a blank input as a validation failure, not a provider one', async () => {
    await expect(evaluator().evaluate({ text: '   ', grade_level: '10' })).rejects.toThrow(
      InputValidationError,
    );
  });
});
