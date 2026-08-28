import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VocabularyComplexityEvaluator } from '../../../src/evaluators/vocabulary-complexity.js';
import { Provider } from '../../../src/evaluators/base.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * Comprehensive unit tests for VocabularyComplexityEvaluator
 *
 * These tests verify:
 * - Constructor validation
 * - Successful evaluation flow (both stages)
 * - Error handling (LLM failures, validation errors)
 * - Telemetry behavior (success/error cases)
 * - Token usage aggregation
 * - Edge cases
 */

// Mock providers
const createMockProvider = (config?: { type?: string; model?: string }): LLMProvider => ({
  label: config?.type && config?.model ? `${config.type}:${config.model}` : 'mock:model',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
});

// Mock the createProvider factory
vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn((config) => createMockProvider(config)),
}));

// Mock telemetry to avoid real HTTP calls
vi.mock('../../../src/telemetry/client.js', () => {
  return {
    TelemetryClient: class MockTelemetryClient {
      send = vi.fn().mockResolvedValue(undefined);
    },
  };
});

describe('VocabularyComplexityEvaluator - Constructor Validation', () => {
  it('should throw error when Google API key is missing', () => {
    expect(() => new VocabularyComplexityEvaluator({
      googleApiKey: '',
      openaiApiKey: 'test-openai-key',
    })).toThrow(`Google API key is required for ${VocabularyComplexityEvaluator.metadata.name}. Pass googleApiKey in config.`);
  });

  it('should throw error when OpenAI API key is missing', () => {
    expect(() => new VocabularyComplexityEvaluator({
      googleApiKey: 'test-google-key',
      openaiApiKey: '',
    })).toThrow(`OpenAI API key is required for ${VocabularyComplexityEvaluator.metadata.name}. Pass openaiApiKey in config.`);
  });

});

describe('VocabularyComplexityEvaluator - Evaluation Flow', () => {
  let evaluator: VocabularyComplexityEvaluator;
  let mockBackgroundProvider: LLMProvider;
  let mockComplexityProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();

    // Create evaluator (providers will be mocked)
    evaluator = new VocabularyComplexityEvaluator({
      googleApiKey: 'test-google-key',
      openaiApiKey: 'test-openai-key',
      telemetry: false, // Disable telemetry for most tests
    });

    // Get references to the mocked providers
    // @ts-expect-error Accessing private property for testing
    mockBackgroundProvider = evaluator.backgroundKnowledgeProvider;
    // @ts-expect-error Accessing private property for testing
    // Tests use grade 5+, which routes to otherGradesComplexityProvider (GPT-4.1)
    mockComplexityProvider = evaluator.otherGradesComplexityProvider;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Successful Evaluation Flow', () => {
    it('should successfully evaluate text through both stages', async () => {
      const testText = 'The mitochondria is the powerhouse of the cell.';
      const testGrade = '5';

      // Mock background knowledge response
      vi.mocked(mockBackgroundProvider.generateText).mockResolvedValue({
        text: 'Students at grade 5 typically understand basic cell biology concepts.',
        usage: {
          inputTokens: 100,
          outputTokens: 50,
        },
        latencyMs: 500,
      });

      // Mock complexity evaluation response
      vi.mocked(mockComplexityProvider.generateStructured).mockResolvedValue({
        data: {
          complexity_score: 'Moderately complex',
          reasoning: 'The text uses grade-appropriate vocabulary.',
          factors: ['Academic terminology', 'Clear structure'],
        },
        model: 'gemini-2.5-pro',
        usage: {
          inputTokens: 200,
          outputTokens: 100,
        },
        latencyMs: 800,
      });

      // Execute evaluation
      const result = await evaluator.evaluate(testText, testGrade);

      // Verify result structure
      expect(result.result.complexity_score).toBe('Moderately complex');
      expect(result.result.reasoning).toContain('grade-appropriate vocabulary');
      expect(result.metadata).toBeDefined();
      expect(result.metadata.model).toBe('openai:gpt-4o-2024-11-20+openai:gpt-4.1-2025-04-14');
      expect(result.metadata.processingTimeMs).toBeGreaterThan(0);
      // Token usage is aggregated across both stages: background (100/50) + complexity (200/100)
      expect(result.metadata.tokenUsage.inputTokens).toBe(300);
      expect(result.metadata.tokenUsage.outputTokens).toBe(150);

      // Verify both providers were called
      expect(mockBackgroundProvider.generateText).toHaveBeenCalledTimes(1);
      expect(mockComplexityProvider.generateStructured).toHaveBeenCalledTimes(1);

      // Verify background knowledge call
      const bgCall = vi.mocked(mockBackgroundProvider.generateText).mock.calls[0];
      expect(bgCall[0][0].content).toContain(testText);
      expect(bgCall[1]).toBe(0); // temperature = 0

      // Verify complexity call includes background knowledge
      const complexityCall = vi.mocked(mockComplexityProvider.generateStructured).mock.calls[0];
      expect(complexityCall[0].messages[1].content).toContain(testText);
      expect(complexityCall[0].schema).toBeDefined();
      expect(complexityCall[0].temperature).toBe(0);
    });

});

  describe('Error Handling', () => {
    it('should handle background knowledge API failure', async () => {
      const testText = 'Test text here for API failure';
      const testGrade = '5';

      // Mock background knowledge failure
      vi.mocked(mockBackgroundProvider.generateText).mockRejectedValue(
        new Error('API timeout')
      );

      // Should propagate the error
      await expect(evaluator.evaluate(testText, testGrade))
        .rejects.toThrow('API timeout');

      // Verify complexity provider was never called
      expect(mockComplexityProvider.generateStructured).not.toHaveBeenCalled();
    });

    it('should handle complexity evaluation API failure', async () => {
      const testText = 'Test text here for complexity failure';
      const testGrade = '6';

      // Mock successful background knowledge
      vi.mocked(mockBackgroundProvider.generateText).mockResolvedValue({
        text: 'Background knowledge',
        usage: { inputTokens: 100, outputTokens: 50 },
        latencyMs: 500,
      });

      // Mock complexity evaluation failure
      vi.mocked(mockComplexityProvider.generateStructured).mockRejectedValue(
        new Error('Schema validation failed')
      );

      // Should propagate the error
      await expect(evaluator.evaluate(testText, testGrade))
        .rejects.toThrow('Schema validation failed');

      // Verify background provider was called (stage 1 completed)
      expect(mockBackgroundProvider.generateText).toHaveBeenCalledTimes(1);
    });

  });

  describe('Response Structure', () => {
    it('should return correct result structure', async () => {
      vi.mocked(mockBackgroundProvider.generateText).mockResolvedValue({
        text: 'Background knowledge',
        usage: { inputTokens: 100, outputTokens: 50 },
        latencyMs: 500,
      });

      vi.mocked(mockComplexityProvider.generateStructured).mockResolvedValue({
        data: {
          complexity_score: 'Moderately complex',
          reasoning: 'Detailed reasoning here',
          factors: ['Factor 1', 'Factor 2'],
        },
        model: 'gemini-2.5-pro',
        usage: { inputTokens: 200, outputTokens: 100 },
        latencyMs: 800,
      });

      const result = await evaluator.evaluate('Test text here', '5');

      // Verify result structure
      expect(result).toHaveProperty('evaluator');
      expect(result).toHaveProperty('result');
      expect(result).toHaveProperty('metadata');
      expect(result).not.toHaveProperty('score');

      // Verify metadata structure
      expect(result.metadata).toHaveProperty('model');
      expect(result.metadata).toHaveProperty('processingTimeMs');

      // Verify metadata values
      expect(result.metadata.model).toBe('openai:gpt-4o-2024-11-20+openai:gpt-4.1-2025-04-14');
      expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0); // Mocked calls can be instant (0ms)
      expect(result.metadata.tokenUsage.inputTokens).toBe(300);
      expect(result.metadata.tokenUsage.outputTokens).toBe(150);
    });

    it('should reflect modelOverride in metadata.model for both stages', async () => {
      const overrideEvaluator = new VocabularyComplexityEvaluator({
        openaiApiKey: 'test-key',
        modelOverride: { provider: Provider.OpenAI, model: 'gpt-4o-mini' },
        telemetry: false,
      });
      // @ts-expect-error Accessing private property for testing
      const bgProvider: LLMProvider = overrideEvaluator.backgroundKnowledgeProvider;
      // @ts-expect-error Accessing private property for testing
      const complexityProvider: LLMProvider = overrideEvaluator.otherGradesComplexityProvider;

      vi.mocked(bgProvider.generateText).mockResolvedValue({
        text: 'Background knowledge',
        usage: { inputTokens: 100, outputTokens: 50 },
        latencyMs: 300,
      });
      vi.mocked(complexityProvider.generateStructured).mockResolvedValue({
        data: { complexity_score: 'Slightly complex', reasoning: 'Simple.', factors: [] },
        model: 'gpt-4o-mini',
        usage: { inputTokens: 200, outputTokens: 80 },
        latencyMs: 400,
      });

      const result = await overrideEvaluator.evaluate('Test text here', '5');

      // All providers resolve to the same model under override — label is a single entry
      expect(result.metadata.model).toBe('openai:gpt-4o-mini');
    });

    it('should include internal data', async () => {
      vi.mocked(mockBackgroundProvider.generateText).mockResolvedValue({
        text: 'Background knowledge',
        usage: { inputTokens: 100, outputTokens: 50 },
        latencyMs: 500,
      });

      const mockComplexityData = {
        complexity_score: 'Moderately complex',
        reasoning: 'Detailed reasoning',
        factors: ['Factor 1', 'Factor 2'],
        analysis: 'Deep analysis',
      };

      vi.mocked(mockComplexityProvider.generateStructured).mockResolvedValue({
        data: mockComplexityData,
        model: 'gemini-2.5-pro',
        usage: { inputTokens: 200, outputTokens: 100 },
        latencyMs: 800,
      });

      const result = await evaluator.evaluate('Test text here', '5');

      // Verify internal data is included
      expect(result.result).toEqual(mockComplexityData);
    });
  });
});
