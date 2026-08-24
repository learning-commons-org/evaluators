import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  findEvaluationStep,
  findFkImplementation,
  supportedGradesFrom,
} from '../../../src/evaluators/single-step-rubric.js';
import { IntertextualityEvaluator } from '../../../src/evaluators/intertextuality.js';
import type { LLMProvider } from '../../../src/providers/base.js';
import type { Logger } from '../../../src/logger.js';

const createMockProvider = (): LLMProvider => ({
  label: 'mock:model',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
});

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    createProvider: vi.fn(() => createMockProvider()),
  };
});

const mockTelemetrySend = vi.fn();
vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class MockTelemetryClient {
    send = mockTelemetrySend;
  },
}));

const MOCK_RESPONSE = {
  data: {
    complexity_score: 'slightly_complex' as const,
    reasoning: 'Self-contained text.',
    details: {
      detailed_summary: [],
      adjustment_and_scaffolding: [],
      recommended_use_cases: [],
    },
  },
  model: 'mock-model',
  usage: { inputTokens: 200, outputTokens: 120 },
  latencyMs: 800,
};

const TEXT = 'When going to the beach, find out which ones have lifeguards.';

// --- Config helpers ---

describe('findEvaluationStep', () => {
  it('finds the step matching the evaluate_{slug} convention', () => {
    const config = {
      evaluator: { id: 'literacy.gla.example' },
      steps: [{ id: 'evaluate_example' }, { id: 'other_step' }],
    };
    expect(findEvaluationStep(config)).toBe(config.steps[0]);
  });

  it('throws when no step matches the convention', () => {
    const config = {
      evaluator: { id: 'literacy.gla.example' },
      steps: [{ id: 'evaluate_something_else' }],
    };
    expect(() => findEvaluationStep(config)).toThrow(
      'Step "evaluate_example" not found in literacy.gla.example config.json',
    );
  });
});

describe('findFkImplementation', () => {
  const impl = { library: 'text-readability', function: 'fleschKincaidGrade' };

  it('returns the TypeScript implementation of the fk_score step', () => {
    const config = {
      evaluator: { id: 'literacy.gla.example' },
      preprocessing: [{ id: 'fk_score', implementation: { typescript: impl } }],
    };
    expect(findFkImplementation(config)).toBe(impl);
  });

  it('throws when the fk_score step is missing', () => {
    const config = {
      evaluator: { id: 'literacy.gla.example' },
      preprocessing: [{ id: 'other', implementation: { typescript: impl } }],
    };
    expect(() => findFkImplementation(config)).toThrow(
      'fk_score preprocessing step not found in literacy.gla.example config.json',
    );
  });
});

describe('supportedGradesFrom', () => {
  it('expands an inclusive integer range into string grades', () => {
    expect(supportedGradesFrom(3, 6)).toEqual(['3', '4', '5', '6']);
  });

  it('handles a single-grade range', () => {
    expect(supportedGradesFrom(5, 5)).toEqual(['5']);
  });
});

// --- Telemetry resilience (shared engine behavior, exercised via a concrete evaluator) ---

describe('SingleStepRubricEvaluator - Telemetry resilience', () => {
  let evaluator: IntertextualityEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();
    // Telemetry deliberately NOT disabled — these tests exercise the send path.
    evaluator = new IntertextualityEvaluator({ googleApiKey: 'test-key' });
    // @ts-expect-error accessing private for testing
    mockProvider = evaluator.provider;
  });

  it('resolves successfully even when success telemetry send rejects', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_RESPONSE);
    mockTelemetrySend.mockRejectedValue(new Error('telemetry endpoint down'));

    const result = await evaluator.evaluate(TEXT, '3');

    expect(result.score).toBe('Slightly complex');
    // Let the fire-and-forget rejection settle so the .catch guard runs.
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(mockTelemetrySend).toHaveBeenCalledTimes(1);
  });

  it('propagates the original error even when error telemetry send rejects', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValue(new Error('API timeout'));
    mockTelemetrySend.mockRejectedValue(new Error('telemetry endpoint down'));

    await expect(evaluator.evaluate(TEXT, '3')).rejects.toThrow('API timeout');
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(mockTelemetrySend).toHaveBeenCalledTimes(1);
  });

  it('reports UnknownError in telemetry when a non-Error value is thrown', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValue('string rejection');
    mockTelemetrySend.mockResolvedValue(undefined);

    await expect(evaluator.evaluate(TEXT, '3')).rejects.toThrow();

    expect(mockTelemetrySend).toHaveBeenCalledTimes(1);
    expect(mockTelemetrySend.mock.calls[0][0].error_code).toBe('UnknownError');
  });

  it('aggregates stage token usage into error telemetry when failure occurs after the LLM stage', async () => {
    // Force a failure AFTER the LLM stage completes: the post-success logger.info throws.
    const throwingLogger: Logger = {
      debug: vi.fn(),
      info: vi.fn((message: string) => {
        if (message.includes('completed successfully')) throw new Error('logger exploded');
      }),
      warn: vi.fn(),
      error: vi.fn(),
    };
    const loggedEvaluator = new IntertextualityEvaluator({
      googleApiKey: 'test-key',
      logger: throwingLogger,
    });
    // @ts-expect-error accessing private for testing
    const provider: LLMProvider = loggedEvaluator.provider;
    vi.mocked(provider.generateStructured).mockResolvedValue(MOCK_RESPONSE);
    mockTelemetrySend.mockResolvedValue(undefined);

    await expect(loggedEvaluator.evaluate(TEXT, '3')).rejects.toThrow();

    // Two sends: the success telemetry (before the logger threw), then the error telemetry.
    expect(mockTelemetrySend).toHaveBeenCalledTimes(2);
    const errorEvent = mockTelemetrySend.mock.calls[1][0];
    expect(errorEvent.status).toBe('error');
    expect(errorEvent.token_usage).toEqual({ input_tokens: 200, output_tokens: 120 });
    expect(errorEvent.metadata?.stage_details).toHaveLength(1);
  });
});
