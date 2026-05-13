import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SentenceStructureEvaluator } from '../../../src/evaluators/sentence-structure.js';
import { ConfigurationError } from '../../../src/errors.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * Comprehensive unit tests for SentenceStructureEvaluator
 *
 * These tests verify:
 * - Constructor validation
 * - Successful evaluation flow (both stages)
 * - Error handling (LLM failures)
 * - Telemetry behavior
 * - Response structure
 */

// Helper to create minimal valid sentence analysis mock
const createMockSentenceAnalysis = () => ({
  reasoning: 'Mock analysis',
  num_sentences: 2,
  num_words: 10,
  flesch_kincaid_grade: 3.5,
  num_simple_sentences: 2,
  num_compound_sentences: 0,
  num_complex_sentences: 0,
  num_compound_complex_sentences: 0,
  num_other_sentences: 0,
  num_independent_clauses: 2,
  num_subordinate_clauses: 0,
  num_total_clauses: 2,
  num_sentences_with_subordinate: 0,
  num_sentences_with_multiple_subordinates: 0,
  num_sentences_with_embedded_clauses: 0,
  num_prepositional_phrases: 1,
  num_participle_phrases: 0,
  num_appositive_phrases: 0,
  num_simple_transitions: 0,
  num_sophisticated_transitions: 0,
  words_in_simple_sentences: 10,
  words_in_compound_sentences: 0,
  words_in_complex_sentences: 0,
  words_in_compound_complex_sentences: 0,
  words_in_other_sentences: 0,
  sentence_word_counts: [5, 5],
  num_one_concept_sentences: 2,
  num_multi_concept_sentences: 0,
  num_cleft_sentences: 0,
  max_clauses_in_any_sentence: 1,
  num_compound: 0,
  num_basic_complex: 0,
  num_advanced_complex: 0,
  percentage_simple: 100,
  percentage_compound: 0,
  percentage_basic_complex: 0,
  percentage_advanced_complex: 0,
});

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

describe('SentenceStructureEvaluator - Constructor Validation', () => {
  it('should throw ConfigurationError when OpenAI API key is missing', () => {
    expect(() => new SentenceStructureEvaluator({
      openaiApiKey: '',
    })).toThrow(ConfigurationError);
  });

});

describe('SentenceStructureEvaluator - Evaluation Flow', () => {
  let evaluator: SentenceStructureEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();

    // Create evaluator (providers will be mocked)
    evaluator = new SentenceStructureEvaluator({
      openaiApiKey: 'test-openai-key',
      telemetry: false,
    });

    // Both stages share a single provider instance
    // @ts-expect-error Accessing private property for testing
    mockProvider = evaluator.provider;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Successful Evaluation Flow', () => {
    it('should successfully evaluate text through both stages', async () => {
      const testText = 'The cat sat on the mat. It was sleeping peacefully.';
      const testGrade = '3';

      // Stage 1: sentence analysis, Stage 2: complexity classification — same provider
      vi.mocked(mockProvider.generateStructured)
        .mockResolvedValueOnce({
          data: createMockSentenceAnalysis(),
          model: 'gpt-4o',
          usage: { inputTokens: 150, outputTokens: 100 },
          latencyMs: 600,
        })
        .mockResolvedValueOnce({
          data: {
            answer: 'Slightly complex',
            reasoning: 'The text uses simple sentence structures appropriate for third grade.',
          },
          model: 'gpt-4o',
          usage: { inputTokens: 250, outputTokens: 80 },
          latencyMs: 500,
        });

      // Execute evaluation
      const result = await evaluator.evaluate(testText, testGrade);

      // Verify result structure
      expect(result.score).toBe('Slightly complex');
      expect(result.reasoning).toContain('simple sentence structures');
      expect(result.metadata).toBeDefined();
      expect(result.metadata.model).toBe('openai:gpt-4o');
      expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
      // Token usage is aggregated across both stages: stage 1 (150/100) + stage 2 (250/80)
      expect(result.metadata.inputTokens).toBe(400);
      expect(result.metadata.outputTokens).toBe(180);

      // Verify provider was called twice (once per stage)
      expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);

      // Verify internal data structure
      expect(result._internal).toBeDefined();
      expect(result._internal?.sentenceAnalysis).toBeDefined();
      expect(result._internal?.features).toBeDefined();
      expect(result._internal?.complexity).toBeDefined();
    });
  });

  describe('Error Handling', () => {
    it('should handle sentence analysis API failure', async () => {
      const testText = 'Test text here for API failure';
      const testGrade = '3';

      // Stage 1 fails — stage 2 should never be reached
      vi.mocked(mockProvider.generateStructured).mockRejectedValueOnce(
        new Error('API timeout')
      );

      // Should propagate the error
      await expect(evaluator.evaluate(testText, testGrade))
        .rejects.toThrow('API timeout');

      // Provider called once (stage 1 only)
      expect(mockProvider.generateStructured).toHaveBeenCalledTimes(1);
    });

    it('should handle complexity classification API failure', async () => {
      const testText = 'Test text here for complexity failure';
      const testGrade = '5';

      // Stage 1 succeeds, stage 2 fails
      vi.mocked(mockProvider.generateStructured)
        .mockResolvedValueOnce({
          data: createMockSentenceAnalysis(),
          model: 'gpt-4o',
          usage: { inputTokens: 150, outputTokens: 100 },
          latencyMs: 600,
        })
        .mockRejectedValueOnce(new Error('Schema validation failed'));

      // Should propagate the error
      await expect(evaluator.evaluate(testText, testGrade))
        .rejects.toThrow('Schema validation failed');

      // Provider called twice (stage 1 completed, stage 2 failed)
      expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);
    });

  });

  describe('Response Structure', () => {
    it('should return correct result structure', async () => {
      vi.mocked(mockProvider.generateStructured)
        .mockResolvedValueOnce({
          data: createMockSentenceAnalysis(),
          model: 'gpt-4o',
          usage: { inputTokens: 150, outputTokens: 100 },
          latencyMs: 600,
        })
        .mockResolvedValueOnce({
          data: {
            answer: 'Moderately complex',
            reasoning: 'Detailed reasoning here',
          },
          model: 'gpt-4o',
          usage: { inputTokens: 250, outputTokens: 80 },
          latencyMs: 500,
        });

      const result = await evaluator.evaluate('Test text here', '5');

      // Verify result structure
      expect(result).toHaveProperty('score');
      expect(result).toHaveProperty('reasoning');
      expect(result).toHaveProperty('metadata');
      expect(result).toHaveProperty('_internal');

      // Verify metadata structure
      expect(result.metadata).toHaveProperty('model');
      expect(result.metadata).toHaveProperty('processingTimeMs');

      // Verify metadata values
      expect(result.metadata.model).toBe('openai:gpt-4o');
      expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
      expect(result.metadata.inputTokens).toBe(400);
      expect(result.metadata.outputTokens).toBe(180);
    });
  });
});
