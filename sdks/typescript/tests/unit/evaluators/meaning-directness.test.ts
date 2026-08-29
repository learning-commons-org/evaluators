import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MeaningDirectnessEvaluator } from '../../../src/evaluators/student-facing-text/ela-reading/meaning-directness.js';
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

describe('MeaningDirectnessEvaluator - Constructor Validation', () => {
  it('should throw with specific message when Google API key is missing', () => {
    expect(() => new MeaningDirectnessEvaluator({ googleApiKey: '' })).toThrow(
      `Missing required credential: googleApiKey. Required by ${MeaningDirectnessEvaluator.metadata.name}.`
    );
  });
});

describe('MeaningDirectnessEvaluator - Metadata', () => {
  it('should have correct metadata', () => {
    expect(MeaningDirectnessEvaluator.metadata.id).toBe('student_facing_text.ela_reading.meaning_directness');
    expect(MeaningDirectnessEvaluator.metadata.idHistory).toContain('conventionality');
    expect(MeaningDirectnessEvaluator.metadata.defaultProviders).toEqual(['google']);
    expect(MeaningDirectnessEvaluator.metadata.supportedGrades).toEqual([
      '3', '4', '5', '6', '7', '8', '9', '10', '11', '12',
    ]);
  });
});

describe('MeaningDirectnessEvaluator - Evaluation Flow', () => {
  let evaluator: MeaningDirectnessEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();

    evaluator = new MeaningDirectnessEvaluator({
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

    const result = await evaluator.evaluate({ text: testText, grade_level: testGrade });

    expect(result.result.complexity_score).toBe('Very complex');
    expect(result.result.reasoning).toContain('irony');
    expect(result.metadata.model).toBe('google:gemini-3-flash-preview');
    expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
    expect(result.metadata.tokenUsage.inputTokens).toBe(250);
    expect(result.metadata.tokenUsage.outputTokens).toBe(120);

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
      evaluator.evaluate({ text: 'The cat sat on the mat outside.', grade_level: '5' })
    ).rejects.toThrow('API timeout');
  });

  it('should not call provider when input validation fails', async () => {
    await expect(evaluator.evaluate({ text: '', grade_level: '5' })).rejects.toThrow();
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

    const result = await evaluator.evaluate({ text: 'Clouds form when water evaporates and rises into the sky.', grade_level: '5' });

    expect(result.result).toEqual(mockData);
    expect(result.result.conventionality_features).toEqual(['literal narrative', 'concrete actions']);
    expect(result.result.grade_context).toBe('Text uses mostly literal, accessible language for Grade 5.');
    expect(result.result.instructional_insights).toBe('No special scaffolding needed for conventionality.');
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
    await evaluator.evaluate({ text: testText, grade_level: '7' });

    const call = vi.mocked(mockProvider.generateStructured).mock.calls[0];
    // The user prompt should contain the FK score (a number)
    expect(call[0].messages[1].content).toMatch(/\d+(\.\d+)?/);
  });
});
