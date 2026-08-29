import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MeaningDirectnessEvaluator } from '../../../src/evaluators/meaning-directness.js';
import { InputValidationError } from '../../../src/errors.js';

/**
 * §4: "Validation runs before every LLM call, inside the error-handling boundary, so
 * failures are captured in telemetry as `error` events."
 *
 * Regression guard. Making the non-object guard reachable meant moving validation ahead
 * of the input destructuring; done carelessly that also moves it outside the try, and
 * validation failures stop being reported. Nothing caught that — the only evidence was
 * a comment left describing the old control flow.
 */

const sent = vi.fn();

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = sent;
  },
}));

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn(() => ({
      label: 'google:stub',
      generateStructured: vi.fn(),
      generateText: vi.fn(),
    })),
  };
});

const evaluator = () => new MeaningDirectnessEvaluator({ googleApiKey: 'k' });

beforeEach(() => {
  sent.mockClear();
  sent.mockResolvedValue(undefined);
});

describe('a validation failure is telemetered', () => {
  it('reports an error event, naming the error class', async () => {
    await expect(
      evaluator().evaluate({ text: 'too short', grade_level: '5' }),
    ).rejects.toThrow(InputValidationError);

    expect(sent).toHaveBeenCalledTimes(1);
    expect(sent.mock.calls[0][0]).toMatchObject({
      status: 'error',
      error_code: 'InputValidationError',
    });
  });

  it('reports an error event even when the input is not an object', async () => {
    // The path that used to raise a bare TypeError before any telemetry ran.
    await expect(evaluator().evaluate(null as never)).rejects.toThrow(InputValidationError);

    expect(sent).toHaveBeenCalledTimes(1);
    expect(sent.mock.calls[0][0]).toMatchObject({
      status: 'error',
      error_code: 'InputValidationError',
    });
  });

  it('makes no LLM call when validation fails', async () => {
    await expect(evaluator().evaluate({ text: 'x', grade_level: '5' })).rejects.toThrow(
      InputValidationError,
    );

    // §4 puts validation before every LLM call; a rejected input must cost nothing.
    expect(sent.mock.calls[0][0].token_usage).toBeUndefined();
  });
});
