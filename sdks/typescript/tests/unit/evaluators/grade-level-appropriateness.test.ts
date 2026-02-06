import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { GradeLevelAppropriatenessEvaluator } from '../../../src/evaluators/grade-level-appropriateness.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * Comprehensive unit tests for GradeLevelAppropriatenessEvaluator
 *
 * These tests verify:
 * - Constructor validation
 * - Successful evaluation flow (single stage)
 * - Error handling (LLM failures)
 * - Telemetry behavior
 * - Response structure
 */

// Mock providers
const createMockProvider = (): LLMProvider => ({
  generateStructured: vi.fn(),
  generateText: vi.fn(),
});

// Mock the createProvider factory
vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn(() => createMockProvider()),
}));

// Mock telemetry to avoid real HTTP calls
vi.mock('../../../src/telemetry/client.js', () => {
  return {
    TelemetryClient: class MockTelemetryClient {
      send = vi.fn().mockResolvedValue(undefined);
    },
  };
});

describe('GradeLevelAppropriatenessEvaluator - Constructor Validation', () => {
  it('should throw error when Google API key is missing', () => {
    expect(() => new GradeLevelAppropriatenessEvaluator({
      googleApiKey: '',
    })).toThrow('Google API key is required. Pass googleApiKey in config.');
  });

});

describe('GradeLevelAppropriatenessEvaluator - Evaluation Flow', () => {
  let evaluator: GradeLevelAppropriatenessEvaluator;
  let mockProvider: LLMProvider;

  beforeEach(() => {
    vi.clearAllMocks();

    // Create evaluator (provider will be mocked)
    evaluator = new GradeLevelAppropriatenessEvaluator({
      googleApiKey: 'test-google-key',
      telemetry: false,
    });

    // Get reference to the mocked provider
    // @ts-expect-error Accessing private property for testing
    mockProvider = evaluator.provider;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Successful Evaluation Flow', () => {
    it('should successfully evaluate text', async () => {
      const testText = 'Tides are the rise and fall of sea levels caused by the combined effects of the gravitational forces exerted by the Moon and the Sun.';

      // Mock grade level response
      vi.mocked(mockProvider.generateStructured).mockResolvedValue({
        data: {
          grade: '6-8',
          alternative_grade: '4-5',
          scaffolding_needed: [
            'Pre-teach gravitational forces',
            'Use visual diagrams of moon-sun-earth system',
          ],
          reasoning: 'The text discusses gravitational forces and celestial mechanics, which are appropriate for middle school science curriculum.',
        },
        model: 'gemini-2.5-pro',
        usage: {
          inputTokens: 200,
          outputTokens: 150,
        },
        latencyMs: 800,
      });

      // Execute evaluation (no grade parameter needed)
      const result = await evaluator.evaluate(testText);

      // Verify result structure
      expect(result.score).toBeDefined();
      expect(result.score.grade).toBe('6-8');
      expect(result.score.alternative_grade).toBe('4-5');
      expect(result.score.scaffolding_needed).toHaveLength(2);
      expect(result.reasoning).toContain('gravitational forces');
      expect(result.metadata).toBeDefined();
      expect(result.metadata.model).toBe('gemini-2.5-pro');
      expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);

      // Verify provider was called
      expect(mockProvider.generateStructured).toHaveBeenCalledTimes(1);
    });

  });

  describe('Error Handling', () => {
    it('should handle API failure', async () => {
      const testText = 'Test text here for API failure';

      // Mock API failure
      vi.mocked(mockProvider.generateStructured).mockRejectedValue(
        new Error('API timeout')
      );

      // Should propagate the error
      await expect(evaluator.evaluate(testText))
        .rejects.toThrow('API timeout');
    });

  });

  describe('Response Structure', () => {
    it('should return correct result structure', async () => {
      vi.mocked(mockProvider.generateStructured).mockResolvedValue({
        data: {
          grade: '9-10',
          alternative_grade: '6-8',
          scaffolding_needed: [
            'Pre-teach advanced vocabulary',
            'Provide background context',
          ],
          reasoning: 'Detailed reasoning about grade appropriateness',
        },
        model: 'gemini-2.5-pro',
        usage: { inputTokens: 200, outputTokens: 150 },
        latencyMs: 800,
      });

      const result = await evaluator.evaluate('Test text here');

      // Verify result structure
      expect(result).toHaveProperty('score');
      expect(result).toHaveProperty('reasoning');
      expect(result).toHaveProperty('metadata');

      // Verify score structure (GradeLevelAppropriateness)
      expect(result.score).toHaveProperty('grade');
      expect(result.score).toHaveProperty('alternative_grade');
      expect(result.score).toHaveProperty('scaffolding_needed');
      expect(result.score).toHaveProperty('reasoning');

      // Verify metadata structure
      expect(result.metadata).toHaveProperty('promptVersion');
      expect(result.metadata).toHaveProperty('model');
      expect(result.metadata).toHaveProperty('timestamp');
      expect(result.metadata).toHaveProperty('processingTimeMs');

      // Verify metadata values
      expect(result.metadata.promptVersion).toBe('1.0');
      expect(result.metadata.model).toBe('gemini-2.5-pro');
      expect(result.metadata.timestamp).toBeInstanceOf(Date);
      expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);

      // Verify score values
      expect(result.score.grade).toBe('9-10');
      expect(result.score.alternative_grade).toBe('6-8');
      expect(result.score.scaffolding_needed).toHaveLength(2);
    });
  });
});
