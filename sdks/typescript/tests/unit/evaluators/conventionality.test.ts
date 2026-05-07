import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ConventionalityEvaluator } from '../../../src/evaluators/conventionality.js';
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

describe('ConventionalityEvaluator - Constructor Validation', () => {
  it('should throw with specific message when Google API key is missing', () => {
    expect(() => new ConventionalityEvaluator({ googleApiKey: '' })).toThrow(
      'Google API key is required for Conventionality evaluator. Pass googleApiKey in config.'
    );
  });
});

describe('ConventionalityEvaluator - Metadata', () => {
  it('should have correct metadata', () => {
    expect(ConventionalityEvaluator.metadata.id).toBe('conventionality');
    expect(ConventionalityEvaluator.metadata.name).toBe('Conventionality');
    expect(ConventionalityEvaluator.metadata.defaultProviders).toEqual(['google']);
    expect(ConventionalityEvaluator.metadata.supportedGrades).toEqual([
      '3', '4', '5', '6', '7', '8', '9', '10', '11', '12',
    ]);
  });
});

describe('ConventionalityEvaluator - Evaluation Flow', () => {
  let evaluator: ConventionalityEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();

    evaluator = new ConventionalityEvaluator({
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
    const testText = 'The author uses sustained irony throughout to critique the hypocrisy of civilized society by comparing it to so-called primitive customs.';
    const testGrade = '10';

    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      data: {
        conventionality_features: [
          'sustained irony: "I know of no savage custom or habit of thought which has not its mate in civilized countries"',
          'implicit comparison requiring inference',
        ],
        grade_context: 'Sustained irony and abstract social critique exceed typical Grade 10 expectations.',
        instructional_insights: 'Pre-teach the rhetorical device of irony; discuss the author\'s implied argument before reading.',
        complexity_score: 'Very complex',
        reasoning: 'The text relies heavily on sustained irony and implicit comparisons that require readers to infer the author\'s critical stance.',
      },
      model: 'gemini-3-flash-preview',
      usage: { inputTokens: 250, outputTokens: 120 },
      latencyMs: 900,
    });

    const result = await evaluator.evaluate(testText, testGrade);

    expect(result.score).toBe('Very complex');
    expect(result.reasoning).toContain('irony');
    expect(result.metadata.model).toBe('google:gemini-3-flash-preview');
    expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);

    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(1);
    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0];
    expect(call[0].messages[1].content).toContain(testText);
    expect(call[0].messages[1].content).toContain(testGrade);
    expect(call[0].schema).toBeDefined();
    expect(call[0].temperature).toBe(0);
  });

  it('should propagate LLM API errors', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValue(new Error('API timeout'));

    await expect(
      evaluator.evaluate('The cat sat on the mat outside.', '5')
    ).rejects.toThrow('API timeout');
  });

  it('should not call provider when input validation fails', async () => {
    await expect(evaluator.evaluate('', '5')).rejects.toThrow();
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('should pass all _internal fields through from LLM response', async () => {
    const mockData = {
      conventionality_features: ['literal narrative', 'concrete actions'],
      grade_context: 'Text uses mostly literal, accessible language for Grade 5.',
      instructional_insights: 'No special scaffolding needed for conventionality.',
      complexity_score: 'Slightly complex' as const,
      reasoning: 'The text is largely explicit and literal with minimal figurative language.',
    };

    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      data: mockData,
      model: 'gemini-3-flash-preview',
      usage: { inputTokens: 180, outputTokens: 90 },
      latencyMs: 700,
    });

    const result = await evaluator.evaluate('Clouds form when water evaporates and rises into the sky.', '5');

    expect(result._internal).toEqual(mockData);
    expect(result._internal?.conventionality_features).toEqual(['literal narrative', 'concrete actions']);
    expect(result._internal?.grade_context).toBe('Text uses mostly literal, accessible language for Grade 5.');
    expect(result._internal?.instructional_insights).toBe('No special scaffolding needed for conventionality.');
  });

  it('should include fk_score in user prompt', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      data: {
        conventionality_features: ['figurative language'],
        grade_context: 'Appropriate for grade 7.',
        instructional_insights: 'Discuss metaphors before reading.',
        complexity_score: 'Moderately complex',
        reasoning: 'Some figurative language present.',
      },
      model: 'gemini-3-flash-preview',
      usage: { inputTokens: 200, outputTokens: 100 },
      latencyMs: 800,
    });

    const testText = 'The minutes crept by as the castle grew into its place in the fog-shrouded distance.';
    await evaluator.evaluate(testText, '7');

    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0];
    // The user prompt should contain the FK score (a number)
    expect(call[0].messages[1].content).toMatch(/\d+(\.\d+)?/);
  });
});
