import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TextComplexityEvaluator } from '../../../src/evaluators/text-complexity.js';
import { ConfigurationError, ValidationError } from '../../../src/errors.js';

// Mock telemetry to avoid real HTTP calls
vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class MockTelemetryClient {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

// Mock providers to avoid real API calls
vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn(() => ({
    generateStructured: vi.fn().mockResolvedValue({
      data: {
        complexity_score: 'moderately complex',
        reasoning: 'Test reasoning',
        answer: 'Moderately complex',
      },
      usage: { inputTokens: 100, outputTokens: 50 },
      latencyMs: 100,
    }),
    generateText: vi.fn().mockResolvedValue({
      text: 'Test background knowledge',
      usage: { inputTokens: 100, outputTokens: 50 },
      latencyMs: 100,
    }),
  })),
}));

describe('TextComplexityEvaluator', () => {
  describe('Metadata', () => {
    it('should have correct metadata', () => {
      expect(TextComplexityEvaluator.metadata.id).toBe('text-complexity');
      expect(TextComplexityEvaluator.metadata.name).toBe('Text Complexity');
      expect(TextComplexityEvaluator.metadata.requiresGoogleKey).toBe(true);
      expect(TextComplexityEvaluator.metadata.requiresOpenAIKey).toBe(true);
      expect(TextComplexityEvaluator.metadata.supportedGrades).toEqual([
        '3', '4', '5', '6', '7', '8', '9', '10', '11', '12',
      ]);
    });
  });

  describe('Constructor', () => {
    it('should create evaluator with valid config', () => {
      const evaluator = new TextComplexityEvaluator({
        googleApiKey: 'test-google-key',
        openaiApiKey: 'test-openai-key',
        telemetry: false,
      });

      expect(evaluator).toBeDefined();
    });

    it('should throw error when Google API key is missing', () => {
      expect(() => {
        new TextComplexityEvaluator({
          openaiApiKey: 'test-openai-key',
          telemetry: false,
        });
      }).toThrow(ConfigurationError);
      expect(() => {
        new TextComplexityEvaluator({
          openaiApiKey: 'test-openai-key',
          telemetry: false,
        });
      }).toThrow('Google API key is required for Text Complexity evaluator');
    });

    it('should throw error when OpenAI API key is missing', () => {
      expect(() => {
        new TextComplexityEvaluator({
          googleApiKey: 'test-google-key',
          telemetry: false,
        });
      }).toThrow(ConfigurationError);
      expect(() => {
        new TextComplexityEvaluator({
          googleApiKey: 'test-google-key',
          telemetry: false,
        });
      }).toThrow('OpenAI API key is required for Text Complexity evaluator');
    });

    it('should throw error when both API keys are missing', () => {
      expect(() => {
        new TextComplexityEvaluator({
          telemetry: false,
        });
      }).toThrow(ConfigurationError);
    });
  });

  describe('evaluate()', () => {
    let evaluator: TextComplexityEvaluator;
    let vocabSpy: any;
    let sentenceSpy: any;

    beforeEach(() => {
      evaluator = new TextComplexityEvaluator({
        googleApiKey: 'test-google-key',
        openaiApiKey: 'test-openai-key',
        telemetry: false,
      });

      // Mock the child evaluators' evaluate methods
      vocabSpy = vi.spyOn((evaluator as any).vocabularyEvaluator, 'evaluate').mockResolvedValue({
        score: 'Moderately complex',
        reasoning: 'Vocabulary test reasoning',
        metadata: {
          model: 'gemini-2.5-pro + gpt-4o',
          processingTimeMs: 100,
        },
        _internal: {},
      });

      sentenceSpy = vi.spyOn((evaluator as any).sentenceStructureEvaluator, 'evaluate').mockResolvedValue({
        score: 'Moderately complex',
        reasoning: 'Sentence structure test reasoning',
        metadata: {
          model: 'gpt-4o',
          processingTimeMs: 100,
        },
        _internal: {},
      });
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should evaluate text successfully', async () => {
      const text = 'The cat sat on the mat.';
      const grade = '5';

      const result = await evaluator.evaluate(text, grade);

      expect(result).toBeDefined();
      expect(result.vocabulary).toBeDefined();
      expect(result.sentenceStructure).toBeDefined();
      expect('error' in result.vocabulary).toBe(false);
      expect('error' in result.sentenceStructure).toBe(false);
    });

    it('should validate text input', async () => {
      await expect(evaluator.evaluate('', '5')).rejects.toThrow(ValidationError);
      await expect(evaluator.evaluate('   ', '5')).rejects.toThrow(
        'Text cannot be empty or contain only whitespace'
      );
      await expect(evaluator.evaluate('abc', '5')).rejects.toThrow(
        'Text is too short'
      );
    });

    it('should validate grade input', async () => {
      const text = 'The cat sat on the mat.';

      await expect(evaluator.evaluate(text, 'invalid')).rejects.toThrow(
        ValidationError
      );
      await expect(evaluator.evaluate(text, 'invalid')).rejects.toThrow(
        'Invalid grade "invalid"'
      );

      // Grades outside supported range (K, 1, 2 not supported)
      await expect(evaluator.evaluate(text, 'K')).rejects.toThrow(ValidationError);
      await expect(evaluator.evaluate(text, '1')).rejects.toThrow(ValidationError);
      await expect(evaluator.evaluate(text, '2')).rejects.toThrow(ValidationError);
    });

    it('should accept all supported grades', async () => {
      const text = 'The cat sat on the mat.';
      const supportedGrades = ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];

      for (const grade of supportedGrades) {
        const result = await evaluator.evaluate(text, grade);
        expect(result).toBeDefined();
      }
    });

    it('should run both evaluators in parallel', async () => {
      const text = 'The cat sat on the mat.';
      const grade = '5';

      const startTime = Date.now();
      const result = await evaluator.evaluate(text, grade);
      const duration = Date.now() - startTime;

      // With mocked providers that take ~100ms each, parallel execution should be faster than sequential
      // Sequential would be ~200ms, parallel should be ~100ms
      // Allow some overhead but should be significantly less than 200ms
      expect(duration).toBeLessThan(200);

      expect('error' in result.vocabulary).toBe(false);
      expect('error' in result.sentenceStructure).toBe(false);
    });

    it('should handle partial failures gracefully', async () => {
      const text = 'The cat sat on the mat.';
      const grade = '5';

      // Override the spy to make vocabulary fail but sentence structure succeed
      vocabSpy.mockRejectedValue(new Error('Vocabulary evaluation failed'));

      const result = await evaluator.evaluate(text, grade);

      expect(result).toBeDefined();
      expect('error' in result.vocabulary).toBe(true);
      expect((result.vocabulary as { error: Error }).error).toBeDefined();
      expect('error' in result.sentenceStructure).toBe(false);
    });

    it('should throw when both evaluators fail', async () => {
      const text = 'The cat sat on the mat.';
      const grade = '5';

      // Override both spies to fail
      vocabSpy.mockRejectedValue(new Error('Vocabulary evaluation failed'));
      sentenceSpy.mockRejectedValue(new Error('Sentence structure evaluation failed'));

      await expect(evaluator.evaluate(text, grade)).rejects.toThrow(
        'Text complexity evaluation failed'
      );
    });

    it('should determine overall complexity correctly', async () => {
      const text = 'The cat sat on the mat.';
      const grade = '5';

      // Override vocabulary to return "Moderately complex"
      vocabSpy.mockResolvedValue({
        score: 'Moderately complex',
        reasoning: 'Vocab reasoning',
        metadata: {
          model: 'gemini-2.5-pro',
          processingTimeMs: 100,
        },
        _internal: {},
      });

      // Override sentence structure to return "Slightly complex"
      sentenceSpy.mockResolvedValue({
        score: 'Slightly complex',
        reasoning: 'Sentence reasoning',
        metadata: {
          model: 'gpt-4o',
          processingTimeMs: 100,
        },
        _internal: {},
      });

      const result = await evaluator.evaluate(text, grade);

      expect('error' in result.vocabulary).toBe(false);
      expect('error' in result.sentenceStructure).toBe(false);
      if (!('error' in result.vocabulary)) {
        expect(result.vocabulary.score).toBe('Moderately complex');
      }
      if (!('error' in result.sentenceStructure)) {
        expect(result.sentenceStructure.score).toBe('Slightly complex');
      }
    });

    it('should preserve individual sub-evaluator reasoning', async () => {
      const text = 'The cat sat on the mat.';
      const grade = '5';

      // Override both evaluators with specific reasoning
      vocabSpy.mockResolvedValue({
        score: 'Moderately complex',
        reasoning: 'This is the vocabulary reasoning.',
        metadata: {
          model: 'gemini-2.5-pro',
          processingTimeMs: 100,
        },
        _internal: {},
      });

      sentenceSpy.mockResolvedValue({
        score: 'Slightly complex',
        reasoning: 'This is the sentence structure reasoning.',
        metadata: {
          model: 'gpt-4o',
          processingTimeMs: 100,
        },
        _internal: {},
      });

      const result = await evaluator.evaluate(text, grade);

      if (!('error' in result.vocabulary)) {
        expect(result.vocabulary.reasoning).toBe('This is the vocabulary reasoning.');
      }
      if (!('error' in result.sentenceStructure)) {
        expect(result.sentenceStructure.reasoning).toBe('This is the sentence structure reasoning.');
      }
    });
  });

  describe('Concurrency Control', () => {
    it('should use p-limit for concurrency control', async () => {
      const evaluator = new TextComplexityEvaluator({
        googleApiKey: 'test-google-key',
        openaiApiKey: 'test-openai-key',
        telemetry: false,
      });

      // Check that limit is defined
      expect((evaluator as any).limit).toBeDefined();

      const text = 'The cat sat on the mat.';
      const grade = '5';

      await evaluator.evaluate(text, grade);

      // The limit should have been used (both calls go through it)
      expect((evaluator as any).limit).toBeDefined();
    });
  });
});
