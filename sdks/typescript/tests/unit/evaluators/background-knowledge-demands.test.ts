import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { BackgroundKnowledgeDemandsEvaluator } from '../../../src/evaluators/background-knowledge-demands.js';
import { Provider } from '../../../src/evaluators/base.js';
import type { LLMProvider } from '../../../src/providers/base.js';

// Mock providers
const createMockProvider = (config?: { type?: string; model?: string }): LLMProvider => ({
  label: config?.type && config?.model ? `${config.type}:${config.model}` : 'mock:model',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
});

vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn((config) => createMockProvider(config)),
}));

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class MockTelemetryClient {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

describe('BackgroundKnowledgeDemandsEvaluator - Constructor Validation', () => {
  it('should throw with specific message when Google API key is missing', () => {
    expect(() => new BackgroundKnowledgeDemandsEvaluator({ googleApiKey: '' })).toThrow(
      `Google API key is required for ${BackgroundKnowledgeDemandsEvaluator.metadata.name}. Pass googleApiKey in config.`
    );
  });
});

describe('BackgroundKnowledgeDemandsEvaluator - Metadata', () => {
  it('should have correct metadata', () => {
    expect(BackgroundKnowledgeDemandsEvaluator.metadata.id).toBe('student_facing_text.ela_reading.background_knowledge_demands');
    expect(BackgroundKnowledgeDemandsEvaluator.metadata.idHistory).toContain('subject-matter-knowledge');
    expect(BackgroundKnowledgeDemandsEvaluator.metadata.defaultProviders).toEqual(['google']);
    expect(BackgroundKnowledgeDemandsEvaluator.metadata.supportedGrades).toEqual([
      '3', '4', '5', '6', '7', '8', '9', '10', '11', '12',
    ]);
  });
});

describe('BackgroundKnowledgeDemandsEvaluator - Evaluation Flow', () => {
  let evaluator: BackgroundKnowledgeDemandsEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();

    evaluator = new BackgroundKnowledgeDemandsEvaluator({
      googleApiKey: 'test-google-key',
      telemetry: false,
    });

    // @ts-expect-error Accessing private property for testing
    mockProvider = evaluator.provider;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should map LLM response to result, call provider once, include text+grade in prompt, use temperature 0', async () => {
    const testText = 'Hydraulic propulsion works by sucking water at the bow and forcing it sternward.';
    const testGrade = '10';

    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      data: {
        identified_topics: ['hydraulics', 'propulsion', 'physics'],
        curriculum_check: 'Specialized high school level — hydraulics is not standard K-8 curriculum.',
        assumptions_and_scaffolding: 'Author assumes knowledge of fluid dynamics and mechanical engineering.',
        friction_analysis: 'Difficulty comes from actual knowledge demands, not just vocabulary.',
        complexity_score: 'Very complex',
        reasoning: 'The text requires specialized knowledge of hydraulic systems.',
      },
      model: 'gemini-3-flash-preview',
      usage: { inputTokens: 200, outputTokens: 100 },
      latencyMs: 800,
    });

    const result = await evaluator.evaluate(testText, testGrade);

    expect(result.score).toBe('Very complex');
    expect(result.reasoning).toContain('hydraulic systems');
    expect(result.metadata.model).toBe('google:gemini-3-flash-preview');
    expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
    expect(result.metadata.inputTokens).toBe(200);
    expect(result.metadata.outputTokens).toBe(100);

    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(1);
    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0];
    expect(call[0].messages[1].content).toContain(testText);
    expect(call[0].messages[1].content).toContain(testGrade);
    expect(call[0].schema).toBeDefined();
    expect(call[0].temperature).toBe(0);
  });

  it('should reflect modelOverride in metadata.model', async () => {
    const overrideEvaluator = new BackgroundKnowledgeDemandsEvaluator({
      anthropicApiKey: 'test-key',
      modelOverride: { provider: Provider.Anthropic, model: 'claude-haiku-4-5-20251001' },
      telemetry: false,
    });
    // @ts-expect-error Accessing private property for testing
    const overrideProvider: LLMProvider = overrideEvaluator.provider;

    vi.mocked(overrideProvider.generateStructured).mockResolvedValue({
      data: {
        identified_topics: ['biology'],
        curriculum_check: 'Standard.',
        assumptions_and_scaffolding: 'None.',
        friction_analysis: 'Low.',
        complexity_score: 'Slightly complex',
        reasoning: 'Simple text.',
      },
      model: 'claude-haiku-4-5-20251001',
      usage: { inputTokens: 150, outputTokens: 50 },
      latencyMs: 400,
    });

    const result = await overrideEvaluator.evaluate(
      'The mitochondria is the powerhouse of the cell.', '5'
    );

    expect(result.metadata.model).toBe('anthropic:claude-haiku-4-5-20251001');
  });

  it('should propagate LLM API errors', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValue(new Error('API timeout'));

    await expect(evaluator.evaluate('The mitochondria is the powerhouse of the cell.', '5'))
      .rejects.toThrow('API timeout');
  });

  it('should not call provider when input validation fails', async () => {
    await expect(evaluator.evaluate('', '5')).rejects.toThrow();
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('should pass all _internal fields through from LLM response', async () => {
    const mockData = {
      identified_topics: ['biology', 'cells'],
      curriculum_check: 'Standard K-8 curriculum.',
      assumptions_and_scaffolding: 'Assumes basic biology knowledge.',
      friction_analysis: 'Difficulty mainly from vocabulary.',
      complexity_score: 'Moderately complex' as const,
      reasoning: 'Detailed reasoning here.',
    };

    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      data: mockData,
      model: 'gemini-3-flash-preview',
      usage: { inputTokens: 200, outputTokens: 100 },
      latencyMs: 800,
    });

    const result = await evaluator.evaluate('The mitochondria is the powerhouse of the cell.', '5');

    expect(result._internal).toEqual(mockData);
  });
});
