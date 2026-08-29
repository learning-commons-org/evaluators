import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { GradeLevelAppropriatenessEvaluator } from '../../../src/evaluators/student-facing-text/ela-reading/grade-level-appropriateness.js';
import { ConfigurationError, InputValidationError } from '../../../src/errors.js';
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

describe('GradeLevelAppropriatenessEvaluator - Constructor Validation', () => {
  it('should throw ConfigurationError when Google API key is missing', () => {
    expect(() => new GradeLevelAppropriatenessEvaluator({
      googleApiKey: '',
    })).toThrow(ConfigurationError);
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
          grade_band: '6-8',
          alternative_grade_band: '4-5',
          scaffolding_needed: 'Pre-teach gravitational forces; Use visual diagrams of moon-sun-earth system',
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
      const result = await evaluator.evaluate({ text: testText });

      // Verify result structure
      expect(result.result.grade_band).toBe('6-8');
      expect(result.result).toBeDefined();
      expect(result.result!.grade_band).toBe('6-8');
      expect(result.result!.alternative_grade_band).toBe('4-5');
      expect(result.result!.scaffolding_needed).toContain('gravitational forces');
      expect(result.result.reasoning).toContain('gravitational forces');
      expect(result.metadata).toBeDefined();
      expect(result.metadata.model).toBe('google:gemini-2.5-pro');
      expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
      expect(result.metadata.tokenUsage.inputTokens).toBe(200);
      expect(result.metadata.tokenUsage.outputTokens).toBe(150);

      // Verify provider was called
      expect(mockProvider.generateStructured).toHaveBeenCalledTimes(1);
    });

  });

  describe('Input Validation', () => {
    it('should throw InputValidationError for empty text', async () => {
      await expect(evaluator.evaluate({ text: '' }))
        .rejects.toThrow(InputValidationError);
    });

    it('should throw InputValidationError for whitespace-only text', async () => {
      await expect(evaluator.evaluate({ text: '   ' }))
        .rejects.toThrow(InputValidationError);
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
      await expect(evaluator.evaluate({ text: testText }))
        .rejects.toThrow('API timeout');
    });

  });

  describe('Response Structure', () => {
    it('should return correct result structure', async () => {
      vi.mocked(mockProvider.generateStructured).mockResolvedValue({
        data: {
          grade_band: '9-10',
          alternative_grade_band: '6-8',
          scaffolding_needed: 'Pre-teach advanced vocabulary; Provide background context',
          reasoning: 'Detailed reasoning about grade appropriateness',
        },
        model: 'gemini-2.5-pro',
        usage: { inputTokens: 200, outputTokens: 150 },
        latencyMs: 800,
      });

      const result = await evaluator.evaluate({ text: 'Test text here' });

      // Verify result structure
      expect(result).toHaveProperty('evaluator');
      expect(result).toHaveProperty('result');
      expect(result).toHaveProperty('metadata');
      expect(result).not.toHaveProperty('score');

      // Verify score is the grade string
      expect(result.result.grade_band).toBe('9-10');

      // Verify _internal structure (GradeLevelAppropriateness)
      expect(result.result).toHaveProperty('grade_band');
      expect(result.result).toHaveProperty('alternative_grade_band');
      expect(result.result).toHaveProperty('scaffolding_needed');
      expect(result.result).toHaveProperty('reasoning');

      // Verify metadata structure
      expect(result.metadata).toHaveProperty('model');
      expect(result.metadata).toHaveProperty('processingTimeMs');

      // Verify metadata values
      expect(result.metadata.model).toBe('google:gemini-2.5-pro');
      expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
      expect(result.metadata.tokenUsage.inputTokens).toBe(200);
      expect(result.metadata.tokenUsage.outputTokens).toBe(150);

      // Verify _internal values
      expect(result.result!.grade_band).toBe('9-10');
      expect(result.result!.alternative_grade_band).toBe('6-8');
      expect(result.result!.scaffolding_needed).toBeTruthy();
    });
  });
});
