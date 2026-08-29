import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { runPreprocessingStep } from '../../../src/features/preprocessing.js';
import CONFIG from '../../../../../evals/student-facing-text/ela-reading/purpose-clarity/config.json';
import { PurposeClarityEvaluator } from '../../../src/evaluators/student-facing-text/ela-reading/purpose-clarity.js';
import { Provider } from '../../../src/evaluators/base.js';
import type { LLMProvider } from '../../../src/providers/base.js';

const STEP = CONFIG.steps[0];

const createMockProvider = (config?: { type?: string; model?: string }): LLMProvider => ({
  label: config?.type && config?.model ? `${config.type}:${config.model}` : 'mock:model',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
});

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    createProvider: vi.fn((config) => createMockProvider(config)),
  };
});

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class MockTelemetryClient {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

const MOCK_RESPONSE = {
  data: {
    complexity_score: 'slightly_complex' as const,
    reasoning: 'The purpose is explicitly stated and straightforward.',
    details: {
      detailed_summary: [
        {
          factor: 'Explicit purpose',
          description: 'Text opens with a clear topic statement.',
          effect_on_complexity_dimension: 'Makes purpose immediately identifiable.',
        },
      ],
      adjustment_and_scaffolding: [
        { scaffolding_need: 'None required', suggestion: 'Text is accessible as-is.' },
      ],
      recommended_use_cases: [
        { opportunity: 'Independent reading', suggestion: 'Suitable for self-directed reading at grade level.' },
      ],
    },
  },
  model: STEP.model.name,
  usage: { inputTokens: 200, outputTokens: 120 },
  latencyMs: 800,
};

// --- Constructor ---

const FK_TEXT = 'The quick brown fox jumps over the lazy dog.';

describe('PurposeClarityEvaluator - Constructor', () => {
  it('throws when Google API key is missing', () => {
    expect(() => new PurposeClarityEvaluator({ googleApiKey: '' })).toThrow(
      /Missing required credential: googleApiKey/,
    );
  });
});

// --- Metadata derives from config.json ---

describe('PurposeClarityEvaluator - Metadata', () => {
  it('derives id from config.json', () => {
    expect(PurposeClarityEvaluator.metadata.id).toBe(CONFIG.evaluator.id);
  });

  it('derives name from config.json', () => {
    expect(PurposeClarityEvaluator.metadata.name).toBe(CONFIG.evaluator.name);
  });

  it('derives description from config.json', () => {
    expect(PurposeClarityEvaluator.metadata.description).toBe(CONFIG.evaluator.description);
  });

  it('defaultProviders includes Google', () => {
    expect(PurposeClarityEvaluator.metadata.defaultProviders).toContain(Provider.Google);
  });

  it('defaultProviders does not include OpenAI', () => {
    expect(PurposeClarityEvaluator.metadata.defaultProviders).not.toContain(Provider.OpenAI);
  });

  it('supports integer grade levels 3–12', () => {
    expect(PurposeClarityEvaluator.metadata.supportedGrades).toEqual(
      ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'],
    );
  });
});

// --- LLM call contract ---

describe('PurposeClarityEvaluator - LLM call contract', () => {
  let evaluator: PurposeClarityEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();
    evaluator = new PurposeClarityEvaluator({ googleApiKey: 'test-key', telemetry: false });
    // @ts-expect-error accessing private for testing
    mockProvider = evaluator.provider;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('calls provider once with model from config.json', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_RESPONSE);

    await evaluator.evaluate({ text: 'When going to the beach, find out which ones have lifeguards.', grade_level: '3' });

    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(1);
  });

  it('passes temperature from config.json', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_RESPONSE);

    await evaluator.evaluate({ text: 'When going to the beach, find out which ones have lifeguards.', grade_level: '3' });

    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.temperature).toBe(STEP.generation.temperature);
    expect(call.temperature).toBe(0);
  });

  it('includes text in user prompt', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_RESPONSE);
    const text = 'Pins are made of either brass or iron wire.';

    await evaluator.evaluate({ text: text, grade_level: '4' });

    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.messages[1].content).toContain(text);
  });

  it('includes grade_level (not grade) in user prompt', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_RESPONSE);

    await evaluator.evaluate({ text: 'Some sample text for testing purposes.', grade_level: '7' });

    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    expect(call.messages[1].content).toContain('7');
    expect(call.messages[1].content).not.toContain('{grade_level}');
  });

  it('includes computed fk_score in user prompt', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_RESPONSE);

    await evaluator.evaluate({ text: FK_TEXT, grade_level: '5' });

    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0][0];
    // The value the contract's own preprocessing produces, not just "some number" — the
    // grade level alone satisfied that, so the assertion held with preprocessing off.
    const fkStep = CONFIG.preprocessing.find((p) => p.id === 'fk_score')!;
    const expected = String(runPreprocessingStep(FK_TEXT, fkStep.implementation.typescript));

    expect(call.messages[1].content).toContain(expected);
    expect(call.messages[1].content).not.toContain('{fk_score}');
    // The declared inputs, at the point they reach the model.
    expect(call.messages[1].content).toContain(FK_TEXT);
    expect(call.messages[1].content).not.toContain('{text}');
    expect(call.messages[1].content).not.toContain('{grade_level}');
  });

  it('maps LLM response to result shape', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_RESPONSE);

    const result = await evaluator.evaluate({ text: 'When going to the beach, find out which ones have lifeguards.', grade_level: '3' });

    expect(result.result.complexity_score).toBe('slightly_complex');
    expect(result.result.reasoning).toBe(MOCK_RESPONSE.data.reasoning);
    expect(result.metadata.model).toBe(`${STEP.model.provider}:${STEP.model.name}`);
    expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
    expect(result.metadata.tokenUsage.inputTokens).toBe(200);
    expect(result.metadata.tokenUsage.outputTokens).toBe(120);
    expect(result.result).toEqual(MOCK_RESPONSE.data);
    expect(result.result.details.detailed_summary).toBeInstanceOf(Array);
    expect(result.result.details.adjustment_and_scaffolding).toBeInstanceOf(Array);
    expect(result.result.details.recommended_use_cases).toBeInstanceOf(Array);
  });

  it('reflects modelOverride in metadata.model', async () => {
    const overrideEvaluator = new PurposeClarityEvaluator({
      anthropicApiKey: 'test-key',
      modelOverride: { provider: Provider.Anthropic, model: 'claude-haiku-4-5-20251001' },
      telemetry: false,
    });
    // @ts-expect-error accessing private for testing
    const overrideProvider: LLMProvider = overrideEvaluator.provider;

    vi.mocked(overrideProvider.generateStructured).mockResolvedValue({
      data: {
        complexity_score: 'slightly_complex' as const,
        reasoning: 'Simple purpose.',
        details: {
          detailed_summary: [],
          adjustment_and_scaffolding: [],
          recommended_use_cases: [],
        },
      },
      model: 'claude-haiku-4-5-20251001',
      usage: { inputTokens: 100, outputTokens: 50 },
      latencyMs: 300,
    });

    const result = await overrideEvaluator.evaluate({ text: 'When going to the beach, find out which ones have lifeguards.', grade_level: '3' });

    expect(result.metadata.model).toBe('anthropic:claude-haiku-4-5-20251001');
  });

  it('accepts string grade (consistent with all other evaluators)', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_RESPONSE);

    await expect(
      evaluator.evaluate({ text: 'Some text long enough to evaluate.', grade_level: '5' }),
    ).resolves.toBeDefined();
  });
});

// --- Validation ---

describe('PurposeClarityEvaluator - Validation', () => {
  let evaluator: PurposeClarityEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();
    evaluator = new PurposeClarityEvaluator({ googleApiKey: 'test-key', telemetry: false });
    // @ts-expect-error accessing private for testing
    mockProvider = evaluator.provider;
  });

  it('rejects grade below 3', async () => {
    await expect(evaluator.evaluate({ text: 'Some text.', grade_level: '2' })).rejects.toThrow(/Invalid grade/);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects grade above 12', async () => {
    await expect(evaluator.evaluate({ text: 'Some text.', grade_level: '13' })).rejects.toThrow(/Invalid grade/);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects empty text', async () => {
    await expect(evaluator.evaluate({ text: '', grade_level: '5' })).rejects.toThrow();
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects whitespace-only text', async () => {
    await expect(evaluator.evaluate({ text: '   ', grade_level: '5' })).rejects.toThrow(/empty or contain only whitespace/);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('propagates LLM errors', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValue(new Error('API timeout'));

    await expect(
      evaluator.evaluate({ text: 'The beach is a fun place to swim and play in the sun.', grade_level: '4' }),
    ).rejects.toThrow('API timeout');
  });
});
